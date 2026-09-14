# FASE 7 -- Auditoria del detalle customer (ServiceDetailContent.vue)

Plan "Rediseno ServiceForm + Content/Media", FASE 7: "verificar que cada
dato realmente tenga representacion" en la pagina publica del servicio.

## Alcance real vs. el plan original

El plan mencionaba auditar `ServiceDetailView.vue` + 6 subcomponentes
propios (`ServiceGallery`, `ServiceFeatureList`, `ServiceScopeList`,
`ServiceSpecificationTable`, `ServiceFAQAccordion`, `ServiceReviews`) --
ninguno existe (ver `SERVICES_FRONTEND_AUDIT_2026-08-14.md` FASE 0, ya
corregido: el archivo real es `ServiceDetailContent.vue` y usa
`BaseGallery`/`BaseAccordion`/`BaseReviews` compartidos +
`ServiceProfessionals.vue` propio). Esta auditoria se hizo contra la
arquitectura real, cruzando `TechnicalServiceDetailSerializer` (todos los
campos expuestos) y `ContentBlockConfig.SERVICE_DEFAULT_ORDER` (los 19
bloques orquestables) contra los `v-if`/`blockVisible()` reales del `.vue`.

De 19 bloques declarados en el orden por defecto, 18 tenian seccion
correspondiente en `ServiceDetailContent.vue`. Se encontraron 2 gaps reales.

## Gap 1 (corregido): bloque "Soporte" huerfano

`ContentBlockConfig.SERVICE_DEFAULT_ORDER` incluia `BLOCK_SUPPORT`
('Soporte'). El admin podia verlo en la pestana "Contenido del Servicio"
(`ContentBlocksTab.vue`, reordenar/ocultar), pero:
- `ServiceDetailContent.vue` nunca llamaba `blockVisible('support')` --
  ninguna seccion "Soporte" existe en la pagina publica.
- `ENTITY_CONFIG.service.ownTab` (en `ContentBlocksTab.vue`) no mapea
  `support` a ninguna pestana propia -- a diferencia de Shop
  (`support: 'servicios-incluidos'`), Services no tiene ningun campo/tab
  para cargar contenido de "Soporte".

Resultado: el admin podia interactuar con un control (toggle
visibilidad/reorder) que no tenia ningun efecto observable en el sitio
publico -- ni submodelo que editar. Bloque fantasma.

**Fix:** se quito `BLOCK_SUPPORT` de `SERVICE_DEFAULT_ORDER`
(`shared/models.py`) en vez de inventarle una seccion/modelo sin pedido
real -- mismo principio que elimino `SERVICE_FALLBACK` en la reingenieria
SDP 2026-08-05 (no crear UI para datos que no existen). `SERVICE_DEFAULT_ORDER`
pasa de 19 a 18 bloques. Actualizados: `technical_services/test_content_blocks.py`
(4 asserts de conteo 19->18), comentarios en `dashboard/api/content_blocks_views.py`,
`ServiceDetailContent.vue`, `UI_MODULO_SERVICES.md`. Verificado:
`test_content_blocks.py` 11/11 PASS tras el cambio.

Nota: `resolve_for()` solo itera sobre el `default_order` recibido -- una
fila `ContentBlockConfig` existente con `block_type='support'` para algun
servicio (si algun admin llego a tocar el toggle antes de este fix) queda
simplemente fuera de toda respuesta futura, sin error ni necesidad de
migracion de datos.

## Gap 2 (corregido): CTA publico ignoraba `is_active`/`is_purchasable`

`serviceHasActiveVariant` (computed que controla el boton "Solicitar
servicio" vs. "No disponible") solo miraba
`serviceDetail.variants.some(v => v.is_active !== false)`. No consultaba
`serviceDetail.is_active` ni `serviceDetail.is_purchasable` -- ambos
expuestos por el serializer y ya identificados como "Indirecto (CTA)" en
`SERVICES_FIELD_MATRIX_2026-08-14.md` (fila `is_purchasable`) sin haberse
verificado entonces si el "indirecto" realmente funcionaba.

Consecuencia real: un servicio con `is_purchasable=False` (o `is_active=False`,
alcanzable via URL directa -- ver "No resuelto" abajo) pero con alguna
variante activa seguia mostrando "Solicitar servicio". El cliente completaba
el wizard completo (seleccion, direccion, fecha, pago) y recien al enviar
chocaba con el rechazo de `ServiceCommands.request_service()`
(`if not variant.service.is_purchasable: raise`, `services/commands.py:26`) --
un error tardio y confuso en vez de una UI honesta desde el inicio.

**Fix:** `serviceHasActiveVariant` ahora exige
`is_active !== false && is_purchasable !== false` ademas de la variante
activa. Verificado en navegador real: `PATCH is_purchasable=False` sobre
"Mantenimiento Preventivo" -> CTA publico cambia a "No disponible"
(el badge de estado arriba, que solo depende de `is_active`, siguio
mostrando "Disponible" correctamente -- son 2 senales distintas). Revertido
el flag de prueba al terminar.

## No resuelto -- reportado, no corregido (fuera de alcance de este incremento)

**`ServiceSelector.get_by_uuid()` no filtra `is_active`.** Es el selector
usado por `TechnicalServiceViewSet.get_object()` (bypassa el `is_active=True`
de `get_queryset()`/`list_active_services()`) para TODAS las acciones del
detalle publico, incluida `full_detail` (`TechnicalServiceDetailSerializer`).
Un servicio desactivado (`is_active=False`) sigue siendo accesible completo
via `/servicios/{uuid}` directo aunque `list_active_services()` ya lo
excluye del catalogo/listados. Con el Gap 2 ya corregido el CTA de compra
al menos queda deshabilitado en ese caso, pero la pagina de detalle
completa (galeria, descripcion, precios, etc.) sigue siendo visible.

No se corrigio en este incremento porque `get_by_uuid()` es compartido con
el admin (`AdminServiceViewSet` lo necesita para poder ver/editar servicios
inactivos) -- un fix correcto requiere diferenciar el selector publico del
admin (ej. un `get_by_uuid_public()` que si filtre `is_active=True`, o un
chequeo condicional en `get_object()` segun `request.user.is_staff`), lo
cual es un cambio de mayor alcance que auditar representacion visual de
contenido. Queda documentado para decidir prioridad en un proximo
incremento.
