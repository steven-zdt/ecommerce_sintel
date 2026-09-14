"""
Bridge HTTP unico entre las Tools y Django (Fase 2 AI Core).

Regla del plan: una Tool "envuelve exclusivamente al Selector real ya
existente" -- como ai_engine corre fuera de Django, el camino fisico
sancionado (Fase 1: "nunca a los modelos directamente") son los endpoints
internos read-only /api/v1/internal/ai/* de Django, cada uno una fachada
delgada del Selector correspondiente. Este modulo es el UNICO lugar donde
las Tools hacen HTTP: reenvia el JWT del usuario, mapea errores a dicts
serializables (nunca lanza hacia el LLM) y respeta el timeout del
ToolMetadata.
"""
import logging

import httpx

from config import DJANGO_INTERNAL_API_URL, internal_django_headers

logger = logging.getLogger("tools.http_bridge")

_INTERNAL_AI_PREFIX = "/internal/ai"


def _map_response(resp: httpx.Response, url: str) -> dict:
    if resp.status_code in (200, 201):
        return resp.json()
    if resp.status_code == 404:
        return {"error": "No encontrado (o no pertenece al usuario).", "status_code": 404}
    if resp.status_code in (401, 403):
        return {"error": "Sesion invalida o sin permisos.", "status_code": resp.status_code}
    if resp.status_code == 400:
        # DRF devuelve {"error": ...} o {campo: [errores]} -- ambos utiles para
        # que el LLM pida exactamente lo que falta. Se pasa completo.
        try:
            body = resp.json()
        except Exception:
            body = {}
        detail = body.get("error") if isinstance(body, dict) else None
        return {"error": detail or body or "Parametros invalidos.", "status_code": 400}

    logger.error("[bridge] Respuesta inesperada de Django (%s) en %s: %s",
                 resp.status_code, url, resp.text[:300])
    return {"error": "Error consultando los datos.", "status_code": resp.status_code}


async def django_internal_get(token: str, path: str, params: dict | None = None,
                              timeout_ms: int = 8000) -> dict:
    """
    GET a un endpoint interno de Django reenviando el JWT del usuario.

    Devuelve el JSON del endpoint en exito; en error devuelve un dict
    {"error": ..., "status_code": ...} apto para que el LLM (Fase 3) lo
    convierta en una respuesta honesta -- una Tool nunca inventa datos.
    """
    url = f"{DJANGO_INTERNAL_API_URL}{_INTERNAL_AI_PREFIX}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            resp = await client.get(
                url,
                params=params or {},
                headers=internal_django_headers({"Authorization": f"Bearer {token}"}),
            )
    except httpx.HTTPError as exc:
        logger.error("[bridge] Django inalcanzable en %s: %s", url, exc)
        return {"error": "No se pudo consultar los datos en este momento.", "status_code": 502}
    return _map_response(resp, url)


async def django_internal_post(token: str, path: str, body: dict | None = None,
                               timeout_ms: int = 10000) -> dict:
    """
    POST a un endpoint interno de escritura (Fase 4). Mismo contrato de
    errores que el GET. La autorizacion real (permission classes) y la
    auditoria (SecurityEvent) viven en Django -- este bridge solo transporta.
    """
    url = f"{DJANGO_INTERNAL_API_URL}{_INTERNAL_AI_PREFIX}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            resp = await client.post(
                url,
                json=body or {},
                headers=internal_django_headers({"Authorization": f"Bearer {token}"}),
            )
    except httpx.HTTPError as exc:
        logger.error("[bridge] Django inalcanzable en %s: %s", url, exc)
        return {"error": "No se pudo ejecutar la accion en este momento.", "status_code": 502}
    return _map_response(resp, url)
