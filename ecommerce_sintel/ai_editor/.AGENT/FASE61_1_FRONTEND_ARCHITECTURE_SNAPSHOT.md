# FASE 61.1 -- FRONTEND ARCHITECTURE SNAPSHOT

**Fecha:** 2026-08-12. **Alcance:** solo lectura -- 0 archivos modificados. Metodo: Knowledge
Graph como primera fuente (`ai_editor.graph_client`), contrastado contra codigo real
(`frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md`, verificado linea por linea 2026-07-18,
y lectura directa de `cart/api/urls.py`/`renting/api/views.py`).

---

## 1. Arquitectura real (confirmada, doc existente + grafo)

SPA unica (Vue 3.5 + Vite 8, `<script setup>` exclusivo), un unico `router.js` sirve DOS
dominios (portal cliente bajo `CustomerLayout`, panel admin bajo `AppShell`, ~90 rutas). Un
unico cliente Axios (`useApi.js`, singleton) con interceptor de refresh JWT. 29 stores Pinia
(sintaxis Options), 25-26 composables, `services/` con wrappers delgados opcionales por dominio.

```
Browser
   |
Vue Components (views/*, modules/*, components/*)
   |
Pinia Stores (29) <-> Composables (useApi, useAuth, useEnums, ...)
   |
useApi.js (Axios singleton, Bearer token, refresh automatico)
   |
Django REST Framework (21 apps, 150 endpoints registrados)
```

Confirmado por grafo: `kg_node_types` incluye `FrontendView: 84`, `FrontendComponent: 321`,
`PiniaStore: 29`, `Composable: 26`, `Route: 89` -- coincide con el conteo del doc existente
(29 stores, ~90 rutas). Sin discrepancia de conteo global.

---

## 2. Cadena REAL verificada #1: Backend -> API -> Frontend -> Tests

Consulta real (`graph_client.resolve_change('EquipmentViewSet.check_availability')`):

```
ViewSet:     EquipmentViewSet (renting/api/views.py)
             actions: get_object, check_availability, availability, calendar, timeline,
                      register_document_download, reviews, review, full_detail
   |
Endpoint:    api/v1/renting/equipment  (GET/POST/PUT/PATCH/DELETE, basename=equipment-rental)
   |
Frontend consumers (7 confirmados por el grafo, no inventados):
   - RentalDetailView.fetchDetail        -> GET renting/equipment/${uuid}/detail/
   - RentalCatalogView.fetchEquipment    -> GET renting/equipment/
   - useCatalogQuoteWizard.fetchEquipment -> GET renting/equipment/
   - bookingService.equipment (services/renting/bookingService.js) -> GET renting/equipment/${uuid}/
   - availabilityService.check (services/renting/availabilityService.js) -> GET .../check-availability/
   - availabilityService.get                                            -> GET .../availability/
   - CatalogQuoteWizardView (composable-based)
   |
Tests: renting/tests_catalog.py (RentalCatalogPublicPayloadTestCase,
       EquipmentReviewFlowTestCase, x4 casos reales)
```

**Confirma que el grafo SI resuelve la cadena completa Backend->API->Frontend->Tests cuando se
consulta desde el lado BACKEND (ViewSet/Endpoint).** Importante para FASE 61.2: elegir el caso
de prueba anclado en una entidad backend (Model/Service/ViewSet), no en una View de frontend
aislada -- ver hallazgo (A) abajo.

## 3. Cadena REAL verificada #2: Component -> Composable -> API Client -> Endpoint

Mismo resultado de arriba, leido en la otra direccion:

```
Component:  RentalCatalogView.vue
   |
Composable: useCatalogQuoteWizard (composables/useCatalogQuoteWizard.js, hook_calls: ['useApi'])
   |
API Client: useApi() (Axios singleton)
   |
Endpoint:   GET renting/equipment/  ->  api/v1/renting/equipment  ->  EquipmentViewSet
```

Patron confirmado igual al documentado en `ARQUITECTURA_COMPLETAFRONEND.md` §2: la mayoria de
consumidores llaman `useApi()` directo o via un wrapper delgado en `services/<dominio>/`, nunca
`axios` importado suelto.

---

## 4. GRAPH GAPS encontrados (reportados, NO corregidos -- regla del prompt maestro)

### GAP A -- `calculate_change_impact()` es una travesia SOLO HACIA ATRAS -- causa raiz exacta
identificada (leyendo `project_knowledge_graph/knowledge_graph/query.py::_functional_dependents()`)

`_functional_dependents(kg, node_id)` construye `direct = {e.source for e in kg.edges if
e.target == node_id and e.label not in {"CONTAINS","BELONGS_TO"}}` -- SOLO seedea con aristas
que APUNTAN HACIA `node_id` ("quien depende de mi"), nunca con las aristas que salen DE
`node_id`. Confirmado con 3 pares de pruebas reales:

| Target resuelto | contracts/frontend_consumers |
|---|---|
| `ProductViewSet` (clase, bare) | VACIOS (`total_affected: 0`) |
| `ProductViewSet.full_detail` (metodo/Symbol especifico) | 1 contract, 6 consumidores reales |
| `RentalDetailView` (FrontendView, bare) | VACIOS, aunque `meta.api_calls` SI tiene el dato |
| `CartViewSet.add_item` (metodo especifico, pero endpoint sin nodo -- ver GAP B) | VACIOS (causa distinta, GAP B) |

Razon exacta: un `ViewSet` clase solo tiene aristas SALIENTES relevantes (`EXPOSES ->
Endpoint`), invisibles a una BFS que solo mira `target==node_id`. Un `Symbol`/metodo especifico
(ej. `ProductViewSet.full_detail`) SI tiene aristas funcionales que ENTRAN a el (llamadas,
referencias) que la BFS hacia atras si encuentra, y desde ahi alcanza el `Endpoint` y sus
consumidores via la cadena completa de aristas. Verificado con datos reales del grafo (no
inferido): `ProductViewSet` tiene 53 aristas salientes (incluye `EXPOSES -> endpoint:api/v1/
shop/products`) pero solo 1 arista ENTRANTE real (`CONTAINS`, excluida) -- por diseno de la
funcion, cero impacto detectado.

**Implicancia CONCRETA y ACCIONABLE para FASE 61.2 en adelante**: `ChangeIntent`/`ChangeContext`
(FASE 61.4/61.5) deben resolver el target como un METODO/ACCION ESPECIFICA de un ViewSet (ej.
`SocialLinkViewSet.list`), NUNCA como el nombre bare de la clase -- de lo contrario
`GenerationContext` (FASE 61.8) recibira `contracts`/`frontend_consumers` vacios y el LLM
generaria sin saber que existen consumidores reales. Esto YA es como `ai_editor.resolver`
viene operando en toda la sesion (siempre se resolvieron metodos/simbolos especificos, nunca
una clase bare) -- se documenta aca porque FASE 61 es la primera vez que se verifica
explicitamente EL POR QUE funciona asi.

### GAP B -- Router registrado con prefijo vacio (`r''`) no genera nodo `Endpoint`

Verificado en `cart/api/urls.py`:
```python
router.register(r'', CartViewSet, basename='cart')       # URL real: api/v1/cart/
router.register(r'wishlist', WishlistViewSet, basename='wishlist')  # URL real: api/v1/cart/wishlist
```
`get_app_summary('cart')['endpoints']` solo devuelve `['api/v1/cart/wishlist']` -- **`CartViewSet`
(basename `cart`, URL real `api/v1/cart/`) no tiene nodo `Endpoint` en el grafo**, aunque
`WishlistViewSet` (mismo archivo, mismo patron, prefijo NO vacio) si lo tiene. Hallazgo real y
reproducible: el scanner de endpoints del Knowledge Graph pierde routes registrados con
`router.register(r'', ...)` (prefijo vacio). **No corregido en esta fase** (fuera de alcance de
observacion pura) -- si FASE 61.2 selecciona un caso sobre `cart/`, este gap se vuelve relevante
directamente.

### GAP C -- 25 `dead_frontend_components` (sin relaciones conocidas en el grafo)

Confirmado con `project_knowledge_graph.audit.validator.find_dead_frontend_components()`:
**25 componentes**, TODOS bajo `views/customer/detail/components/*` (ej.
`PublicDetailAvailability.vue`, `PublicDetailGallery.vue`, `PublicDetailHero.vue`,
`PublicDetailPricing.vue`, ...). Posible falso positivo: el proyecto usa un patron de
"renderers" (`src/renderers/HomeRenderer.vue`/`SectionRenderer.vue`, resolucion dinamica de
layout para el Home Builder) que el scanner estatico de imports podria no seguir -- **no
verificado en esta fase si son componentes realmente muertos o consumidos dinamicamente**
(quedaria para una fase de correccion de grafo, fuera de alcance de FASE 61). Reportado tal cual,
sin asumir ninguna de las dos hipotesis como cierta.

### GAP D -- validation_summary pre-existente (ya capturado en baseline, referenciado aca)

`stale_documentation=12`, `service_layer_violations=2`, `import_cycles=1`,
`contradictory_counts=43` -- ver `AI_MODEL_QUALIFICATION_BASELINE.md` seccion 3. No repetido en
detalle aca, solo referenciado para que el snapshot de frontend quede completo.

---

## 5. Contratos API -- formato confirmado

`Endpoint.meta` trae: `http_methods` (lista), `viewset` (nombre real), `basename`. NO trae
todavia (a nivel de `Endpoint`) el detalle de campos/tipos/nullability del `Serializer` asociado
-- eso requiere una consulta aparte (`SERIALIZES` edge, Endpoint->Serializer, ya existente desde
FASE 4 del rediseno original) -- disponible pero no explorado en detalle en esta fase (no
necesario para el snapshot arquitectonico, si sera necesario en FASE 61.15 "Contract
Validation").

---

## 6. Conclusion de FASE 61.1

El Knowledge Graph SI resuelve correctamente la cadena Backend<->API<->Frontend<->Tests para
targets anclados en un METODO/SIMBOLO especifico del backend (verificado con datos reales, no
fixtures). Existen 2 gaps estructurales reales del scanner (GAP A: `calculate_change_impact()`
solo camina hacia atras, se debe resolver siempre un metodo/simbolo especifico, nunca una clase
bare; GAP B: routers con prefijo vacio no generan nodo `Endpoint`) y 1 gap de cobertura sin
diagnosticar (GAP C: 25 componentes posiblemente muertos o dinamicos). Ninguno de los 3 bloquea
FASE 61.2 -- se tendran en cuenta al elegir el caso de prueba (evitar `cart/` por GAP B, resolver
siempre un metodo especifico del backend nunca una clase bare por GAP A, evitar
`views/customer/detail/components/*` por GAP C).
