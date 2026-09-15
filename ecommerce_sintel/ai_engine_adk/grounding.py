"""
grounding.py -- Mision RAG Enterprise (2026-09-16, FASE 7).

Grounding / claim validation POST-generacion: verifica que la respuesta
publica del LLM este realmente sustentada por el contexto de conocimiento
recuperado -- distinto de retrieval confidence/answerability
(sintel_rag_adapter.py, FASE 6), que decide ANTES de generar si hay
evidencia suficiente. "Hubo evidencia disponible" no es lo mismo que "la
respuesta la uso correctamente" -- esta capa cierra ese hueco.

## Por que una llamada LLM minima, no extraccion de claims

El patron mas sofisticado (extraer cada afirmacion de la respuesta y
verificarla una por una contra la evidencia) se evaluo y se descarto POR
AHORA:
- Regla 1 de la mision ("no sobrearquitecturar") + Regla 2 ("no crear
  Agentic RAG prematuramente -- solo si las pruebas demuestran que el
  retrieval monolitico actual es insuficiente"): sin corpus real todavia
  (hallazgo F-1, AUDITORIA/RAG_SUPPORT_BASELINE.md) no hay evidencia de que
  una pregunta binaria/ternaria sea insuficiente.
- Duplicaria significativamente el costo/latencia de CADA turno de intent
  "knowledge" si se hiciera claim-por-claim.

Se implementa UNA sola llamada LLM adicional, MINIMA (maximo 10 tokens de
respuesta), acotada a turnos donde SI hubo evidencia real recuperada --
nunca corre sobre los marcadores de "sin conocimiento"/"baja confianza" de
sintel_rag_adapter.py (ahi no hay nada que validar, la respuesta ya deberia
ser una calificacion honesta, no una afirmacion de datos).

## Por que NO reutiliza Part.thought ni toca public_response.py

Esta validacion es un paso ANTES de que la respuesta se devuelva al
cliente, no un cambio en como se separa razonamiento/contenido de UN evento
de ADK -- se ejecuta sobre `final_text` ya extraido (texto publico limpio),
con una llamada litellm directa, sin pasar por LlmAgent/Runner/Session (no
hace falta Tools ni estado para una pregunta de si/no). La frontera publica
existente (public_response.py) queda intacta.
"""
import logging

logger = logging.getLogger("grounding")

SUPPORTED = "SUPPORTED"
PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"

_VALID_VERDICTS = {SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED}

# Mismo tono/patron que los marcadores de sintel_rag_adapter.py -- nunca
# expone al cliente que hubo un "validador" interno, solo una calificacion
# honesta de incertidumbre.
UNGROUNDED_FALLBACK_RESPONSE = (
    "No tengo informacion verificada suficiente para confirmar eso con certeza. "
    "Puedo poner en contacto a un agente humano si necesitas una respuesta exacta."
)

_GROUNDING_PROMPT_TEMPLATE = (
    "Evalua si la RESPUESTA esta sustentada por la EVIDENCIA. No evalues si la "
    "respuesta es correcta en general ni si es una buena respuesta -- solo si "
    "los datos concretos que afirma (precios, plazos, politicas, cifras, "
    "nombres, fechas) aparecen o se deducen directamente de la evidencia.\n\n"
    "EVIDENCIA:\n{evidence}\n\n"
    "RESPUESTA:\n{response}\n\n"
    "Responde con EXACTAMENTE una palabra, sin explicacion: SUPPORTED (todo lo "
    "afirmado esta en la evidencia), PARTIALLY_SUPPORTED (una parte si y otra "
    "no, o no se puede verificar del todo), o UNSUPPORTED (la respuesta afirma "
    "datos concretos que NO estan en la evidencia)."
)


def _parse_verdict(raw: str) -> str:
    text = (raw or "").strip().upper()
    for verdict in (UNSUPPORTED, PARTIALLY_SUPPORTED, SUPPORTED):  # mas largo primero (SUPPORTED es substring de los otros dos)
        if verdict in text:
            return verdict
    # Respuesta no reconocida del validador -- fail-safe explicito: tratar
    # como NO verificable, nunca como SUPPORTED por defecto (misma regla de
    # honestidad que ya aplica al resto del RAG: "si algo no se pudo
    # confirmar, el sistema debe reconocerlo", no asumir lo mejor).
    logger.warning("[grounding] veredicto no reconocido del validador: %r -- tratado como UNSUPPORTED", raw)
    return UNSUPPORTED


async def check_grounding(*, response: str, evidence: str, model: str,
                           api_base: str | None = None, api_key: str | None = None) -> str:
    """Llamada litellm directa (mismo modelo/proveedor real del turno) con
    una pregunta minima de si/no. Nunca lanza -- si el validador falla
    (timeout, proveedor caido), se degrada a PARTIALLY_SUPPORTED: no
    bloquea el turno con una respuesta generica, pero tampoco lo certifica
    como confiable (mismo criterio de "degradar con gracia" que ya usa el
    resto del pipeline de RAG -- nunca romper /chat, nunca fingir certeza)."""
    import litellm

    prompt = _GROUNDING_PROMPT_TEMPLATE.format(evidence=evidence[:4000], response=response[:2000])
    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "timeout": 15,
        "max_tokens": 10,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    try:
        completion = await litellm.acompletion(**kwargs)
        raw = completion.choices[0].message.content
    except Exception as exc:
        logger.warning("[grounding] check_grounding fallo (%s) -- degradando a PARTIALLY_SUPPORTED", exc)
        return PARTIALLY_SUPPORTED
    return _parse_verdict(raw)
