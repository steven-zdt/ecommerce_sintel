"""
HARDENING F22 (2026-09-25) -- Security impact gate del AI Editor.

Plan PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md secciones 26.1/26.2: el AI Editor NO puede
promover automaticamente cambios sobre autenticacion, autorizacion, politicas de Tools, kill switches, endpoints de modelo, red/Docker/nginx de
produccion, RAG, memoria o respaldos sin aprobacion humana ELEVADA. Es determinista (patrones de ruta): el LLM no participa en la decision.

Los archivos con secretos (.env, claves, certificados) siguen bloqueados por completo en `repository/sandbox.py::_SENSITIVE_PATTERNS`; esto
cubre el resto: se pueden proponer, pero promoverlos exige `ApprovalRecord.security_review_acknowledged=True`.
"""

# categoria -> fragmentos de ruta (minusculas, separador "/", con "/" inicial implicito). Coincidencia por subcadena, igual criterio que
# _SENSITIVE_PATTERNS.
SECURITY_PATH_RULES: dict[str, tuple[str, ...]] = {
    "production_config": ("docker-compose.prod", "nginx.prod", "nginx-common", "/deploy/"),
    "authentication_authorization": (
        "/accounts/", "/security/", "permissions.py", "/permissions/", "authentication", "/auth.py", "settings/production",
    ),
    "ai_tool_policy": (
        "ai_engine/tools/", "ai_engine_adk/sintel_adapter.py", "ai_engine_adk/rate_limit.py", "ai_engine_adk/idempotency.py",
        "ai_engine_adk/permissions.py",
    ),
    "kill_switches_and_model_endpoints": (
        "ai_engine/config.py", "ecommerce/settings/", "ai_engine_adk/model_runtime.py", "ai_engine_adk/admission.py", "/ai_provider/",
    ),
    "rag_policy": ("/ai_knowledge/",),
    "memory_policy": ("/customer_memory/",),
    "backup_config": ("/deploy/backup", "/deploy/restore", "/scripts/security/"),
    "ai_editor_boundary": ("/ai_editor/approval/", "/ai_editor/repository/", "/ai_editor/patch/", "/ai_editor/agent/policy.py"),
    "ai_input_output_guards": ("ai_engine_adk/input_guard.py", "ai_engine_adk/output_guard.py", "ai_engine_adk/public_response.py"),
}


def _normalize(path) -> str:
    text = str(path).replace("\\", "/").lower()
    while text.startswith("./"):
        text = text[2:]
    return "/" + text.lstrip("/")


def classify_security_impact(files) -> dict[str, list[str]]:
    """{categoria: [archivos]} para los archivos que tocan una superficie de seguridad. Vacio = no requiere revision elevada."""
    result: dict[str, list[str]] = {}
    for original in files or []:
        norm = _normalize(original)
        for category, fragments in SECURITY_PATH_RULES.items():
            if any(fragment in norm for fragment in fragments):
                result.setdefault(category, []).append(str(original))
    return result


def security_review_required(files) -> bool:
    return bool(classify_security_impact(files))


__all__ = ["SECURITY_PATH_RULES", "classify_security_impact", "security_review_required"]
