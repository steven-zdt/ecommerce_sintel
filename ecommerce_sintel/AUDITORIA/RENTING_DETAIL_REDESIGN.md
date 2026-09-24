# Rediseno PDP Publica (Renting) — Fase 2: 3 columnas (2026-09-16)

Ver [RENTING_DETAIL_BASELINE.md](RENTING_DETAIL_BASELINE.md) (Fase 0) para el
inventario completo de la arquitectura real. Este documento cubre lo
efectivamente implementado en la Fase 2 (layout), la decision explicita del
usuario de posponer el panel de reserva interactivo a una Fase 3 separada, y
un bug real de backend encontrado y corregido en el camino.

## Alcance de esta fase (decision explicita del usuario)

La auditoria de Fase 0 encontro que, a diferencia de Shop (donde
`ProductPurchaseCard.vue` ya existia completo), Renting **no tiene ningun
componente de reserva interactivo hoy** -- ni selector de variante, ni
toggle dia/hora, ni selector de fechas, ni llamada a disponibilidad por
periodo. Toda esa logica vive solo dentro de `RentalBookingWizard.vue`.
Construir el "Panel de Reserva" completo del brief original (variante +
modalidad + periodo + disponibilidad verificada + resumen de costo) es una
**funcionalidad nueva real**, no una reorganizacion de grid.

Se le presento esta disyuntiva al usuario, que eligio explicitamente:
**Fase 2 primero (solo layout, con los datos que ya trae el detalle hoy)**,
dejando el panel interactivo para una Fase 3 aparte con su propio alcance.
Este documento cubre solo la Fase 2.

## Componente real modificado

`frontend/src/views/customer/detail/RentingDetailContent.vue` (renderizado
por `PublicDetailView.vue` en la ruta real `alquiler/:uuid`). Un solo fetch
real (`GET /api/v1/unified/detail/{uuid}/?module=renting`), sin cambios.

## Equipo usado para validar

**El UUID del brief (`d443139b-7b94-4c41-9fed-9e96c409ac7f`) no existe en la
base de datos de dev** (mismo patron que la mision Shop, confirmado por ORM).
Se uso `693e2d7e-b260-4206-9058-4566b08e4e6a` ("Grua Hidraulica 20T Demo",
marca CAT Demo, 2 imagenes, 2 variantes, precio dia+hora, features/specs/
included/excluded/FAQ/reviews/video reales) -- el equipo real mas rico
encontrado en dev para probar el layout con contenido real.

## Bug real encontrado y corregido (bloqueaba el equipo elegido para validar)

Al intentar cargar el detalle de "Grua Hidraulica 20T Demo" por primera vez,
el endpoint devolvia **500 real**: `ValueError: The 'thumbnail' attribute has
no file associated with it`. Causa raiz real en
`renting/services/presenters.py:407`:
`thumbnail=getattr(video, 'thumbnail', None)` -- el atributo `thumbnail` de
un `RentalVideo` SIN archivo subido no es `None`, es un `FieldFile` vacio (el
atributo existe, `getattr` nunca cae al default), y ese objeto crudo rompia
la serializacion JSON al llegar hasta el encoder de DRF. **Esto afecta a
CUALQUIER equipo real que tenga un video sin thumbnail subido -- un bug de
produccion real, no solo un problema de datos de prueba.**

Fix aplicado: `thumbnail=video.thumbnail.url if video.thumbnail else None`.
Verificado: el mismo endpoint que devolvia 500 ahora devuelve 200 con el
campo `thumbnail: null` correctamente. `manage.py check` limpio (mismo
warning preexistente de siempre, no relacionado).

## Cambios reales (Fase 2)

### Grid de 3 columnas

Antes: `col-lg-5` (galeria + trust-grid + tarjeta de disponibilidad
informativa) + `col-lg-7` (badges/titulo/urgency/quick-specs + el
"package-panel" -- precio + 1 boton -- anidado al final del mismo bloque).
Ahora, 3 columnas hermanas (mismo patron que Shop, 4/5/3 en `lg+`):

- **Columna 1** (`col-12 col-md-6 col-lg-4`): `BaseGallery` (ahora con
  `lightbox` activado, mismo prop opt-in que se agrego para Shop -- reuso
  directo, cero codigo nuevo en `BaseGallery.vue`) + trust grid.
- **Columna 2** (`col-12 col-md-6 col-lg-5`): badges/chips, rating, titulo,
  descripcion, mensajes de marketing, urgency banner, discount badge,
  beneficios destacados, quick-specs (marca/categoria/variantes/stock).
- **Columna 3** (`col-12 col-lg-3`): panel "Valor del alquiler" -- **precio
  por dia Y por hora simultaneos** (el modelo dual del brief seccion 12 es
  real, ambos vienen en el DTO), disponibilidad (status + detalle, tal como
  ya lo resuelve el backend HOY -- sin inventar un chequeo por periodo que
  no existe todavia), boton "Reservar ahora" (mismo `RouterLink` de antes,
  mismo destino `rental-request`, sin cambios de comportamiento) y
  "Consultar fechas exactas" (movido aqui desde la columna de galeria, mismo
  link de siempre).

**Responsive:** identico patron a Shop -- `lg+` 3 columnas (galeria y panel
sticky), `md` galeria+info a 2 columnas, `<768px` apilado completo en su
orden natural del DOM (galeria, info, panel -- precio/disponibilidad/CTA
quedan antes de las secciones full-width de Descripcion/Especificaciones/
Reseñas, mismo criterio que Shop).

### Nada mas se toco

Sin cambios en el contrato de API, en el CTA (mismo texto/destino/logica),
en `RentalBookingWizard.vue` (no se toco, sigue siendo el unico lugar con
logica real de variante/fechas/disponibilidad/costo), en reviews/FAQ/specs/
features/incluye-no incluye (mismos componentes reusados, mismo orden).

## Gaps reales que NO se resolvieron en esta fase (documentados, no fabricados)

1. **El panel de reserva interactivo completo (Fase 3)** -- variante,
   modalidad dia/hora, fechas, chequeo real de disponibilidad por periodo
   (endpoint ya existe y es seguro: `GET renting/equipment/{uuid}/
   check-availability/`, ver baseline seccion 4), resumen de costo. Decision
   explicita del usuario de posponerlo, no un olvido.
2. **COMODATO y `EquipmentLogisticsConfig`** -- reales y ya serializados,
   pero solo en el DTO "rico" (`GET renting/equipment/{uuid}/detail/`) que el
   frontend publico hoy no consume (usa el DTO unificado, mas liviano). Mostrar
   modalidad/logistica real requeriria migrar de DTO o sumar una segunda
   llamada -- fuera de alcance de un rediseno de layout puro, ver baseline
   gap 6.
3. **`EquipmentFeatureTable.vue`/`EquipmentSpecificationTable.vue` existen
   pero `RentingDetailContent.vue` los reemplaza con markup inline propio**
   (`feature-card`/`spec-group-card` a mano) -- limpieza real disponible, no
   se toco en esta fase para no ampliar el diff mas alla del layout.
4. **Selector de variante** -- no se agrego en esta fase (parte del panel
   interactivo de Fase 3). El equipo de prueba SI tiene 2 variantes reales
   (`Variantes: 2` visible en quick-specs), pero el panel de precio sigue
   mostrando el precio agregado del equipo (`pricing.formatted_price_per_day`
   /`_hour`), no un precio por variante -- correcto para esta fase, ya que
   ninguna variante esta seleccionada todavia.

## Verificacion real ejecutada (dev, nunca prod)

- `docker exec ecommerce_sintel_frontend npx playwright test
  renting-pdp-redesign` -- **9/9 passed**: carga sin errores de consola ni
  requests fallidos; 3 columnas confirmadas via bounding boxes reales;
  panel muestra precio dia+hora+disponibilidad y el CTA real navega (redirige
  a `/login` sin sesion, comportamiento preexistente correcto -- la ruta del
  wizard exige auth); lightbox abre/cierra (reuso real del prop agregado
  para Shop); **0 overflow horizontal** en los 5 viewports pedidos, con
  screenshot real guardado por viewport.
- `docker exec ecommerce_sintel_frontend npx playwright test
  pdp-regression-check pdp-redesign renting-pdp-redesign` (los 3 specs de PDP
  juntos) -- **21/21 passed**: Shop y Services (que comparten `BaseGallery`/
  `PublicDetailView`) siguen sin errores tras el cambio de Renting.
- Revision visual manual del screenshot desktop 1440: 3 columnas reales,
  precio dia/hora, disponibilidad, CTA, y todas las secciones inferiores
  (features, incluye/no incluye, specs, requisitos, video -- con el bug de
  thumbnail ya corregido, se ve el placeholder de video correctamente en vez
  de un 500), documentacion, FAQ, reseñas -- coherente con el diseño
  objetivo.

## No ejecutado en esta fase (limite de alcance, no fabricado como hecho)

- Nada de disponibilidad-por-periodo, seleccion de variante, ni calculo de
  costo -- todo eso es la Fase 3, todavia no iniciada.
- Medicion formal de performance / accesibilidad con lector de pantalla real
  -- mismo alcance que se documento para la mision Shop.
