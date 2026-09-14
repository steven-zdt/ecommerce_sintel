"""
`build_prompt()` -- FASE 27 "Architecture-Aware Prompt Engine" (plan
"AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro aplicada aca: "No utilizar un prompt gigante
estatico para todo tipo de cambios. Crear estrategias segun tipo." --
`_classify_change_type()` decide una de `CHANGE_TYPES` a partir de datos
YA reales del plan (extension del archivo del target principal +
`intent.scope`, ambos ya resueltos por POST-GRAPH 2/4, cero heuristica
nueva sobre el grafo), y `_TYPE_GUIDANCE` agrega SOLO las reglas
especificas de ese tipo al prompt base -- no hay un prompt "para todo".

El prompt final es JSON estructurado (secciones explicitas, no prosa
libre) para que sea trazable: dado un `ChangeGenerationRequest`, el mismo
prompt se puede reconstruir siempre igual (determinístico), y un humano
revisando un log de auditoria puede ver EXACTAMENTE que contexto broke
recibio el LLM (FASE 48 "Generation Audit" reusara esto).
"""
import json

TYPE_BACKEND = "backend"
TYPE_FRONTEND = "frontend"
TYPE_API = "api"
TYPE_TESTS = "tests"
TYPE_DOCUMENTATION = "documentation"
TYPE_CONFIGURATION = "configuration"
TYPE_CROSS_STACK = "cross-stack"
TYPE_UNKNOWN = "unknown"

_FRONTEND_EXTENSIONS = (".vue", ".js", ".ts")
_CONFIG_MARKERS = ("docker-compose", "dockerfile", "nginx", ".env", ".yml", ".yaml")

_TYPE_GUIDANCE: dict[str, str] = {
    TYPE_BACKEND: (
        "Este cambio es BACKEND (Django). Reglas obligatorias del proyecto: "
        "cero logica de negocio en ViewSets (usar *Commands para escritura, "
        "*Selectors para lectura, ambos estaticos); nunca DELETE fisico "
        "(soft-delete via is_active/is_deleted); usar las clases de permiso "
        "reales de users/api/permissions.py, nunca rest_framework.permissions "
        "directo para reglas de negocio."
    ),
    TYPE_API: (
        "Este cambio afecta un CONTRATO de API (Endpoint/Serializer). "
        "Cualquier cambio de forma de Request/Response puede romper "
        "consumidores frontend reales -- ver 'contracts'/'frontend_consumers' "
        "en CONTRACTS/DEPENDENCIES antes de proponer un cambio de forma."
    ),
    TYPE_FRONTEND: (
        "Este cambio es FRONTEND (Vue 3). Reglas obligatorias: peticiones via "
        "composables useApi()/useAuth() reales del proyecto, nunca axios "
        "directo desde un componente; mantener el patron de Pinia store "
        "existente si el target ya usa uno."
    ),
    TYPE_TESTS: (
        "Este cambio toca un archivo de TESTS. No eliminar un test existente "
        "salvo que el CHANGE REQUEST lo pida explicitamente -- si el "
        "comportamiento cambia, declarar el test en 'tests_to_update', no "
        "borrarlo en silencio."
    ),
    TYPE_DOCUMENTATION: (
        "Este cambio toca DOCUMENTACION. Generar solo la propuesta -- no se "
        "aplica automaticamente en esta fase del sistema (ver ARCHITECTURAL "
        "RULES); preferir el mismo tono/estructura que el resto del "
        "documento real que se adjunta en CURRENT SOURCE."
    ),
    TYPE_CONFIGURATION: (
        "Este cambio toca CONFIGURACION de infraestructura (Docker/nginx/env). "
        "Maxima cautela: un error aca puede afectar todos los servicios, no "
        "solo una app -- si hay cualquier duda, declarar confidence baja."
    ),
    TYPE_CROSS_STACK: (
        "El intent declara scope tanto backend como frontend (cross-stack). "
        "Un cambio de contrato en el backend DEBE ir acompanado del ajuste "
        "correspondiente en cada consumidor frontend real listado en "
        "DEPENDENCIES -- no proponer solo el lado backend si el frontend "
        "tambien depende del comportamiento actual."
    ),
    TYPE_UNKNOWN: (
        "No se pudo clasificar el tipo de cambio con certeza -- proceder con "
        "cautela extra y declarar confidence baja si el target no es "
        "inequivocamente claro."
    ),
}

SYSTEM_PROMPT_BASE = """Sos un generador de PROPUESTAS de patch para el proyecto Sintel \
E-Commerce (Django 5 + DRF backend, Vue 3 + Pinia frontend). No aplicas cambios directamente \
-- tu unica salida es una propuesta estructurada que un pipeline separado valida, prueba en \
sandbox y un humano aprueba antes de promoverla.

REGLAS ABSOLUTAS:
1. Tu respuesta DEBE ser un unico objeto JSON valido, sin texto antes ni despues, sin bloques \
markdown ```json``` alrededor -- JSON crudo. Si no podes generar una propuesta valida con el \
contexto dado, respondelo igual como JSON con "operations": [] y explica por que en \
"reasoning_summary"/"risks".
2. Nunca modifiques un archivo que no aparezca en CHANGE PLAN o en TARGET FILES.
3. "old_content" de cada operacion debe ser una copia EXACTA de lo que ya existe en CURRENT \
SOURCE para ese rango -- si no estas seguro del contenido exacto, no propongas esa operacion.
4. No elimines codigo, tests o funcionalidad no relacionada con el CHANGE REQUEST.
5. Declara honestamente "risks"/"assumptions" -- una propuesta con riesgos declarados es mejor \
que una que los oculta.
6. El esquema de salida esperado (ver EXPECTED RESULT) es fijo -- no agregues ni quites campos.
"""


def _classify_change_type(request) -> str:
    request_dict = request.to_dict() if hasattr(request, "to_dict") else dict(request)
    plan = request_dict.get("change_plan") or {}
    steps = plan.get("steps") or []
    primary = next((s for s in steps if s.get("operation") == "MODIFY"), None)
    scope = (request_dict.get("change_intent") or {}).get("scope") or []

    if primary is None or not primary.get("file"):
        return TYPE_UNKNOWN

    file = primary["file"].lower()
    if len(set(scope)) > 1:
        return TYPE_CROSS_STACK
    if file.endswith(".md"):
        return TYPE_DOCUMENTATION
    if any(marker in file for marker in _CONFIG_MARKERS):
        return TYPE_CONFIGURATION
    if "test" in file and file.endswith(".py"):
        return TYPE_TESTS
    if file.endswith(_FRONTEND_EXTENSIONS):
        return TYPE_FRONTEND
    if "/api/" in file and file.endswith(".py"):
        return TYPE_API
    if file.endswith(".py"):
        return TYPE_BACKEND
    return TYPE_UNKNOWN


EXPECTED_RESULT_SCHEMA = {
    "proposal_id": "string unico, ej. 'gen-<uuid corto>'",
    "operations": [
        {
            "file": "string, path relativo tal como aparece en CHANGE PLAN/TARGET FILES",
            "symbol": "string o null",
            "operation": "uno de: MODIFY, ADD, DELETE, REPLACE",
            "old_content": "string exacto del contenido actual, o null si operation=ADD",
            "new_content": "string con el contenido propuesto, o null si operation=DELETE",
            "reason": "string, por que este cambio puntual",
        }
    ],
    "tests_to_update": ["lista de nombres de test EXISTENTES que este cambio podria requerir actualizar"],
    "tests_to_add": ["lista de nombres/descripciones de tests NUEVOS que este cambio deberia agregar"],
    "tests_to_remove": ["lista de nombres de test EXISTENTES que ya no aplican -- solo si es "
                        "genuinamente necesario, nunca porque 'dificultan el cambio'"],
    "documentation_to_update": ["lista de documentos que quedarian desactualizados por este "
                                "cambio -- NUNCA se modifican automaticamente, solo se declaran"],
    "risks": ["lista de riesgos concretos, no generico"],
    "assumptions": ["lista de supuestos que hiciste por falta de informacion"],
    "reasoning_summary": "string, resumen breve de la estrategia elegida",
    "confidence": "numero entre 0.0 y 1.0",
}


def build_prompt(request, previous_attempts: list[str] | None = None) -> tuple[str, str]:
    """Devuelve `(system_prompt, user_prompt)`. `request` es un
    `ChangeGenerationRequest` (FASE 25) ya ensamblado por
    `context.build_generation_context()` (FASE 26).

    `previous_attempts` (FASE 30 "Generation Retry Engine", NUEVO): lista
    de notas de correccion en TEXTO, una por intento previo fallido (ver
    `retry._build_correction_note()`) -- si se pasa, agrega una seccion
    `PREVIOUS_ATTEMPTS_FEEDBACK` al prompt para que el LLM vea EXACTAMENTE
    que penso mal la vez anterior, en vez de repetir el mismo error a
    ciegas. `None`/lista vacia (primer intento) no agrega la seccion."""
    request_dict = request.to_dict() if hasattr(request, "to_dict") else dict(request)
    change_type = _classify_change_type(request_dict)

    system = SYSTEM_PROMPT_BASE + "\n" + _TYPE_GUIDANCE[change_type]

    sections = {
        "CHANGE_REQUEST": request_dict["change_intent"],
        "CHANGE_PLAN": request_dict["change_plan"],
        "TARGET_FILES_AND_SYMBOLS": request_dict["source_context"],
        "CURRENT_SOURCE": {
            k: v.get("source") for k, v in (request_dict["source_context"].get("targets") or {}).items()
        },
        "CONTRACTS_AND_DEPENDENCIES": {
            "contracts": request_dict["graph_context"].get("contracts", []),
            "frontend_consumers": request_dict["graph_context"].get("frontend_consumers", []),
            "backend_dependencies": request_dict["graph_context"].get("backend_dependencies", []),
        },
        "TESTS": request_dict["test_context"],
        "ARCHITECTURAL_RULES": request_dict["architecture_context"],
        "CHANGE_TYPE": change_type,
        "EXPECTED_RESULT_SCHEMA": EXPECTED_RESULT_SCHEMA,
    }
    if previous_attempts:
        sections["PREVIOUS_ATTEMPTS_FEEDBACK"] = {
            "note": "Ya intentaste generar esta propuesta antes y fallo -- no repitas los mismos "
                    "errores. Cada entrada abajo es un intento previo real, en orden.",
            "failed_attempts": previous_attempts,
        }
    user = "\n\n".join(f"## {key}\n{json.dumps(value, ensure_ascii=False, indent=2)}" for key, value in sections.items())
    return system, user


__all__ = ["build_prompt", "CHANGE_TYPES"]

CHANGE_TYPES = (
    TYPE_BACKEND, TYPE_FRONTEND, TYPE_API, TYPE_TESTS, TYPE_DOCUMENTATION,
    TYPE_CONFIGURATION, TYPE_CROSS_STACK, TYPE_UNKNOWN,
)
