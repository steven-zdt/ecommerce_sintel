# FASE 61.5 -- GRAPH RESOLUTION

**Fecha:** 2026-08-12. **0 archivos modificados** (aunque esta fase SI corrigio el alcance
declarado del CHANGE_REQUEST -- ver seccion 3, la correccion se aplico como texto/documentacion,
no como cambio de codigo).

## Llamada real

`ai_editor.resolver.resolve_change_context(intent)` con el `ChangeIntent` validado en FASE 61.4
(sin LLM -- 100% grafo real, `graph_client`).

## 1. Resultado

```
status: RESOLVED
primary_target: Model SocialLink (organization/models.py) -- prioridad Symbol>Model aplicada
                 correctamente (ni OrganizationView ni CustomerFooter, ambos FrontendComponent,
                 ganaron la prioridad)
resolved_entities: FrontendComponent OrganizationView, FrontendComponent CustomerFooter
unresolved_entities: [] -- 0 entidades sin confirmar
risk: MEDIUM
contracts: ['api/v1/organization/social-links', 'api/v1/dashboard/footer']
frontend_consumers (del Model): organizationAdmin.fetchAll, organizationAdmin (PiniaStore),
                                  OrganizationView
backend_dependencies: OrganizationCommands.create_social_link, AdminFooterViewSet.delete_link,
                       SocialLinkSerializer, copy_data_forward (migracion historica, ver 2 abajo),
                       AdminFooterViewSet.update_link, OrganizationSelector.list_social_links,
                       SocialLinkViewSet, AdminFooterViewSet
tests: direct=[], indirect=['OrganizationSelectorAndCommandsTests.test_social_link_crud']
```

## 2. Correccion real al CHANGE_REQUEST (FASE 61.3) -- descubierta por el grafo, NO por
exploracion manual previa

El grafo devolvio 2 `contracts`, no 1 (el que yo habia identificado manualmente en FASE 61.2):
`api/v1/dashboard/footer` ademas de `api/v1/organization/social-links`. Investigado contra
codigo real (`dashboard/api/views.py:2074`, `AdminFooterViewSet`, y `core/api/views.py:109`,
`CoreViewSet.footer`):

- **`AdminFooterViewSet`** (`dashboard/api/views.py`) es un ViewSet legacy admin, documentado
  explicitamente en su propio docstring: "Contacto y redes sociales viven ahora en
  `organization`... Este ViewSet sigue exponiendo los MISMOS endpoints/contrato JSON que antes...
  para no romper el panel admin antes de la Fase 6". Despacha `create_link`/`update_link`/
  `delete_link` entre `core.FooterLink` (nav) y `organization.SocialLink` (social) segun
  `category`. **Decision: fuera de alcance del CHANGE_REQUEST** -- tocarlo ampliaria la prueba
  mas alla de "PEQUEÑA" (seccion 3 del prompt maestro) y toca un panel admin legacy
  (`HomeConfigView.vue`) explicitamente marcado como "no romper" en su propio codigo.
  **Consecuencia real, documentada, no oculta**: un admin usando el panel VIEJO
  (`HomeConfigView.vue` -> `AdminFooterViewSet`) no podra editar `opens_in_new_tab` -- solo
  el panel NUEVO (`OrganizationView.vue` -> `SocialLinkViewSet`).
- **`core.api.views.py::CoreViewSet.footer` (`GET core/footer/`)** -- este SI es el endpoint
  real que consume `CustomerFooter.vue` (confirmado leyendo el archivo:
  `api.get('core/footer/')`, linea 234) -- **ya declarado en el alcance del CHANGE_REQUEST**,
  pero mi exploracion manual de FASE 61.2/61.3 NO habia identificado que este endpoint usa
  `social_link_to_footer_link_shape()` (funcion compartida en `core/api/serializers.py`, la
  MISMA que usa el `AdminFooterViewSet` legacy) para convertir cada `SocialLink` a JSON --
  **`SocialLinkSerializer` (organization) NO es lo que llega al footer publico** -- llega via
  esta funcion de conversion separada. **Correccion real y NECESARIA del alcance**:
  `social_link_to_footer_link_shape()` debe agregarse a la lista de archivos a tocar
  (`core/api/serializers.py`) o el campo nuevo nunca llegaria al footer publico aunque
  `SocialLinkSerializer` y `CustomerFooter.vue` SI se modifiquen -- el dato se perderia en la
  conversion intermedia.
- Cacheo real detectado (no bloqueante para el sandbox): `core/footer/` cachea la respuesta
  (`FOOTER_CACHE_KEY`/`FOOTER_CACHE_TTL`) -- en un despliegue real haria falta invalidar cache
  tras el cambio; irrelevante para la prueba en sandbox (nunca hay cache real involucrada).
- `copy_data_forward` (aparecio en `backend_dependencies`): confirmado que es una funcion de
  migracion HISTORICA (`core/migrations/0001_initial_squashed_0026_...py`, ya ejecutada) --
  **no se toca, correctamente fuera de alcance**, aparece solo porque referencia el modelo en
  su logica de copia de datos de una migracion ya aplicada.

**Alcance CORREGIDO del CHANGE_REQUEST (reemplaza la lista de FASE 61.3):**
```
Backend:  organization/models.py (SocialLink + migracion nueva)
          organization/api/serializers.py (SocialLinkSerializer, SocialLinkInputSerializer)
          core/api/serializers.py (social_link_to_footer_link_shape -- NUEVO, requerido)
Frontend: frontend/src/modules/organization/OrganizationView.vue
          frontend/src/components/customer/CustomerFooter.vue
          frontend/src/store/organizationAdmin.js (si aplica)
Tests:    organization/tests.py -- AMPLIAR OrganizationSelectorAndCommandsTests.
          test_social_link_crud (test REAL ya existente, encontrado por el grafo -- mi
          verificacion manual de FASE 61.3 estaba INCOMPLETA, decia "sin test directo
          encontrado")
Explicitamente FUERA de alcance: dashboard/api/views.py::AdminFooterViewSet,
          frontend HomeConfigView.vue (panel admin legacy, documentado arriba)
```

## 3. GraphContextPacket -- regla de contexto minimo verificada con numeros reales

```
stats: {
  total_graph_nodes: 9575, relevant_nodes: 27 (0.28%), relevant_files: 9,
  relevant_symbols: 6, relevant_contracts: 2, relevant_tests: 1, relevant_documents: 11
}
tamaño del packet: 5964 caracteres  vs  9,270,511 caracteres del grafo completo
ratio real: 0.064% -- la "REGLA ABSOLUTA DE CONTEXTO" del prompt maestro ("nunca enviar el
grafo completo al LLM") se cumple con evidencia numerica real, no solo declarativa.
```

## 4. Conclusion

El grafo resolvio correctamente `SocialLink` como target principal, encontro un test real
existente que mi verificacion manual habia pasado por alto, y **encontro un archivo backend
adicional genuinamente necesario** (`core/api/serializers.py::social_link_to_footer_link_shape`)
que mi exploracion manual de FASE 61.2/61.3 no habia detectado -- exactamente el tipo de
verificacion cruzada que FASE 61 esta diseñada para producir. El CHANGE_REQUEST (FASE 61.3)
queda corregido con esta seccion, no reescrito -- ambos documentos se conservan para trazabilidad.
