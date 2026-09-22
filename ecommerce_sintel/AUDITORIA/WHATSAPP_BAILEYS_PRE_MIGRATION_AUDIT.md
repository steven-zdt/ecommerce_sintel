# WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT

**Fecha:** 2026-09-22
**Fase:** 0 de `PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md` — auditoría previa, sin escritura de código.
**Ubicación:** se coloca en `AUDITORIA/` (no en `docs/audits/`, que el propio `CLAUDE.md` del proyecto marca
como directorio inexistente/roto en este checkout) para seguir la convención real ya establecida — los 10
documentos `WHATSAPP_*.md` de esta misma familia ya viven aquí.

---

## RESUMEN EJECUTIVO — LEER ANTES DE CONTINUAR

**El plan de migración a Baileys entra en conflicto directo con una decisión arquitectónica y de negocio
explícita, reciente (2026-09-16) y muy bien documentada, ya tomada en este mismo repositorio.** Ver sección
`RISKS` — es el hallazgo más importante de esta auditoría y determinaba si las Fases 1+ del plan debían
siquiera comenzar.

**AUTORIZACIÓN EXPLÍCITA OBTENIDA (2026-09-22, esta sesión):** consultado directamente, el usuario confirmó
que Baileys debe conectarse al **mismo número de producción real (`+573144601878`)**, aceptando
explícitamente el riesgo documentado de violación de los Términos de Servicio de WhatsApp Business y de
pérdida de la integración oficial de Meta Cloud API si el número es baneado. Esto satisface el requisito que
`AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` dejó pendiente ("requiere autorización explícita del usuario
— no se toma unilateralmente"). La Fase 1 del plan queda desbloqueada con esta condición.

---

## CURRENT_PROVIDER

- **Mecanismo activo real hoy:** `META_CLOUD_API` (oficial), vía `WhatsAppConnectionFactory` →
  `MetaCloudAPIAdapter` → `MetaWhatsAppClient` (`marketing/integrations/meta/`) → `graph.facebook.com`.
  Número real de producción: `WHATSAPP_PHONE_NUMBER_ID=+573144601878` (`.env.production:65`), sirviendo
  soporte a clientes reales.
- **"QR Web Session (experimental)"** — el proveedor que este plan busca reemplazar por Baileys — **existe
  únicamente como esqueleto arquitectónico, sin ningún gateway real conectado**:
  - `whatsapp/adapters/qr_web_session_adapter.py::QRWebSessionAdapter` — cada método real
    (`send_message`, `generate_pairing_qr`, `translate_inbound`) lanza `WhatsAppQRNotImplementedError`
    explícitamente. `connect()`/`health_check()` devuelven `NOT_IMPLEMENTED`/`False` fijos.
  - `whatsapp/adapters/session_manager.py::WhatsAppSessionManager` — máquina de estados completa
    (`DISABLED → NOT_CONFIGURED → QR_REQUIRED → QR_READY → SCANNING → AUTHENTICATING → CONNECTED →
    RECONNECTING/DISCONNECTED/ERROR`) construida, pero el estado real hoy es siempre `NOT_CONFIGURED` (en
    memoria de proceso, sin persistencia — no hay nada real que persistir).
  - No hay Node.js, no hay librería QR (Baileys/whatsapp-web.js) instalada, no hay contenedor Docker para
    esto — el "gateway" que el plan asume que existe **no existe en absoluto**, ni siquiera en forma
    prototipo.

## FRONTEND_FILES

- `frontend/src/modules/whatsapp/WhatsAppConnectionStatusView.vue` — única vista real. Consume
  `GET dashboard/whatsapp/connection-status/` vía `useApi()`. Muestra 2 tarjetas (Meta Cloud API / QR Web
  Session) con estado, capacidades y un **banner de advertencia explícito en la UI del panel admin**:
  *"EXPERIMENTAL · TERCERO · NO ES LA API OFICIAL DE META... bloqueado explícitamente para el número de
  producción real, por riesgo de perder también la integración oficial (Meta Cloud API) que ya funciona en
  ese mismo número."*
- Ruta: `/panel/soporte/whatsapp` (registrada en `Sidebar.vue:228`, icono `bi-whatsapp`, label "Conexion
  WhatsApp"). No hay store Pinia dedicado ni composable propio — fetch directo con `ref()` local.
- No hay flujo de QR, pairing, ni polling implementado en frontend — solo lectura de estado.
- Otras referencias a "WhatsApp" en frontend (`WhatsAppButton.vue`, `CommunicationCenter.vue`,
  `useCommunication.js`, etc.) son el botón de contacto de cara al cliente (`wa.me/...` o similar) — dominio
  distinto, fuera del alcance de esta migración.

## BACKEND_FILES

Dominio `whatsapp/` (arquitectura hexagonal completa, misión "Refactorización/Migración Arquitectónica de
WhatsApp", 2026-09-16):

```
whatsapp/
├── ports/connection.py           — WhatsAppConnectionPort (contrato ABC, sincrono)
├── factory.py                    — WhatsAppConnectionFactory (unico if/else de mecanismo)
├── domain/
│   ├── contracts.py              — WhatsAppInboundMessage / WhatsAppOutboundMessage
│   ├── service.py                — WhatsAppService (logica de negocio real)
│   ├── customer_resolver.py      — telefono -> User (UserProfile.phone_number)
│   ├── conversation_resolver.py  — User -> ChatRoom (via support.services.commands.ChatCommands)
│   └── idempotency.py            — WhatsAppIdempotencyGuard (channel, external_message_id)
├── adapters/
│   ├── meta_cloud_api_adapter.py — REAL, envuelve marketing/integrations/meta/
│   ├── qr_web_session_adapter.py — ESQUELETO, sin gateway (ver CURRENT_PROVIDER)
│   └── session_manager.py        — maquina de estados QR (solo usada por el adapter QR)
└── tests/                        — test_contract.py, test_isolation.py, test_failure_isolation.py, test_service.py
```

Integración con el resto del sistema:
- `notifications/tasks.py::process_whatsapp_inbound_task` / `send_whatsapp_agent_reply_task` — construyen
  `WhatsAppService(WhatsAppConnectionFactory.create())` y delegan.
- `notifications/api/whatsapp_webhook.py::WhatsAppInboundWebhookView` — único punto de entrada HTTP real
  (webhook de Meta), invoca `WhatsAppIdempotencyGuard` antes de encolar.
- `dashboard/api/views.py::AdminWhatsAppConnectionStatusView` — backend de la vista de estado del panel.
- `support/services/commands.py::ChatCommands`, `support/services/ai_bridge.py` (`ask_ai`,
  `is_ai_mode_active`, `is_ai_rate_limited`) — reusados tal cual, sin duplicación.

## API_ENDPOINTS

| Método | Ruta | Vista | Propósito |
|---|---|---|---|
| GET | `dashboard/whatsapp/connection-status/` | `AdminWhatsAppConnectionStatusView` | Estado de ambos mecanismos para el panel |
| POST | `notifications/whatsapp-webhook/` | `WhatsAppInboundWebhookView` | Webhook entrante real de Meta Cloud API |

No existen endpoints de `session/start`, `session/qr`, `session/logout` etc. que el plan (Fase 1) asume —
habría que crearlos desde cero.

## MODELS

- `notifications/models.py::MetaWebhookEvent` (`SintelBaseModel`) — auditoría de cada evento entrante de
  Meta, persistido ANTES de procesar. Específico de Meta Cloud API, sin cambios previstos por el plan.
- **No existe** ningún modelo `WhatsAppIdentity` ni equivalente — la resolución de identidad hoy es
  puramente por lookup (`UserProfile.phone_number`, últimos 10 dígitos), sin persistir la relación
  teléfono↔JID que el plan (Fase 9) propone. Si Baileys avanza, esa entidad nueva sí tendría que crearse.
- No hay modelo de mensajes específico de WhatsApp — todo pasa por el modelo de mensajería genérico de
  `support` (`ChatCommands.save_message`), compartido con el canal web.

## SERVICES

`WhatsAppService` (`whatsapp/domain/service.py`) es el único punto de entrada de lógica real:
`process_inbound_message()` (resuelve usuario → resuelve `ChatRoom` → persiste → respeta
`is_ai_mode_active`/rate limit → `ask_ai()` vía `support.services.ai_bridge` → responde por WhatsApp) y
`send_agent_reply()` (respuesta humana desde el panel). Cero condicionales de infraestructura — recibe el
adapter ya resuelto, nunca construye uno. Esto **ya satisface** buena parte de lo que el plan pide en sus
Fases 1, 9, 10, 11, 19 — un adapter Baileys nuevo se conectaría aquí sin tocar este archivo.

## TASKS

- `notifications/tasks.py::process_whatsapp_inbound_task` (Celery, con retry) — dispara `WhatsAppService`.
- `notifications/tasks.py::send_whatsapp_agent_reply_task` (Celery) — idem para respuestas de agente humano.
- No hay tasks de reconexión, limpieza de QR, ni heartbeat de sesión — no aplica porque no hay sesión real.

## DOCKER

- **No existe** ningún servicio `whatsapp_gateway` (ni con ese ni otro nombre) en `docker-compose.yml` ni
  `docker-compose.prod.yml`. Confirmado por grep — cero referencias.
- El único bridge de mensajería fuera de Docker en este proyecto es `sms_bridge/` (SMS por módem físico,
  COM5, dominio completamente distinto — no confundir con WhatsApp).

## ENV

Variables reales ya en uso (dev `.env` / prod `.env.production`):
```
WHATSAPP_CONNECTION_TYPE       (default META_CLOUD_API, dev y prod no lo sobreescriben -> META_CLOUD_API)
WHATSAPP_WEBHOOK_VERIFY_TOKEN
WHATSAPP_PHONE_NUMBER_ID       (=+573144601878 en produccion, numero real)
META_ACCESS_TOKEN / META_APP_SECRET / META_BUSINESS_ID / META_WABA_ID / META_GRAPH_API_VERSION
```
Ninguna variable `WHATSAPP_QR_*`/`WA_GATEWAY_*`/`WHATSAPP_GATEWAY_*` existe todavía — son íntegramente
nuevas si el plan avanza (Fases 6, 22).

## TESTS

`whatsapp/tests/`:
- `test_contract.py` — contract tests parametrizados, corridos contra cada adapter real.
- `test_isolation.py` — `DomainNeverKnowsConnectionMechanismTests` (análisis AST real, no solo revisión
  manual) + `SwitchConnectionBehaviorTests` (mismo resultado de negocio con 2 adapters inyectados).
- `test_failure_isolation.py`, `test_service.py`.

Ningún test ejercita un gateway QR real (no existe). Un adapter Baileys nuevo heredaría gratis
`test_contract.py`/`test_isolation.py` si implementa `WhatsAppConnectionPort` correctamente — ya validan
exactamente lo que el plan pide en su Fase 23/24 (aislamiento de dominio, switch de proveedor).

## RISKS

### RIESGO CRÍTICO — decisión de negocio ya tomada y explícitamente BLOQUEADA (2026-09-16)

`AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` (misma sesión de trabajo que construyó toda la arquitectura
de adapters que este plan quiere reutilizar) evaluó exactamente Baileys/whatsapp-web.js/alternativas y
concluyó:

> **"BLOQUEADO para el número de producción real de SINTEL. No se instala ninguna librería QR contra el
> número real de negocio."**

Razones documentadas, verificadas contra el estado real del sistema (no genéricas):

1. SINTEL ya tiene una integración **oficial** de Meta Cloud API, real, en **producción**, sobre el **mismo
   número de negocio real** (`+573144601878`).
2. Conectar ese **mismo número** a Baileys (no oficial) **viola directamente los Términos de Servicio de
   WhatsApp Business** — no es un riesgo genérico de baneo, es una violación contractual sobre una cuenta ya
   aprobada y en uso real.
3. Si Meta banea el número por actividad no oficial, se pierde **también** la integración oficial que ya
   funciona — el riesgo contamina el canal de producción real, no queda aislado al experimento.
4. Usar un número distinto evita ese riesgo, pero entonces deja de ser "el mismo WhatsApp de soporte" desde
   la perspectiva del cliente.
5. Costo de infraestructura real: Baileys es Node.js, este proyecto es 100% Python/Django/Celery — exige un
   microservicio nuevo por una capacidad que la integración oficial **ya cubre por completo**.

Esta conclusión está también incrustada como comentario explícito en `settings.py:363-373` (no solo en el
documento de auditoría) y repetida textualmente en el propio `QRWebSessionAdapter` y en la UI del panel
(`WhatsAppConnectionStatusView.vue`) — es una decisión de múltiples capas del código, no una nota aislada.

**El documento `PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md` no menciona esta evaluación previa en
ningún punto de sus 42 fases**, ni aborda los puntos 1-5 arriba, ni especifica si Baileys se conectaría al
mismo número de producción (`+573144601878`) o a uno separado. La propia auditoría anterior es explícita:

> **"Esta decisión requiere autorización explícita del usuario — no se toma unilateralmente en esta sesión,
> dado el riesgo real sobre un canal de producción activo."**

Esa autorización explícita **no se ha obtenido en esta conversación**. No debería iniciarse la Fase 1 del
plan (contrato del gateway) sin resolver primero esta contradicción con el usuario.

### Riesgos secundarios (si la decisión anterior se reabre explícitamente)

- **Auth state**: no existe hoy ningún mecanismo de persistencia de credenciales criptográficas en este
  proyecto — habría que construirlo desde cero (Fase 4 del plan), con las mismas garantías de secretos que
  ya usa el proyecto para `sintel_secrets/` (patrón: fuera del repo, fuera de la imagen Docker).
- **Doble conversación (`wa-{user_id}` vs `room-{uuid}`)**: el código actual usa
  `conversation_id=f"wa-{user.id}"` al llamar `ask_ai()` (`whatsapp/domain/service.py:91`) — la brecha de
  namespace que el plan (Fase 10) pide resolver es real y verificable en el código, no hipotética.
- **Gateway inexistente**: todo el trabajo de Fases 3-8, 12-18 parte de cero — no hay nada que "migrar" de
  QR a Baileys porque QR nunca tuvo una implementación real que reemplazar. Es una implementación nueva, no
  una migración en el sentido estricto.

## DEPRECATED_CODE

Ninguno. Todo el código de `whatsapp/adapters/qr_web_session_adapter.py` y `session_manager.py` es
deliberadamente un esqueleto "honesto" (fail-loud, `NOT_IMPLEMENTED` explícito) — no hay código muerto que
limpiar, es infraestructura preparada a propósito para este momento.

## MIGRATION_BOUNDARY

Si la decisión de negocio se reafirma (usar Baileys, número separado o el mismo con riesgo aceptado
explícitamente), el límite real de la migración es:

- **Reutilizable sin cambios:** `whatsapp/ports/connection.py`, `whatsapp/domain/*` completo,
  `whatsapp/factory.py` (solo agregar un tercer `CONNECTION_TYPE_BAILEYS` + import condicional),
  `notifications/tasks.py` (sin cambios, ya es agnóstico del adapter), `support`/`ai_bridge` (sin tocar, por
  diseño).
- **Nuevo, desde cero:** microservicio `whatsapp_gateway/` (Node/TS/Baileys), `BaileysAdapter` en
  `whatsapp/adapters/`, endpoints internos gateway↔Django, contrato de eventos, persistencia de auth state,
  entrada en `docker-compose.yml`/`docker-compose.prod.yml`, variables de entorno nuevas, frontend (QR real,
  reemplazo del banner "no hay gateway conectado").
- **A resolver explícitamente antes de escribir código:** mismo número de producción vs. número separado
  (decide el resto del diseño de seguridad y de UX), y la autorización de negocio que
  `WHATSAPP_QR_PROVIDER_EVALUATION.md` dejó pendiente.
