"""
`interpret_request()` -- POST-GRAPH 2 "Change Intent" (rediseno "AI
Editor Runtime", 2026-08-11).

Convierte una solicitud humana en un `ChangeIntent` real: llama al LLM
(via `ai_editor.llm`, independiente, ver ese paquete) con un prompt que
fuerza salida JSON estructurada, y CRUZA el `domain` propuesto contra el
Knowledge Graph real (via `ai_editor.graph_client.find_node()`, POST-GRAPH
1) -- Regla fundamental del planner del prompt maestro, aplicada aca
tambien: "El AI Editor NO puede inventar... si el Knowledge Graph no lo
confirma, UNKNOWN". Un LLM puede alucinar un nombre de app plausible pero
inexistente (ej. "rentals" en vez de "renting") -- este modulo no confia
ciegamente en la interpretacion del LLM, la verifica contra datos reales.
"""
import json
import logging
import re
import uuid

from ai_editor import graph_client, llm
from ai_editor.intent.prompts import SYSTEM_PROMPT, build_user_prompt
from ai_editor.intent.schema import (
    STATUS_NEEDS_CLARIFICATION,
    STATUS_RESOLVED,
    ChangeIntent,
)

logger = logging.getLogger(__name__)

_LOW_CONFIDENCE_THRESHOLD = 0.5
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw_text: str) -> dict | None:
    """El LLM a veces envuelve el JSON en un fence de markdown pese a que
    el prompt pide texto plano -- se tolera, no se falla por eso."""
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text
    try:
        return json.loads(candidate.strip())
    except (json.JSONDecodeError, AttributeError):
        return None


def _validate_domain_against_graph(domain: str | None) -> tuple[str | None, str | None]:
    """Confirma `domain` contra un nodo `App` REAL del grafo -- nunca
    convierte la suposicion del LLM en un hecho sin verificar. Devuelve
    `(domain_confirmado_o_None, nota_de_ambiguedad_o_None)`."""
    if not domain:
        return None, None
    node = graph_client.find_node(domain)
    if node is not None and node.get("type") == "App":
        return domain, None
    return None, (
        f"El dominio propuesto '{domain}' no corresponde a ninguna app real "
        "del Knowledge Graph -- no se confirma, requiere aclaracion."
    )


def interpret_request(request: str, provider: str | None = None) -> ChangeIntent:
    """Punto de entrada de POST-GRAPH 2. `provider` permite forzar un LLM
    especifico para esta llamada (ver `ai_editor.llm`)."""
    intent_id = str(uuid.uuid4())

    try:
        response = llm.complete(
            user=build_user_prompt(request), system=SYSTEM_PROMPT,
            max_tokens=512, temperature=0.0, provider=provider,
        )
    except (llm.LLMConfigError, llm.LLMRequestError) as exc:
        logger.warning("[ai_editor.intent] fallo real llamando al LLM: %s", exc)
        return ChangeIntent(
            id=intent_id, request=request, domain=None, intent=None,
            confidence=0.0, ambiguities=[f"No se pudo interpretar la solicitud: {exc}"],
            status=STATUS_NEEDS_CLARIFICATION,
        )

    parsed = _extract_json(response.text)
    if parsed is None:
        return ChangeIntent(
            id=intent_id, request=request, domain=None, intent=None,
            confidence=0.0,
            ambiguities=["El LLM no devolvio JSON valido -- respuesta no interpretable."],
            status=STATUS_NEEDS_CLARIFICATION,
        )

    raw_domain = parsed.get("domain")
    confirmed_domain, domain_ambiguity = _validate_domain_against_graph(raw_domain)

    ambiguities = list(parsed.get("ambiguities") or [])
    if domain_ambiguity:
        ambiguities.append(domain_ambiguity)

    confidence = float(parsed.get("confidence") or 0.0)
    status = STATUS_RESOLVED
    if ambiguities or confidence < _LOW_CONFIDENCE_THRESHOLD or confirmed_domain is None:
        status = STATUS_NEEDS_CLARIFICATION

    return ChangeIntent(
        id=intent_id,
        request=request,
        domain=confirmed_domain,
        intent=parsed.get("intent"),
        entities=list(parsed.get("entities") or []),
        scope=list(parsed.get("scope") or []),
        confidence=confidence,
        ambiguities=ambiguities,
        status=status,
    )
