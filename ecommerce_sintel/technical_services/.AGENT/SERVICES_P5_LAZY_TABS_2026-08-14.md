# P5 -- Lazy-mount de pestanas en ServiceForm.vue

Plan "Rediseno ServiceForm + Content/Media", P5 (prioridad explicita del
usuario, ejecutada tras cerrar FASE 7). Objetivo: evitar que las 14
pestanas de EDIT disparen todas su fetch inicial al abrir el formulario,
cuando el admin solo esta mirando "General".

## Problema real (confirmado con Network antes del fix)

Cada una de las 14 pestanas de EDIT (`Imagen, Variantes, Costos, Paquetes,
FAQ, Marketing, Incluye, No incluye, Requisitos, Ficha tecnica,
Documentacion, Videos, Proceso, Contenido del Servicio`) usaba solo
`v-show="tab === 'x' && localMode === 'edit'"` -- Vue monta TODOS los
`v-show` de una vez (solo alterna `display:none`), asi que abrir el
formulario de edicion montaba las 14 al mismo tiempo. La mayoria de sus
subcomponentes disparan su fetch en `onMounted` o en un
`watch(props.entityUuid, fetch, {immediate:true})` (ej.
`ContentBlocksTab.vue` linea ~366), sin condicionarlo a si la pestana esta
visible. Resultado: cada apertura del formulario disparaba ~10-13 requests
GET simultaneos aunque el usuario solo viera "General".

## Fix -- lazy-mount-then-preserve (`v-if` + `v-show`)

`ServiceForm.vue`:
- `visitedTabs = reactive(new Set(['general']))` -- Set reactivo (no
  `ref`, Vue 3 no reacciona a `.add()`/`.has()` sobre un Set dentro de un
  `ref`) que registra que pestanas se visitaron en la sesion de edicion
  actual.
- `watch(tab, (t) => visitedTabs.add(t))` -- registra cualquier cambio de
  `tab.value`, sea por click en el nav o programatico (el `submit()` de
  CREATE cambia `tab.value = 'variants'` tras crear el servicio; este
  watch lo captura igual, sin caso especial).
- Se reinicia (`visitedTabs.clear(); visitedTabs.add('general')`) en el
  mismo punto donde ya se reseteaba `tab.value = 'general'`, dentro del
  `watch([() => props.item, () => props.mode], ...)` -- cambiar de
  servicio no debe arrastrar pestanas "visitadas" del servicio anterior.
- Cada una de las 14 pestanas de EDIT paso de
  `v-show="tab === 'x' && localMode === 'edit'"` a
  `v-if="localMode === 'edit' && visitedTabs.has('x')" v-show="tab === 'x'"`
  -- el `v-if` retrasa el primer montaje a la primera visita; una vez
  montada, el `v-show` la mantiene en el DOM (no se desmonta al volver a
  "General") para no perder borradores en curso (ej. la cola
  `pendingFiles` de `ServiceGalleryManager`, o un item a medio llenar en
  `CatalogListManager`).

`ServicePackagesPanel` (pestana "Paquetes") es la unica excepcion
deliberada: su fetch (`packagesStore.fetchPackages(item.uuid)`) sigue
siendo eager, disparado en el mismo `watch` de sincronizacion del padre --
alimenta el badge con el conteo de paquetes que se muestra en el propio
boton de la pestana (`Paquetes <badge>`), asi que debe estar disponible
aunque el admin nunca abra esa pestana.

## Verificado en navegador real (Network, no solo lectura de codigo)

Contra "Mantenimiento Preventivo" (servicio real con datos):
1. **Apertura del formulario de edicion**: solo dispararon
   `service-categories/`, `service-levels/`, `services/` (listado) y
   `service-packages/?service=...` (el badge, eager por diseno). Ningun
   `service-variants/`, `service-faqs/`, `service-content-blocks/`,
   `service-included-items/`, etc.
2. **Click en "Variantes"**: disparo `service-variants/?service=...` por
   primera vez.
3. **Volver a "General" y click en "Variantes" de nuevo**: **cero**
   requests nuevos a `service-variants/` -- el componente sigue montado,
   no se re-fetchea.
4. **Click en "Contenido del Servicio"**: disparo
   `service-content-blocks/?service=...` (una sola vez) y el listado
   renderizado mostro exactamente **18 bloques** (confirma tambien el fix
   de FASE 7 que quito `support`, ver
   `SERVICES_FASE7_DETALLE_CUSTOMER_2026-08-14.md`).
5. **Caso limite -- creacion**: se creo un servicio de prueba
   ("P5 Lazy Test Service") desde cero. Tras `submit()`, el formulario
   cambia de CREATE a EDIT y navega automaticamente a "Variantes"
   (`tab.value = 'variants'`, fuera del watcher de sincronizacion
   padre/hijo) -- el `watch(tab, ...)` lo capturo igual, `VariantsTab` se
   monto por primera vez con el nuevo `service-uuid` y disparo su fetch
   correctamente (`service-variants/?service=<uuid-nuevo>`). Servicio de
   prueba eliminado al terminar.

No se corrio un build/lint de frontend dedicado (este repo no tiene suite
de tests unitarios de Vue) -- la verificacion es la establecida en toda la
sesion para cambios de frontend: uso real en navegador + inspeccion de
Network, sin regresiones visibles ni errores nuevos en consola.

## P6 -- Preview Admin -> Customer

Mismo incremento, prioridad siguiente del plan. No existia ningun patron
de "vista previa" en ningun formulario admin del proyecto (Shop/Renting/
Services, verificado por busqueda) -- se replico el unico precedente
cercano encontrado (`HomeConfigView.vue`, link plano `target="_blank"` con
icono `bi-eye`, "Ver sitio").

`ServiceForm.vue` gano un link "Vista previa (cliente)" (`btn btn-sm
btn-outline-secondary`, arriba del nav de pestanas), visible solo en modo
EDIT y con `localItem.uuid` disponible, apuntando a
`/servicios/{uuid}` -- la pagina publica real (`ServiceDetailContent.vue`),
sin componente ni modal nuevo. Se abre en pestana nueva para no perder el
formulario admin en curso.

Verificado en navegador: el link aparece con el `href` correcto en modo
EDIT (`/servicios/e0d81ab7-...`), y esta ausente en modo CREATE (no hay
`uuid` todavia).

## P7 (parcial) -- regresion real encontrada y corregida al validar P5

Al validar manualmente las 14 pestanas de EDIT una por una tras el cambio
de P5 (parte de P7, "validacion E2E"), "Costos" mostro
**"Crea al menos una variante para ver los detalles de costos."** para un
servicio que si tenia una variante -- pero solo quando se abria "Costos"
**sin haber visitado "Variantes" antes** en esa misma sesion de edicion.

Causa: `CostosTab.vue` nunca hacia su propio fetch -- leia `variants`
directo del store compartido (`storeToRefs(useTechnicalServicesStore())`)
asumiendo implicitamente que `VariantsTab.vue` (unico componente que llama
`store.fetchVariants(serviceUuid)`, en su `onMounted`) ya lo habia
poblado. Antes de P5 esto "funcionaba" porque ambas pestanas montaban
siempre juntas (`v-show`); con el lazy-mount de P5 dejo de ser cierto --
un admin puede legitimamente abrir "Costos" primero.

**Fix:** `CostosTab.vue` ahora tambien llama
`store.fetchVariants(props.serviceUuid)` en su propio `onMounted`,
igual que `VariantsTab.vue` -- deja de depender del orden de visita.
Revisadas las demas 12 pestanas (`grep` de `storeToRefs`/
`useTechnicalServicesStore` en todo `modules/technical_services/`):
ninguna otra tiene este patron -- las que usan el store solo invocan
acciones de mutacion (`PricingSourceCard.vue`), no leen estado
pre-poblado por otra pestana.

Verificado en navegador: reabierto el formulario de "Mantenimiento
Preventivo" y clickeado "Costos" **directamente** (sin pasar por
"Variantes") -- ahora muestra la variante real
(`SVC-mantenimiento-preven-MQPDGJHZ · FIXED`) en vez del mensaje de "sin
variantes". Las 15 pestanas (General + 14 de EDIT) se revisaron una por
una tras el fix: todas renderizan contenido real o un estado vacio
legitimo, sin pantallas en blanco ni errores nuevos en consola.
