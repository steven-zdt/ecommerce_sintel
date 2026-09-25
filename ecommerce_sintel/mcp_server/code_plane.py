"""
mcp_server/code_plane.py -- herramientas del plano de codigo sobre ai_editor (plan MCP, FASE 7-8). SOLO DESARROLLO.

El MCP es un adaptador: todo lo hace Django (`/api/v1/dashboard/code/...`, apagado por defecto) reusando ai_editor. Aqui no hay escritura de archivos, ni shell, ni tests.
NO existe Tool para aprobar: la decision es de un admin humano con sesion normal (Django rechaza `via=mcp`). Promover exige aprobacion humana previa + confirm=true.
"""
import re

from . import audit, errors, sanitize
from .errors import McpToolError

_CHANGE_ID = re.compile(r"^chg-[0-9a-f]{16}$")
ANALYSIS_OPS = {"symbol", "references", "impact", "resolve", "tests", "context"}
_UPSTREAM_TIMEOUT = 240.0  # generar una propuesta llama a un LLM local


def _check_id(change_id: str) -> str:
    if not isinstance(change_id, str) or not _CHANGE_ID.match(change_id):
        raise McpToolError(errors.INVALID_ARGUMENT, "change_id invalido (formato chg-<16 hex>).")
    return change_id


class CodePlane:
    def __init__(self, api):
        self.api = api

    async def _call(self, method, tail, principal, *, params=None, body=None, timeout=None) -> dict:
        resp = await self.api.call(method, tail, token=principal.token, request_id=audit.request_id_var.get(), params=params, json_body=body, timeout=timeout)
        if resp.status == 404 and isinstance(resp.data, dict) and resp.data.get("detail") == "CODE_PLANE_DISABLED":
            raise McpToolError(errors.CODE_PLANE_DISABLED, "El plano de codigo esta apagado en Django (AI_EDITOR_CODE_PLANE_ENABLED).")
        if resp.status in (401, 403):
            raise McpToolError(errors.UPSTREAM_DENIED, "Django denego la operacion.", http_status=resp.status,
                               detail=sanitize.redact(resp.data) if isinstance(resp.data, (dict, list)) else None)
        if resp.status == 404:
            raise McpToolError(errors.NOT_FOUND, "No existe (o expiro) esa propuesta.")
        if resp.status >= 500 or resp.data is None and resp.status != 204:
            raise McpToolError(errors.UPSTREAM_ERROR, "Django no pudo completar la operacion.", http_status=resp.status)
        return {"status": resp.status, "data": resp.data}

    @staticmethod
    def _wrap(result: dict, ok: bool = True, **extra) -> dict:
        payload = {"ok": ok, **extra, "data": sanitize.redact(result["data"])}
        payload["data_notice"] = sanitize.DATA_NOTICE
        return payload

    async def analysis(self, principal, op: str, query: str | None) -> dict:
        if op != "status" and op not in ANALYSIS_OPS:
            raise McpToolError(errors.INVALID_ARGUMENT, "Operacion de analisis desconocida.")
        if op != "status" and (not query or not query.strip() or len(query) > 300):
            raise McpToolError(errors.INVALID_ARGUMENT, "Falta la consulta (max 300 caracteres).")
        params = {"op": op}
        if op != "status":
            params["q"] = query.strip()
        return self._wrap(await self._call("GET", "code/analysis/", principal, params=params), op=op)

    async def propose(self, principal, request: str) -> dict:
        text = (request or "").strip()
        if not 10 <= len(text) <= 2000:
            raise McpToolError(errors.INVALID_ARGUMENT, "La peticion debe tener entre 10 y 2000 caracteres.")
        res = await self._call("POST", "code/proposals/", principal, body={"request": text}, timeout=_UPSTREAM_TIMEOUT)
        if res["status"] == 400:
            raise McpToolError(errors.INVALID_ARGUMENT, "Django rechazo la peticion.", detail=sanitize.redact(res["data"]))
        return self._wrap(res, next_step="Revisa el detalle con code.change_status. Un humano debe aprobar en el panel; el MCP no puede aprobar. Ejecuta los tests requeridos manualmente.")

    async def list_changes(self, principal) -> dict:
        return self._wrap(await self._call("GET", "code/proposals/", principal))

    async def status(self, principal, change_id: str) -> dict:
        return self._wrap(await self._call("GET", f"code/proposals/{_check_id(change_id)}/", principal))

    async def promote(self, principal, change_id: str, confirm: bool) -> dict:
        if confirm is not True:
            raise McpToolError(errors.CONFIRMATION_REQUIRED, "Promover escribe codigo: confirm=true es obligatorio y exige aprobacion humana previa.")
        res = await self._call("POST", f"code/proposals/{_check_id(change_id)}/promote/", principal, body={"confirm": True})
        return self._wrap(res, ok=res["status"] == 200, note="Sin aprobacion humana previa o con una compuerta de ai_editor sin pasar, no se promueve nada.")

    async def rollback(self, principal, change_id: str, confirm: bool) -> dict:
        if confirm is not True:
            raise McpToolError(errors.CONFIRMATION_REQUIRED, "El rollback reescribe archivos: confirm=true es obligatorio.")
        res = await self._call("POST", f"code/proposals/{_check_id(change_id)}/rollback/", principal, body={"confirm": True})
        return self._wrap(res, ok=res["status"] == 200)

    async def discard(self, principal, change_id: str) -> dict:
        await self._call("DELETE", f"code/proposals/{_check_id(change_id)}/", principal)
        return {"ok": True, "discarded": change_id}
