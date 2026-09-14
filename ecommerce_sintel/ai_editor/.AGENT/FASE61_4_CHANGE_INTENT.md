# FASE 61.4 -- CHANGE INTENT

**Fecha:** 2026-08-12. **LLM real usado:** Ollama, `llama3.1:8b`, `localhost:11434`. Tiempo de
respuesta: 7.2s. **0 archivos modificados.**

## Llamada real

`ai_editor.intent.parser.interpret_request()` con el texto completo del CHANGE_REQUEST
(`FASE61_3_CHANGE_REQUEST.md`, resumido a una sola solicitud en lenguaje natural).

## ChangeIntent producido (crudo, sin editar)

```json
{
  "status": "RESOLVED",
  "domain": "organization",
  "intent": "add_boolean_field_to_model_and_expose_in_serializers",
  "entities": ["SocialLink", "OrganizationView", "CustomerFooter"],
  "scope": ["backend", "frontend"],
  "confidence": 1.0,
  "ambiguities": []
}
```

## Validacion INDEPENDIENTE (no se acepto el resultado del LLM a ciegas)

Por instruccion explicita del usuario ("no confies ciegamente en Ollama, debes validar su
respuesta"), cada campo se verifico por separado ANTES de aceptar el intent como valido:

| Campo | Verificacion | Resultado |
|---|---|---|
| `domain: organization` | `interpret_request()` ya confirma internamente el dominio contra `graph_client.find_node()` (si no fuera una app real, el status hubiera quedado `NEEDS_CLARIFICATION`) -- reverificado manualmente | REAL, coincide con FASE 61.2/61.3 |
| `SocialLink` | `find_node('SocialLink')` | FOUND -- Model, `organization/models.py` |
| `OrganizationView` | `find_node('OrganizationView')` | FOUND -- FrontendComponent, `modules/organization/OrganizationView.vue` |
| `CustomerFooter` | `find_node('CustomerFooter')` | FOUND -- FrontendComponent, `components/customer/CustomerFooter.vue` |
| `scope: [backend, frontend]` | Coincide con el alcance real declarado en el CHANGE_REQUEST | Correcto |

**0 de 3 entidades alucinadas** -- las 3 existen exactamente con ese nombre en el grafo real.

## Hallazgos reales sobre el modelo (ni "funciona perfecto" ni "no sirve" -- honesto)

1. **Extraccion de entidades correcta pero INCOMPLETA por diseño, no por error**: el LLM
   nombro solo las 3 entidades "titulares" (el modelo + las 2 vistas Vue mencionadas
   explicitamente en el texto), no enumero `SocialLinkViewSet`/`SocialLinkSerializer`/
   `SocialLinkInputSerializer`/`organizationAdmin` (el store). Esto es ACEPTABLE -- el Change
   Resolver (FASE 61.5) es quien debe derivar esas entidades intermedias desde el grafo, no el
   LLM de intencion (que solo interpreta lenguaje natural, nunca "busca" en el repo, regla del
   prompt maestro seccion 1).
2. **`confidence: 1.0` -- sospechosamente perfecto, mal calibrado**: un modelo local de 8B
   reportando confianza maxima exacta en una tarea con multiples partes (backend+frontend+
   footer) es una señal de mala calibracion, no necesariamente de que el intent este mal --
   se documenta como limitacion real del modelo, no se corrige ni se ajusta artificialmente.
3. **`ambiguities: []` -- el modelo no señalo preguntas legitimas que SI existen** (ej.: ¿los
   `SocialLink` ya creados antes de la migracion deben quedar en `True` o `False`? ¿el checkbox
   del formulario de alta arranca marcado?). No son bloqueantes (el CHANGE_REQUEST de FASE 61.3
   ya las resuelve explicitamente -- default `True`), pero el modelo no las detecto por su
   cuenta como parte de interpretar la solicitud.

## Decision

**VALIDADO: la IA entendio correctamente la solicitud.** 0 entidades inventadas, dominio
correcto, scope correcto. Se continua a FASE 61.5. No se registra `INTENT_FAILURE`.
