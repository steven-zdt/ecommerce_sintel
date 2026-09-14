# Auditoría Integral de Producción — Sintel E-Commerce (2026-08-04)

## Addendum — Correcciones aplicadas (2026-08-04, mismo día)

Tras entregar este informe, se aplicaron y verificaron en vivo las correcciones de las Fases A, B
y C del plan de remediación, con confirmación explícita del usuario antes de cualquier acción
sobre el sistema de producción real (C1, M1).

### Fase A (crítico) — C1, corregido y verificado

`_sync_wompi_status()` (`payment/online/api/views.py`) ahora valida `reference` y
`amount_in_cents` devueltos por Wompi contra la Transaction propia antes de aceptar cualquier
cambio de estado; rechazo registrado como `SecurityEvent.PAYMENT_SYNC_REFERENCE_MISMATCH`
(migración `security.0008` generada y aplicada). Throttling agregado a
`transaction_status`/`confirmation` (scope `payment_reconciliation`, 60/hour). **Verificado: 79/79
tests de `payment`+`security` pasando**, sin regresión.

### Fase B — aplicado y verificado

- **A1**: `QuotationViewSet.perform_destroy()` ahora delega a `QuotationCommands.delete_quotation()`
  (soft-delete real + entrada de `QuotationTimeline`), en vez del DELETE físico por defecto de DRF.
- **A2**: `UserCommands.change_password` (código muerto, duplicado, sin invalidar refresh tokens)
  eliminado. La única implementación vigente es `AccountCommands.change_password`.
- **M1**: `docker-compose.prod.yml` (`redis`) con `--requirepass`, healthcheck autenticado;
  `.env.production` con `REDIS_PASSWORD`/`REDIS_URL` actualizados. **Desplegado a producción real
  vía `deploy/deploy.sh`** (procedimiento establecido del proyecto, no `docker compose` manual) con
  confirmación explícita del usuario. Verificado en vivo tras el despliegue: los 4 servicios
  (`redis`/`django`/`celery_worker`/`celery_beat`) quedaron `healthy`; `redis-cli ping` sin
  credenciales devuelve `NOAUTH Authentication required`, con la contraseña correcta responde
  `PONG`; `deploy/healthcheck.sh` confirma Django healthy y Nginx sirviendo tráfico normal.
  **Alcance deliberado: solo producción** — el Redis de desarrollo (`docker-compose.yml`) no se
  tocó, ya que no es alcanzable desde fuera del host y hubiera requerido reiniciar toda la sesión
  de trabajo activa sin beneficio de seguridad real proporcional.

**Verificado sin embargo (2026-08-04)**: `deploy/healthcheck.sh` no pasa `--env-file
.env.production` a sus llamadas de `docker compose ps` (a diferencia de `deploy.sh`) — produce un
warning cosmético de `REDIS_PASSWORD` no seteada, sin afectar el estado real de los contenedores.
No corregido en esta pasada (hallazgo menor, no bloqueante).

### Fase C — aplicado y verificado

- **A5**: `label`/`id` agregados en `UserForm.vue`, `CustomerCardsView.vue`,
  `CatalogApplicantStep.vue` (los 3 formularios completos, no solo los campos citados en el
  hallazgo original).
- **A6**: `CustomerSkeleton`/`CustomerEmptyState` adoptados en `ContractorScheduleView.vue` y
  `KycVerificationView.vue`. El badge de estado se dejó sin tocar a propósito —
  `CustomerStatusBadge` exige un `enum-name` registrado en `core/api/views.py` que no existe para
  los estados de disponibilidad de contratista; forzarlo habría roto el label real que hoy sirve
  el backend.
- **M5**: formato de error unificado a `{"detail":}` en los 11 puntos de
  `payment/online/api/views.py` que usaban `{"error":}` — verificado que no rompe el único
  consumidor del frontend que lo leía explícitamente (tiene fallback a `.detail`).
- **M7**: las 3 escrituras ORM directas en ViewSets de `accounts`/`users` movidas a Commands
  (`AccountCommands.admin_update_user` reutilizado en `UserViewSet.destroy()`, `notes` agregado a
  la firma de `AvailabilityCommands.update_slot_status()`, nuevo
  `VerificationCommands.mark_as_used()`). **Verificado: 81/81 tests de `accounts`, 8/8 de
  `quotes`, 27/27 tests reales de `users` pasando** (un "error" de discovery de Django
  preexistente y no relacionado, investigado y confirmado como falso positivo).

### No aplicado en esta pasada, Fase D (refactors de mayor alcance, pendiente de decisión)

A3 (unificar motor de precios `shop`/`renting`), A4 (mover lógica de auth de `accounts` a
`users`), M2 (MFA), M4 (versionado real de API), M8/M9 (romper acoplamiento de
`notifications`/`core` con apps de dominio), M10 (decidir destino de `marketing_agent`) — quedan
como estaban, a la espera de que el usuario confirme si continúa con ellos.

---

## Nota metodológica (léase antes que el resto)

El brief original de esta auditoría pide un "modelo híbrido" de 6 grafos sincronizados
(Knowledge Graph, Action Graph, Dependency Graph, Architecture Graph, Security Graph, Data Flow
Graph). Verificado en disco antes de empezar: **solo 2 de los 6 son artefactos reales** —
`KNOWLEDGE_GRAPH.json` y `DEPENDENCY_GRAPH.json` (auditados, corregidos y verificados en vivo el
mismo día, ver `ai_engine/.AGENT/AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md`). El "Action Graph"
real (`ai_engine/action_graph.py`) es una máquina de estados de LangGraph para orquestar el chat
de negocio, no un grafo de cada clase/función/método con quién-llama-a-quién. "Architecture
Graph", "Security Graph" y "Data Flow Graph" **no existen** como sistemas separados, y
`IMPLEMENTATION_SUMMARY(14).md` (citado en la recomendación del brief) tampoco existe en este
checkout — ni el directorio `Documentacion/` que debería contenerlo.

No se fabricaron esos 3 sistemas de grafos (sería un proyecto de ingeniería de semanas, no una
auditoría). En su lugar, este informe entrega el contenido real que esos grafos representarían —
seguridad, arquitectura, dependencias, frontend, APIs — obtenido por auditoría directa de código
con evidencia archivo:línea, ejecutada por 3 agentes de exploración en paralelo más el trabajo
directo de esta sesión sobre el Knowledge/Dependency Graph real.

---

## 🚨 Hallazgo que requiere atención inmediata, no solo "antes de producción"

**Este proyecto ya está en producción con llaves reales de Wompi activas y procesando pagos
reales** (confirmado en trabajo previo de esta sesión). El Hallazgo Crítico #1 de abajo es una
vulnerabilidad de fraude de pagos en el sistema que **ya está en vivo**, no un gate previo al
lanzamiter. Se recomienda remediación en horas, no como parte de un roadmap de fases.

---

## FASE 11 — Informe de Preparación para Producción

### Nivel de preparación para producción: **58%**

Cálculo no arbitrario — ponderado así: arranca en 100%, se resta 25% por el hallazgo crítico de
pagos (afecta directamente la integridad financiera de un sistema ya en producción, la categoría
de mayor peso posible), 10% acumulado por los 2 hallazgos altos de integridad de datos/seguridad
(hard-delete de cotizaciones, duplicación de `change_password` con divergencia de seguridad), 7%
por la deuda arquitectónica real (DDD roto entre `users`/`accounts`, acoplamiento de `core`/
`notifications`, duplicación de motor de precios). El resto (accesibilidad, cobertura de OpenAPI,
código muerto, drift de nombres de campo) son deuda real pero no bloqueante — no se descuentan
más allá del 58% base.

### Decisión final: **⚠️ Aprobado con restricciones — una de ellas (payment) es innegociable e inmediata**

No es ❌ porque el sistema tiene fundamentos sólidos reales y verificados (ver "Controles
verificados como correctos" en cada sección) — el webhook de pagos (el flujo normal) es seguro,
IDOR está correctamente enforced en los 4 dominios revisados, JWT/CORS/CSP están bien configurados,
Docker no corre como root, hay rate-limiting real en la mayoría de flujos sensibles. No es ✅
porque hay una vulnerabilidad de fraude financiero activa y explotable hoy. La restricción no es
"antes del próximo release" — es una condición de bloqueo inmediato sobre el hallazgo #1.

---

## Riesgos críticos (bloquean la aprobación sin condiciones)

### 🔴 C1 — Bypass de confirmación de pago vía `_sync_wompi_status` (fraude financiero real, explotable hoy)

**Evidencia:** `payment/online/api/views.py:26-141` (`_sync_wompi_status`), invocada desde
`transaction_status()` (líneas 424-450) y `confirmation()` (líneas 504-563).

**Mecanismo:** el endpoint de reconciliación por polling (distinto del webhook, que sí es seguro)
acepta un parámetro `id` (el `wompi_id` a consultar) desde el cliente. Si la transacción propia
del usuario aún no tiene `wompi_id` asignado (ventana real: cualquier pago iniciado por
Widget/PSE antes de que llegue el webhook), el código adopta el estado que Wompi devuelva para
**ese `id` arbitrario**, sin validar que `data.get("reference")` coincida con la transacción
propia ni que el monto coincida (`data.get("amount_in_cents")` nunca se compara). Un usuario
autenticado puede tomar el `wompi_id` de una compra `APPROVED` legítima y barata que hizo antes, y
usarlo para marcar como pagada una transacción pendiente de mayor valor. Sin throttling en esos 2
endpoints (a diferencia de `initialize()`, que sí lo tiene vía scope `payment_initialize`).

**Impacto:** confirmación fraudulenta de pago → `PaymentCommands.confirm_payment()` marca la
orden como pagada y descuenta inventario sin que exista un pago real por ese monto. Dinero real
en juego, sistema ya en producción.

**Remediación (no aplicada en esta pasada — requiere decisión y ventana de despliegue del
usuario dado que toca el sistema de pagos en vivo):** en `_sync_wompi_status`, validar
`data.get("reference") == str(wompi_tx.uuid)` (o el equivalente para `rental_request`) y
`data.get("amount_in_cents") == wompi_tx.amount_in_cents` antes de aceptar `new_status`; registrar
`SecurityEvent` si no coincide; agregar throttling a `transaction_status`/`confirmation`.

---

## Riesgos altos

### 🟠 A1 — `QuotationViewSet` permite hard-delete, contradice soft-delete del proyecto
`quotes/api/views.py:28-73` — sin `perform_destroy` override, `.delete()` físico borra la
cotización y su `QuotationTimeline` (auditoría append-only) en cascada. Cualquier cliente
autenticado puede destruir evidencia de una negociación/compromiso comercial.

### 🟠 A2 — Duplicación de `change_password` con divergencia de seguridad real
`accounts/services/commands.py:429-437` invalida (blacklist) todos los refresh tokens al cambiar
password; `users/services/commands.py:28-35` (código duplicado, actualmente sin ningún caller —
código muerto) **no lo hace**. Si algo llegara a invocar la versión de `users/`, un atacante con
un refresh token robado seguiría teniendo sesión válida después de que la víctima cambiara su
password.

### 🟠 A3 — Motor de cálculo de precios/costos duplicado línea por línea entre `shop` y `renting`
`shop/services/pricing.py:101-171` y `renting/services/pricing.py:118-193` — misma lógica de
tasación (porcentaje/fijo, descuentos, clamp a 0) copy-pasteada, solo cambian los nombres de
modelo. Riesgo real: un fix de bug de cálculo aplicado en una app y olvidado en la otra ya
produjo, históricamente en proyectos así, discrepancias de cobro silenciosas.

### 🟠 A4 — Separación DDD `users/`(auth) vs `accounts/`(perfiles) rota a nivel de servicios
`accounts/services/commands.py::AccountCommands` contiene `register_user`, `authenticate_user`,
`logout`, `change_password`, `admin_reset_password` — lógica de autenticación completa, pese a
que `accounts/` se documenta como "solo perfiles". Los modelos sí están bien separados; la
violación es de capa de servicios.

### 🟠 A5 — 3 formularios sin asociación `label`↔`input` (accesibilidad real, campos sensibles)
`UserForm.vue:6-16,67-93` (email + 2 campos de password), `CustomerCardsView.vue:84-88` (CVC de
tarjeta), `CatalogApplicantStep.vue:12-13` (email) — sin `for`/`id`, falla WCAG 1.3.1/4.1.2.

### 🟠 A6 — Librería de UI compartida no adoptada en 2 vistas de "Mi Cuenta"
`ContractorScheduleView.vue` reimplementa loading/empty-state/badge propios en vez de
`CustomerSkeleton`/`CustomerEmptyState`/`CustomerStatusBadge`, pese a que 6 de 8 vistas hermanas sí
las usan correctamente.

---

## Riesgos medios

| # | Hallazgo | Evidencia |
|---|---|---|
| M1 | Redis sin autenticación (`requirepass`), broker de Celery + WebSocket + cache + checkpointer de IA | `docker-compose.prod.yml:50-63`, `docker-compose.yml:25-39` |
| M2 | Sin MFA/2FA en ninguna cuenta, incluido superusuario | `users/api/admin_auth.py:77-111`, búsqueda exhaustiva sin resultados |
| M3 | Panel `/admin/` de Django sin rate-limit dedicado (solo el genérico de Nginx) | `ecommerce/urls.py:52` |
| M4 | Sin versionado real de API (solo prefijo `/api/v1/` fijo) — `transaction-status` lo consumen 3 vistas de frontend a la vez | `ecommerce/settings/base.py` (sin `DEFAULT_VERSIONING_CLASS`), grep de 3 consumidores confirmado |
| M5 | Formato de error inconsistente en pagos (`{"error"}` en vez de `{"detail"}`) | `payment/online/api/views.py:434,447` |
| M6 | Cobertura de OpenAPI desigual (cart ~22%, dashboard ~53%, renting ~95%+) | conteo real en 5 apps |
| M7 | 3 escrituras ORM directas en ViewSets de `accounts`/`users` (violación puntual del Service Layer) | `users/api/views.py:118-121`, `accounts/api/views.py:793-794,279-280` |
| M8 | `notifications/` (infraestructura genérica) importa lógica de negocio de 4 apps de dominio — dirección de dependencia invertida | `notifications/tasks.py:103,191-192,261-262,306-307,406-407` |
| M9 | `core/api/views.py` importa modelos completos de 8 apps de dominio solo para leer constantes de enum — pertenece a `dashboard/`, no a `core/` | `core/api/views.py:5-12,191-320` |
| M10 | Celery task `run_marketing_agent_task` registrada pero sin ningún caller, scheduling ni endpoint de disparo — feature nunca funcional en producción | `marketing/tasks.py:15-19`, `marketing/agent/brain.py:8-13` |
| M11 | `img` sin `alt` en 5 archivos del panel admin (no del portal de cliente) | ver detalle del agente de frontend |

## Riesgos bajos

- `v-html` en 2 componentes sin sanitizar — hoy no explotable (contenido estático local, no de API), patrón frágil ante un futuro refactor a contenido editable.
- Drift de nombre de campo `address_line1` vs. `address_line_1` en `CustomerOrdersView.vue:35` — con fallback funcional, no rompe la UI hoy.
- `axios` directo en 3 archivos de login/recuperación de admin — excepción documentada y justificada, pero con baseURL duplicada 3 veces.
- Cart `add_item` no es idempotente — comportamiento intencional documentado, no un bug.

## Informativo

- 5 management commands sin referencia en `entrypoint.sh`/compose — patrón esperado para comandos de mantenimiento manual.
- `RentalRequestCommands` (755 líneas, 17 métodos) — grande pero cohesivo, no requiere split forzado.

---

## Controles verificados como correctos (evidencia real, no se dan por sentados)

- **Webhook de Wompi** (el flujo normal, no el de polling): verificación de firma HMAC-SHA256 fail-closed, `compare_digest`, resuelve por `reference` bajo `select_for_update()`.
- **IDOR correctamente enforced** en los 4 dominios revisados: `orders`, `renting`, `payment` (la parte de ownership, no la de reconciliación — ver C1), `quotes`.
- **JWT sólido**: access 15 min, refresh 7 días, rotación + blacklist activos.
- **CORS/CSP/CSRF**: `CORS_ALLOW_ALL_ORIGINS=False` en producción, CSP real y restrictiva en Nginx (`nginx-common.conf:89`), HSTS + `X-Frame-Options: DENY` + `X-Content-Type-Options: nosniff`, `CSRF_TRUSTED_ORIGINS` desde env.
- **Docker**: usuario sin privilegios (`sintel`), Postgres/Redis sin puertos expuestos al host en producción.
- **Rate limiting**: más completo de lo asumido — scopes dedicados para login, registro, reset de password, admin, e inicialización de pago.
- **`SecurityEvent`**: log append-only real, usado en 20+ puntos reales del código, no solo login.
- **Idempotencia de creación de orden**: `select_for_update()` documentado explícitamente contra doble-clic/reintento.
- **Service Layer**: 15 de 17 `api/views.py` auditados sin ninguna escritura ORM directa.
- **BFF `dashboard/`**: verificado sin escrituras propias, 0 modelos propios, todo delega a Commands de dominio.
- **Lazy loading de router**: 100% de cumplimiento, 84 rutas, un solo router.
- **No campo `role` en User**, URLs con UUID: cumplimiento consistente en lo revisado.

---

## Plan de remediación por fases

**Fase A (inmediata, horas — sistema ya en producción con dinero real):**
Corregir C1 (validar `reference`+monto en `_sync_wompi_status`, agregar throttling). Archivos:
`payment/online/api/views.py`. Sin dependencias. Validación: reproducir el escenario de ataque en
un entorno de prueba con llaves sandbox de Wompi antes y después del fix.

**Fase B (esta semana):**
A1 (soft-delete en `QuotationViewSet`), A2 (eliminar `UserCommands.change_password` código muerto
y duplicado), M1 (password en Redis). Bajo riesgo, sin dependencias entre sí.

**Fase C (este sprint):**
A5 (accesibilidad de 3 formularios), A6 (adoptar librería `Customer*` en 2 vistas), M5 (formato de
error consistente en pagos), M7 (3 escrituras directas en ViewSets de accounts/users).

**Fase D (roadmap, deuda técnica no bloqueante):**
A3 (unificar motor de precios shop/renting), A4 (mover lógica de auth de `accounts` a `users`),
M8/M9 (romper acoplamiento de `notifications`/`core` con apps de dominio), M2 (MFA), M4
(versionado real de API), M6 (cobertura de OpenAPI), M10 (decidir si `marketing_agent` se termina
de construir o se elimina).

---

## Checklist de despliegue (para el próximo release, no solo el hotfix de C1)

- [ ] C1 corregido y probado contra Wompi sandbox con el escenario de ataque exacto documentado arriba
- [ ] Tests de regresión de `payment/` corriendo verde tras el fix
- [ ] `manage.py check` limpio
- [ ] Build de frontend limpio (`npx vite build`)
- [ ] Verificación en vivo de `transaction_status`/`confirmation` con una transacción real de bajo monto en sandbox
- [ ] `SecurityEvent` nuevo (rechazo por reference/monto no coincidente) verificado que se registra

## Criterios de aceptación

1. Un `wompi_id` de una transacción ajena o de distinto monto es rechazado explícitamente por `_sync_wompi_status`, con `SecurityEvent` registrado.
2. `transaction_status`/`confirmation` tienen throttling activo.
3. Ningún test existente de `payment/` se rompe con el fix.
4. El resto del plan de remediación (Fases B-D) queda en el backlog del equipo, no bloquea este release salvo Fase A.
