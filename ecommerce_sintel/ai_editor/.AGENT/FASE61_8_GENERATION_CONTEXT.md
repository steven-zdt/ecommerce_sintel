# FASE 61.8 -- GENERATION CONTEXT

**Fecha:** 2026-08-12. **0 archivos modificados.** LLM: NO invocado (`build_generation_context()`
es 100% mecanico, sin llamada a red). Construido con el **plan FINAL CURADO de FASE 61.7**
(8 pasos de codigo -- la migracion nueva, paso 9 de FASE 61.7, no es codigo fuente legible, no
aplica a esta fase).

## 1. Resultado real

```
ChangeGenerationRequest:
  change_intent:  6 campos (FASE 61.4, sin editar)
  change_plan:    8 steps (plan curado FASE 61.7)
  graph_context:  13 campos (resolution completa de FASE 61.5)
  source_context: 8 targets, 9271 caracteres de codigo fuente REAL (leido directo de cada
                  archivo, con margen de contexto ±10 lineas sobre lo pedido)
  architecture_context: app=organization, global_rules (5 reglas reales de .AGENT.md/CLAUDE.md,
                  leidas en vivo) -- architecture_doc_path/excerpt = None (ver GAP G abajo)
  test_context:   1 test recomendado (OrganizationSelectorAndCommandsTests.
                  test_social_link_crud), 0 requeridos, tests_run=false (documentado el motivo
                  real: sandbox sin Django/Postgres)

TAMAÑO TOTAL: 61,072 caracteres (~15,268 tokens estimados, chars/4)
vs grafo completo: 9,270,511 caracteres -- 0.659%
```

**Regla absoluta de contexto (seccion 5 del prompt maestro) verificada con numeros reales: el
LLM NUNCA veria el grafo completo, ni el repositorio completo -- solo 61KB de un total de
~9.3MB del grafo (sin contar el codigo fuente completo del repo, que seria ordenes de magnitud
mayor).**

## 2. Detalle de `source_context` (8 targets, ninguno el archivo completo)

| # | Archivo | Simbolo | Lineas pedidas | Lineas con margen | Caracteres |
|---|---|---|---|---|---|
| 1 | `organization/models.py` | `SocialLink` | 102-116 | 92-121 | 1112 |
| 2 | `organization/api/serializers.py` | `SocialLinkSerializer` | 74-77 | 64-82 | 735 |
| 3 | `organization/api/serializers.py` | `SocialLinkInputSerializer` | 80-85 | 70-90 | 775 |
| 4 | `core/api/serializers.py` | `social_link_to_footer_link_shape` | 558-577 | 548-582 | 1185 |
| 5 | `frontend/src/store/organizationAdmin.js` | `organizationAdmin.createSocialLink` | 98-104 | 88-109 | 769 |
| 6 | `frontend/src/modules/organization/OrganizationView.vue` | (form alta) | 79-102 | 69-107 | 2278 |
| 7 | `frontend/src/components/customer/CustomerFooter.vue` | (template `<a>`) | 16-26 | 6-31 | 1214 |
| 8 | `organization/tests.py` | `test_social_link_crud` | 90-99 | 80-104 | 1203 |

## 3. GAP G -- bug REAL confirmado en `ai_editor/generation/context.py`, NO en el grafo

`architecture_context.architecture_doc_path`/`architecture_doc_excerpt` quedaron `None` para
`organization`, a pesar de que `CLAUDE.md` SI tiene la fila real:

```
| `ecommerce_sintel/organization/` *(nueva, en construccion)* | `ecommerce_sintel/organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` |
```

**Causa raiz exacta** (`ai_editor/generation/context.py::build_architecture_context()`, la
regex): `rf"\|\s*`ecommerce_sintel/{app}/`\s*\|\s*`([^`]+)`\s*\|"` exige que, tras el backtick de
cierre de la primera celda, solo haya espacios en blanco antes del siguiente `|` -- pero la fila
real de `organization` (y de `seo`, mismo patron) tiene el texto literal
`*(nueva, en construccion)*` en el medio, que la regex no contempla. El resultado: el doc de
arquitectura real de `organization` NUNCA llega al contexto de generacion para esta app
especifica (las demas apps, sin anotacion en su fila, no tienen este problema -- confirmado
contra el resto de la tabla de `CLAUDE.md`).

**Impacto real**: `architecture_context.global_rules` (las 5 reglas globales de `.AGENT.md`) SI
llegaron bien -- el LLM/generador de codigo SI sabria las reglas generales del proyecto, pero NO
la regla ESPECIFICA de `organization` mas importante para este caso exacto: **"nadie consulta
los modelos directamente... toda lectura pasa por `OrganizationSelector` -> `OrganizationService`"**
(de `organization/CLAUDE.md`, visto en el system prompt de esta sesion, NO en el doc que
`build_architecture_context()` intento leer -- son 2 archivos DISTINTOS: hay un
`organization/CLAUDE.md` con reglas propias ademas del
`organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` que la funcion intenta cargar).
Sin esa regla en el contexto, un generador (LLM o yo mismo) podria escribir codigo que consulta
`SocialLink.objects` directo en vez de pasar por `OrganizationSelector`/`OrganizationCommands`
-- exactamente el tipo de violacion arquitectonica que FASE 37 "Architectural Compliance" (ya
construida, plan anterior) esta diseñada para atrapar DESPUES, pero mejor prevenir en el
contexto que solo detectar despues.

**CORREGIDO (2026-08-12, con confirmacion explicita del usuario)**: la regex de
`build_architecture_context()` ahora tolera texto sin `|` entre el cierre de la primera celda
y el separador (`[^|]*` en vez de `\s*`). Verificado end-to-end contra las 21 filas reales de
`CLAUDE.md` -- las 21 resuelven correctamente (antes, 2 fallaban: `organization`/`seo`). Test
nuevo agregado: `test_build_architecture_context_resolves_app_rows_with_an_annotation_in_
claude_md` (`project_knowledge_graph/tests/test_ai_editor_generation_context.py`). Suite
completa: **450/450 passing** (449 previos + 1 nuevo), 0 regresiones -- un fallo transitorio
visto en una corrida intermedia (`test_cross_stack_proposal_applies_to_two_real_files_since_
fase_38`) se confirmo NO relacionado con este fix (reproducido igual con la regex vieja Y con
la nueva en corridas aisladas, desaparecio en la siguiente corrida completa -- condicion de
carrera transitoria sobre `renting/api/views.py`, que tiene cambios reales sin commitear del
usuario, ajena a este cambio).

## 4. Mitigacion aplicada manualmente para esta fase (sin tocar codigo)

Dado que `architecture_doc_excerpt` no llego automaticamente, se aniade aca a mano (para no
generar sin esa regla, ya que se detecto el gap ANTES de llegar a generacion, que es
exactamente para lo que sirve esta fase):

> **`organization/CLAUDE.md` (regla obligatoria):** "Ninguna otra app puede importar los modelos
> de `organization` ni leer `settings` para datos institucionales. Toda lectura pasa por
> `OrganizationSelector` -> `OrganizationService`... Sin signals, sin logica distribuida."

## Conclusion

`GenerationContext` construido: 61KB, 0.659% del grafo completo, 8 fuentes reales con margen,
reglas globales reales. 1 gap real nuevo encontrado en el propio `ai_editor` (no en el grafo,
GAP G) -- mitigado manualmente para esta fase, no corregido en codigo sin autorizacion explicita.
