"""
mcp_server/media.py -- subida de imagenes de producto (extension del plan MCP, 2026-09-26).

Diseno (mismas reglas que crud.*):
- Una sola ruta destino FIJA en Django (`product-catalog-images/`): el LLM no elige URL ni host.
- El tipo se decide por la FIRMA de los bytes (PNG/JPEG/WebP), nunca por el nombre ni por un content-type declarado; el nombre se normaliza.
- Tope de tamano derivado de MCP_MAX_BODY_BYTES (la imagen viaja en base64 dentro del JSON de la Tool).
- Preview -> confirmation_token ligado al hash de los bytes; la subida exige idempotency_key. Auditoria como el resto de escrituras.
- Django sigue siendo la autoridad: valida el archivo con su propia capa de servicio y sus permisos (token del propio admin).
"""
import base64
import binascii
import hashlib
import re

from . import audit, errors, sanitize
from .django_client import ApiResponse, validate_uuid
from .errors import McpToolError

TOOL_UPLOAD = "media.upload_product_image"
RESOURCE = "product-images"
_NAME_RE = re.compile(r"[^a-z0-9._-]+")
_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def sniff(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class MediaService:
    def __init__(self, crud):
        self.crud = crud
        self.s, self.api = crud.s, crud.api

    @property
    def max_bytes(self) -> int:
        # base64 infla ~4/3 y el JSON agrega un poco: se deja margen sobre MCP_MAX_BODY_BYTES.
        return max(10_000, self.s.max_body_bytes * 3 // 4 - 4096)

    def _decode(self, image_base64: str, filename: str) -> tuple[bytes, str, str]:
        if not isinstance(image_base64, str) or not image_base64:
            raise McpToolError(errors.INVALID_ARGUMENT, "image_base64 es obligatorio.")
        if len(image_base64) > self.s.max_body_bytes:
            raise McpToolError(errors.INVALID_ARGUMENT, f"La imagen excede el limite ({self.max_bytes} bytes). Optimizala (WebP, ~800 px) antes de subirla.")
        try:
            raw = base64.b64decode(image_base64, validate=True)
        except (binascii.Error, ValueError):
            raise McpToolError(errors.INVALID_ARGUMENT, "image_base64 no es base64 valido.")
        if not raw or len(raw) > self.max_bytes:
            raise McpToolError(errors.INVALID_ARGUMENT, f"La imagen debe pesar entre 1 y {self.max_bytes} bytes.")
        mime = sniff(raw)
        if mime is None:
            raise McpToolError(errors.INVALID_ARGUMENT, "Formato no permitido: solo PNG, JPEG o WebP (se comprueba por el contenido).")
        stem = _NAME_RE.sub("-", str(filename or "imagen").lower().rsplit(".", 1)[0]).strip("-.")[:80] or "imagen"
        return raw, mime, stem + _TYPES[mime]

    @staticmethod
    def _fields(alt_text, is_primary, display_order) -> dict:
        alt = str(alt_text or "")[:255]
        order = int(display_order or 0)
        if order < 0 or order > 1000:
            raise McpToolError(errors.INVALID_ARGUMENT, "display_order fuera de rango.")
        return {"alt_text": alt, "is_primary": "true" if is_primary else "false", "display_order": str(order)}

    async def _product(self, principal, product: str) -> str:
        product = validate_uuid(product)
        await self.crud.get(principal, "products", product)  # 404/permisos los decide Django
        return product

    def _payload(self, product: str, raw: bytes, name: str, fields: dict) -> dict:
        return {"product": product, "sha256": hashlib.sha256(raw).hexdigest(), "filename": name, **fields}

    async def preview(self, principal, product, image_base64, filename, alt_text="", is_primary=False, display_order=0) -> dict:
        product = await self._product(principal, product)
        raw, mime, name = self._decode(image_base64, filename)
        fields = self._fields(alt_text, is_primary, display_order)
        payload = self._payload(product, raw, name, fields)
        meta = {"risk": "medium", "requires_confirmation": True, "executes": False,
                **self.crud.confirm.issue(principal=principal.uuid, tool=TOOL_UPLOAD, resource=RESOURCE, operation="create", target=product,
                                          payload_hash=sanitize.payload_hash(payload), version="")}
        return {"ok": True, "operation": "upload", "resource": RESOURCE, "product": product, "filename": name, "content_type": mime, "bytes": len(raw),
                "sha256": payload["sha256"], "fields": fields, "max_bytes": self.max_bytes,
                "note": "Preview: no se subio nada. media.upload_product_image exige idempotency_key y el mismo contenido.", **meta}

    async def upload(self, principal, product, image_base64, filename, idempotency_key, alt_text="", is_primary=False, display_order=0,
                     confirmation_token=None) -> dict:
        product = await self._product(principal, product)
        raw, mime, name = self._decode(image_base64, filename)
        fields = self._fields(alt_text, is_primary, display_order)
        payload = self._payload(product, raw, name, fields)
        key = self.crud._idem_key(idempotency_key, required=True)
        digest = sanitize.payload_hash(payload)
        prior = self.crud.idem.lookup(principal.uuid, TOOL_UPLOAD, key, digest)
        if prior is not None:
            audit.audit("write_replay", principal=principal.label, tool=TOOL_UPLOAD, resource=RESOURCE, operation="create", result="replay")
            return {**prior, "idempotent_replay": True}
        self.crud.confirm.verify(confirmation_token, principal=principal.uuid, tool=TOOL_UPLOAD, resource=RESOURCE, operation="create", target=product,
                                 payload_hash=digest, version="")
        audit.audit("write_attempt", principal=principal.label, tool=TOOL_UPLOAD, resource=RESOURCE, operation="create", changed_fields=list(fields) + ["image"],
                    risk="medium", confirmation="token", result="attempt")
        resp: ApiResponse = await self.api.upload_product_image(product=product, filename=name, content_type=mime, data=raw, fields=fields,
                                                                token=principal.token, request_id=audit.request_id_var.get())
        if not resp.ok:
            await self.crud._log(principal, "write_result", tool=TOOL_UPLOAD, resource=RESOURCE, operation="create", target=product, result=f"upstream_{resp.status}")
            raise self.crud._map_error(resp, "la subida de la imagen")
        record = sanitize.redact(resp.data) if isinstance(resp.data, (dict, list)) else {}
        result = {"ok": True, "operation": "upload", "resource": RESOURCE, "product": product, "record": record, "idempotent_replay": False}
        self.crud.idem.store(principal.uuid, TOOL_UPLOAD, key, digest, result)
        await self.crud._log(principal, "write_result", tool=TOOL_UPLOAD, resource=RESOURCE, operation="create", target=product,
                             changed_fields=list(fields) + ["image"], result="ok")
        return result
