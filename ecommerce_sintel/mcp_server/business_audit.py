"""
mcp_server/business_audit.py -- `business.audit`: alineamiento entre documentacion, codigo y contrato de API (plan MCP, FASE 9). SOLO LECTURA.

Determinista y con evidencia: cada hallazgo lleva clasificacion, regla, evidencia (archivo/linea o operacion OpenAPI) y recomendacion. No usa un LLM ni escribe nada.
Clasificaciones: MATCH, INCONSISTENCY, MISSING_IMPLEMENTATION, STALE_DOCUMENTATION, DEAD_CODE, CONTRACT_DRIFT, SECURITY_GAP, UNVERIFIED (no se pudo comprobar; nunca se asume MATCH).
Alcance honesto: audita lo que el MCP puede comprobar (registro de recursos vs OpenAPI vivo, soft-delete del modelo, recursos sensibles de solo lectura, documentacion del propio MCP). No audita reglas de negocio de
dominio (precios, IVA, pedidos): eso exige leer la logica de Django y contrastarla con documentos, y queda fuera de este alcance. DEAD_CODE no se calcula todavia.
"""
from . import audit, errors, policy
from .errors import McpToolError
from .registry import RESOURCES, WRITE_OPS

SCOPES = ("all", "contract", "soft_delete", "security", "docs")
# recurso -> (archivo del modelo, clase). Solo los recursos con `delete` habilitado.
_MODELS = {"products": ("shop/models.py", "Product"), "categories": ("shop/models.py", "Category"), "brands": ("shop/models.py", "Brand"),
           "services": ("technical_services/models.py", "TechnicalService"), "service-categories": ("technical_services/models.py", "ServiceCategory"),
           "equipment": ("renting/models/equipment.py", "Equipment"), "renting-categories": ("renting/models/common.py", "RentingCategory"),
           "renting-brands": ("renting/models/common.py", "RentingBrand")}
_DOC_FILE = "mcp_server/.AGENT/TOOL_REGISTRY.md"


def _f(cls: str, rule: str, subject: str, evidence: str, recommendation: str = "") -> dict:
    return {"classification": cls, "rule": rule, "subject": subject, "evidence": evidence, "recommendation": recommendation}


class BusinessAuditor:
    def __init__(self, app):
        self.app = app

    async def run(self, principal, scope: str) -> dict:
        if scope not in SCOPES:
            raise McpToolError(errors.INVALID_ARGUMENT, "scope invalido: " + ", ".join(SCOPES))
        findings: list = []
        if scope in ("all", "contract"):
            findings += await self._contract(principal)
        if scope in ("all", "soft_delete"):
            findings += self._soft_delete()
        if scope in ("all", "security"):
            findings += self._security()
        if scope in ("all", "docs"):
            findings += self._docs()
        counts: dict = {}
        for item in findings:
            counts[item["classification"]] = counts.get(item["classification"], 0) + 1
        gaps = [i for i in findings if i["classification"] not in ("MATCH", "UNVERIFIED")]
        return {"ok": True, "scope": scope, "summary": counts, "aligned": not gaps, "findings": findings,
                "limits": "Solo comprueba registro de recursos vs OpenAPI, soft-delete de modelos, recursos sensibles y documentacion del MCP; no audita reglas de negocio de dominio."}

    async def _contract(self, principal) -> list:
        await self.app.openapi.ensure(principal.token, audit.request_id_var.get())
        out = []
        for r in RESOURCES:
            for op in r.operations:
                method, path = r.openapi_operations()[op]
                ok = self.app.openapi.verified(method, path)
                subject = f"{r.name}.{op}"
                if ok is None:
                    out.append(_f("UNVERIFIED", "R-CONTRACT", subject, "El OpenAPI de Django no se pudo cargar.", "Reintentar con Django disponible."))
                elif ok:
                    out.append(_f("MATCH", "R-CONTRACT", subject, f"{method.upper()} {path} existe en el OpenAPI."))
                else:
                    out.append(_f("CONTRACT_DRIFT", "R-CONTRACT", subject, f"{method.upper()} {path} NO existe en el OpenAPI; el registro del MCP lo declara.",
                                  "Corregir el registro (registry.py) o exponer el endpoint en Django."))
        return out

    def _soft_delete(self) -> list:
        out = []
        for r in RESOURCES:
            if "delete" not in r.operations:
                continue
            spec = _MODELS.get(r.name)
            if not spec:
                out.append(_f("UNVERIFIED", "R-SOFT-DELETE", r.name, "Sin mapeo recurso->modelo para comprobar el borrado logico.", "Anadirlo a _MODELS."))
                continue
            try:
                res = self.app.code.search("", path_scope=spec[0].rsplit("/", 1)[0], symbol=spec[1])
            except McpToolError as exc:
                out.append(_f("UNVERIFIED", "R-SOFT-DELETE", r.name, f"Plano de codigo no disponible ({exc.code}).", "Montar el workspace de solo lectura."))
                continue
            hit = next((m for m in res["matches"] if m["path"] == spec[0]), None)
            if hit is None:
                out.append(_f("MISSING_IMPLEMENTATION", "R-SOFT-DELETE", r.name, f"No se encontro la clase {spec[1]} en {spec[0]}.", "Actualizar _MODELS o el registro."))
            elif "SintelBaseModel" in hit["text"]:
                out.append(_f("MATCH", "R-SOFT-DELETE", r.name, f"{hit['path']}:{hit['line']} {hit['text']} (hereda el borrado logico de SintelBaseModel)."))
            else:
                out.append(_f("INCONSISTENCY", "R-SOFT-DELETE", r.name, f"{hit['path']}:{hit['line']} {hit['text']} no hereda de SintelBaseModel.",
                              "Confirmar que el borrado del recurso es logico antes de mantener `delete` habilitado."))
        return out

    def _security(self) -> list:
        out = []
        for r in RESOURCES:
            writes = [op for op in r.operations if op in WRITE_OPS]
            if r.sensitive and writes:
                out.append(_f("SECURITY_GAP", "R-SENSITIVE-READONLY", r.name, f"Recurso sensible con escrituras habilitadas: {writes}.", "Dejarlo de solo lectura."))
            elif r.sensitive:
                out.append(_f("MATCH", "R-SENSITIVE-READONLY", r.name, "Recurso sensible solo de lectura."))
            if r.api_tail.startswith("inventory/"):
                out.append(_f("INCONSISTENCY", "R-INVENTORY-PATH", r.name, "El inventario no vive bajo /api/v1/dashboard/inventory/.", "Usar /api/v1/inventory/stock-records/."))
        leaks = [t for t in policy.TOOL_CLASS if policy.TOOL_CLASS[t] in (policy.WRITE, policy.DESTRUCTIVE) and t in policy.PROFILE_TOOLS["READ_ONLY"]]
        for t in leaks:
            out.append(_f("SECURITY_GAP", "R-DEFAULT-PROFILE", t, "Tool de escritura incluida en el perfil READ_ONLY.", "Quitarla de READ_ONLY."))
        if not leaks:
            out.append(_f("MATCH", "R-DEFAULT-PROFILE", "READ_ONLY", "Ninguna Tool de escritura en el perfil por defecto."))
        approvals = [t for t in policy.TOOL_CLASS if any(w in t for w in ("approve", "decision", "approval"))]
        if approvals:
            out.append(_f("SECURITY_GAP", "R-NO-APPROVAL-TOOL", ",".join(approvals), "Existe una Tool de aprobacion.", "Retirarla: la decision es humana."))
        else:
            out.append(_f("MATCH", "R-NO-APPROVAL-TOOL", "tools", "No existe Tool de aprobacion de cambios."))
        return out

    def _docs(self) -> list:
        try:
            doc = self.app.code.read(_DOC_FILE)["content"]
        except McpToolError as exc:
            return [_f("UNVERIFIED", "R-DOC-TOOLS", _DOC_FILE, f"No se pudo leer la documentacion ({exc.code}).")]
        out = []
        for tool in sorted(policy.TOOL_CLASS):
            short = tool.split(".", 1)[1]
            if tool in doc or short in doc:
                out.append(_f("MATCH", "R-DOC-TOOLS", tool, f"Documentada en {_DOC_FILE}."))
            else:
                out.append(_f("STALE_DOCUMENTATION", "R-DOC-TOOLS", tool, f"La Tool existe pero no aparece en {_DOC_FILE}.", "Documentarla."))
        return out
