# ARQUITECTURA COMPLETA — APP organization

**Ultima actualizacion:** 2026-07-12
**Estado:** Fases 1-5 completas. Fase 6 completa para `core`, `Notifications`, `Marketing` y
`Quotes` (parcial, solo el hardcode de nombre encontrado); `Payment` confirmado **no-op** (no
consume ningun dato de `organization`, cero coincidencias de EMAIL_*/META_*/etc en `payment/`).
Fase 7 completa para todo lo migrado hasta ahora.

**[2026-07-12] Panel administrativo propio construido** (adelanta el core de la Fase 8 del
plan CORE v4 mas grande, ver `MIGRACION_CORE_V4_DOMINIOS_FASE2_NAVEGACION.md` y
`MIGRACION_CORE_V4_DOMINIOS_FASE5_PROPUESTA_OPERACIONES.md`): `organization/api/views.py` +
`urls.py` con 8 ViewSets (uno por agregado, patron `list()`+`@action update`, mismo estilo que
`AdminSiteBrandViewSet` en `dashboard`), montado en `/api/v1/organization/` directo (NO via
`dashboard/` -- decision deliberada, `organization` es dueno de su propia API admin, como ya
hacen `kyc`/`security`/`notifications`/`operations`). Frontend:
`frontend/src/modules/organization/OrganizationView.vue` (vista unica con 8 tabs), ruta
`/panel/organizacion`, primer item del sidebar. `EmailSettings`/`DomainSettings`/
`SeoSettings`/`LegalEntityInfo` ya tienen su primer endpoint/UI (el hueco que quedaba pendiente
desde Fase 5 quedo cerrado).

## Responsabilidad

SSoT de todo dato institucional/de empresa: Branding, Contacto, Correos, Redes Sociales,
Dominios, SEO, Integraciones (credenciales de posteo en redes) e Informacion Legal. Elimina la
duplicidad de configuracion de negocio que hoy vive repartida entre `core` (5 modelos:
`SiteBrandConfig`, `CompanyContactInfo`, `FooterLink`, `NavbarLink`, `FooterCTAConfig`) y
`ecommerce/settings/base.py` (EMAIL_*, FRONTEND_BASE_URL, META_*, GOOGLE_BUSINESS_*, YOUTUBE_*,
TIKTOK_*, X_*).

Ver la auditoria completa (matriz de propietarios, consumidores y duplicidades reales
encontradas) en `Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md`
— incluye 2 bugs reales de sincronizacion silenciosa y 1 bug de mayor severidad
(`FRONTEND_ADMIN_LOGIN_URL` fantasma en `users/api/admin_auth.py`) encontrados durante la
Fase 1/2.

## Plan de migracion (9 fases, definidas por el usuario 2026-07-12)

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Auditoria arquitectonica — matriz de propietarios | **Completa** |
| 2 | Inventario global de referencias a EMAIL_*/PHONE/ADDRESS/SOCIAL/COMPANY/BRAND/etc. | **Completa** (hecha junto con Fase 1) |
| 3 | Diseno de `organization` — skeleton de la app | **Completa** |
| 4 | Definicion del dominio — agregados con owner unico | **Completa** (8 modelos, migracion `0001_initial` aplicada) |
| 5 | Crear `OrganizationSelector`/`OrganizationCommands` (unico punto de lectura/escritura) | **Completa** — 8 metodos get_*, upserts para los 7 singletons + CRUD de SocialLink, fachada de solo lectura sobre `settings` para Integraciones |
| 6 | Migracion por consumidor, orden: Notifications -> Core -> Marketing -> Payment -> Quotes -> Dashboard -> Frontend SPA | **`core` completo** (adelantado por pedido explicito del usuario, antes que Notifications). Resto pendiente. |
| 7 | Eliminacion de redundancias (borrar duplicados de otras apps) | **Completa para `core`**: `SiteBrandConfig`/`CompanyContactInfo` eliminados, filas sociales de `FooterLink` borradas. Resto de apps sin auditar todavia (Notifications/Marketing/Payment/Quotes no tenian duplicados reales segun la auditoria Fase 1). |
| 8 | Panel administrativo en `/panel/organization` | **Completa** (2026-07-12, adelantada) — `organization/api/views.py` (8 ViewSets) + `frontend/src/modules/organization/OrganizationView.vue` en `/panel/organizacion`. Ver nota de cabecera. |
| 9 | Validacion final (owner unico, sin copias, todo via `OrganizationService`, regresion) | Pendiente para el alcance completo; para `core` especificamente: owner unico OK, sin copias OK, `manage.py check`+tests OK |

## Estructura de directorios (Fase 3)

```
organization/
├── __init__.py
├── apps.py                  # OrganizationConfig, sin ready() -- sin signals
├── admin.py                 # vacio -- gestion real via /panel/, no /admin/
├── models.py                # vacio -- Fase 4
├── tests.py                 # vacio -- Fase 4+
├── CLAUDE.md
├── .AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md  # este documento
├── api/
│   ├── __init__.py
│   ├── serializers.py       # vacio -- Fase 4/5
│   ├── views.py              # vacio -- Fase 4/5
│   └── urls.py               # DefaultRouter() vacio, NO incluido todavia en ecommerce/urls.py
├── services/
│   ├── __init__.py           # re-exporta OrganizationCommands, OrganizationSelector
│   ├── commands.py           # class OrganizationCommands: pass -- Fase 5
│   └── selectors.py          # class OrganizationSelector: pass -- Fase 5
├── management/
│   └── commands/              # vacio, listo para seeds via management command o data migration
└── migrations/                # vacio -- se genera en Fase 4 con los primeros modelos
```

**Decisiones de patron (siguiendo la app mas completa del proyecto, `notifications/`, como
referencia — NO se usan carpetas `selectors/`/`commands/` separadas a nivel raiz, siguen el
patron real ya establecido: `services/commands.py` + `services/selectors.py`):**

- Sin `fixtures/` — este proyecto siembra datos via **data migrations** (patron ya usado en
  `payment/migrations/0008_seed_reconcile_periodic_task.py`), no via fixtures JSON.
- `admin.py` existe por convencion de estructura pero se espera que quede minimo — la gestion
  real de esta app es el panel Vue en `/panel/organization` (Fase 8), no Django admin.
- `api/urls.py` existe pero **no esta incluido en `ecommerce/urls.py` todavia** — se conecta en
  la Fase 5/6 cuando haya al menos un endpoint real.
- Sin signals en ningun punto de esta app (regla explicita del usuario) — cualquier
  invalidacion de cache futura se hace explicita dentro de `OrganizationCommands`, en la misma
  transaccion, replicando el patron manual que ya usan los ViewSets admin de `core`
  (`_invalidate_home_feed_cache()` etc.) pero sin el signal paralelo que `core` si tiene.

## Modelos (Fase 4 — migracion `0001_initial`)

Todos heredan `SintelBaseModel`. Los singletons (todos salvo `SocialLink`) usan `SingletonMixin`
(`save()` desactiva cualquier otro registro activo cuando `is_active=True`), mismo patron que
`core.SiteBrandConfig`/`CompanyContactInfo` pero sin signals.

| Modelo | Agregado | Campos propios | Reemplaza / origen |
|---|---|---|---|
| `Company` | Empresa | `trade_name`, `description`, `founded_year` | Parte de `core.SiteBrandConfig.site_name` (Fase 6/7 la migra) |
| `Branding` | Branding | `logo`, `favicon`, `tagline` | Resto de `core.SiteBrandConfig` (`favicon` es campo nuevo) |
| `ContactInfo` | Contacto | `phone`, `email`, `address`, `working_hours` | `core.CompanyContactInfo` (campos identicos) |
| `SocialLink` | Redes Sociales | `platform`, `url`, `icon_class`, `display_order` (no singleton) | `core.FooterLink` filtrado por `category='social'` |
| `EmailSettings` | Correos | `default_from_email`, `frontend_base_url`, `admin_login_url` | `settings.DEFAULT_FROM_EMAIL`/`FRONTEND_BASE_URL` + resuelve el bug `FRONTEND_ADMIN_LOGIN_URL` fantasma (ver auditoria Fase 1) |
| `DomainSettings` | Dominios | `primary_domain`, `admin_panel_domain`, `api_domain` | Nuevo, sin precedente previo |
| `SeoSettings` | SEO | `meta_title`, `meta_description`, `og_image` | Nuevo, sin precedente previo |
| `LegalEntityInfo` | Informacion Legal | `legal_name`, `tax_id`, `fiscal_address`, `legal_representative`, `city`, `department` | Nuevo — no existia en ningun lugar del backend (confirmado en auditoria Fase 1) |
| `CommunicationEvent` | Centro de Comunicacion | `event_type`, `channel`, `module`, `user` (nullable), `metadata` (JSONField) | Nuevo (2026-07-31) — **NO es singleton, NO usa `SingletonMixin`**: cada interaccion real es una fila append-only. Unico modelo de esta app escrito desde un endpoint publico (`AllowAny`) |

**Decisiones confirmadas por el usuario (2026-07-12), no reabrir sin instruccion explicita:**

1. **Empresa y Branding quedaron SEPARADOS** en 2 modelos (`Company`/`Branding`), no fusionados
   en uno solo aunque hoy provengan del mismo modelo `core.SiteBrandConfig`.
2. **Secretos operativos NO se centralizan en BD.** `EmailSettings` solo tiene datos de negocio
   (remitente, URLs). El password SMTP (`EMAIL_HOST_PASSWORD`) sigue en `.env`.
3. **Por la misma logica de seguridad, "Integraciones" NO tiene modelo propio en esta fase.**
   Los tokens de Meta/WhatsApp/Facebook/Instagram/YouTube/TikTok/X/Google Business Profile
   siguen en `settings/base.py` (`.env`). `OrganizationService` (Fase 5) los expondra como
   fachada de solo lectura sobre `settings`, sin tabla ni cifrado adicional que mantener. Esta
   decision no se pregunto explicitamente (es la misma logica que la decision 2, aplicada por
   consistencia) — revisar con el usuario si prefiere un tratamiento distinto.
4. **Dominios y SEO se crearon con campos iniciales razonables** (sin precedente en el
   codigo) — se pueden ajustar libremente sin bloquear las fases siguientes.

## Registrada en

- `ecommerce/settings/base.py` → `INSTALLED_APPS` (agregada al final del bloque "Project
  Modules", antes de `django_vite`, junto a `kyc`/`security`).
- `ecommerce_sintel/.AGENT.md` y `ecommerce_sintel/CLAUDE.md` → tabla de referencia de docs por
  modulo (sincronizado el mismo dia que se creo esta app).

## Cambios Recientes

### 2026-07-31 — Centro de Comunicacion: primer endpoint publico de esta app

Consumidor nuevo: `CommunicationCenter.vue` (widget flotante de contacto, portal cliente, ver
`frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` §5.1). Dos cambios:

1. **Numero institucional**: se reusa `ContactInfo.phone` (SSoT ya existente, ya publico via
   `core/footer/`) — NO se creo un campo nuevo. Seteado a `+57 314 460 1878` via
   `OrganizationCommands.upsert_contact_info()` (mismo camino de escritura que el panel admin usa).
2. **`CommunicationEvent`** (modelo nuevo, migracion `0003_communicationevent`): log append-only de
   interacciones con el widget (`panel_open`/`channel_click`). Primer y unico modelo de esta app que
   se escribe desde un endpoint **publico** (`CommunicationEventViewSet`, `AllowAny`,
   `ScopedRateThrottle` scope `communication_event: 60/hour`) — visitantes anonimos disparan estos
   eventos igual que usuarios autenticados (`user` queda `null` para anonimos,
   `OrganizationCommands.log_communication_event()` lo resuelve). Todo el resto de esta app sigue
   siendo admin-only (`IsAdminUser`), esto es una excepcion deliberada, no un relajamiento general
   de permisos. Sin `list()`/`retrieve()` — solo `create()`, no hay panel de lectura publico para
   estos eventos todavia. 11/11 tests en `organization/tests.py` (incluye 5 nuevos para este
   modelo/endpoint).

### 2026-07-12 (g) — Panel administrativo propio (adelanta Fase 8)

- `organization/api/views.py` (nuevo): `CompanyViewSet`, `BrandingViewSet`,
  `ContactInfoViewSet`, `SocialLinkViewSet` (unico CRUD completo, el resto son singletons
  `list()`+`update()`), `EmailSettingsViewSet`, `DomainSettingsViewSet`, `SeoSettingsViewSet`,
  `LegalEntityInfoViewSet`. Todos con `IsAdminUser` (`users.api.permissions`).
- `organization/api/serializers.py`: agregados los Input serializers que faltaban
  (`EmailSettingsInputSerializer`, `DomainSettingsInputSerializer`, `SeoSettingsInputSerializer`,
  `LegalEntityInfoInputSerializer`) -- antes solo existian los de lectura para esos 4.
- `organization/api/urls.py`: `DefaultRouter` con los 8 ViewSets, montado en
  `ecommerce/urls.py` bajo `/api/v1/organization/` (nuevo, junto a kyc/security/notifications/
  operations -- NO via `dashboard/`).
- `frontend/src/modules/organization/OrganizationView.vue` (nuevo): vista unica con 8 tabs
  (Empresa, Branding, Contacto, Redes Sociales, Correos, Dominios, SEO, Informacion Legal).
  Ruta `/panel/organizacion`, primer grupo del sidebar (`frontend/src/components/layout/
  Sidebar.vue`) -- recomendacion de la Fase 2 de que Organization vaya primero/segundo en el
  menu.
- Verificado: `manage.py check` limpio, los 8 endpoints devuelven 200 via `Client` autenticado
  de solo lectura, `manage.py test organization` 6/6 OK, Vite compilo `OrganizationView.vue`/
  `router.js`/`Sidebar.vue` sin errores, navegacion a `/panel/dashboard` sin auth redirige
  correctamente a login sin errores de consola.

### 2026-07-12 (f) — Fase 6: consumidor Marketing + confirmacion Payment no-op

Continuacion del mismo pedido del usuario ("si", confirmando seguir con Marketing/Payment/
Fase 8/Fase 9).

- **Los 8 adaptadores de `marketing/channels/*.py`** (`email`, `facebook`, `instagram`,
  `youtube`, `tiktok`, `x`, `whatsapp`, `google_business`) migrados de `settings.X` directo a
  `OrganizationSelector.get_integration_settings()` (dict fachada, credenciales siguen en
  `.env`, decision de seguridad de Fase 4) / `get_email_settings()` para el canal email. Import
  `from django.conf import settings` eliminado de los 7 archivos que ya no lo necesitan (queda
  solo en `email_channel.py`, que conserva el fallback a `settings.DEFAULT_FROM_EMAIL`).
- `notifications/clients/whatsapp.py` (envio TRANSACCIONAL, distinto del canal de campanas de
  marketing) **no se toco** — queda anotado como fuera de alcance de "Marketing" en el
  comentario de `whatsapp_channel.py`; si se quiere migrar tambien, es un paso aparte.
- **`payment` confirmado no-op**: grep de todas las claves EMAIL_*/META_*/WHATSAPP_*/FACEBOOK_*/
  INSTAGRAM_*/YOUTUBE_*/TIKTOK_*/X_BEARER*/GOOGLE_BUSINESS_* sobre `payment/` -> cero
  coincidencias. No hay nada que migrar ahi, confirma la auditoria Fase 1.
- Verificado: `manage.py check` limpio, `manage.py test marketing` 9/9 OK, smoke test manual
  confirmando que `OrganizationSelector.get_integration_settings()` retorna las 13 claves
  esperadas y los 8 adaptadores importan sin error.

### 2026-07-12 (e) — Fase 7: ultimo duplicado real eliminado (quotes)

`quotes/services/pdf_service.py` tenia el unico hardcode de nombre de empresa fuera de una
fuente centralizada encontrado en la auditoria Fase 1 (`"PRESUPUESTO COMERCIAL - SINTEL"`).
Ahora lee `OrganizationSelector.get_company().trade_name` (fallback `'Sintel'` si no hay fila
activa, no deberia pasar en ningun ambiente real desde el seed de la migracion 0017).
Verificado con `manage.py check` + smoke test manual (`quotes` no tiene suite de tests propia).

Con esto, **Fase 7 (Eliminacion de Redundancias) queda completa para todo lo migrado hasta
ahora** (core + notifications + accounts + users + quotes) — no quedan duplicados conocidos de
Branding/Contacto/Correos en el codigo. Pendiente: Marketing (Integraciones — no es una
"redundancia" a eliminar, es una migracion de origen de lectura, ver Fase 6) y Payment (sin
duplicados reales segun la auditoria).

### 2026-07-12 (d) — Fase 6 consumidor Notifications + 3 bugs reales corregidos

Continuacion inmediata de (c), mismo pedido del usuario ("continua"). Siguiente consumidor en
el orden original del plan (Notifications, Core [ya hecho fuera de orden], Marketing, Payment,
Quotes, Dashboard, Frontend SPA).

1. **`organization/migrations/0002_seed_email_settings.py`**: sembro `EmailSettings` con los
   valores REALES de este ambiente (`default_from_email='sintel.technology@gmail.com'`,
   `frontend_base_url='http://localhost:5173'`, `admin_login_url=''` porque nunca se configuro)
   — sin este seed, `OrganizationSelector.get_email_settings()` hubiera devuelto `None` y todos
   los consumidores hubieran caido siempre al fallback de `settings`, sin usar organization en
   la practica.
2. **`notifications/tasks.py::send_email_notification_task`**: el remitente de TODO email
   transaccional (pedidos, verificacion, etc.) ahora lee `OrganizationSelector.get_email_settings().default_from_email`
   primero, con `settings.DEFAULT_FROM_EMAIL` como fallback si no hay fila activa.
3. **2 bugs reales de la auditoria Fase 1 corregidos** (fallbacks hardcodeados que duplicaban
   literalmente los defaults de `settings/base.py` sin leer de ahi):
   - `accounts/services/commands.py::resend_verification_email` — `base_url` ya no cae directo
     a `'http://localhost:5173'` hardcodeado, primero intenta `organization.EmailSettings.frontend_base_url`.
   - `users/services/commands.py::VerificationCommands._send_otp_email` — mismo patron con
     `DEFAULT_FROM_EMAIL`/`'noreply@sintel.co'`.
4. **Bug de mayor severidad corregido**: `users/api/admin_auth.py` calculaba
   `_FRONTEND_LOGIN` a nivel de MODULO (import time) desde un setting
   (`FRONTEND_ADMIN_LOGIN_URL`) que nunca se definio en ningun `.env` — el redirect del login
   admin siempre caia a `localhost:5173` incluso en produccion. Ahora es una funcion evaluada
   por request (`_get_frontend_login_url()`) que prefiere `organization.EmailSettings.admin_login_url`,
   manteniendo los mismos 2 fallbacks de antes como red de seguridad (comportamiento actual
   identico hasta que alguien configure el campo desde el futuro panel admin). Se respeto la
   regla explicita "NO MODIFICAR" del archivo (no se toco logica de autenticacion/autorizacion,
   solo el origen del dato de configuracion).
5. **Verificado**: `manage.py check` limpio; `manage.py test accounts users notifications organization`
   corrido por separado (colision de discovery de Django al pasar `accounts`+`users` juntos en
   el mismo comando -- issue preexistente de las apps, no de esta migracion).

### 2026-07-12 (c) — Fase 5 + Fase 6/7 (consumidor `core`)

A peticion explicita del usuario: "migra toda la informacion de la empresa que esta en core
app a organization... cuando hagas esto continua con fase 5". Se ejecuto en este orden real
(datos primero, servicio despues, porque `core` necesitaba `OrganizationSelector` para poder
seguir sirviendo sus endpoints publicos sin el dato propio):

1. **`organization/services/selectors.py` + `commands.py`**: implementados de verdad (antes
   `pass`). `OrganizationSelector` tiene un `get_*`/`list_*` por agregado + `get_integration_settings()`
   (fachada de solo lectura sobre `django.conf.settings`, sin tabla — ver Fase 4). `OrganizationCommands`
   tiene upserts para los 7 singletons + CRUD de `SocialLink`.
2. **`organization/api/serializers.py`**: serializers reales (antes vacio) con los nombres de
   campo NATURALES de organization (`trade_name`, `platform`, etc.) — la adaptacion al
   contrato JSON legado de `core` vive en `core`, no aqui (separacion de responsabilidad).
3. **Migracion de datos real**: `core/migrations/0017_migrate_company_data_to_organization.py`
   (RunPython) copio el `SiteBrandConfig`/`CompanyContactInfo` activos de PRODUCCION
   ("SINTEL CORP", telefono +57 319..., email info@sintel.net.co) y las 4 redes sociales
   reales (WhatsApp, Instagram, Facebook, LinkedIn) antes de que `core` eliminara los modelos.
4. **`core` reescrito para consumir `organization`**: ver la entrada "2026-07-12" en
   `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` para el detalle completo
   (`core/services/selectors.py`, `core/api/views.py`, `core/signals.py`,
   `dashboard/api/views.py` — `AdminFooterViewSet`/`AdminSiteBrandViewSet`).
5. **Contrato publico preservado**: `/api/v1/core/site-config/` y `/api/v1/core/footer/`
   siguen respondiendo exactamente la misma forma JSON de siempre — el frontend
   (`CustomerFooter.vue`, `HomeConfigView.vue`) no se toco. `SocialLink.platform` se adapta a
   `title` via `core.api.serializers.social_link_to_footer_link_shape()`.
6. **Verificado**: `manage.py check` limpio, `manage.py test organization` (6 tests nuevos,
   Django `TestCase` — no pytest, el proyecto no lo tiene instalado en el contenedor) y
   `manage.py test core dashboard` (50/52 tests preexistentes en verde; los 2 que fallan son
   un `ImportError: No module named 'pytest'` en `core/tests/test_models_and_signals.py` que
   ya existia ANTES de esta migracion, no es una regresion introducida aqui).
7. **Decision de diseno registrada**: Empresa/Branding se mantuvieron SEPARADOS (`Company` +
   `Branding`, no un solo modelo), aunque hoy `core.SiteBrandConfig` era un unico modelo — la
   migracion de datos crea 1 fila en cada tabla a partir de la 1 fila original.

### 2026-07-12 (b) — Fase 4: dominio definido y migrado
- 8 modelos creados (`Company`, `Branding`, `ContactInfo`, `SocialLink`, `EmailSettings`,
  `DomainSettings`, `SeoSettings`, `LegalEntityInfo`), migracion `0001_initial` aplicada.
- Confirmado con el usuario: Empresa/Branding separados, secretos SMTP e Integraciones se
  quedan en `.env` (no se centralizan en BD).
- `python manage.py check` + `manage.py test organization` sin errores.
- Ningun modelo de `core` fue tocado ni eliminado todavia — la migracion de datos y limpieza
  de duplicados es Fase 6/7, no esta fase.

### 2026-07-12 (a) — Fase 3: skeleton creado
- App `organization` creada y registrada en `INSTALLED_APPS`.
- Sin modelos todavia (Fase 4 pendiente de confirmacion de diseno).
- Verificado con `python manage.py check` sin errores.
