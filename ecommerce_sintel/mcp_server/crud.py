"""
mcp_server/crud.py -- CRUD administrativo via la API REST existente (plan MCP sec. 8-14, 26, FASES 4-5).

El MCP NO es un segundo motor de negocio: cada operacion llama al endpoint del panel (`/api/v1/dashboard/<recurso>/`) con el bearer del propio admin, asi que Django aplica su
autenticacion, permisos, validacion y capa de servicio (Commands/Selectors). Aqui NO se calculan precios, IVA, stock, envios ni transiciones de pedido.

Escrituras: preview (no ejecuta) -> confirmation_token (medio/alto) -> ejecucion con idempotency_key + expected_version (control de lost update) + auditoria.
Version = `updated_at` si el recurso lo expone; si no (p. ej. productos) un hash del JSON canonico del registro (ETag). Limite: entre releer y escribir hay una ventana
pequena (TOCTOU) porque la API de Django no admite precondiciones (If-Match); un cambio humano en esa ventana no se detectaria.
"""
import re

from . import audit, errors, sanitize
from .config import Settings
from .confirmations import Confirmations, IdempotencyStore
from .django_client import ApiResponse, DjangoAPI, validate_uuid
from .errors import McpToolError
from .limits import Limiter
from .openapi import OpenAPIIndex
from .registry import RISK_ORDER, WRITE_OPS, Resource, get_resource, require_operation

_KEY_RE = re.compile(r"^[A-Za-z0-9_\-:.]{8,128}$")
_PII_KEY = re.compile(r"(email|mail|phone|telefono|celular|address|direccion|document|cedula|nit|identification|customer|client|first_name|last_name|full_name|user\b|owner)", re.I)
PII = "[PII]"


def _mask_pii(value, depth: int = 0):
    if depth > 6:
        return value
    if isinstance(value, dict):
        return {k: (PII if _PII_KEY.search(str(k)) and not isinstance(v, (dict, list)) else _mask_pii(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_pii(v, depth + 1) for v in value]
    return value


class CrudService:
    def __init__(self, settings: Settings, api: DjangoAPI, limiter: Limiter, confirmations: Confirmations, idempotency: IdempotencyStore, openapi: OpenAPIIndex):
        self.s, self.api, self.limiter = settings, api, limiter
        self.confirm, self.idem, self.openapi = confirmations, idempotency, openapi

    # ---------- utilidades ----------
    async def _log(self, principal, event: str, **fields) -> None:
        """Auditoria de una escritura: linea JSON en los logs del MCP + copia durable en Django (SecurityEvent MCP_ACTION, best-effort)."""
        audit.audit(event, principal=principal.label, **fields)
        await self.api.report_audit(token=principal.token, request_id=audit.request_id_var.get(), payload=audit.durable_payload(event, **fields))

    def _clean(self, resource: Resource, data):
        """Salida segura: redaccion de claves sensibles, PII enmascarada en recursos sensibles y version calculada."""
        redacted = sanitize.redact(data)
        return _mask_pii(redacted) if resource.sensitive else redacted

    @staticmethod
    def _version(record) -> str:
        if isinstance(record, dict) and record.get("updated_at"):
            return "ua:" + str(record["updated_at"])
        return "h:" + sanitize.record_version(record)

    def _map_error(self, resp: ApiResponse, action: str) -> McpToolError:
        if resp.status in (401, 403):
            return McpToolError(errors.UPSTREAM_DENIED, "Django denego la operacion (autenticacion o permisos).", status=resp.status)
        if resp.status == 404:
            return McpToolError(errors.NOT_FOUND, "El registro no existe o no es visible.")
        if resp.truncated:
            return McpToolError(errors.UPSTREAM_ERROR, "La respuesta de Django excede el tamano permitido.")
        detail = sanitize.redact(resp.data) if isinstance(resp.data, (dict, list)) else None
        return McpToolError(errors.UPSTREAM_ERROR, f"Django rechazo {action} (HTTP {resp.status}).", status=resp.status, upstream=detail)

    async def _available(self, principal, resource: Resource, op: str) -> None:
        require_operation(resource, op)
        await self.openapi.ensure(principal.token, audit.request_id_var.get())
        method, path = resource.openapi_operations()[op]
        verified = self.openapi.verified(method, path)
        if verified is False or (verified is None and op in WRITE_OPS):
            raise McpToolError(errors.OPERATION_NOT_ALLOWED, f"La operacion '{op}' de '{resource.name}' no esta confirmada en el OpenAPI de Django (falla cerrado).")

    def _filters(self, resource: Resource, filters) -> dict:
        out = {}
        for key, value in (filters or {}).items():
            if key not in resource.filters:
                raise McpToolError(errors.INVALID_ARGUMENT, f"Filtro '{str(key)[:30]}' no permitido para {resource.name}.", allowed=list(resource.filters))
            if isinstance(value, bool):
                value = "true" if value else "false"
            if not isinstance(value, (str, int, float)) or len(str(value)) > 100:
                raise McpToolError(errors.INVALID_ARGUMENT, f"El filtro '{key}' debe ser un valor simple (texto/numero/booleano).")
            out[key] = value
        return out

    def _idem_key(self, key, required: bool):
        if key is None or key == "":
            if required:
                raise McpToolError(errors.IDEMPOTENCY_KEY_REQUIRED, "Esta escritura requiere idempotency_key (8-128 caracteres: letras, digitos, - _ : .).")
            return None
        if not isinstance(key, str) or not _KEY_RE.match(key):
            raise McpToolError(errors.INVALID_ARGUMENT, "idempotency_key invalida (8-128 caracteres: letras, digitos, - _ : .).")
        return key

    async def _fetch(self, principal, resource: Resource, target: str) -> dict:
        target = validate_uuid(target)
        resp = await self.api.call("GET", f"{resource.api_tail}{target}/", token=principal.token, request_id=audit.request_id_var.get())
        if not resp.ok or not isinstance(resp.data, dict):
            raise self._map_error(resp, "la lectura")
        return resp.data

    def _needs_confirmation(self, resource: Resource, op: str) -> bool:
        return RISK_ORDER[resource.risk_of(op)] >= RISK_ORDER["medium"]

    # ---------- lecturas ----------
    async def list(self, principal, resource_name, filters=None, limit=None, page=None) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "list")
        size, page_no = self.limiter.clamp_limit(limit), self.limiter.check_page(page)
        params = {"page_size": size, "page": page_no, **self._filters(resource, filters)}
        resp = await self.api.call("GET", resource.api_tail, token=principal.token, request_id=audit.request_id_var.get(), params=params)
        if not resp.ok:
            raise self._map_error(resp, "el listado")
        data = resp.data
        if isinstance(data, dict):
            rows, has_next, count = data.get("results", []), bool(data.get("next")), data.get("count")
        else:
            # ViewSet sin paginar (lista completa): el MCP pagina por su cuenta para no devolver todo el recurso de golpe.
            full = data if isinstance(data, list) else []
            start = (page_no - 1) * size
            rows, has_next, count = full[start:start + size], len(full) > start + size, len(full)
        items = [{**self._clean(resource, r), "_version": self._version(r)} if isinstance(r, dict) else self._clean(resource, r) for r in rows[:size]]
        return sanitize.untrusted_wrap({
            "ok": True, "resource": resource.name, "count": count, "page": page_no,
            "page_size": size, "has_next": has_next, "next_page": page_no + 1 if has_next else None, "items": items,
            "max_page": self.s.max_page_depth, "pii_masked": resource.sensitive})

    async def get(self, principal, resource_name, target) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "get")
        record = await self._fetch(principal, resource, target)
        return sanitize.untrusted_wrap({"ok": True, "resource": resource.name, "record": self._clean(resource, record), "version": self._version(record),
                                        "pii_masked": resource.sensitive})

    # ---------- previews (no ejecutan) ----------
    def _preview_meta(self, principal, resource: Resource, op: str, tool: str, target: str, payload, version: str = "") -> dict:
        risk = resource.risk_of(op)
        meta = {"risk": risk, "requires_confirmation": self._needs_confirmation(resource, op), "executes": False}
        if meta["requires_confirmation"]:
            meta.update(self.confirm.issue(principal=principal.uuid, tool=tool, resource=resource.name, operation=op, target=target,
                                           payload_hash=sanitize.payload_hash(payload), version=version))
        if risk == "high":
            meta["requires_explicit_confirm_flag"] = True
        return meta

    async def preview_create(self, principal, resource_name, data) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "create")
        self._check_data(data)
        meta = self._preview_meta(principal, resource, "create", "crud.create", "-", data)
        return {"ok": True, "operation": "create", "resource": resource.name, "changes": {k: {"to": self._clean_value(v)} for k, v in data.items()},
                "note": "Preview: no se escribio nada. Django validara los campos al ejecutar. crud.create exige idempotency_key.", **meta}

    async def preview_update(self, principal, resource_name, target, changes) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "update")
        self._check_data(changes)
        current = await self._fetch(principal, resource, target)
        version = self._version(current)
        diff = {k: {"from": self._clean_value(current[k]), "to": self._clean_value(v)} for k, v in changes.items() if k in current and current[k] != v}
        unchanged = [k for k, v in changes.items() if k in current and current[k] == v]
        unknown = [k for k in changes if k not in current]
        meta = self._preview_meta(principal, resource, "update", "crud.update", validate_uuid(target), changes, version)
        return {"ok": True, "operation": "update", "resource": resource.name, "target": validate_uuid(target), "changes": diff, "unchanged_fields": unchanged,
                "unknown_fields": unknown, "version": version, **meta}

    async def preview_delete(self, principal, resource_name, target) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "delete")
        current = await self._fetch(principal, resource, target)
        version = self._version(current)
        meta = self._preview_meta(principal, resource, "delete", "crud.delete", validate_uuid(target), {}, version)
        return {"ok": True, "operation": "delete", "resource": resource.name, "target": validate_uuid(target), "version": version,
                "effect": f"borrado logico ({resource.delete_semantics}-delete; no es un DELETE fisico)", "record_summary": self._summary(resource, current), **meta}

    def _summary(self, resource: Resource, record: dict) -> dict:
        keep = {k: v for k, v in record.items() if k in ("uuid", "id", "name", "sku", "slug", "is_active", "status", "title")}
        return self._clean(resource, keep)

    def _clean_value(self, value):
        return sanitize.redact({"v": value})["v"]

    def _check_data(self, data) -> None:
        if not isinstance(data, dict) or not data:
            raise McpToolError(errors.INVALID_ARGUMENT, "data/changes debe ser un objeto con al menos un campo.")
        if any(not isinstance(k, str) or len(k) > 60 for k in data):
            raise McpToolError(errors.INVALID_ARGUMENT, "Los nombres de campo deben ser texto corto.")
        self.limiter.check_payload(data)

    # ---------- escrituras ----------
    def _guard_write(self, principal, resource: Resource, op: str, tool: str, target: str, payload, version: str, token, confirm_flag) -> str:
        risk = resource.risk_of(op)
        # El flag de riesgo alto se comprueba ANTES de consumir la ficha: un olvido de confirm=true no debe quemar el confirmation_token.
        if risk == "high" and confirm_flag is not True:
            raise McpToolError(errors.CONFIRMATION_REQUIRED, "Operacion de riesgo alto: pasa confirm=true ademas del confirmation_token.")
        if self._needs_confirmation(resource, op):
            self.confirm.verify(token, principal=principal.uuid, tool=tool, resource=resource.name, operation=op, target=target,
                                payload_hash=sanitize.payload_hash(payload), version=version)
            confirmation = "token"
        else:
            confirmation = "not_required"
        return confirmation

    async def create(self, principal, resource_name, data, idempotency_key, confirmation_token=None, confirm=False) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "create")
        self._check_data(data)
        key = self._idem_key(idempotency_key, required=True)
        digest = sanitize.payload_hash(data)
        prior = self.idem.lookup(principal.uuid, "crud.create:" + resource.name, key, digest)
        if prior is not None:
            audit.audit("write_replay", principal=principal.label, tool="crud.create", resource=resource.name, operation="create", result="replay")
            return {**prior, "idempotent_replay": True}
        confirmation = self._guard_write(principal, resource, "create", "crud.create", "-", data, "", confirmation_token, confirm)
        audit.audit("write_attempt", principal=principal.label, tool="crud.create", resource=resource.name, operation="create", changed_fields=data.keys(),
                    risk=resource.risk_of("create"), confirmation=confirmation, result="attempt")
        resp = await self.api.call("POST", resource.api_tail, token=principal.token, request_id=audit.request_id_var.get(), json_body=data)
        if not resp.ok:
            await self._log(principal, "write_result", tool="crud.create", resource=resource.name, operation="create", result=f"upstream_{resp.status}")
            raise self._map_error(resp, "la creacion")
        result = {"ok": True, "operation": "create", "resource": resource.name, "record": self._clean(resource, resp.data), "version": self._version(resp.data),
                  "idempotent_replay": False}
        self.idem.store(principal.uuid, "crud.create:" + resource.name, key, digest, result)
        await self._log(principal, "write_result", tool="crud.create", resource=resource.name, operation="create",
                    target=str((resp.data or {}).get("uuid", "-")) if isinstance(resp.data, dict) else "-", changed_fields=data.keys(), result="ok")
        return result

    async def update(self, principal, resource_name, target, changes, expected_version, idempotency_key=None, confirmation_token=None, confirm=False) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "update")
        self._check_data(changes)
        target = validate_uuid(target)
        if not expected_version:
            raise McpToolError(errors.INVALID_ARGUMENT, "expected_version es obligatorio (usa el `version` de crud.get/preview_update) para evitar sobrescribir cambios ajenos.")
        key = self._idem_key(idempotency_key, required=False)
        digest = sanitize.payload_hash({"t": target, "c": changes, "v": expected_version})
        if key:
            prior = self.idem.lookup(principal.uuid, "crud.update:" + resource.name, key, digest)
            if prior is not None:
                return {**prior, "idempotent_replay": True}
        current = await self._fetch(principal, resource, target)
        version = self._version(current)
        if version != expected_version:
            await self._log(principal, "write_conflict", tool="crud.update", resource=resource.name, operation="update", target=target, result="version_conflict")
            raise McpToolError(errors.VERSION_CONFLICT, "El registro cambio desde que lo leiste: vuelve a leerlo y previsualiza de nuevo. No se escribio nada.",
                               current_version=version, current_values={k: self._clean_value(current.get(k)) for k in changes})
        confirmation = self._guard_write(principal, resource, "update", "crud.update", target, changes, version, confirmation_token, confirm)
        audit.audit("write_attempt", principal=principal.label, tool="crud.update", resource=resource.name, operation="update", target=target,
                    changed_fields=changes.keys(), risk=resource.risk_of("update"), confirmation=confirmation, result="attempt")
        resp = await self.api.call("PATCH", f"{resource.api_tail}{target}/", token=principal.token, request_id=audit.request_id_var.get(), json_body=changes)
        if not resp.ok:
            await self._log(principal, "write_result", tool="crud.update", resource=resource.name, operation="update", target=target, result=f"upstream_{resp.status}")
            raise self._map_error(resp, "la actualizacion")
        result = {"ok": True, "operation": "update", "resource": resource.name, "target": target, "record": self._clean(resource, resp.data),
                  "version": self._version(resp.data), "idempotent_replay": False}
        if key:
            self.idem.store(principal.uuid, "crud.update:" + resource.name, key, digest, result)
        await self._log(principal, "write_result", tool="crud.update", resource=resource.name, operation="update", target=target, changed_fields=changes.keys(), result="ok")
        return result

    async def delete(self, principal, resource_name, target, expected_version, idempotency_key=None, confirmation_token=None, confirm=False) -> dict:
        resource = get_resource(resource_name)
        await self._available(principal, resource, "delete")
        target = validate_uuid(target)
        if not expected_version:
            raise McpToolError(errors.INVALID_ARGUMENT, "expected_version es obligatorio (usa el `version` de crud.get/preview_delete).")
        key = self._idem_key(idempotency_key, required=False)
        digest = sanitize.payload_hash({"t": target, "v": expected_version})
        if key:
            prior = self.idem.lookup(principal.uuid, "crud.delete:" + resource.name, key, digest)
            if prior is not None:
                return {**prior, "idempotent_replay": True}
        current = await self._fetch(principal, resource, target)
        version = self._version(current)
        if version != expected_version:
            await self._log(principal, "write_conflict", tool="crud.delete", resource=resource.name, operation="delete", target=target, result="version_conflict")
            raise McpToolError(errors.VERSION_CONFLICT, "El registro cambio desde que lo leiste: vuelve a leerlo. No se borro nada.", current_version=version)
        confirmation = self._guard_write(principal, resource, "delete", "crud.delete", target, {}, version, confirmation_token, confirm)
        audit.audit("write_attempt", principal=principal.label, tool="crud.delete", resource=resource.name, operation="delete", target=target, risk=resource.risk_of("delete"),
                    confirmation=confirmation, result="attempt")
        resp = await self.api.call("DELETE", f"{resource.api_tail}{target}/", token=principal.token, request_id=audit.request_id_var.get())
        if not resp.ok:
            await self._log(principal, "write_result", tool="crud.delete", resource=resource.name, operation="delete", target=target, result=f"upstream_{resp.status}")
            raise self._map_error(resp, "el borrado")
        result = {"ok": True, "operation": "delete", "resource": resource.name, "target": target, "deleted": True, "semantics": resource.delete_semantics,
                  "idempotent_replay": False}
        if key:
            self.idem.store(principal.uuid, "crud.delete:" + resource.name, key, digest, result)
        await self._log(principal, "write_result", tool="crud.delete", resource=resource.name, operation="delete", target=target, result="ok")
        return result
