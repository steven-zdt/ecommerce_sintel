# CORE v4 — Arquitectura por Dominios: Fase 8 (Pruebas de Regresión)

**Fecha:** 2026-07-12
**Objetivo:** Garantizar que toda la reorganización de las Fases 1-7 no introdujo regresiones.

---

## 1. Suite completa de tests — todas las apps del proyecto

Corrida en 4 bloques (por límites de discovery de Django al combinar ciertas apps en un mismo
comando — colisión conocida, no relacionada con esta migración, documentada abajo).

| Bloque | Apps | Resultado |
|---|---|---|
| 1 | core, organization, dashboard, notifications, operations, technical_services, renting, orders | **159/162** — 3 fallos, los 3 preexistentes (ver sección 2) |
| 2 | accounts | **70/72** — 2 fallos, los 2 preexistentes (ver sección 2) |
| 3 | users | **15/16** — 1 error, preexistente (ver sección 2) |
| 4 | quotes, marketing, payment, shop, cart, inventory, kyc, security, support | **64/64** — limpio (quotes y support no tienen suite de tests propia, 0 tests cada uno) |

**Total: 308/314 tests ejecutados en verde. 6 fallos, los 6 confirmados preexistentes y sin
relación con ningún cambio de esta sesión (ver detalle exacto en la sección 2). Cero
regresiones nuevas introducidas por las Fases 1-8 del plan CORE v4.**

### Nota técnica: colisión de discovery de Django

`manage.py test <app1> <app2> ...` con ciertas combinaciones de apps falla con
`ImportError: 'tests' module incorrectly imported from ...` — es un problema de cómo el
descubrimiento de tests basado en archivos de `unittest` resuelve módulos `tests.py` con el
mismo nombre en distintas apps cuando se combinan en un solo comando (afectó a
`accounts`+`users` y luego a `shop`+`cart` en esta sesión). **Preexistente, no relacionado con
CORE v4** — la solución fue correr los bloques afectados por separado.

---

## 2. Los 6 fallos preexistentes (confirmados en esta y sesiones previas de este mismo plan)

| Test | Causa | Por qué es preexistente |
|---|---|---|
| `core.tests.test_models_and_signals` (todo el módulo) | `ModuleNotFoundError: No module named 'pytest'` | El archivo ya usaba `@pytest.mark.django_db` antes de esta sesión; el contenedor nunca tuvo pytest instalado (el proyecto usa `manage.py test`, no pytest) |
| `technical_services...test_serializer_accepts_richer_request_metadata` | `datetime.date(2026, 8, 15) != '2026-08-15'` | Comparación de tipo `date` vs `string` en un serializer que no se tocó en ningún momento de esta migración |
| `orders...test_order_fulfillment_workflow` | `405 != 201` en `POST .../tracking/` | El test llama por error al endpoint `GET`-only `tracking/` en vez de `add-tracking-point/` — bug del test mismo, confirmado leyendo `orders/api/views.py` |
| `accounts.tests_availability` (2 tests) | `ServiceVariant.CONTRACTOR_RATES` no existe | La constante se eliminó deliberadamente en `technical_services/migrations/0014_servicevariant_remove_contractor_rates.py`; el test viejo nunca se actualizó |
| `users` (test discovery) | `ImportError: attempted relative import beyond top-level package` en `users.services.selectors` | Quirk de discovery de Django al importar `users.services` como candidato a módulo de test — no relacionado a ningún cambio de código |

---

## 3. Endpoints validados (además de la suite de tests)

| Endpoint | Método de verificación | Resultado |
|---|---|---|
| `GET /api/v1/core/site-config/`, `/footer/`, `/home-feed/` | `curl` directo | 200 los 3 |
| `GET /api/v1/organization/{8 recursos}/` sin autenticar | `curl` directo | **401 los 8** — permisos correctos |
| `GET /api/v1/organization/{8 recursos}/` autenticado (admin real, solo lectura) | Django test Client + `force_login` | 200 los 8 |
| `GET /api/v1/dashboard/operations/` (tablero real que consume `OperationBoard.vue`) | Django test Client autenticado | 200, `effective_status` presente y correcto en los 9 tickets reales |

---

## 4. Incidencias encontradas y corregidas en esta misma fase

Fase 8 cumplió su propósito — encontró 2 regresiones reales introducidas en fases anteriores
de este mismo plan, ambas corregidas antes de cerrar esta fase:

### 4.1 🔴 Caché de site-config no se invalidaba desde el nuevo endpoint de `organization`

**Síntoma:** actualizar `Company.trade_name` vía el nuevo `PATCH /api/v1/organization/company/update/`
(construido en Fase 6) no invalidaba `SITE_CONFIG_CACHE_KEY` — el endpoint público
`core/site-config/` seguía mostrando el valor viejo hasta que expirara el TTL de 5 minutos. El
endpoint antiguo equivalente (`dashboard/site-brand/update/`) sí lo hacía.

**Causa:** al construir `organization/api/views.py` en Fase 6, se replicó la lógica de
`dashboard/api/views.py::AdminSiteBrandViewSet` pero se omitieron las llamadas a
`_invalidate_site_config_cache()`/`_invalidate_footer_cache()`.

**Corrección:** se agregaron los mismos helpers (duplicados a propósito, no importados desde
`dashboard`, para no crear una dependencia `organization` → `dashboard`) y se invocan después
de cada escritura en `CompanyViewSet`, `BrandingViewSet`, `ContactInfoViewSet` y
`SocialLinkViewSet` (create/update/delete). Verificado con una prueba real: `PATCH` vía el
endpoint → el público refleja el cambio inmediatamente.

### 4.2 🔴 `effective_status` no llegaba al tablero admin real

**Síntoma:** en la Fase 6 se agregó `effective_status` a `OperationTicketListSerializer`/
`OperationTicketDetailSerializer` y se conectó `OperationBoard.vue` a `op.effective_status` —
pero el tablero admin real (`dashboard/operations/` → `AdminOperationViewSet`) usa un
serializer **distinto** (`AdminTicketBoardSerializer`) que nunca se tocó. El campo hubiera
llegado como `undefined` al frontend.

**Causa:** suposición incorrecta en Fase 6 sobre qué serializer alimenta el tablero admin
unificado — hay dos serializers de listado de `OperationTicket` en el proyecto (uno para el
endpoint del cliente en `/api/v1/operations/my/`, otro para el tablero admin en
`/api/v1/dashboard/operations/`), y se editó el que no correspondía.

**Corrección:** `effective_status` agregado también a `AdminTicketBoardSerializer`. Verificado
con el endpoint real (`dashboard/operations/`): los 9 tickets reales devuelven
`effective_status` correcto, incluyendo el caso de divergencia `OP-2026-7C215EE1`.

### 4.3 Sin incidencias adicionales

Ningún otro endpoint, comando, o migración de las Fases 1-8 mostró comportamiento inesperado.

---

## 5. Verificar panel administrativo — parcialmente pendiente

Todo lo verificable sin interacción visual (endpoints, permisos, caché, compilación de Vite,
ausencia de errores de consola en rutas protegidas) se confirmó en esta fase y en la Fase 6.
**La verificación visual del panel ya autenticado (sidebar reorganizado, `OrganizationView.vue`
renderizado, tablero de Operaciones con los badges de `effective_status`) sigue pendiente** —
requiere credenciales que el clasificador de seguridad de la sesión bloqueó usar de forma
automatizada. Recomendado que el usuario la haga manualmente antes de la Fase 9
(Certificación).

---

## Estado

**Fase 8: COMPLETA.** 2 incidencias reales encontradas y corregidas en el momento. Informe de
pruebas (secciones 1-3) y lista de incidencias (sección 4) son el entregable.

**⏳ Pendiente de autorización explícita para iniciar la Fase 9** (Certificación
Arquitectónica — auditoría final, checklist, documentación consolidada).
