# FASE 61.7 -- CHANGE PLAN

**Fecha:** 2026-08-12. **0 archivos modificados** (esta fase es planificacion). LLM: NO
invocado (100% grafo real, `ai_editor.planner.build_change_plan()`).

## 1. Plan auto-generado por el grafo (real, sin editar) -- 26 pasos

`build_change_plan(context)` produjo 26 `PlanStep` reales (`plan.status: PLANNED`,
`validate_plan()`: **APPROVED**, 0 issues, 11 warnings -- todos informativos, sobre
documentacion fuera de `WORKSPACE_ROOT`, no bloqueantes). Resumen por categoria:

- Step 1: `organization/models.py` -- `MODIFY` (target principal).
- Steps 2-3: `REVIEW` -- contratos (`Endpoint`/`Serializer`) del target.
- Steps 4-6: `REVIEW` -- consumidores frontend (`organizationAdmin.js` x2, `OrganizationView.vue`).
- Steps 7-14: `REVIEW` -- dependencias backend (`AdminFooterViewSet.*` x3, `OrganizationSelector.
  list_social_links`, `copy_data_forward`, `organization/api/serializers.py`,
  `OrganizationCommands.create_social_link`, `organization/api/views.py`).
- Step 15: `RUN` -- `organization/tests.py::OrganizationSelectorAndCommandsTests.
  test_social_link_crud` (el test real encontrado en FASE 61.5).
- Steps 16-26: `REVIEW` -- 11 documentos que mencionan el target (informativo).

## 2. GAP F -- confirmado con evidencia dura: el plan automatico NO incluye 2 archivos que
FASE 61.5/61.6 verificaron como necesarios

**`frontend/src/components/customer/CustomerFooter.vue` y
`core/api/serializers.py::social_link_to_footer_link_shape` NO aparecen en ninguno de los 26
pasos**, a pesar de que FASE 61.5 encontro (y FASE 61.6 verifico contra codigo real) que ambos
son imprescindibles para que el campo nuevo llegue al footer publico. Causa probable (no
verificada en detalle, fuera de alcance de FASE 61 corregir el scanner): el walk automatico de
`build_change_plan()` conecta `SocialLink -> OrganizationSelector.list_social_links` (SI
capturado, step 8), pero no continua desde ahi hacia `CoreViewSet.footer` (quien LLAMA a
`social_link_to_footer_link_shape()`, que a su vez llama a `OrganizationSelector.
list_social_links()`) ni desde ahi hacia `CustomerFooter.vue` -- la cadena de llamadas cruza de
`organization` a `core` a traves de una funcion pura (no una relacion de tipo `USES_STORE`/
`CONSUMES_ENDPOINT` que el scanner rastree en esa direccion). **Se agregan 2 pasos manuales al
plan final (abajo), con la evidencia de FASE 61.5/61.6 como unica justificacion -- no se acepta
"porque si", igual que el resto del plan.**

## 3. Plan FINAL CURADO (el que rige para FASE 61.8 en adelante)

| Step | File | Symbol | Operation | Origen | Risk |
|---|---|---|---|---|---|
| 1 | `organization/models.py` | `SocialLink` | **MODIFY** | plan automatico (target principal) | MEDIUM |
| 2 | `organization/api/serializers.py` | `SocialLinkSerializer` | **MODIFY** | plan automatico, step 10, escalado de REVIEW a MODIFY (contrato del target) | LOW |
| 3 | `organization/api/serializers.py` | `SocialLinkInputSerializer` | **MODIFY** | igual que 2 | LOW |
| 4 | `core/api/serializers.py` | `social_link_to_footer_link_shape` | **MODIFY** | **MANUAL -- GAP F, evidencia FASE 61.5/61.6** | LOW |
| 5 | `frontend/src/store/organizationAdmin.js` | `organizationAdmin.createSocialLink` (si el payload necesita el campo nuevo explicito) | **MODIFY** (probablemente no-op, ver nota) | plan automatico, step 4/6, escalado a MODIFY | LOW |
| 6 | `frontend/src/modules/organization/OrganizationView.vue` | (formulario de alta, seccion "Redes Sociales") | **MODIFY** | plan automatico, step 5, escalado a MODIFY | LOW |
| 7 | `frontend/src/components/customer/CustomerFooter.vue` | (template del `<a>` de red social, linea ~21) | **MODIFY** | **MANUAL -- GAP F, evidencia FASE 61.5/61.6** | LOW |
| 8 | `organization/tests.py` | `OrganizationSelectorAndCommandsTests.test_social_link_crud` | **MODIFY** (ampliar, no reescribir) | plan automatico, step 15 (`RUN`), escalado a MODIFY porque hay que AMPLIAR el test, no solo correrlo | LOW |
| 9 | `organization/migrations/` (nueva) | -- | **ADD** | derivado del step 1 (todo `BooleanField` nuevo en un modelo con datos existentes requiere migracion) | LOW |
| 10-12 | `dashboard/api/views.py` (`AdminFooterViewSet.*`) | -- | **REVIEW** (sin modificar) | plan automatico, steps 7/11/13 -- confirmar que NO se rompe (decision explicita FASE 61.5: legacy, fuera de alcance) | LOW |
| 13 | `core/migrations/...:copy_data_forward` | -- | **REVIEW** (sin modificar) | plan automatico, step 9 -- migracion historica, confirmar que no se toca | LOW |

Nota sobre step 5: `organizationAdmin.createSocialLink(payload)` hace `POST` del `payload` tal
cual llega del formulario (`this._api().post('organization/social-links/', payload)`, sin
transformar campos) -- si el formulario de `OrganizationView.vue` (step 6) ya incluye
`opens_in_new_tab` en el objeto que arma, el store NO necesitaria cambios (pasa-through). Se
mantiene en el plan como candidato porque el ChangePlan debe declarar TODO lo que PODRIA
tocarse, no porque se confirme necesario -- la generacion real (fase futura, ver FASE 61.9)
decidira si efectivamente lo toca.

**Total real declarado: 9 archivos a modificar (backend: 3 + 1 migracion; frontend: 3; tests: 1
ampliado), 4 archivos a solo revisar (confirmar que no se rompen), 11 documentos informativos.
Nada fuera de esta lista se considerara valido en FASE 61.9+ (regla "NO permitir cambios fuera
del plan").**

## 4. `validate_plan()` -- resultado real

```
status: APPROVED
issues: []
warnings: 11 (todos "documentacion fuera de WORKSPACE_ROOT, informativo" -- ninguno bloqueante)
```

## Conclusion

El plan automatico del grafo (26 pasos) es un buen PUNTO DE PARTIDA pero **incompleto** --
confirmado con evidencia dura (GAP F), no solo con la sospecha de FASE 61.5. El plan FINAL
CURADO (9 modificaciones + 4 revisiones) es el que se usara para construir el `GenerationContext`
en FASE 61.8. Ningun cambio fuera de esta lista de 9 archivos sera aceptado en fases posteriores.
