# MARKETING_GAPS — Hallazgos reales (FASE 0-1)

Ordenados por severidad. Evidencia real (archivo:linea o prueba directa contra `ecommerce_sintel_django`
dev, JWT de un admin real).

---

## GAP #1 — CRITICO (CERRADO en esta pasada): ruta de frontend nunca registrada

**Evidencia:** `frontend/src/components/layout/Sidebar.vue:180` enlaza `{ to: '/panel/marketing', ... }`
desde siempre. `frontend/src/apps/admin/router.js` (unico router del panel, ver
`frontend/CLAUDE.md`) **no tenia ninguna entrada** para ese path -- ni `path: 'marketing'`, ni import
de `MarketingView.vue`, en ningun `routes/adminX.routes.js` existente. Confirmado con
`grep -in "marketing" router.js` -> 0 resultados antes del fix.

**Impacto real:** el administrador nunca podia llegar al formulario de creacion -- el click en
"Campanias" del sidebar navegaba a una ruta sin registrar, resuelta por el catch-all
(`{ path: '/:pathMatch(.*)*', redirect: ... '/panel/dashboard' }`), es decir, **el click simplemente
regresa al dashboard sin explicacion.** Esto explica exactamente el sintoma reportado en el plan
("`/panel/marketing` no permite crear campanias") sin que el backend tuviera ningun problema.

**Verificado que el backend SI funcionaba desde antes:** `POST /api/v1/marketing/campaigns/` con un
JWT de admin real y un payload minimo valido -> `201 Created`, tanto con formato ISO completo como con
el formato exacto de `<input type="datetime-local">` (sin segundos/timezone) que produce
`CampaignForm.vue`. 2 pruebas reales, ambas exitosas, datos de prueba limpiados despues.

**Severidad: CRITICA** (bloqueaba el 100% del uso del modulo), pero **fix trivial**.

**[CERRADO 2026-09-23, FASE 1]** Creado `frontend/src/apps/admin/routes/adminMarketing.routes.js`
(mismo patron exacto que `adminAi.routes.js`) y registrado en `router.js`
(import + `...adminMarketingRoutes` en el array de children de `/panel`). Verificado: Vite recargo el
router sin errores de compilacion (`docker logs ecommerce_sintel_frontend`, "page reload
src/apps/admin/router.js" sin warnings/errores). `marketing.tests.py`: 58/58 OK antes y despues (el fix
es 100% frontend, no se esperaba ni se encontro regresion backend).

---

## GAP #2 — INFORMATIVO: `channels` no se valida contra `CHANNEL_CHOICES`

**Evidencia:** `MarketingCampaign.channels = models.JSONField(default=list, help_text=...)` --
`CHANNEL_CHOICES` (8 valores) existe en el modelo pero **nunca se usa como `choices=` de un campo real**
(el campo es `JSONField`, no `CharField`/`MultiSelectField`). `MarketingCampaignSerializer` tampoco
agrega un validator custom. Un POST con `"channels": ["cualquier_string_invalido"]` seria aceptado sin
error -- no probado explicitamente en esta pasada (fuera del alcance minimo de Fase 0-1), pero se
desprende directamente de leer el codigo.

**Hallazgo relacionado en el frontend:** `CampaignForm.vue:87-95` tiene un checkbox para el canal
`"sms"` -- **`sms` NO esta en `CHANNEL_CHOICES` ni en `channels/registry.py`** (los 8 canales reales son
`email/whatsapp/facebook/instagram/youtube/tiktok/x/google_business`, sin SMS). Si un admin marca ese
checkbox y guarda, el backend lo aceptaria silenciosamente (por el gap de arriba) pero **ningun canal
real llamado `sms` existe en `channels/registry.py`** -- el envio por ese "canal" fallaria en runtime
(o simplemente no se procesaria, no verificado en esta pasada) sin que el admin lo sepa al guardar.

**Severidad: MEDIA.** No bloquea el CRUD basico, pero es un caso real de UI mostrando una opcion que no
existe en el backend -- exactamente el tipo de cosa que la Fase 15 del plan pide auditar
("inventariar los canales reales, no inventar nombres"). Candidato directo para la Fase 15/16 si se
continua el plan.

---

## GAP #3 — INFORMATIVO: brecha grande entre el modelo real y lo que el plan (Fases 3-17) asume

**Evidencia:** ver la tabla completa en `MARKETING_BASELINE.md`. Resumen: `MarketingCampaign` hoy es
6 campos (`title`, `content`, `channels`, `scheduled_at`, `sent_at`, `is_completed`) mas la relacion
`logs` (via `CampaignLog`). Cero FK a catalogo (Producto/Servicio/Renting), cero soporte de media, cero
beneficios estructurados, cero contenido estructurado (CTA/terms), cero maquina de estados granular.

**No es un bug** -- es simplemente el estado real y honesto del modulo, necesario documentar antes de
que el usuario decida cuanto del resto del plan (Fases 2-34) ejecutar. Construir lo que el plan pide
requiere: nuevos campos o modelos satelite, migraciones, nuevos endpoints, nueva UI de seleccion de
catalogo/beneficios/media, y decidir si el flujo de escritura de estos sub-recursos sigue la convencion
`dashboard/` (ver `frontend/CLAUDE.md`, regla de endpoints) o se mantiene bajo `marketing/campaigns/`
como hoy (que ya tiene `IsAdminUser` directo, sin necesitar el prefijo `dashboard/`).

**Severidad: N/A (hallazgo de alcance, no un defecto).**

---

## GAP #4 — INFORMATIVO: cobertura de tests de `MarketingCampaign` CRUD no auditada en detalle

**Evidencia:** `marketing/tests.py` tiene 58 tests reales (confirmado corriendo la suite completa, todos
pasan), incluyendo cobertura solida de `MetaGraphClient` (canales Meta: Facebook/Instagram/etc.) y envio
de WhatsApp. **No se verifico linea por linea** cuantos de esos 58 prueban especificamente el ciclo
CRUD de `MarketingCampaignViewSet` (create/list/retrieve/update/delete) -- fuera del alcance minimo de
esta pasada (Fase 0-1 es descubrimiento + fix del bug de ruta, no auditoria exhaustiva de tests).

**Severidad: BAJA.** Si se continua a la Fase 24 del plan ("Tests backend"), esto es el punto de partida
real: confirmar cobertura existente antes de escribir tests nuevos (mismo criterio que se aplico en la
auditoria de Email de esta sesion, donde se encontro que la cobertura existente ya era solida y solo
faltaban 4 tests puntuales).

---

## FASE 2 — CRUD existente: verificado end-to-end, sin bugs de wiring (2026-09-23)

**Resultado: LIST/DETAIL/UPDATE/DELETE funcionan correctamente, backend Y frontend, sin necesidad de
ningun fix.** Probado en vivo contra `ecommerce_sintel_django` (JWT admin real):

| Operacion | Backend (HTTP real) | Frontend | Resultado |
|---|---|---|---|
| LIST | `GET .../campaigns/` -> `200`, incluye `logs` anidados | `MarketingView.vue` tabla, consume `store.campaigns` (`fetchAll()`) | **PASS** |
| DETAIL | `GET .../campaigns/<uuid>/` -> `200` | `openEdit(camp)` pasa el objeto completo (ya lo tiene de la lista, no hace un GET individual) | **PASS** |
| UPDATE | `PATCH .../campaigns/<uuid>/` -> `200`, campo actualizado confirmado | `CampaignForm.vue:185-187` rama `mode==='edit'` -> `store.updateCampaign(uuid, payload)`, pre-llena el formulario con los datos reales | **PASS** |
| DELETE | `DELETE .../campaigns/<uuid>/` -> `204`, fila **fisicamente eliminada** de Postgres (confirmado: `MarketingCampaign.objects.filter(uuid=...).exists()` -> `False` despues) | `MarketingView.vue:113,268-272` boton + `confirm()` nativo -> `store.deleteCampaign()` | **PASS** |
| ACTIVATE / DEACTIVATE | **No existe en el backend** -- `MarketingCampaign` no tiene campo `is_active` (solo `is_completed`, gestionado por el flujo de envio, no un toggle manual). `ModelViewSet` no expone ninguna `@action` custom para esto. | Sin boton en la UI (consistente -- no hay nada que conectar) | **N/A -- gap real de alcance, no un bug** (ver GAP #3, es exactamente el tipo de feature que corresponderia a una fase futura si el usuario la pide) |

**Hallazgo tecnico adicional**: el `DELETE` es un **hard-delete real**, no soft-delete, pese a que
`MarketingCampaign` hereda `is_deleted` de `SintelBaseModel` -- ese campo existe en la tabla pero
`MarketingSelector.list_campaigns_for_admin()` usa `.objects.all()` (manager por defecto, sin
override), y `ModelViewSet.destroy()` no esta sobreescrito, asi que llama al `.delete()` estandar de
Django (fisico). Esto **no es un bug** (es consistente con como se comporta el modelo hoy, y el plan
solo pide "DELETE / soft-delete" como alternativas validas, no exige soft-delete especificamente) pero
es una divergencia real frente a la convencion soft-delete que otros modelos del proyecto si usan
activamente -- documentado por si el usuario quiere alinearlo en una fase futura.

**Sin cambios de codigo en esta pasada** -- no se encontro ningun bug de wiring (a diferencia de la
Fase 1). `marketing.tests.py`: 58/58 OK, sin tocar.

---

## FASE 3 + FASE 4 + FASE 8 — Producto como base + beneficios (2026-09-23)

**[PARCIALMENTE CERRADO GAP #3]** La brecha modelo-real-vs-plan se redujo para el caso de Producto:

**Modelo** (`marketing/migrations/0006_marketingcampaign_source_content_type_and_more.py`):
- `MarketingCampaign.source_content_type` (FK nullable a `ContentType`) + `source_object_uuid`
  (UUIDField nullable) -- mismo patron que `shared.models.CatalogRelation` (content_type + uuid,
  NUNCA `GenericForeignKey`), decision tomada para dejar el esquema listo para Servicio/Renting
  (Fase 5/6) sin otro cambio de esquema. `None` en ambos = "Desde cero" (Fase 3).
- `CampaignBenefit` (modelo nuevo, FK a `MarketingCampaign`, `benefit_type` con 4 choices:
  `FREE_SHIPPING`/`FREE_INSTALLATION`/`DISCOUNT_PERCENT`/`DISCOUNT_FIXED`, `label` texto libre,
  `value` decimal nullable). **`FlashOffer` se evaluo y NO se reutilizo**: conceptualmente distinto
  (descuento con ventana de tiempo propia atado a UN variant especifico, no un beneficio de texto
  libre adjunto a una campana completa, potencialmente combinable con "Desde cero").

**Serializer** (`marketing/api/serializers.py::MarketingCampaignSerializer`): contrato de
escritura `source_type: 'product'|'none'` + `source_uuid` (ergonomico para el frontend, se resuelve
a `source_content_type`/`source_object_uuid` reales en `create()`/`update()`); lectura expone
`source_type`, `source_uuid`, y `source_preview` (el `ProductSerializer` completo del objeto real --
nombre, marca, precio con impuestos, descripcion, imagenes, variantes -- resuelto en vivo, **nunca
copiado a la campana**, cumple "no duplicar datos innecesariamente" de la Fase 4 del plan). `benefits`
es una lista anidada writable (replace completo en `update()`, no merge parcial).

**Sin Commands nuevos**: `MarketingCampaignViewSet` ya era (y sigue siendo) un `ModelViewSet` plano sin
capa de Commands para escritura (confirmado: `marketing/services/commands.py::MarketingCommands` solo
tiene `dispatch()`/`send_now()`, nada de create/update de campanas) -- no se introdujo una capa nueva
solo para esto, la logica de resolucion de `source`/`benefits` vive en el serializer (`create()`/
`update()` sobreescritos), consistente con el patron real ya existente en este ViewSet especifico.

**Frontend** (`CampaignForm.vue`): toggle "Desde cero"/"Desde catalogo", buscador de producto real
(reusa `useShopAdminStore().fetchProducts({search, is_active})`, el mismo endpoint admin ya usado por
`ProductList.vue` -- **no se creo un endpoint de busqueda paralelo**), preview del producto seleccionado
(nombre/marca/precio/imagen, todo del objeto real via `source_preview`), seccion de beneficios (4
checkboxes, 2 con input numerico para el valor del descuento). Estado nuevo vive fuera del schema yup
existente (`campaignValidationSchema` no se toco, sigue validando solo title/content/channels/
scheduled_at) -- se mezcla al payload en `handleSubmit`, cambio localizado sin tocar
`useFormValidation.js` (composable compartido).

**Verificado real**: HTTP `POST /api/v1/marketing/campaigns/` con un producto real de dev
(`camara IP`, marca `dahua`, `$350.000`) + 2 beneficios (`FREE_SHIPPING`, `FREE_INSTALLATION`) ->
`201`, `source_preview` devuelve el producto real completo (precio con desglose de IVA, 3 imagenes,
variante con SKU real). Caso "desde cero" (sin `source_type`) -> `source_type: "none"`,
`source_preview: null`. UUID de producto invalido -> `400` con mensaje claro, sin crash. Datos de
prueba limpiados despues. Vite recargo `CampaignForm.vue` sin errores (HMR limpio, sin overlay de
error, logs del contenedor sin lineas `error`/`fail`).

**Tests**: `marketing/tests.py::MarketingCampaignSourceAndBenefitsTestCase` (5 tests nuevos: desde
cero sin source, desde Producto con preview real, UUID invalido -> 400, creacion con beneficios
persistidos, update reemplaza beneficios). Suite completa: **63/63 OK** (58 previos + 5 nuevos).

**Explicitamente NO implementado en esa pasada** (decidido con el coordinador antes de empezar,
alcance intencional): Servicio/Renting como source (Fase 5/6 -- resuelto abajo), cantidad/
composicion multiple de items (Fase 7, ej. "2 camaras"), media imagen/video (Fase 11+), UI de
seleccion de canales reales en vez del checkbox actual con "SMS" fantasma (Fase 15, ver GAP #2, sin
tocar).

---

## FASE 5+6 (2026-09-23) — Servicio y Renting como base

Extiende el mismo patron de Fase 4 (`source_content_type`/`source_object_uuid`, contrato
`source_type`/`source_uuid`/`source_preview`) sin tocar el esquema otra vez -- ya estaba preparado
para esto desde Fase 4.

**Mapeo real (`_SOURCE_TYPE_TO_CTYPE`, `marketing/api/serializers.py`)**:
`'service' -> (technical_services, technicalservice)`, `'renting' -> (renting, equipmentvariant)`.
Renting referencia la **variante** (tarifa/modalidad/stock reales), no el Equipment -- el preview
igual expone el Equipment padre completo (`EquipmentSerializer`, incluye `images`/`category`/
`brand`/`commercial_options` con `modality`) con la variante seleccionada anidada en
`selected_variant` (`EquipmentVariantSerializer`). "Disponibilidad" (pedida por la Fase 6) se
resuelve como `stock` de la variante -- una campana no trae fechas de alquiler concretas, asi que
invocar `AvailabilityEngine` (motor de periodos) no tiene un anchor real; `stock` es el dato de
disponibilidad que el modelo si expone sin inventar contexto. Servicio usa
`TechnicalServiceDetailSerializer` (mismo nivel de detalle que `ProductSerializer` en Fase 4).

**Reuso, no duplicacion**: `TechnicalServiceDetailSerializer` y `EquipmentSerializer`/
`EquipmentVariantSerializer` ya existian (`technical_services/api/serializers.py`,
`renting/api/serializers.py`) -- ningun serializer nuevo del lado de catalogo. Buscadores del
frontend: Servicio reusa `useTechnicalServicesStore().fetchServices()` (**hallazgo real**:
`dashboard/services/` no soporta `?search=` server-side -- a diferencia de Productos y Equipment,
que si lo soportan -- se filtra client-side sobre la lista completa, documentado aqui en vez de
tocar el ViewSet de `dashboard`, fuera del alcance minimo de esta fase). Renting reusa
`useRentingCatalogAdminStore().fetchEquipment({search})` (endpoint SI soporta `search` real).

**Frontend**: `CampaignForm.vue` gano un selector "Tipo de Origen" (Producto/Servicio/Renting,
visible solo si `sourceMode === 'catalog'`) -- Servicio con buscador simple (nombre), Renting con
flujo de 2 pasos (elegir equipo -> elegir variante entre las del equipo, ya nested en la respuesta
de `fetchEquipment`, sin llamada adicional).

**Verificado real**: 2 campanas creadas via HTTP con datos reales de dev -- Servicio
(`TechnicalService` real "Servicio Fijo Prueba", categoria "CCTV & Seguridad") -> `201`,
`source_preview.name` correcto, variantes con pricing real (`calculated_price`/`price_info` con
desglose de IVA). Renting (`EquipmentVariant` real `SKU-SMOKE-UPDATED`, equipo "taladro") -> `201`,
`source_preview.name`/`selected_variant.sku`/`selected_variant.stock` correctos,
`commercial_options` con `modality: COMODATO` real. UUID invalido en ambos casos -> `400` limpio
(cubierto tambien por test automatizado). Datos de prueba eliminados despues.

**Tests**: `marketing/tests.py::MarketingCampaignServiceAndRentingSourceTestCase` (4 tests nuevos:
Servicio con preview real, Servicio UUID invalido -> 400, Renting con preview real +
`selected_variant`, Renting UUID invalido -> 400). Suite completa: **67/67 OK** (63 previos + 4
nuevos).

**Explicitamente NO implementado en esta pasada**: cantidad/composicion multiple (Fase 7), media
(Fase 11+), UI de canales reales (Fase 15) -- mismo alcance diferido que Fase 4.

---

## FASE 7 (2026-09-23) — Campañas compuestas

**Cambio de esquema real**: el campo singular `source_content_type`/`source_object_uuid` de
`MarketingCampaign` (Fase 3-6, nunca commiteado ni usado por datos reales -- confirmado 0
campañas con source seteado en dev antes de este cambio) fue **reemplazado**, no extendido, por
`CampaignItem` (FK a `MarketingCampaign`, `content_type` + `object_uuid` + `quantity`, mismo
patrón que `CatalogRelation`). Migración `0006` fue regenerada limpia (unapply + edit modelo +
`makemigrations` de nuevo) en vez de encadenar un add-then-remove, dado que no había datos reales
que preservar.

**Contrato de API**: `source_type`/`source_uuid`/`source_preview` (singular, escritura y
lectura) reemplazado por `items: [{type, uuid, quantity, preview}]` (lista, 0 a N elementos).
"02 cámaras" es **un** `CampaignItem` con `quantity=2` (misma referencia de catálogo, no dos
items separados) -- decisión explícita, documentada en el docstring de `CampaignItem`, análoga a
`OrderItem.quantity`. "Transporte gratis"/"Instalación gratis" quedaron como `CampaignBenefit`
(ya existían desde Fase 8), no como items de servicio -- son atributos de la campaña, no
referencias a catálogo.

**Verificado real — caso de aceptación completo del plan (sección 42), sin media/canales-UI**:
`POST /api/v1/marketing/campaigns/` con producto real de dev ("camara IP", `quantity=2`) + 2
`CampaignBenefit` (`FREE_SHIPPING`, `FREE_INSTALLATION`) -> `201`, `items[0].preview` con datos
reales del producto (precio, IVA, imágenes, stock). `GET` de la misma campaña -> `200`, mismo
contenido persistido. Dato de prueba eliminado (`204` en `DELETE`).

**Tests**: `marketing/tests.py::MarketingCampaignCompositeTestCase` (5 tests nuevos: 2 cámaras =
1 item con quantity=2, items de tipos mixtos producto+servicio, 0 items = desde cero, UUID
inválido en un item de una lista con más de uno, caso de aceptación completo). Las 2 clases de
test de Fase 4/5/6 se actualizaron al contrato `items` nuevo (mismos escenarios, nueva forma).
Suite completa: **72/72 OK** (67 previos + 5 nuevos).

**Frontend**: `CampaignForm.vue` -- el selector único de Producto/Servicio/Renting se convirtió
en una lista repetible ("Items de la Campaña" + sub-formulario "agregar item" con selector de
tipo, buscador, cantidad, botón agregar). Cada item agregado aparece como fila con imagen/nombre/
cantidad editable/botón quitar. Reusa los mismos buscadores y endpoints ya validados en Fase 4-6
(sin endpoints nuevos).

**Explícitamente NO implementado en esta pasada**: media (Fase 11+), UI de canales reales
(Fase 15), programar/enviar (Fase 17+).

---

## FASE 9+10 (2026-09-23) — Campaña desde cero (set completo) + contenido estructurado

**Campos nuevos en `MarketingCampaign`** (migración `0007_marketingcampaign_cta_label_and_more`):
`description` (resumen corto, distinto de `content`), `subheadline`, `cta_label`, `cta_url`,
`terms` (condiciones), `valid_from`/`valid_until` (vigencia de la OFERTA -- distinto de
`scheduled_at`/`sent_at`, que son de ENVÍO de la campaña, no de vigencia de la promoción).

**Mapeo del contrato conceptual del plan (sección 13) a campos reales, sin duplicar**:
`headline` → `title` (ya existía). `body` → `content` (ya existía, es el "Mensaje principal"
de Fase 9). `benefit_text` → **NO agregado**, `CampaignBenefit` (Fase 8) ya cubre esto
estructurado (`benefit_type`+`label`), un texto libre duplicado no tendría fuente de verdad
clara. `cta_label`/`cta_url`/`terms`/`subheadline` → nuevos.

**"Audiencia" (Fase 9)**: `target_audience` (JSONField) **ya existía en el modelo desde antes**
pero nunca se expuso en el serializer -- corregido (agregado a `fields`), sin campo nuevo ni
motor de segmentación construido (el plan permite un campo simple si no hay algo reusable; en
este caso ni siquiera hizo falta un campo simple, el JSONField de filtros ya cubre el caso).

**Validación**: `valid_until` anterior a `valid_from` → `400` con error claro en el campo
(`MarketingCampaignSerializer.validate()`). Sin sobre-validación (no se exige formato de URL
custom más allá del `URLField` estándar de DRF, no se limita el rango de fechas).

**Frontend**: `CampaignForm.vue` -- nueva sección con los 7 campos (todos opcionales, sin
schema de `vee-validate`/`yup` propio ya que ninguno es requerido -- refs simples mezcladas al
payload en `handleSubmit`, mismo criterio que `items`/`benefits` ya usaban). Aplican a
CUALQUIER campaña (con o sin `items` de catálogo), no solo a "desde cero" -- no hay razón real
para que una campaña con producto no tenga también su propio CTA/vigencia.

**Verificado real -- ejemplo EXACTO del plan (sección 12)**: `POST /api/v1/marketing/campaigns/`
con `title="02 cámaras + instalación y transporte gratis"`,
`content="Lleva 2 cámaras de seguridad y recibe instalación y transporte gratis."`,
`cta_label="Solicitar información"` -> `201`, todos los campos persistidos correctamente. `GET`
posterior -> `200`, mismo contenido. Dato de prueba eliminado (`204`).

**Tests**: `marketing/tests.py::MarketingCampaignScratchFieldsTestCase` (4 tests nuevos: el
ejemplo exacto del plan, los 7 campos nuevos persisten y se leen bien incluido
`target_audience`, todos son opcionales -- default vacío/`None`, `valid_until` antes de
`valid_from` -> `400`). Suite completa: **76/76 OK** (72 previos + 4 nuevos).

**Explícitamente NO implementado en esta pasada**: motor de segmentación de audiencia (no se
pidió, `target_audience` ya cubre filtros simples), media (Fase 11+), programar/enviar
(Fase 17+).

---

## FASE 11-14 (2026-09-23) — `CampaignMedia`: modelo, validación real, galería en el panel

**Investigado primero (Fase 0/Dependency Map)**: no existe un sistema de media compartido en el
proyecto -- cada dominio repite el patrón `<X>Image`/`<X>Video` (`shop.ProductImage`/
`ProductVideo`, `renting.EquipmentImage`, `technical_services.ServiceVideo`). `CampaignMedia`
replica ese patrón, con la diferencia deliberada de que el plan pide UN modelo para ambos tipos
(no 2 separados como Shop) -- por eso usa un `FileField` genérico + `media_type`, no un
`ImageField` (que rompería con archivos de video).

**Validación real implementada** (`marketing/services/commands.py`, sin librerías nuevas --
Pillow ya es dependencia del proyecto vía `ImageField`):
- Imagen: `PIL.Image.open().verify()` decodifica el contenido real (no confía en la extensión ni
  en el `Content-Type` declarado por el cliente) -- rechaza un `.txt` renombrado a `.jpg`.
  Formatos válidos: JPEG/PNG/WEBP. Dimensiones reales leídas del archivo. Tamaño máximo
  configurable (`MARKETING_MEDIA_MAX_IMAGE_MB`, default 5MB). Hash SHA-256 real (stdlib
  `hashlib`, sin dependencia nueva) para deduplicación futura.
- Video: MIME/extensión validados (solo `.mp4`/`video/mp4`), tamaño máximo configurable
  (`MARKETING_MEDIA_MAX_VIDEO_MB`, default 100MB). **`duration`/`width`/`height` quedan SIN
  VALIDAR a propósito** -- no existe en el proyecto ninguna librería de metadata de video
  (confirmado: `ffmpeg-python`/`moviepy`/`pymediainfo` ausentes de `requirements.txt`) y el plan
  no exige agregar una dependencia nueva solo para esto ("no exige librería específica").
  **Gap documentado, no corregido**: si se necesita validar duración de video en el futuro, hay
  que evaluar agregar `ffmpeg-python` o equivalente como decisión aparte.

**Procesamiento SÍNCRONO** (sin Celery) -- confirmado que ningún dominio del proyecto usa una
task async para el upload de imagen/video en sí (grep sin resultados en `shop`/`renting`/
`technical_services`), consistente con "no duplicar arquitectura".

**Subida/gestión vía acciones dedicadas del ViewSet**, NUNCA como lista anidada writable del
serializer principal (a diferencia de `items`/`benefits`, que sí son full-replace-on-provide) --
esto es lo que garantiza la regla del plan "no debe perder medios existentes al editar otros
campos": un `PATCH` de texto normal ni siquiera toca la relación `media`. Mismo patrón de subida
multipart que `shop.dashboard.api.views::ProductViewSet.add_image` (`request.FILES.get(...)`,
delegado a un Commands, `201`).

**Bug real encontrado y corregido durante la implementación**: `POST .../media/reorder/`
devolvía `405 Method Not Allowed`. Causa raíz: DRF genera las rutas de `@action` ordenando por
`inspect.getmembers()` -- es decir, **alfabéticamente por nombre de método**, no por orden de
declaración en el archivo (confirmado empíricamente: reordenar el código no tuvo ningún efecto).
`delete_media` (con un regex de `media_uuid` genérico `[^/.]+`) queda alfabéticamente antes que
`reorder_media`, así que intercepta primero la URL `/media/reorder/` (matchea "reorder" como si
fuera el uuid), encuentra que el método POST no está permitido ahí (es DELETE-only) y devuelve
405 sin intentar la otra ruta. **Corregido restringiendo el regex de `media_uuid` al shape real
de un UUID** (`[0-9a-fA-F]{8}-...`), que nunca puede matchear la palabra "reorder" -- fix robusto
independiente de nombres/orden, no un parche cosmético. Mismo tipo de problema (rutas literales
vs. parametrizadas del mismo router compitiendo por el mismo path) ya visto antes en esta sesión
con `/orders/orders/create-from-cart/` (ahí el mecanismo era otro: `create_from_cart` vs.
`retrieve()`, pero la misma familia de bug).

**Frontend**: sección nueva en `CampaignForm.vue` (galería inline, sin componente reusable --
`BaseGallery.vue` existente es de solo-visualización para el cliente final, lightbox/zoom, no
sirve para admin edit/upload/reorder). Requiere que la campaña ya exista (`props.campaign.uuid`)
-- en modo "create" se avisa "guarda la campaña primero", sin bloquear el resto del formulario.
Reordenamiento con botones subir/bajar (sin librería de drag-and-drop, más simple y suficiente
para una galería típicamente corta). Subir/eliminar/activar-desactivar/reordenar actúan de
inmediato contra el backend (no esperan al submit del formulario), a diferencia de items/
benefits -- inherente a que un archivo no puede "esperar" dentro del payload JSON del submit.

**Bug propio encontrado y corregido en el mismo cambio**: `marketingAdmin.js::_mutate()`
descartaba el valor de retorno de la mutación (`return {ok: true}` sin el `data`) -- el nuevo
handler de subida de media necesitaba el objeto creado (uuid/preview) para agregarlo a la
galería local sin recargar toda la campaña. Corregido (`return {ok: true, data}`), cambio
aditivo verificado seguro (los 2 callers existentes -- `createCampaign`/`updateCampaign` en
`CampaignForm.vue` -- solo leen `.ok`, nunca dependían de la ausencia de `.data`).

**Tests**: `marketing/tests.py::MarketingCampaignMediaTestCase` (10 tests nuevos: subida de
imagen válida con dimensiones reales, subida de video MP4 válido, archivo falso con MIME
incorrecto rechazado, video con extensión incorrecta rechazado, límite de tamaño configurable
rechaza correctamente, eliminar, activar/desactivar, reordenar, editar campos de texto no toca
la galería existente, el detalle de la campaña incluye la galería). Suite completa: **86/86 OK**
(76 previos + 10 nuevos).

**Smoke test real (HTTP, no solo test client de Django)**: `POST
.../campaigns/<uuid>/media/` con un PNG real generado con Pillow (200×100) -> `201`, dimensiones
reales confirmadas en la respuesta. `GET` de la campaña -> `200`, galería incluida con la URL
real del archivo servido (`/media/marketing/campaigns/...`). Dato de prueba (campaña + archivo
en disco) eliminado al terminar.

**Explícitamente NO implementado en esta pasada**: validación de duración/dimensiones de video
(gap documentado arriba), soporte de video por URL externa (YouTube/Vimeo, el plan solo pide
"imagen"/"video" sin mencionar fuentes externas), programar/enviar (Fase 17+), UI de selección
de canales reales (Fase 15+, no tocada).

---

## FASE 15-20 (2026-09-23) — Canales, contrato de tracking, Enviar ahora, difusión real

**Fase 15 — SMS fantasma confirmado y corregido**: `marketing/channels/registry.py::
CHANNEL_REGISTRY` tiene exactamente 8 canales reales (email/whatsapp/facebook/instagram/
youtube/tiktok/x/google_business) -- NO existe ni existió nunca un adapter de SMS. El checkbox
"SMS" de `CampaignForm.vue` se quitó. **Hallazgo mayor no anticipado**: la UI solo mostraba
Email/WhatsApp/SMS -- los 6 canales de broadcast reales (facebook/instagram/youtube/tiktok/x/
google_business) nunca se mostraban en absoluto, pese a tener adapter real y funcional desde
antes. Agregados los 6 checkboxes faltantes.

**Fase 16 — el contrato de tracking YA EXISTÍA, sin construir nada nuevo**: `CampaignLog`
(`marketing/models.py:274`) es exactamente el contrato conceptual que el plan pide en su sección
19 (`campaign`, `channel`, `status` vía `is_sent`/`error_message`, `scheduled_at` implícito en el
dispatch, `sent_at`, `error`) -- con idempotencia real (`unique_together=(campaign, channel,
recipient)`), y ya expuesto en el serializer (`logs`, campo anidado read-only). No se creó
ningún modelo nuevo. Correcto no reusar `NotificationLog`: el propio hallazgo de la auditoría de
Email de esta sesión ya documentó que el Campaign Engine es un sistema paralelo por diseño (no
notificaciones transaccionales 1:1).

**Fase 17 — `status` derivado, sin migración nueva**: `MarketingCampaignSerializer.get_status()`
calcula `DRAFT`/`RUNNING`/`SCHEDULED`/`COMPLETED` a partir de `is_completed`/`logs.exists()`/
`scheduled_at` ya existentes -- evita un enum de BD paralelo que se pudiera desincronizar. NO se
implementaron botones "Pausar"/"Cancelar" en esta pasada (el mecanismo de dispatch async actual
no tiene un punto de cancelación real una vez encolada la task en Celery -- cancelar una task ya
en cola/ejecución es una capacidad que el proyecto no tiene hoy para ningún dominio, no solo
marketing; implementarla sería una funcionalidad nueva de infraestructura, fuera del alcance
"cambio mínimo" de este plan. Documentado como gap, no construido).

**Fase 18-20 — difusión real, mecanismo YA EXISTÍA (`MarketingCommands.dispatch()`), solo se
conectó al CRUD manual**: hasta esta fase, `dispatch()` solo lo llamaba
`marketing/agent/brain.py` (el agente IA autónomo), nunca un endpoint manual del admin. Se agregó
`POST /api/v1/marketing/campaigns/<uuid>/send/` (`MarketingCampaignViewSet.send_campaign`,
`IsAdminUser`). Cambio aditivo mínimo a `MarketingCommands.dispatch()`: nuevo parámetro opcional
`channels` (subconjunto a despachar, default `None` = todos los canales de la campaña, igual
comportamiento que antes) -- necesario porque los canales de broadcast (sin `recipient` real,
usan el sentinel `"broadcast"`) y los canales directos (email/whatsapp, necesitan un `recipient`
real) no pueden despacharse en la misma llamada con el mismo `recipient`. El agente IA
(`brain.py`) sigue llamando sin este argumento, comportamiento idéntico al de antes.

**Comportamiento del endpoint `send`**: canales de broadcast se despachan siempre (sentinel
`"broadcast"`, mismo criterio ya usado por el agente IA, seguro porque esos adapters ignoran
`recipient`). Canales directos (email/whatsapp) solo se despachan si el request incluye
`recipient` explícito -- si no, se omiten y se reportan en `skipped_channels` (nunca se disparan
a ciegas a un destinatario inventado).

**Prueba real controlada (HTTP real, Celery real, SMTP real)**: campaña de prueba con canal
`email`, `POST .../send/` con `recipient=contacto@sintel.net.co` (destinatario ya autorizado en
la auditoría de Email de esta sesión) -> `200`, `CampaignLog` creado, tarea Celery real
`marketing.send_via_channel` ejecutada por el worker real (confirmado en
`docker logs ecommerce_sintel_celery_worker`) -> intento SMTP real -> **mismo error 535 de
GAP #8 de la auditoría de Email** (credenciales de Gmail de desarrollo invalidas, NO un bug
nuevo) -- capturado limpiamente en `CampaignLog.error_message`, sin excepción sin capturar, sin
pérdida silenciosa. Esto prueba que el pipeline completo (endpoint -> dispatch -> Celery ->
adapter -> SMTP) funciona correctamente de punta a punta; el único bloqueo real es de
infraestructura de dev ya conocido, no de este código. Canales de broadcast/WhatsApp
**deliberadamente no disparados de verdad** (restricción explícita: no enviar a redes sociales o
WhatsApp reales) -- verificados solo con tests mockeados (`send_via_channel_task.delay`
patcheado), confirmando que se encolan con el `recipient`/`channel` correctos.

**Tests**: 7 nuevos (`MarketingCampaignSendAndStatusTestCase`). Suite completa: **93/93 OK**
(86 previos + 7 nuevos). Dato de prueba (campaña `SMOKE-TEST Fase 15-20`) eliminado.

---

## FASE 21-23 (2026-09-23) — IA complementaria, previsualización, permisos

**FASE 21 (AI/AgentRun)**: `marketing/agent/brain.py::MarketingAgent.run()` SÍ tiene una
capacidad real de generación de contenido -- orquesta `MarketingSelector.get_consolidated_
dashboard()` -> `LLMRouter.complete()` (soporta OpenAI/Anthropic/Gemini) -> crea y despacha una
`MarketingCampaign` completa (título/contenido/canales/audiencia), todo en un solo ciclo
autónomo, sin paso de confirmación humana intermedio hoy. **Pero no está operativa en este
entorno**: `MARKETING_AGENT_PROVIDER=gemini` en `.env`, y las 3 claves (`OPENAI_API_KEY`/
`ANTHROPIC_API_KEY`/`GEMINI_API_KEY`) son placeholders literales (`sk-your_openai_key_here`,
etc.) -- ninguna llamada real a un LLM puede completarse en dev hoy. Por esto **no se conectó
ningún botón "✨ Mejorar copy"/"✨ Generar CTA" a la UI en esta pasada**: construir un endpoint
nuevo que solo puede fallar (sin credenciales reales) violaría el criterio "no fabricar un botón
que llame a algo que no funciona". El código existente (`LLMRouter`) es reutilizable el día que
se configure una clave real -- no requiere ningún cambio de arquitectura para conectarse a un
"Mejorar copy" futuro, solo un prompt nuevo y una acción de ViewSet, ambos triviales sobre la
infraestructura ya construida.

**FASE 22 (Previsualización)**: hallazgo real corregido -- `MarketingCommands.send_now()` (el
envío real) solo construía `CampaignMessage(subject=campaign.title, body=campaign.content)`,
ignorando por completo `items`/`benefits`/`cta_label`/`cta_url`/`terms` agregados en Fase 3-10.
El mensaje que realmente salía por cualquier canal nunca reflejaba nada más que título+contenido
base, sin importar cuántos items/beneficios/CTA configurara el admin. Corregido extrayendo
`MarketingCommands.build_message(campaign, recipient)` (único lugar que arma el cuerpo final,
incluye items con cantidad, beneficios, CTA con URL, y términos) -- usado tanto por `send_now()`
(envío real) como por el nuevo endpoint `GET .../campaigns/<uuid>/preview/` (`IsAdminUser`,
sección "## FASE 21-23" arriba), que devuelve el mensaje real por cada canal seleccionado. Nunca
puede desincronizarse preview vs. envío real porque es literalmente el mismo método.
Verificado con HTTP real: campaña con 1 item (cantidad 2), 2 beneficios, CTA y términos ->
`GET .../preview/` devuelve el `body` completo con todo compuesto correctamente; campaña "desde
cero" sin items -> `body` es solo el `content` libre, sin líneas vacías espurias.

**FASE 23 (Permisos)**: verificado, sin bugs -- `MarketingCampaignViewSet.permission_classes =
[IsAdminUser]` a nivel de clase, sin ningún `@action` que lo sobreescriba (confirmado por
`grep`), aplica automáticamente a las acciones agregadas en Fase 11-22 (`upload_media`,
`delete_media`, `reorder_media`, `toggle_media`, `send_campaign`, `preview`) sin que nadie las
haya declarado explícitamente -- correcto por herencia de DRF, no por casualidad. `FlashOfferViewSet`
sigue en `AllowAny` (intencional, vitrina pública). Prueba real: `test_preview_requiere_admin`
(cliente CUSTOMER real autenticado) -> `403`, no `500` ni `200`.

**Tests**: 3 nuevos (`MarketingCampaignPreviewTestCase`). Suite completa: **96/96 OK**
(93 previos + 3 nuevos). Dato de prueba (campaña `SMOKE-PREVIEW-TEST`) eliminado.
