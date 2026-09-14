# FASE 61.2 -- SELECCIÓN DEL CASO DE PRUEBA

**Fecha:** 2026-08-12. **Alcance:** solo seleccion, 0 archivos modificados.

## Caso seleccionado

```
Model:      organization.SocialLink  (organization/models.py:102)
            platform, url, icon_class, display_order, is_active
Service:    SocialLinkViewSet (organization/api/views.py) -- actions: list, create,
            partial_update, destroy
Serializer: (asociado al ViewSet, via SERIALIZES, no explorado en detalle en esta fase --
            se resolvera en FASE 61.5)
Endpoint:   api/v1/organization/social-links  (Endpoint node CONFIRMADO en el grafo)
Frontend
API client: organizationAdmin.fetchAll() -- store/organizationAdmin.js (Pinia STORE, no
            composable/service suelto -- coincide con el patron prioritario del prompt maestro)
Component:  OrganizationView.vue -- modules/organization/OrganizationView.vue (panel admin)
Tests:      organization/tests.py existe (sin tests directos de SocialLink encontrados via
            grafo todavia -- "facilmente ampliable", patron CRUD ya usado por otros modelos
            del mismo archivo)
```

**Target de resolucion recomendado para FASE 61.4+ (por GAP A del snapshot FASE 61.1):
`SocialLinkViewSet.list` o `SocialLinkViewSet.create` -- NUNCA `SocialLinkViewSet` a secas.**

## Verificacion contra los 10 criterios (seccion 9 del prompt maestro)

| # | Criterio | Cumple | Evidencia |
|---|---|---|---|
| 1 | Backend identificable | SI | `organization.SocialLink` (modelo real, `organization/models.py:102`) |
| 2 | Endpoint identificable | SI | `api/v1/organization/social-links` (nodo `Endpoint` real, confirmado con `find_endpoint`) |
| 3 | Frontend consumer identificable | SI | `organizationAdmin` (Pinia store) + `OrganizationView.vue` (confirmado via `resolve_change`) |
| 4 | Tests existentes o facilmente ampliables | PARCIAL | `organization/tests.py` existe, sin test directo de `SocialLink` encontrado -- se ampliara en FASE 61.13, mismo patron CRUD que otros modelos del archivo |
| 5 | Bajo riesgo | SI | `calculate_impact('SocialLinkViewSet.list')` -> `risk: LOW`, `total_affected: 5` (el mas bajo de todos los candidatos evaluados) |
| 6 | Reversible | SI | mismo mecanismo sandbox + `rollback_outcome()` ya verificado real en FASE 54-55 |
| 7 | Sin secretos | SI | redes sociales son configuracion publica de la organizacion, no credenciales |
| 8 | Sin produccion | SI | todo el flujo hasta FASE 61.12 corre en sandbox, nunca `WORKSPACE_ROOT` |
| 9 | Sin autenticacion critica | SI | el ViewSet exige `requiresAuth+requiresAdmin` para ESCRIBIR (patron admin estandar), pero no es parte del flujo de login/tokens en si -- no se toca `auth/`/`admin-auth/` |
| 10 | Sin pagos | SI | ningun vinculo con `payment/`/Wompi |

## Por que NO se eligieron los otros 4 candidatos evaluados (evidencia real de cada uno)

- **`renting.EquipmentViewSet`** -- trazabilidad PERFECTA (7 consumidores reales, tests
  reales, demostrada en el snapshot de FASE 61.1) pero: (a) reusado extensamente durante
  toda la sesion previa (FASE 36/51-53/54-55), y (b) `renting/tests_presenters.py` tiene
  **17 de los 20 fallos ya conocidos del baseline** (FASE 61.0) en esta misma area de detalle
  -- empezar ahi mezclaria "fallo por mi cambio" con "ya fallaba antes".
- **`shop.ProductViewSet.full_detail`** -- 6 consumidores reales, pero uno de sus tests
  indirectos (`ProductDetailSerializerContentBlocksTestCase.test_detail_endpoint_exposes_new_
  fields`) es uno de los **3 fallos ya conocidos** de `shared/tests/test_content_blocks.py`
  (baseline FASE 61.0) -- mismo problema de contaminacion de resultados.
- **`technical_services.TechnicalServiceViewSet.full_detail`** -- `risk: HIGH`,
  `total_affected: 46`, con 20 consumidores frontend, varios de dominios NO relacionados
  (`RentingList`, `ProductList`, `ProductForm`) -- demasiado grande para "la primera prueba
  debe ser PEQUEÑA" (seccion 3 del prompt maestro).
- **`cart.CartViewSet`** -- descartado por GAP B (sin nodo `Endpoint` en el grafo, confirmado
  con `CartViewSet.add_item` tambien vacio) -- elegirlo mezclaria "el modelo fallo" con "el
  grafo tiene un gap conocido", exactamente lo que la regla 36.D del prompt maestro pide evitar.

## CHANGE_REQUEST (borrador para FASE 61.3, no ejecutado en esta fase)

Descripcion candidata para la siguiente fase (a confirmar/refinar en FASE 61.3, sin ambiguedad
tipo "mejora el frontend"): **"Agregar un campo booleano `opens_in_new_tab` a `SocialLink`
(default `True`) y exponerlo en el formulario/lista de `OrganizationView.vue` para que el admin
pueda controlar si el link abre en pestaña nueva."** -- pequeño, funcional, sin ambigüedad, con
criterio de éxito objetivo (el campo existe en modelo+serializer+API+UI, sin romper nada
existente).
