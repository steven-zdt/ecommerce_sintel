# FASE 4/5 -- Galeria descriptiva real (ServiceImage)

Plan "Rediseno ServiceForm + Content/Media", P2 (prioridad explicita del
usuario, ejecutada tras completar P1 -- auditoria). Backend + frontend +
verificacion en navegador real, mismo rigor que el resto de la sesion.

## Backend

`ServiceImage` (migracion `0037_serviceimage_gallery_fields`) gano
`caption` (CharField 150), `description` (TextField), `display_order`
(PositiveIntegerField, `Meta.ordering=['display_order','created_at']`).
Ninguno de los "espejos" habituales (`shop.ProductImage`,
`renting.Equipment*Image`) tenia este patron -- confirmado en la auditoria
FASE 0 que esto era trabajo genuinamente nuevo, no una replica.

`ServiceImageCommands` (technical_services/services/commands.py) gano:
- `add_image(..., caption='', description='')` -- ahora asigna
  `display_order` incremental automatico (`count()` de imagenes existentes).
- `update_metadata(image, **fields)` -- solo permite
  `alt_text`/`caption`/`description` (whitelist explicita).
- `replace_file(image, image_file)` -- reemplaza `image` conservando el
  resto de la metadata.
- `reorder(service, ordered_uuids)` -- reasigna `display_order` segun la
  posicion en la lista.

`AdminServiceViewSet` (dashboard/api/views.py) gano 3 acciones nuevas
(mismo patron BFF que el resto: `ServiceAdminOrchestrator` -> Commands,
cero ORM directo):
- `PATCH .../update_image/{image_uuid}/` -- metadata sin archivo.
- `POST .../replace_image/{image_uuid}/` -- multipart, reemplaza archivo.
- `POST .../reorder_images/` -- `{ordered_uuids: [...]}`, devuelve la
  galeria completa ya reordenada.
- `add_image` existente extendido para aceptar `caption`/`description`
  opcionales en el mismo payload multipart.

## Bug real encontrado y corregido: `reorder_images` devolvia el orden viejo

`ServiceSelector.get_by_uuid()` (usado por `get_service()`, la primera
linea de CADA accion del ViewSet) hace
`prefetch_related('variants__...', 'images', ...)` para evitar N+1 en el
endpoint de detalle. Ese prefetch se puebla en el momento de
`get_service(uuid)` -- **antes** de que `reorder_images` reasigne
`display_order`. Django no invalida un `prefetch_related` cache por
escrituras posteriores en la misma request, asi que `service.images.all()`
al final de la vista devolvia la galeria en su orden **anterior** al
reorder, aunque cada `.save()` individual se confirmaba correcto (verificado
con relectura inmediata por PK durante el debug). Fix: la vista consulta
`ServiceImage.objects.filter(service=service)` directo en vez de
`service.images.all()`, forzando una query fresca que ignora el prefetch
cache del objeto `service` ya cargado. Cubierto por
`test_reorder_images_success` (fallaba de forma reproducible antes del fix,
con logs de debug temporales que probaron la causa exacta antes de tocar
codigo).

## Frontend

`ServiceGalleryManager.vue` (nuevo, `service-form/`) reemplaza a
`ImagesTab.vue` (eliminado, sin mas referencias en el codebase). Capacidades
verificadas en navegador real contra "Mantenimiento Preventivo":

- **Multi-upload**: cola de varios archivos con preview, caption/
  description/marca-principal por archivo antes de subir.
- **Reorder**: drag&drop (mismo patron que `ContentBlocksTab.vue`),
  persistido y verificado directo en Postgres (`display_order` coincidio
  exactamente con el orden visual tras el drop).
- **Editar metadata inline**: caption/description/alt_text sin re-subir.
- **Reemplazar archivo**: input file dedicado por imagen, conserva
  metadata (verificado: la URL de imagen cambio, `caption` no se toco).
- **Hacer principal** / **Eliminar**: reusan `store.setPrimaryImage()`/
  `store.deleteImage()` ya existentes, sin cambios.

Store (`technicalServicesAdmin/services.js`) gano
`updateImageMetadata()`, `replaceImageFile()`, `reorderImages()` -- mismo
patron BFF, mismo override explicito de `Content-Type: multipart/form-data`
que ya tenia `uploadImage()` (FASE 5 del plan pedia preservar ese fix
explicitamente -- confirmado intacto).

Datos de prueba (2 imagenes subidas durante la verificacion en navegador)
se eliminaron al terminar, dejando "Mantenimiento Preventivo" en su estado
original.

## Tests

`technical_services/tests_gallery.py` (nuevo, 12 tests): comandos
(`add_image` asigna orden incremental, guarda caption/description,
`update_metadata` solo toca los 3 campos permitidos, `replace_file`
conserva metadata, `reorder` persiste y `Meta.ordering` refleja el nuevo
orden sin `order_by()` explicito) + API admin (las 3 acciones nuevas,
incluyendo auth requerida y validacion de archivo requerido en replace).
**12/12 PASS.**

Regresion completa de `technical_services`: **198/199 PASS** -- el unico
fallo (`IntegrityError` en `auth_permission` durante `flush`, en
`test_pricing_strategy_hourly_with_bounds`) se confirmo como flake
preexistente de infraestructura de test, no relacionado con este cambio:
el mismo test corrido en aislamiento pasa limpio (`OK`, exit 0).

## No hecho en este incremento

- ~~FASE 6 (Presentation DTO) y FASE 7 (rediseno del detalle customer)~~ --
  **ambas cerradas en incrementos posteriores el mismo dia**: FASE 6
  expuso `caption`/`description` en `BaseGallery.vue` (`show-caption`,
  opt-in). FASE 7 (auditoria del detalle publico contra la matriz de
  campos) ver `SERVICES_FASE7_DETALLE_CUSTOMER_2026-08-14.md`.
- FASE 2/3 (rediseno conceptual del formulario, creacion rapida) -- P3 del
  plan, no priorizado en este incremento (P2 = galeria, ya cerrado).
- **[2026-08-14, mismo dia] Intento y reversion de "creacion rapida sin
  precio":** se implemento y verifico en navegador un toggle "Configurar
  precio ahora" en `GeneralTab.vue` (aprovechando que
  `TechnicalServiceAdminCreateSerializer.initial_variant` ya era opcional a
  nivel de API) que permitia crear un servicio sin variante inicial. El
  usuario lo rechazo explicitamente: el precio debe ingresarse **siempre**
  de forma manual por el admin, en cualquier formulario, sin via de
  omitirlo al crear. Revertido en el mismo turno -- `GeneralTab.vue`/
  `ServiceForm.vue` vuelven al comportamiento original (precio siempre
  visible y obligatorio en la Variante inicial de CREATE). Ver memoria de
  proyecto `project_service_price_always_manual` para el detalle completo
  de esta regla de negocio antes de reintentar cualquier simplificacion de
  la creacion que toque el bloque de precio.
