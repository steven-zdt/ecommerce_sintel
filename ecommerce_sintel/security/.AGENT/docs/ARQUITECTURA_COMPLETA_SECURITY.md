# Arquitectura — Security (Centro de Seguridad, Fase 1 + Fase 2)

**Ultima actualizacion:** 2026-07-09 (Fase 2: auditoria transversal completa)

## Responsabilidad

Dominio transversal de auditoria de seguridad. NO reemplaza `users.UserAuditLog`,
`kyc.VerificationEvent` ni `kyc.ConsentRecord` (siguen siendo las fuentes de verdad de
auditoria administrativa/KYC) -- `security.SecurityEvent` es un registro complementario
enfocado en senales de seguridad (logins fallidos, rate-limit, archivos rechazados, KYC
bloqueado/rechazado) consultable desde un unico lugar (`/panel/seguridad`).

`security` nunca posee logica de negocio de otra app: solo se importa de forma diferida
(`from security.services.commands import SecurityCommands`) desde el punto donde ocurre el
evento, igual que `notifications.services.commands.NotificationCommands.dispatch_notification`.

## Alcance de esta fase (decision explicita del usuario)

Se implemento el **nucleo real**: modelo + entrypoint transversal + 4 integraciones reales +
2 fixes de validacion de archivos + throttling nuevo en 2 endpoints sensibles + health-check +
dashboard admin simple. Explicitamente NO se construyo (ver plan
`iridescent-snuggling-pond.md` de esa sesion): motor de firewall, rate-limit multi-dimension,
middleware Django inyectado transversalmente, `SecurityCryptoService`/`SecurityStorageService`,
proteccion WS de flood/replay, bloqueo de IPs, CSP/HSTS a nivel nginx.

## Modelo

`SecurityEvent(SintelBaseModel)`: `event_type` (LOGIN_SUCCESS/LOGIN_FAILED/KYC_REJECTED/
KYC_BLOCKED/RATE_LIMIT_HIT/FILE_REJECTED/AI_ACTION_EXECUTED/...), `severity` (INFO/WARNING/CRITICAL), `user` (FK
nullable SET_NULL), `ip_address`, `user_agent`, `path`, `metadata` (JSONField). Append-only --
el admin de Django (`security/admin.py`) es de solo lectura (`has_add_permission`/
`has_change_permission` retornan `False`).

## Servicios

- `SecurityCommands.log_event(event_type, request=None, user=None, severity=INFO,
  metadata=None)` -- unico punto de escritura. Nunca propaga excepciones al caller (try/except
  interno + log).
- `SecuritySelector.list_events(event_type=None, severity=None, user_uuid=None)` /
  `get_health_snapshot()` (ping DB/Redis/Celery).

## Integraciones reales (imports diferidos)

| Origen | Evento |
|---|---|
| `accounts/api/views.py::AccountViewSet.login()` | `LOGIN_SUCCESS` / `LOGIN_FAILED` |
| `kyc/services/commands.py::KycCommands.reject()` | `KYC_REJECTED` |
| `kyc/services/commands.py::KycCommands.block()` | `KYC_BLOCKED` |
| `ecommerce/api_exceptions.py::api_exception_handler` (excepcion `Throttled`) | `RATE_LIMIT_HIT` |
| `accounts/services/commands.py::validate_file()` (al rechazar) | `FILE_REJECTED` |
| `ecommerce/internal_ai_utils.py::log_ai_action(request, tool, metadata)` -- helper compartido, invocado desde `core`/`kyc`/`renting`/`quotes`/`support` en sus respectivos `api/internal_ai.py` (ej. `support/api/internal_ai.py::AiOpenSupportTicketView`, con `metadata={'tool': 'OpenSupportTicketTool', 'room_uuid': ..., 'attached_context': ...}`) | `AI_ACTION_EXECUTED` — **[AGREGADO 2026-08-01, Fase 3 de AUDITORIA/17]** toda escritura del AI Core queda auditada aca, no solo loggeada |

## Fixes de validacion de archivos (gap real encontrado en la auditoria)

- `technical_services/services/commands.py::ServiceAttachmentCommands.add_attachment` y
  `renting/services/commands.py::RentalRequestCommands.add_project_attachments` (nuevo, la
  logica vivia antes en la vista `renting/api/views.py::attachments()`) ahora llaman a
  `accounts.services.commands.validate_file(..., magic_bytes_check=True)` en vez de su propia
  validacion ad-hoc de tamano/content-type -- cierra el hueco de archivos con extension
  falsificada que antes pasaban sin chequeo de magic-bytes.

## Throttling nuevo

`kyc/api/views.py::KycViewSet` gano `ACTION_THROTTLE_SCOPES`/`get_throttles()` (mismo patron que
`AccountViewSet`): `upload_document` -> scope `kyc_upload` (20/hour), `request_upgrade` -> scope
`kyc_upgrade` (5/hour). Tasas en `ecommerce/settings/base.py::REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`.

## Endpoints

- `GET /api/v1/security/health/` -- `SecurityHealthView`, solo admin (`IsAdminUser`).
- `GET /api/v1/dashboard/security-events/` -- `AdminSecurityViewSet` (BFF, `ADMIN_PERMISSIONS`),
  lista paginada con filtros `event_type`/`severity`/`user_uuid`.
- `GET /api/v1/dashboard/security-events/health/` -- proxy BFF del health-check.

## Frontend

`/panel/seguridad` -> `SecurityDashboardView.vue` (banner de salud + tabla de eventos con
filtros). Entrada de navegacion en `Sidebar.vue::systemLinks`.

## Fase 2 -- Auditoria transversal completa (2026-07-09)

Tras certificar Fase 1, se audito el resto del proyecto (payment, orders, shop, marketing,
inventory, support, operations, core; 3 agentes Explore en paralelo, solo lectura) buscando
puntos que realmente ameriten un evento de seguridad. `shop`/`marketing` quedaron fuera
deliberadamente: solo tienen CRUD administrativo generico, sin una senal de seguridad
distintiva (instrumentar cada cambio de precio/campana seria ruido, no senal).

**Integraciones nuevas:**

| Origen | Evento |
|---|---|
| `payment/online/api/views.py::_verify_wompi_event_signature()` (firma invalida o `WOMPI_EVENTS_SECRET` sin configurar) | `PAYMENT_WEBHOOK_INVALID_SIGNATURE` (CRITICAL) |
| `payment/online/services/commands.py::WompiCommands.process_webhook_notification()` (status DECLINED/VOIDED/FAILED) | `PAYMENT_DECLINED` (WARNING) |
| `payment/cards/views.py::TokenizedCardViewSet.destroy()` | `PAYMENT_CARD_REMOVED` (INFO) |
| `orders/services/commands.py::OrderCommands.create_from_cart()` (cupon invalido/expirado) | `COUPON_REJECTED` (WARNING) |
| `inventory/api/views.py::StockRecordViewSet.adjust_stock()` | `INVENTORY_MANUAL_ADJUSTMENT` (INFO) |
| `operations/services/commands.py::OperationCommands.transition_status()` (a CANCELLED) | `OPERATION_FORCE_CANCELLED` (WARNING) |

**Bug real encontrado y corregido**: `OrderCommands.create_from_cart()` estaba decorado
`@transaction.atomic` completo -- el `SecurityEvent(COUPON_REJECTED)` se creaba y luego se
perdia en el rollback cuando el cupon invalido disparaba el `ValidationError` (la insercion del
evento de auditoria vivia dentro de la misma transaccion que se abortaba). Fix: se separo la
validacion (lectura pura, sin `@transaction.atomic`) de la escritura real de la orden, movida a
un nuevo metodo interno `OrderCommands._create_order_atomic()`. Verificado con ejecucion real:
el evento ahora persiste tras el rollback, y el camino feliz (crear orden sin cupon) sigue
funcionando igual.

**Throttling nuevo**: `orders/api/views.py::OrderViewSet` gano `ACTION_THROTTLE_SCOPES` para
`create_from_cart` -> scope `order_create` (30/hour) -- cierra el vector de fuerza bruta de
codigos de cupon (antes sin ningun limite).

**Fix de XSS almacenado (gap real encontrado)**: ninguno de los serializers de entrada del
Visual Builder de `core` (`HomeBannerInputSerializer`, `HomeCardInputSerializer`,
`HomeCardGroupInputSerializer`, `FooterLinkInputSerializer`, `CompanyContactInfoInputSerializer`,
`NavbarLinkInputSerializer`, `FooterCTAConfigInputSerializer`) sanitizaba HTML, y estos campos se
sirven tal cual en endpoints 100% publicos (`home-feed`/`footer`/`site-config`). Fix: helper
`_strip_html_fields()` (`django.utils.html.strip_tags`, sin dependencia nueva) + `validate()` en
cada uno de los 7 serializers. Verificado con ejecucion real: `<script>alert(1)</script>` y
`<img src=x onerror=alert(1)>` quedan neutralizados (sin tag ejecutable) al guardar.

Todas las integraciones de Fase 2 fueron verificadas con ejecucion real (no solo lectura de
codigo): firma de webhook invalida, cupon rechazado (incluyendo el fix de rollback), ajuste
manual de inventario, y cancelacion forzada de un ticket de operaciones -- los 6 `event_type`
nuevos generaron su fila correspondiente en `SecurityEvent`.

## Certificacion (2026-07-09)

Auditoria de codigo real (no de intencion) contra el checklist de 22 fases que el usuario uso
para pedir la certificacion. Verificado con evidencia de ejecucion real: 0 imports circulares
o hacia dominios de negocio (`security` solo depende de `users.api.permissions` y
`ecommerce.base_models`, ambos sustrato no-negocio), 0 raw SQL, 0 regresiones sobre 220 tests,
y los 6 tipos de `SecurityEvent` verificados end-to-end (login real, throttle real disparado 12x,
archivo con magic-bytes falso rechazado, `KycCommands.reject()`/`block()` ejecutados de verdad).
Veredicto: **CERTIFICADO CON OBSERVACIONES** para el alcance de Fase 1 aprobado. Contra el brief
original de 18 fases el veredicto seria NO CERTIFICADO -- ver tabla de fases pendientes abajo,
que documenta esto por diseno, no por omision.

## Fases pendientes del brief original (18 fases) -- si se decide ampliar el alcance

| Fase del brief original | Estado | Que faltaria construir |
|---|---|---|
| Middleware (`SecurityMiddleware`, `RequestAuditMiddleware`, `RateLimitMiddleware`, `AttackDetectionMiddleware`, `HeaderValidationMiddleware`) | Pendiente | 5 middlewares Django nuevos + registro en `MIDDLEWARE`; requiere definir primero que trafico interceptar y con que criterio (sin esto, alto riesgo de romper auth global) |
| Firewall (IP/headers/origin/host/referer/payload) | Pendiente | Motor de reglas + modelo `SecurityPolicy`/`BlockedIP` + middleware que lo aplique |
| Rate-limit multi-dimension (usuario/IP/rol/metodo/WS/admin/API separados) | Pendiente | Reemplazar `ScopedRateThrottle` por un motor propio con backend Redis dedicado |
| Auditoria transversal completa | **Completada (Fase 2)** | Payment/Orders/Inventory/Operations integrados con eventos reales; Support/Notifications/Marketing/Core (parcial, solo XSS)/Shop quedaron fuera por no tener una senal de seguridad distintiva (CRUD generico) |
| WebSocket (rate-limit, origin validation, flood/replay protection en `support/consumers.py`/`channels_auth.py`) | Pendiente | Extender `JWTAuthMiddleware` + `SupportChatConsumer.receive()` |
| `SecurityCryptoService`/`SecurityStorageService`/`DatabaseHealthService`/`BackupVerificationService`/`ConstraintAuditService`/`ConnectionMonitor` | Pendiente | Servicios nuevos, ninguno tiene precedente hoy |
| Modelos separados (`SecurityIncident`, `BlockedIP`, `SecurityPolicy`, `SecurityMetric`, `SecuritySession`, `ApiAccessLog`, `SecurityAlert`, `SecurityConfiguration`) | Pendiente | Se opto por 1 modelo unificado (`SecurityEvent`) en vez de ~10 -- expandir requeriria decidir si de verdad se justifican tablas separadas o si siguen caben como `event_type` adicionales |
| Endpoints `/api/v1/security/{metrics,alerts,incidents,firewall,sessions,rate-limit,blocked-ip,security-score}` | Pendiente | Requieren los modelos de arriba primero |
| Frontend: `SecurityMetrics.vue`, `ThreatPanel.vue`, `AuditTimeline.vue`, `SecurityAlerts.vue` | Pendiente | Hoy todo vive en un unico `SecurityDashboardView.vue` |
| CSP/HSTS/`limit_req` a nivel nginx | Pendiente | Cambio de infraestructura (`nginx.conf`), fuera del codigo Django |
| Antivirus real (`DocumentScanner.scan()`) | Pendiente (preexistente) | Sigue siendo un stub que retorna `SKIPPED` -- reemplazar el cuerpo por ClamAV/clamd no requiere tocar callers |

### 2026-09-25 - Tokens personales del servidor MCP y auditoria de acciones MCP
- **Modelo** `McpAccessToken` (`security/models.py`, migracion `0011_mcp_access_tokens`): solo el sha256 del token, prefijo, caducidad (1-90 dias), `last_used_at`, `revoked_at`. **Eventos nuevos** en `SecurityEvent`:
  `MCP_TOKEN_CREATED`, `MCP_TOKEN_REVOKED`, `MCP_TOKEN_EXCHANGED`, `MCP_TOKEN_EXCHANGE_FAILED`, `MCP_ACTION` (metadata solo con ids/codigos/nombres de campo; nunca el token, su hash ni valores de datos).
- **Servicio** `security/services/mcp_tokens.py` (`McpTokenCommands.create_token|revoke_token|exchange`, `McpTokenSelectors`). El canje devuelve un JWT de 15 min con claim `via=mcp`; todo rechazo es un 401 generico auditado; limite 30/min por IP; el usuario debe seguir siendo admin activo.
- **Frontera**: un JWT `via=mcp` no puede crear/revocar tokens (`is_mcp_authenticated`); mas adelante tampoco aprobar cambios de codigo.
- **Rutas**: `GET/POST/DELETE /api/v1/dashboard/mcp-tokens/` (admin, solo sus propios tokens), `POST /api/v1/internal/mcp/exchange/` (interno, sin JWT: la credencial es el token), `POST /api/v1/dashboard/mcp/audit/` (copia durable de las escrituras del MCP), `GET /api/v1/dashboard/mcp/whoami/`.
- Tests escritos (no ejecutados): `security/tests_mcp_tokens.py`. Detalle: `mcp_server/.AGENT/SECURITY_MODEL.md`, `AUDITORIA/MCP_SECURITY_AUDIT.md`.
