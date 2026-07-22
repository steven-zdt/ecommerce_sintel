# IMPLEMENTATION SUMMARY — Sintel E-Commerce REST

> **Punto de entrada:** este documento es el paso 3b (fallback) del flujo de consulta jerarquico
> definido en `ecommerce_sintel/.AGENT.md` ("FLUJO OBLIGATORIO ANTES DE MODIFICAR CODIGO") —
> usarlo cuando la app exacta de una tarea no se conoce de antemano. Si SI se conoce la app,
> ir directo a su fila en la tabla "DOCUMENTOS DE REFERENCIA POR MODULO" de `.AGENT.md`.

Ultima revision: 2026-07-20 (v9 — auditoria contra codigo real: 2 apps completas que no
aparecian en NINGUNA version anterior de este documento (`organization`, `security`), rutas API
raiz reescritas contra `ecommerce/urls.py` real (2026-07-09 ya estaba desactualizada: faltaban
`admin-auth/forgot-password-*`, `internal/ai*`, `organization/`, `api/v1/` -> `security.api.urls`,
segundo include de `technical_services`), AI Core del AI Engine documentado por primera vez aqui,
Design System de frontend (`components/base/*`), modulo "Nosotros", rediseno de Auth y aislamiento
de dominio del panel referenciados)

> **Nota sobre esta version:** esta pasada (2026-07-20) NO releyo a fondo todas las apps — se
> concentro en cerrar los gaps mas graves encontrados: (1) `organization` (creada 2026-07-12) y
> `security` (creada ~2026-07-09) llevaban **meses sin aparecer en este documento**, ambas con
> apps y endpoints reales funcionando en produccion; (2) la seccion "Rutas API raiz" estaba
> desactualizada desde la v8 — reescrita completa contra el `ecommerce/urls.py` real; (3) el AI
> Engine evoluciono de "motor de generacion de codigo" a tener ademas un "AI Core" conversacional
> completo (Fases 1-8, `/chat`, Tool Registry, Agent Profiles) que este documento nunca menciono
> — agregada una referencia (el detalle vive en `ai_engine/.AGENT/` y no se repite aqui). Lo que
> **no** se releyo a fondo esta pasada: `quotes`, `marketing`, `shop`, `cart`, `inventory`,
> `technical_services` (mas alla de confirmar que su segundo `urls.py` existe), `ecommerce` (base).
> Las secciones `payment`, `dashboard`, RBAC (base) y kyc de la v8 siguen vigentes salvo lo
> anotado explicitamente abajo. Las secciones "Correcciones y mejoras aplicadas" y "Cambios
> recientes" al final del documento son **registro historico** de versiones previas (2026-06-19
> en adelante) — se conservan como bitacora, no como estado actual.

---

## Mapa de Documentacion por App

Cada app de negocio mantiene su propio documento de arquitectura en `.AGENT/docs/`.
El AI Engine los carga automaticamente en cada sesion.
Actualizar el documento de la app afectada despues de cada cambio estructural.

| App | Documento de Arquitectura | Estado (2026-07-20) |
|-----|--------------------------|--------|
| `accounts` | [ARQUITECTURA_COMPLETA_ACCOUNTS.md](../../ecommerce_sintel/accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md) | Sincronizado 2026-07-09 (SSoT de identidad endurecido: admin ya no crea perfiles especializados directamente) — probablemente afectado por el rediseno de Auth (2026-07-17, ver seccion dedicada), no releido |
| `cart` | [ARQUITECTURA_COMPLETA_CART.md](../../ecommerce_sintel/cart/.AGENT/docs/ARQUITECTURA_COMPLETA_CART.md) | Sincronizado 2026-07-03, no releido en esta pasada |
| `core` | [ARQUITECTURA_COMPLETA_CORE.md](../../ecommerce_sintel/core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md) | Sincronizado 2026-07-09 ("Constructor Visual" de Home + `FooterCTAConfig` + endpoint `enums/{name}/`, no documentados antes) |
| `dashboard` | [ARQUITECTURA_COMPLETA_DASHBOARD.md](../../ecommerce_sintel/dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md) | Creado 2026-07-03, no releido en esta pasada |
| `ecommerce` (base) | [ARQUITECTURACOMPLETA_SETTING.md](../../ecommerce_sintel/ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md) | No releida en esta pasada |
| `inventory` | [ARQUITECTURA_COMPLETA_INVENTORY.md](../../ecommerce_sintel/inventory/.AGENT/docs/ARQUITECTURA_COMPLETA_INVENTORY.md) | No releido en esta pasada |
| `kyc` | [ARQUITECTURA_COMPLETA_KYC.md](../../ecommerce_sintel/kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md) | **App nueva, no listada en ninguna version anterior de este documento** — verificacion de identidad (2026-07-06), ver seccion dedicada abajo |
| `marketing` | [ARQUITECTURA_COMPLETA_MARKETING.md](../../ecommerce_sintel/marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md) | No releido a fondo desde 2026-07-03 |
| `notifications` | [ARQUITECTURA_COMPLETA_NOTIFICATIONS.md](../../ecommerce_sintel/notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md) | Vigente — gano plantillas nuevas (`shop_*`, `service_payment_confirmed`) via las Operaciones post-pago, no releido a fondo |
| `operations` | [ARQUITECTURA_COMPLETA_OPERATIONS.md](../../ecommerce_sintel/operations/.AGENT/docs/ARQUITECTURA_COMPLETA_OPERATIONS.md) | Vigente, no releido en esta pasada |
| `organization` | [ARQUITECTURA_COMPLETA_ORGANIZATION.md](../../ecommerce_sintel/organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md) | **App nueva, no listada en ninguna version anterior de este documento** — creada 2026-07-12, SSoT de datos institucionales (antes repartidos entre `core` y `settings/base.py`), ver seccion dedicada abajo |
| `security` | [ARQUITECTURA_COMPLETA_SECURITY.md](../../ecommerce_sintel/security/.AGENT/docs/ARQUITECTURA_COMPLETA_SECURITY.md) | **App nueva, no listada en ninguna version anterior de este documento** — creada ~2026-07-09, auditoria de seguridad (`SecurityEvent`), ver seccion dedicada abajo |
| `orders` | [ARQUITECTURA_COMPLETA_ORDERS.md](../../ecommerce_sintel/orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md) | Sincronizado 2026-07-09 — "Shop Operations" extiende `Shipment` con FSM de picking/packing/despacho/entrega + `assigned_dispatcher`, ver seccion dedicada abajo |
| `payment` | [ARQUITECTURA_COMPLETA_PAYMENT.md](../../ecommerce_sintel/payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md) | Sincronizado 2026-07-13 — migracion a integracion API propia con Wompi (ADR-001, 10 fases completas), ver seccion dedicada abajo (la app **no se llama `wompi`**) |
| `quotes` | [ARQUITECTURA_COMPLETA_QUOTES.md](../../ecommerce_sintel/quotes/.AGENT/docs/ARQUITECTURA_COMPLETA_QUOTES.md) | Vigente — sistema CPQ/cuestionarios, no un wizard simple (ver seccion) |
| `renting` | [ARQUITECTURA_COMPLETA_RENTIG.md](../../ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md) | Gano `RentalOperation` (FSM post-pago, `/api/v1/renting/operations/`) y un `AvailabilityEngine` de 2 fases (2026-07-07) — ver seccion dedicada abajo |
| `shop` | [ARQUITECTURA_COMPLETA_SHOP.md](../../ecommerce_sintel/shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md) | No releido a fondo desde 2026-07-03 — la evolucion de fulfillment de productos fisicos vive en el doc de `orders` ("Shop Operations"), no aqui |
| `support` | [ARQUITECTURA_COMPLETA_SUPPORT.md](../../ecommerce_sintel/support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md) | Corregido 2026-07-03, no releido en esta pasada |
| `technical_services` | [ARQUITECTURA_COMPLETA_SERVICES.md](../../ecommerce_sintel/technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md) | Sincronizado 2026-07-09 — checkout en modal (nunca sale de la SPA) + `ServiceOperation` (FSM post-pago), ver seccion dedicada abajo |
| `users` | [ARQUITECTURA_COMPLETA_USER.md](../../ecommerce_sintel/users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md) | Sincronizado 2026-07-09 (`UserAdminCreateSerializer`/`UserAdminUpdateSerializer` ya no exponen `user_type`) |
| Frontend | [ARQUITECTURA_COMPLETAFRONEND.md](../../ecommerce_sintel/frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md) | No releido a fondo en esta pasada — ver seccion Frontend actualizada abajo |

### Regla de actualizacion

Cuando se modifica o crea logica en una app, agregar al final del doc de esa app:

```markdown
## Cambios Recientes

### [fecha] Titulo del cambio
- Que cambio y por que
- Archivos afectados
- Contrato de API si cambio
```

---

## Arquitectura general

El proyecto es una API-first SaaS con frontend SPA desacoplado.

```
Cliente (navegador)
    |
    +-- Vue.js 3 SPA (Vite) --- /panel/*  (admin)
    |                       --- /         (landing / tienda / alquiler / servicios)
    |
    +-- HTTP / WebSocket
    |
Nginx (reverse proxy, puerto 80)
    |
    +-- /api/*  -> Daphne ASGI (puerto 8000) -> Django 5 + DRF
    +-- /ws/*   -> Django Channels (WebSocket)
    |
PostgreSQL 16  +  Redis 7.2  +  Celery  +  Celery Beat

AI Engine (FastAPI, puerto 8100) + ChromaDB (8200) + Ollama (11434) — contenedores
separados, no forma parte del request path de la tienda. Dos motores en un solo
servicio (2026-07-16, "AI Core", 8 fases): (a) generacion/validacion de codigo asistida
(el uso original, sin auth, solo dev); (b) `POST /chat` conversacional con JWT real de
Django, Tool Registry (29 Tools) + Agent Profiles (9 agentes) + confirmacion humana
para escrituras — usado por el widget de soporte web y WhatsApp via Django (el motor
nunca se expone directo al cliente). Detalle completo NO se repite aqui — ver
`ai_engine/.AGENT/GUIA_USO.md` (uso practico), `FLIJO_COMPLETO_IA_ENGINE.md`
(arquitectura) y `PLAN_DE_ACCION_AI_CORE.md` (historia de las 8 fases).
```

**Stack (version real verificada 2026-07-03):**

| Capa | Tecnologia |
|------|-----------|
| Backend | Django **5.2.13** + Django REST Framework |
| API schema | drf-spectacular (OpenAPI 3) |
| Auth | simplejwt — email como USERNAME_FIELD |
| Real-time | Django Channels + channels_redis |
| Async tasks | Celery + django_celery_beat |
| Payments | Wompi Colombia (widget hospedado, firma SHA256) + Nequi Push + COD — ver app `payment` |
| Frontend | Vue 3 + Vite + Pinia + Vue Router + Axios |
| DB | PostgreSQL 16 |
| Cache/Broker | Redis 7.2 |
| Proxy | Nginx 1.26 |
| AI Engine | FastAPI + ChromaDB + Ollama (auditoria/generacion de codigo, no parte del checkout) |

---

## RBAC — Control de acceso

> **[CORREGIDO 2026-07-03]** Toda esta seccion describia un campo `User.role` (ADMIN=1, CUSTOMER=2,
> VENDOR=3, TECHNICIAN=4) que **no existe en el codigo**. Fue eliminado en un refactor DDD anterior
> (ver `users/CLAUDE.md`: *"role (ADMIN/CUSTOMER/VENDOR/TECHNICIAN) — ELIMINADO — usar
> is_staff/is_superuser + accounts.UserProfile.user_type"*). Verificado leyendo `users/models.py`
> directamente: `User` solo tiene `email, is_active, is_staff, is_verified, date_joined` (+ lo
> heredado de `PermissionsMixin`/`SintelBaseModel`). Reescrito con el modelo real.

### Modelo de usuario real

```
users.models.User (AbstractBaseUser + PermissionsMixin + SintelBaseModel)
  email, is_active, is_staff, is_superuser, is_verified, date_joined, uuid, is_deleted
  # SIN campo role. SIN first_name/last_name (viven en accounts.UserProfile).

accounts.models.UserProfile (OneToOneField -> user.profile)
  first_name, last_name, phone_number, profile_picture, user_type
  user_type in {CUSTOMER, TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR, TRANSPORTER, ACCOUNTANT}
```

- **Admin real:** `is_staff=True AND is_superuser=True` — solo via `createsuperuser` CLI, la API nunca los crea.
- **Clasificacion de usuarios regulares:** `accounts.UserProfile.user_type` (no un campo en `User`).

### TechnicianProfile (vive en `accounts`, no en `users`)

- `user`: OneToOneField a `User`, `related_name='technician_profile'` (singular).
- `specialties`: ManyToManyField a `technical_services.ServiceCategory`,
  **`related_name='technician_profiles'`** (plural, no `'technicians'` como decia la version
  anterior de este doc — ese nombre esta literalmente comentado como "reservado" en el codigo).
  Para buscar tecnicos por categoria: `category.technician_profiles.all()`.
- `is_available`: BooleanField (default True).
- Se crea automaticamente via signal `post_save` en `UserProfile` cuando `user_type == TECHNICIAN`
  (`accounts/models.py`).

### Clases de permiso (fuente de verdad)

Archivo: `users/api/permissions.py`

| Clase | Condicion de acceso |
|-------|---------------------|
| `IsAdminUser` | `is_staff AND is_superuser` |
| `IsAuthenticatedActiveUser` (alias `IsCustomerUser`) | cualquier usuario activo autenticado |
| `IsOwnerOrAdmin` | objeto propio o admin (object-level) |
| `IsAdminOrReadOnly` | GET/HEAD/OPTIONS libres; escritura solo admin |
| `IsDispatcherUser` / `IsDispatcherOrAdmin` | `DispatcherProfile` activo (app `operations`) |
| `IsOperationalUser` | TECHNICIAN/PROFESSIONAL/SPECIALIST/TRANSPORTER/CONTRACTOR o dispatcher |
| `IsBuyerOrAdmin` | `UserProfile.user_type` en `BUYER_TYPES` (`CUSTOMER, TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR`) + admin — usar en `cart`, `orders`, `renting` |
| `IsServiceProviderUser` / `IsServiceProviderOrAdmin` | `user_type` en `SERVICE_PROVIDER_TYPES` (`TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR`) — usar en CV/skills/agenda |
| `IsTransporterUser` | solo `TRANSPORTER` |
| `IsAccountantUser` | solo `ACCOUNTANT` |

**Importacion correcta en ViewSets de negocio (nunca `rest_framework.permissions.IsAdminUser`):**

```python
from users.api.permissions import IsAdminUser
```

### Gap conocido — CERRADO 2026-07-03

Se encontraron y corrigieron **inconsistencias reales** de `permission_classes` no declarado en
varios ViewSets de solo-lectura:

| App | ViewSet | Antes | Corregido a |
|---|---|---|---|
| `renting` | `RentingCategoryViewSet`, `RentingBrandViewSet`, `RentalLaborViewSet` | Sin declarar -> `IsAuthenticated` (default) | `permissions.AllowAny` explicito — ademas las dos primeras usaban selectores "_for_admin" (exponian items inactivos); ahora usan `list_categories()`/`list_rental_labor()` (solo `is_active=True`) |
| `marketing` | `MarketingCampaignViewSet`, `AgentRunViewSet`, `DashboardViewSet` | Sin declarar -> `IsAuthenticated` (default) | `IsAdminUser` (de `users.api.permissions`) |
| `marketing` | `FlashOfferViewSet` | Sin declarar -> `IsAuthenticated` (default) | `permissions.AllowAny` (su selector ya filtraba `is_active=True`, es vitrina publica) |

Cubierto por `renting/tests.py` y `marketing/tests.py` (no existian antes de esta correccion).

### SSoT de identidad + arquitectura de perfiles (2026-07-06 a 2026-07-09) — no capturado en v7

Dos piezas nuevas que cambian como el resto del proyecto debe leer/escribir `user_type`:

1. **`ProfileResolver`/`ProfileRegistry`** (`accounts/services/profile_resolver.py`,
   `profile_registry.py`) — punto unico de acceso a `user.profile`/`user.technician_profile`/
   `user.dispatcher_profile`. Prohibido `getattr(user, 'profile', None)` directo en codigo nuevo;
   usar `ProfileResolver.get_profile()`/`get_type()`/`has_type()`/`resolve()` (lanza
   `MissingRequiredProfile`/`ProfileMismatchError` cuando corresponde). `BUYER_TYPES`/
   `SERVICE_PROVIDER_TYPES`/`OPERATIONAL_TYPES`/`CONTRACTOR_ASSIGNABLE_TYPES` en
   `profile_registry.py` son la unica fuente de verdad de que tipos pertenecen a que grupo de
   dominio — nunca redefinir listas de tipos sueltas en otra app. `VendorProfile` se elimino
   (codigo muerto, ningun endpoint lo poblaba).
2. **Registro siempre CUSTOMER + upgrade via KYC** — todo registro publico
   (`AccountCommands.register_user()`/`create_from_verified_payload()`) crea SIEMPRE
   `UserProfile.CUSTOMER` con acceso instantaneo (`KycCommands.bootstrap_approved`, sin esperar
   revision admin). Convertirse en TECHNICIAN/PROFESSIONAL/SPECIALIST/CONTRACTOR es un **upgrade
   posterior**, disparado solo desde el dashboard autenticado
   (`ContractorOnboardingWizard.vue` → `POST auth/request-upgrade/` → app `kyc`, ver seccion
   dedicada abajo). **Endurecido 2026-07-09:** ni siquiera un admin puede crear un perfil
   especializado directamente desde `/panel/usuarios` — `UserAdminCreateSerializer` ya no expone
   `user_type` (siempre CUSTOMER); el unico camino para que un usuario cambie de tipo es
   `KycCommands._apply_requested_user_type()` al aprobar un upgrade. TRANSPORTER sigue siendo un
   sistema separado (`operations.DispatcherProfile`, gestionado en `/panel/despachadores`, con
   test de regresion propio que garantiza que nunca toca `UserProfile.user_type`) — no participa
   de este flujo de upgrade.

---

## Service Layer

Todas las apps implementan el mismo patron DDD:

```
app/
  services/
    __init__.py       # re-exporta Commands y Selectors
    commands.py       # operaciones de escritura (@transaction.atomic)
    selectors.py      # queries de lectura (sin efectos secundarios)
    [extra].py        # pricing_service, calculator, pdf_service, summary, kardex

dashboard/
  services/
    admin_orchestrators.py  # Orchestrators del BFF — delegan a Commands/Selectors
```

### Reglas

- **Commands:** toda escritura en un Command estatico. Usan `@transaction.atomic`.
  WebSocket notifications via `transaction.on_commit(lambda: ...)` — hoy centralizadas en
  `notifications.services.commands.NotificationCommands.dispatch_notification()`, no `ws_notify`
  directo (ver app `notifications`).
- **Selectors:** toda lectura en un Selector estatico. Sin efectos secundarios.
- **Los ViewSets no tocan ORM directamente** — solo llaman Commands y Selectors.
- **Soft-delete obligatorio:** `is_active=False` + `is_deleted=True` (ambos campos, cuando el
  modelo tiene ambos). Los selectores de admin filtran `is_deleted=False`. Nunca DELETE fisico.

> **Leccion de la auditoria 2026-07-03:** se encontraron 10 casos donde un refactor "para
> desacoplar de `inventory` via un signal" quedo a medias — el signal nunca se construyo, y
> quedaron funciones stubeadas (`return True`/`pass`) o imports comentados con la marca
> `# INVENTORY_REMOVED: ... -> usar /api/v1/inventory/ o signal` mientras el codigo que los
> consumia seguia intacto. Esto rompio: descuento de inventario real en pagos (Wompi/Nequi/COD),
> validacion de stock en `cart`, confirmacion de ordenes COD en `orders`, estadisticas de
> `shop.services.summary`, y varios archivos `tests.py` (crasheaban con `NameError` antes de
> correr). **Regla derivada:** si aparece un comentario `INVENTORY_REMOVED` o similar prometiendo
> un reemplazo, verificar que el reemplazo exista antes de asumir que el codigo esta bien.

---

## Modelo base compartido

```python
# ecommerce/base_models.py
class SintelBaseModel(models.Model):
    uuid       = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    class Meta:
        abstract = True
```

Todos los modelos de negocio heredan de `SintelBaseModel`. `is_active` es un campo aparte que cada
modelo declara por su cuenta cuando aplica (no viene de `SintelBaseModel`).

> **[CORREGIDO 2026-07-03 — Fase 6, auditoria de base de datos]** `SintelBaseModel.Meta.indexes`
> declaraba `models.Index(fields=['uuid'])` y `models.Index(fields=['-created_at'])` **ademas**
> de `db_index=True` en esos mismos campos. Verificado con `sqlmigrate` contra Postgres real: esto
> generaba **dos indices fisicos redundantes por tabla** en absolutamente todas las tablas del
> proyecto (el de `uuid` es 100% redundante con el indice que ya crea `unique=True`; el de
> `created_at` descendente es redundante en Postgres porque un B-tree se recorre en ambas
> direcciones). Se elimino `Meta.indexes` del modelo base. Se generaron 8 migraciones
> (`cart`, `marketing`, `orders`, `quotes`, `renting`, `shop`, `technical_services`, `users` —
> las demas apps no tenian modelos con esos indices duplicados todavia) con **unicamente
> operaciones `RemoveIndex`**, aplicadas y verificadas contra la BD real (`pg_indexes`) y contra
> la suite de tests completa (102+5 tests, sin regresiones nuevas). Efecto: menos overhead de
> escritura (INSERT/UPDATE) y de espacio en disco en cada tabla del sistema, sin cambio de
> comportamiento de consultas.

---

## dashboard — BFF Administrativo (patron clave)

`dashboard` es un Backend for Frontend centralizado. El panel admin SPA consume
exclusivamente `/api/v1/dashboard/`.

```
Vue SPA (/panel/*)
    |
    +-- /api/v1/dashboard/*  ->  dashboard/api/views.py  (ViewSets)
                                        |
                                dashboard/services/admin_orchestrators.py
                                        |
                        Commands + Selectors de cada app (shop, renting, orders, ...)
```

### Orchestrators (verificado 2026-07-03 contra los imports reales de `dashboard/api/views.py`)

| Orchestrator | Delegacion |
|-------------|-----------|
| `AdminMetricsOrchestrator` | Metricas consolidadas para `AdminMetricsView` |
| `UserAdminOrchestrator` | `UserSelector`, `AccountCommands` |
| `ShopAdminOrchestrator` | `ProductSelector/Commands`, `CategorySelector/Commands`, `BrandSelector/Commands`, `TaxSelector/Commands` |
| `ServiceAdminOrchestrator` | `ServiceSelector/Commands`, `ServiceCategoryCommands` |
| `RentingAdminOrchestrator` | `RentingSelector`, `EquipmentCommands`, `EquipmentVariantCommands`, `RentingBrandCommands`, `RentingCategoryCommands` |
| `QuotationAdminOrchestrator` | `QuotationSelector`, `QuotationCommands` |
| `QuoteTemplateAdminOrchestrator` | Comandos del constructor de plantillas/cuestionarios CPQ |
| `OrderAdminOrchestrator` | `OrderSelector` |
| `MarketingAdminOrchestrator` | `MarketingSelector` |
| `SupportAdminOrchestrator` | `ChatSelector`/`ChatCommands` (panel `/panel/soporte`) |

> Ver ahora `dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` (creado 2026-07-03) para
> el inventario completo de las 34 ViewSets reales — esta seccion se mantiene como resumen rapido.

> **[CORREGIDO 2026-07-03] `InventoryAdminOrchestrator` NO EXISTE.** La version anterior de este
> documento lo listaba con rutas `/api/v1/dashboard/inventory/...`. Se verifico que fue eliminado
> por completo (sin ninguna referencia colgante en todo el proyecto) y que la administracion de
> inventario se **consolido correctamente** en `/api/v1/inventory/stock-records/...`
> (`inventory/api/views.py`, `StockRecordViewSet`). Confirmado con una prueba real: `GET/POST
> /api/v1/dashboard/inventory/...` devuelve 404. No reintroducir esta ruta — usar siempre
> `/api/v1/inventory/`.

### Endpoints del dashboard (corregidos)

Todos requieren `IsAuthenticated + IsAdminUser` (de `users.api.permissions`).

| Endpoint | ViewSet |
|----------|---------|
| `GET /api/v1/dashboard/metrics/` | `AdminMetricsView` — ventas, ordenes, clientes, productos |
| `/api/v1/dashboard/users/` | `AdminUserViewSet` |
| `/api/v1/dashboard/products/` | `AdminProductViewSet` + actions: `variants/`, `variants/create`, `variants/<pk>` |
| `/api/v1/dashboard/categories/` | `AdminCategoryViewSet` — acepta multipart (image upload) |
| `/api/v1/dashboard/brands/` | `AdminBrandViewSet` — acepta multipart (logo upload) |
| `/api/v1/dashboard/taxes/` | `AdminTaxViewSet` |
| `/api/v1/dashboard/orders/` | `AdminOrderViewSet` |
| ~~`/api/v1/dashboard/inventory/`~~ | **Eliminado — usar `/api/v1/inventory/stock-records/`** |
| `/api/v1/dashboard/equipment/` | `AdminEquipmentViewSet` + actions: `variants/`, `variants/create`, `variants/<pk>` |
| `/api/v1/dashboard/renting-categories/` | `AdminRentingCategoryViewSet` |
| `/api/v1/dashboard/renting-brands/` | `AdminRentingBrandViewSet` |
| `/api/v1/dashboard/rental-labor/` | `AdminRentalLaborViewSet` |
| `/api/v1/dashboard/quotations/` | `AdminQuotationViewSet` |
| `/api/v1/dashboard/services/` | `AdminTechnicalServiceViewSet` |
| `/api/v1/dashboard/service-categories/` | `AdminServiceCategoryViewSet` |
| `/api/v1/dashboard/marketing/summary` | `AdminMarketingViewSet` |
| `/api/v1/dashboard/home-config/` (u similar) | Configuracion de landing/home — ver app `core` |
| `/api/v1/dashboard/operations/` | Panel admin de tickets/asignaciones — ver app `operations` |

### Serializers

`dashboard/api/serializers.py` re-exporta los serializers de cada app.
No define serializers propios — es un punto de entrada unico.

---

## Rutas API raiz (`ecommerce/urls.py`) — reescrito 2026-07-20 (la version 2026-07-09 ya estaba
desactualizada: le faltaban las 3 rutas de `admin-auth` de recuperacion de clave, las 2 de
`internal/ai*`, `organization/` completa y `security` — verificado leyendo el archivo real)

```python
path('api/v1/health/',        health_check),
path('admin/',                 admin.site.urls),                 # Django Admin, no confundir con /panel/*
path('api/schema/',            SpectacularAPIView...),            # OpenAPI, solo IsAdminUser
path('api/docs/',              SpectacularSwaggerView...),        # Swagger UI, solo IsAdminUser

# Admin auth — ruta aislada, nunca fusionar con api/v1/auth/ (login de CLIENTE)
path('api/v1/admin-auth/login/',                     AdminLoginView.as_view()),
path('api/v1/admin-auth/forgot-password-request/',   AdminForgotPasswordRequestView.as_view()),  # <- nuevo, rediseno Auth 2026-07-17
path('api/v1/admin-auth/forgot-password-verify/',    AdminForgotPasswordVerifyView.as_view()),    # <- nuevo
path('api/v1/admin-auth/reset-password/',            AdminResetPasswordView.as_view()),           # <- nuevo

# Internal — SOLO consumido por el AI Engine via red Docker, nunca por el frontend
path('api/v1/internal/ai-context/', AiContextView.as_view()),      # <- nuevo, AI Core Fase 1 (2026-07-16)
path('api/v1/internal/ai/',   include('ecommerce.internal_ai_urls')),  # <- nuevo, AI Core Fase 2+ (Tools de lectura)

path('api/v1/auth/',          include('accounts.urls')),
path('api/v1/auth/',          include('kyc.api.urls')),        # <- comparte prefijo con accounts
path('api/v1/users/',         include('users.urls')),
path('api/v1/dashboard/',     include('dashboard.api.urls')),
path('api/v1/shop/',          include('shop.urls')),
path('api/v1/cart/',          include('cart.urls')),
path('api/v1/orders/',        include('orders.urls')),
path('api/v1/payment/',       include('payment.urls')),       # <- NO 'wompi'
path('api/v1/inventory/',     include('inventory.urls')),
path('api/v1/services/',      include('technical_services.urls')),
path('api/v1/service-operations/', include('technical_services.api.operation_urls')),
path('api/v1/services/',      include('technical_services.api.availability_urls')),  # <- segundo include, no listado antes
path('api/v1/quotes/',        include('quotes.urls')),
path('api/v1/marketing/',     include('marketing.urls')),
path('api/v1/renting/',       include('renting.urls')),        # incluye 'operations/' desde 2026-07-07
path('api/v1/core/',          include('core.urls')),
path('api/v1/notifications/', include('notifications.api.urls')),
path('api/v1/operations/',    include('operations.api.urls')),
path('api/v1/organization/',  include('organization.api.urls')),  # <- nuevo, app creada 2026-07-12
path('api/v1/',               include('security.api.urls')),      # <- nuevo, monta SIN prefijo propio: resuelve a /api/v1/security/health/
```

**No existe `path('api/v1/support/', ...)`** — `support` es 100% WebSocket, ver seccion dedicada.
**No existe `path('api/v1/wompi/', ...)`** — cualquier referencia a esa ruta en documentacion vieja
o memoria es incorrecta.
**`kyc.api.urls` comparte el prefijo `api/v1/auth/`** con `accounts.urls` (no tiene prefijo propio
`api/v1/kyc/`) — ej. `POST /api/v1/auth/request-upgrade/`, `GET /api/v1/auth/verification/`.
**`security.api.urls` se monta en la raiz `api/v1/`, sin prefijo `security/` en el `include()`**
— el prefijo real (`api/v1/security/health/`) viene del propio `path()` dentro de
`security/api/urls.py`, no de como se incluye en `ecommerce/urls.py`. Si se agrega otra ruta a
esa app, debe llevar su propio prefijo `security/` explicito (el `include()` raiz no lo aporta).
**Fulfillment de productos fisicos ("Shop Operations") NO tiene prefijo propio** — vive como
acciones nuevas dentro de `OrderViewSet` bajo `/api/v1/orders/orders/` (`operations/`,
`operations-dashboard/`, `pack/`, `assign-dispatcher/`, `schedule-dispatch/`, etc. — ver seccion
`orders` abajo).
**El AI Engine (`ai_engine/`, FastAPI puerto 8100) es un servicio Docker separado, NO parte de
este `urls.py`** — sus rutas (`/chat`, `/api/v1/ai/context`, `/generate`, etc.) viven en su
propio proceso; solo los 2 endpoints `internal/ai*` de arriba son el lado Django del puente.

---

## Apps y estado de implementacion

### accounts — Autenticacion

Archivo: `accounts/api/views.py`

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/auth/register/` | POST | AllowAny |
| `/api/v1/auth/login/` | POST | AllowAny |
| `/api/v1/auth/logout/` | POST | IsAuthenticated |
| `/api/v1/auth/profile/` | GET, PATCH | IsAuthenticated |
| `/api/v1/auth/change-password/` | POST | IsAuthenticated |
| `/api/v1/auth/register-request/` | POST | AllowAny |
| `/api/v1/auth/register-verify/` | POST | AllowAny |

Services: `AccountCommands`, `AccountSelector`

**[NUEVO 2026-07-17, no releido a fondo esta pasada] Rediseno de Auth (5 fases).** Login/
Registro/Recuperar-contrasena del cliente se movieron a `CustomerAuthLayout.vue` (pantalla
completa, sin navbar/footer de marketing) en `/login` y `/register`. El login de ADMIN sigue
100% separado (`/panel/login` -> `AdminLoginView`/`admin-auth/login/`, nunca fusionar). Nuevo:
`GatedTokenObtainPairSerializer` (`accounts/api/views.py`) — hace que la ruta paralela
`POST /api/v1/auth/token/` (SimpleJWT estandar) tambien pase por el mismo gate de KYC que
`AccountCommands.authenticate_user()`, y rechaza explicitamente cuentas `is_staff`/`is_superuser`
("Esta cuenta debe iniciar sesion desde el panel de administracion") — sin este gate, esa ruta
emitia tokens sin pasar por ninguna de las 2 validaciones. Un usuario recien creado por
`User.objects.create()` fuera del flujo normal de registro (ej. en un script de datos de prueba)
NO puede loguearse hasta que se le llame `kyc.services.commands.KycCommands.bootstrap_approved(user)`
— el registro normal ya lo hace automaticamente, esto solo importa para scripts/seeds manuales.

**[NUEVO 2026-07-13, no releido a fondo esta pasada] Aislamiento de dominio del panel (ADR-001).**
`panel.sintel.net.co` (admin) y `sintel.net.co`/`api.sintel.net.co` (cliente) son 2 vhosts nginx
separados que comparten directivas via `nginx-common.conf` (Fase 2 del ADR) — YA DESPLEGADO en
produccion. No confundir con el rediseno de Auth (frentes distintos, misma semana de trabajo).

---

### kyc — Verificacion de identidad — app nueva, no listada antes (2026-07-06)

Archivo: `kyc/api/views.py` — montada bajo el mismo prefijo `/api/v1/auth/` que `accounts`
(`path('api/v1/auth/', include('kyc.api.urls'))`), no tiene prefijo propio.

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/auth/verification/` | GET | IsAuthenticatedActiveUser — estado propio |
| `/api/v1/auth/upload-document/` | POST | IsAuthenticatedActiveUser |
| `/api/v1/auth/submit-for-review/` | POST | IsAuthenticatedActiveUser |
| `/api/v1/auth/request-upgrade/` | POST | IsAuthenticatedActiveUser — unico disparador de un cambio de `user_type` |
| `/api/v1/auth/documents/` | GET, DELETE | IsAuthenticatedActiveUser — propios |
| `/api/v1/auth/documents/<uuid>/download/` | GET | dueno o IsAdminUser (storage privado) |
| `/api/v1/auth/admin/verifications/` | GET | IsAdminUser — cola de revision (`/panel/validaciones`) |
| `/api/v1/auth/admin/verifications/<uuid>/` | GET, actions `approve/`, `reject/`, `request-info/`, `force-approve/`, `block/`, `review-document/` | IsAdminUser |
| `/api/v1/auth/admin/verifications/metrics/` | GET | IsAdminUser — KPIs para `/panel/validaciones` |

Modelos: `UserVerification` (OneToOne con `User`, reutilizada toda la vida del usuario — para el
acceso CUSTOMER inicial y para cualquier upgrade posterior), `VerificationDocument`,
`VerificationEvent` (timeline append-only), `ConsentRecord` (Habeas Data, Ley 1581/2012).

Services: `KycCommands` (`bootstrap_approved`, `request_upgrade`, `upload_document`,
`submit_for_review`, `approve`, `force_approve`, `reject`, `request_more_info`, `block`,
`review_document`), `KycSelector` (`get_own_verification`, `list_queue`, `get_admin_metrics`).

**Maquina de estados:** `PENDING -> UNDER_REVIEW -> APPROVED | REJECTED`, mas `BLOCKED` (terminal)
y `EXPIRED` (reservado, nada lo dispara aun). `approve()` exige que todos los documentos
requeridos para el `requested_user_type` esten `APPROVED` individualmente.

**Motor de requisitos por tipo:** `kyc/services/config.py::REQUIRED_DOC_TYPES_BY_TYPE` — dict
`user_type -> [doc_type]`, una entrada por cada `SERVICE_PROVIDER_TYPES` (hoy los 4 tipos
comparten los mismos 5 documentos; agregar un tipo nuevo = sumar una entrada, no reescribir
`KycCommands`).

**Storage privado — critico:** `VerificationDocument.file` usa `PrivateKycStorage`, fuera de
`MEDIA_ROOT` (`KYC_PRIVATE_STORAGE_ROOT`), `base_url=None` — el unico acceso posible es el
endpoint `download/` autenticado. Nunca exponer esa ruta en nginx.

**Gate de login:** `AccountCommands._assert_kyc_approved(user)` bloquea solo si
`status == BLOCKED`, o si `first_approved_at is None` (nunca fue aprobado) — permite que un
CUSTOMER con un upgrade `PENDING`/`UNDER_REVIEW` en curso siga comprando sin perder acceso.

---

### users — Gestion de usuarios (admin)

Archivo: `users/api/views.py`

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/users/` | GET, POST | IsAuthenticated + IsAdminUser |
| `/api/v1/users/<uuid>/` | GET, PATCH, DELETE | IsAuthenticated + IsAdminUser |

**SSoT de identidad (2026-07-09):** `UserAdminCreateSerializer`/`UserAdminUpdateSerializer`
(`users/api/serializers.py`) ya NO exponen `user_type` — todo usuario creado desde `/panel/usuarios`
nace CUSTOMER (`AccountCommands.register_user()` defaultea a `UserProfile.CUSTOMER`); el tipo de un
usuario existente solo cambia al aprobar un upgrade KYC (`KycCommands._apply_requested_user_type`),
nunca desde este endpoint.

Services: `UserCommands`, `UserSelector`

---

### shop — Catalogo de productos

Archivo: `shop/api/views.py`

| ViewSet | Endpoint base | Escritura |
|---------|--------------|-----------|
| `ProductViewSet` | `/api/v1/shop/products/` | Solo lectura publica |
| `CategoryViewSet` | `/api/v1/shop/categories/` | Solo lectura publica |
| `BrandViewSet` | `/api/v1/shop/brands/` | Solo lectura publica |
| `TaxViewSet` | `/api/v1/shop/taxes/` | Solo lectura publica |

Escritura SIEMPRE via `dashboard/products/`, `dashboard/categories/`, etc.

Services: `ProductCommands`, `CategoryCommands`, `BrandCommands`, `TaxCommands`,
`ProductSelector`, `CategorySelector`, `BrandSelector`, `PricingService`, `ShopSummaryProvider`

Notas:
- `create_product()` crea un `ProductVariant` por defecto en la misma transaccion; el SKU se
  **auto-genera** (`_generate_variant_sku()`), nunca se acepta SKU manual del usuario (verificado
  2026-07-03 al descartar un cambio incorrecto que habria reintroducido SKU manual).
- `stock` en `ProductVariant` es cache — fuente de verdad es `StockRecord` (inventory).
- `ShopSummaryProvider.get_summary()` (consumido por `marketing`) tuvo una regresion corregida el
  2026-07-03: devolvia `in_stock/out_of_stock/total_stock_units` hardcodeados en 0 — restaurado
  para calcularlos desde `StockRecord` real.
- Soft-delete: `is_active=False` + `is_deleted=True`.

**Corregido 2026-07-03 (Fase 6, auditoria de BD):**
- `Product.is_active`/`is_featured` no tenian `db_index=True` pese a filtrarse en los selectores
  publicos de catalogo. Agregado (migracion `shop/0008`).
- `ProductReview` prevenia duplicados (`user`+`product`) solo a nivel de aplicacion
  (`ProductReviewSerializer.validate()`); una condicion de carrera podia dejar reseñas
  duplicadas. Agregado `unique_together = ('user', 'product')` en BD (verificado que no habia
  duplicados existentes antes de migrar), y `ProductViewSet.review()` ahora atrapa
  `IntegrityError` -> 400 limpio en vez de dejar escalar un 500 si la carrera llegara a ocurrir.
  Cubierto por `shop/tests.py` (no existia antes).

---

### inventory — Stock y movimientos

Archivo: `inventory/api/views.py` — `StockRecordViewSet`

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/inventory/stock-records/` | GET | IsAdminUser |
| `/api/v1/inventory/stock-records/<uuid>/transactions/` | GET | IsAdminUser |
| `/api/v1/inventory/stock-records/<uuid>/adjust-stock/` | POST | IsAdminUser |

Services: `InventoryCommands` (`register_entry`, `register_exit`), `InventorySelector`
(`get_current_stock`, `get_stock_for_variant`), `InventoryKardex`.

**Esta es la unica fuente de verdad de stock del proyecto.** Todo descuento post-pago pasa por
`payment.shared.commands._deduct_inventory_for_order()`, que a su vez llama
`InventoryCommands.register_exit()` — nunca se debe llamar `register_exit()` directamente desde
otra app fuera de ese punto (ver app `payment`).

---

### cart — Carrito de compras

Archivo: `cart/api/views.py` — `CartViewSet` (permiso real `IsBuyerOrAdmin`, no `IsAuthenticated`
generico) + `WishlistViewSet` (`IsAuthenticatedActiveUser`)

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/cart/` | GET | IsBuyerOrAdmin |
| `/api/v1/cart/add_item/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/update_item/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/clear/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/remove-item/<uuid>/` | POST | IsBuyerOrAdmin |
| `/api/v1/cart/checkout/` | POST | IsBuyerOrAdmin — preview de checkout, precios congelados + verificacion de stock |
| `/api/v1/cart/wishlist/` | GET, POST | IsAuthenticatedActiveUser |
| `/api/v1/cart/wishlist/<uuid>/` | DELETE (soft) | IsAuthenticatedActiveUser |

Services: `CartCommands`, `CartSelector`

**Fix 2026-07-03:** `_check_availability()` y `checkout_cart()` habian perdido la validacion real
de stock (retornaban `9999` fijo) — restaurado via `InventorySelector.get_current_stock()`.

**Corregido 2026-07-03 (Fase 6, auditoria de BD):** "un carrito por usuario" y "un CartItem por
(cart, variant)/(cart, service_variant)" solo se garantizaban por convencion de aplicacion
(`get_or_create()`), vulnerables a condicion de carrera. Se agrego `unique=True` en `Cart.user` y
`CheckConstraint` + 2 `UniqueConstraint` parciales en `CartItem` (migration `cart/0005_...`).
`CartCommands.add_item()` ahora captura el `IntegrityError` resultante y fusiona la cantidad en
vez de fallar. Ver `[[project_db_audit_duplicate_indexes]]`.

---

### orders — Pedidos y fulfillment

Archivo: `orders/api/views.py`, `orders/api/service_orders.py`, `orders/services/fulfillment/`

| ViewSet | Endpoint | Permiso |
|---------|----------|---------|
| `ShippingAddressViewSet` | `/api/v1/orders/addresses/` | IsBuyerOrAdmin |
| `OrderViewSet` | `/api/v1/orders/orders/` | IsBuyerOrAdmin |
| `OrderViewSet.create_from_cart` | `POST /api/v1/orders/orders/create_from_cart/` | IsBuyerOrAdmin |
| `OrderViewSet` (fulfillment) | `/{uuid}/prepare/`, `/pack/`, `/assign-dispatch-center/`, `/assign-carrier/`, `/assign-driver/`, `/dispatch/`, `/in-transit/`, `/deliver/`, `/timeline/`, `/tracking/` | admin (fulfillment) |
| `ServiceOrderViewSet` | `/api/v1/orders/service-orders/` (create/list/retrieve `IsAuthenticated`; `assign-technician/`, `auto-assign/` `IsAdminUser`; `confirm-cod/` owner) | mixto — ver `technical_services` |

Vista admin de ordenes: `GET /api/v1/dashboard/orders/` (via dashboard BFF).

Services: `OrderCommands.create_from_cart()`, `OrderSelector`, `FulfillmentCommands`
(`start_preparation`, `complete_packing`, etc. — motor de estados granular con modelo `Shipment`).

**Modelo de estados real (no el modelo viejo `pending/processing/paid/shipped/delivered`):**
`STATUS_CREATED`, `STATUS_PENDING_PAYMENT`, `STATUS_PAID`, `STATUS_PREPARING`,
`STATUS_READY_FOR_DISPATCH`, `STATUS_ASSIGNED`, `STATUS_PICKED_UP`, `STATUS_IN_TRANSIT`,
`STATUS_OUT_FOR_DELIVERY`, `STATUS_DELIVERED`, `STATUS_COMPLETED`, `STATUS_CANCELLED`,
`STATUS_RETURN_REQUESTED`, `STATUS_RETURNED`, `STATUS_FAILED_DELIVERY`, `STATUS_LOST`.
`'pending'`/`'processing'` quedan solo como choices legacy — `create_from_cart()` ya no los usa.

**Bug critico corregido 2026-07-03 (checkout COD completo):** `create_from_cart()` habia dejado de
llamar a `CodCommands.confirm_order()` para pagos COD — toda orden COD quedaba creada y atascada en
`STATUS_PENDING_PAYMENT` para siempre, sin `CodTransaction` ni descuento de inventario. Restaurado;
`CodCommands.confirm_order()` ahora tambien transiciona `order.status = STATUS_PAID` (mismo gate que
usan Wompi/Nequi). Ademas se encontraron y corrigieron **3 instancias** de un bug relacionado:
`WompiPaymentViewSet.initialize()`, `NequiPaymentViewSet.initialize()` y
`ServiceOrderViewSet.confirm_cod()` comparaban `order.status` contra el string legacy `'pending'` en
vez de `Order.STATUS_PENDING_PAYMENT` — rechazaban con 400 toda orden recien creada. Ver
`orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md` para el detalle completo y los tests de
regresion agregados.

**Bug de rendimiento corregido 2026-07-03 (Fase 6, auditoria de BD):** `OrderSelector.list_for_user()`
y `list_all_for_admin()` (usadas por `OrderViewSet.list()` **y** `.retrieve()`, ya que el ViewSet no
sobreescribe `get_object()`) no traian `select_related`/`prefetch_related` para las relaciones que
`OrderSerializer` siempre serializa (`items`, `shipping_address`, `shipment` +
`shipment.dispatch_center/carrier/driver`). Ademas usaban un `.only(*LIST_FIELDS)` que ni siquiera
cubria todos los campos que el serializer necesita (`payment_method`, `discount_amount`,
`tracking_number`, `shipping_address_id` no estaban incluidos), causando recargas de campos
diferidos por cada orden. **Medido empiricamente:** listar 2 ordenes con item+shipment+carrier
completos tomaba **19 queries**, escalando linealmente con la cantidad de ordenes. Corregido:
`OrderSelector` ahora usa `select_related(...)` + `prefetch_related('items')` sin `.only()`
parcial — **3 queries constantes** sin importar cuantas ordenes se listen. Cubierto por
`orders.tests.OrderFulfillmentAPITestCase.test_list_orders_has_no_n_plus_1`
(`assertNumQueries(3)` — falla si alguien reintroduce el N+1). `OrderSelector.DETAIL_FIELDS` (dead
code, nunca se uso) se elimino en el mismo cambio.

**Indice agregado:** `Order.status` no tenia `db_index=True` pese a filtrarse constantemente
(metricas del dashboard, `ShopSummaryProvider`, etc.) — agregado.

### "Shop Operations" — fulfillment logistico de productos fisicos (2026-07-09, nuevo)

Evolucion de la logistica de pedidos de producto (picking/packing/despacho/entrega),
implementada **extendiendo** `orders.Shipment` + `orders/services/fulfillment/` (que ya existia
con el FSM base) en vez de crear un modelo nuevo — la auditoria previa a implementar encontro que
~90% de lo pedido ya estaba construido, solo faltaba UI funcional, notificaciones y creacion
automatica.

- **`Shipment` extendido:** nuevos campos `assigned_dispatcher` (FK a `operations.DispatcherProfile`
  — reusa el mismo pool de transportistas que Renting, gestionado en `/panel/despachadores`, en vez
  de duplicar con el `driver`/`carrier` legado sin FK a `User`), `responsible`, `shipping_method`
  (7 opciones), `dispatch_scheduled_at`, `route`, campos de empaque
  (`package_type/weight/volume/dimensions`), `evidence_photos`, `delivery_signature`,
  `customer_confirmed_at`.
- **Creacion automatica:** `FulfillmentCommands.ensure_shipment_for_order()` se dispara desde
  `payment/shared/commands.py::confirm_order_payment` y `payment/cod/services/commands.py::CodCommands.confirm_order`
  — el mismo punto donde ya se descuenta inventario. Solo para ordenes con al menos un item de
  producto fisico. El inventario se descuenta **una sola vez**, al pago; el despacho
  (`FulfillmentCommands.dispatch()`) solo valida stock de solo lectura, nunca vuelve a descontar.
- **Notificaciones nuevas:** 7 plantillas (`shop_order_received`, `shop_preparing_order`,
  `shop_dispatch_assigned`, `shop_order_shipped`, `shop_delivery_scheduled`, `shop_order_delivered`,
  `shop_delivery_confirmed`) disparadas desde `ShipmentTimelineCommands.add_event()`.
- **Endpoints nuevos en `OrderViewSet`** (`/api/v1/orders/orders/{uuid}/...`): `assign-dispatcher/`,
  `schedule-dispatch/`, `out-for-delivery/`, `complete/`, `confirm-delivery/` (cliente confirma
  recepcion); mas `operations/` y `operations-dashboard/` (detail=False) para la bandeja
  administrativa.
- **Frontend:** `ShopOperationBoard.vue` en `/panel/productos/operaciones` (anidado en el grupo
  "Tienda" del sidebar, no un menu independiente); `ShipmentStatusBadge.vue`/`ShipmentTimeline.vue`
  nuevos; `CustomerOrdersView.vue` gano el timeline real del shipment (reemplazo un stepper
  generico que usaba claves inexistentes en `Order.STATUS_CHOICES`).
- **Bug real encontrado en E2E (no reportado por el usuario):** `AssignmentCommands.assign_dispatcher()`
  actualizaba `Order.status` pero no `Shipment.status` — el boton de "siguiente paso" nunca
  aparecia tras asignar transportista. Corregido.

Ver [[project_shop_operations_module]] en memoria para el detalle completo.

---

### payment — Pagos (Wompi online + COD + Nequi Push)

> **[CORREGIDO 2026-07-03] Esta app se llama `payment`, NUNCA `wompi`.** La version anterior de
> este documento (y varios otros documentos del proyecto) la describian con un nombre de app, rutas
> y variables de entorno que no correspondian al codigo real. Verificado exhaustivamente contra
> `payment/apps.py`, `ecommerce/urls.py`, `ecommerce/settings/base.py` y las llamadas reales del
> frontend (`CheckoutView.vue`, etc.).

> **[NUEVO 2026-07-13] Migracion a integracion API propia con Wompi (ADR-001, 10 fases completas).**
> El checkout de tarjeta (nueva o guardada) ya NO depende del Widget de Wompi para crear la
> transaccion -- el backend la crea de forma sincrona via un adaptador propio
> (`payment/online/wompi_client.py::WompiApiClient`), con un feature flag real de reversion
> instantanea, historial de auditoria (`TransactionEvent`), reconciliacion mejorada, panel admin con
> acciones reales, y pruebas E2E/carga permanentes. **PSE queda excluido a proposito** (sigue usando
> el Widget completo, requiere redireccion al banco). Detalle completo:
> [ARQUITECTURA_COMPLETA_PAYMENT.md](../../ecommerce_sintel/payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md)
> seccion 10, y el ADR + informes por fase en `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md` /
> `FASE{0..9}_*.md` — no se repite el detalle aqui a proposito, este documento es un resumen de alto
> nivel, no la fuente de verdad.

Archivo: `payment/online/api/views.py` — `WompiPaymentViewSet` (el widget de Wompi es un metodo
dentro de la app `payment`, no la app en si); `payment/nequi/api/views.py` — `NequiPaymentViewSet`;
`payment/cards/views.py` — `TokenizedCardViewSet`.

| Endpoint | Metodo | Permiso | Descripcion |
|----------|--------|---------|-------------|
| `/api/v1/payment/payments/initialize/` | POST | IsAuthenticated | Crea `Transaction` PENDING, calcula firma SHA256. Si el body trae `card_token`/`payment_source_id` (checkout con tarjeta, 2026-07-13), crea la transaccion TAMBIEN de forma sincrona en Wompi -- 403 si el feature flag lo tiene desactivado |
| `/api/v1/payment/payments/feature-flags/` | GET | AllowAny | Estado del kill-switch `card_api_flow_enabled` (2026-07-13) |
| `/api/v1/payment/payments/webhook/` | POST | AllowAny | Receptor de eventos Wompi (firma HMAC verificada) |
| `/api/v1/payment/payments/transaction-status/` | GET | IsAuthenticated + ownership | Detalle post-pago (`?tx=<uuid>`) |
| `/api/v1/payment/payments/confirmation/` | GET | IsAuthenticated + ownership | Resultado consolidado; si sigue PENDING, sincroniza en vivo contra la API de Wompi (`_sync_wompi_status`) |
| `/api/v1/payment/nequi/initialize/` | POST | IsAuthenticated | Push Nequi |
| `/api/v1/payment/nequi/status/` | GET | IsAuthenticated + ownership | Polling de estado |
| `/api/v1/payment/cards/` | GET, POST, DELETE, `set-default/` | IsAuthenticatedActiveUser | Tarjetas tokenizadas — alta ahora automatizada desde el frontend (`useCardTokenization.js`, 2026-07-13), ya no se pega el token a mano |
| `/api/v1/dashboard/payment-transactions/{uuid}/resync/`, `.../events/`, `.../feature-flags/` | POST/GET/PATCH | Admin | Panel de pagos con acciones reales (2026-07-13) — antes 100% de solo lectura |

**Variables de entorno reales (verificadas en `ecommerce/settings/base.py`):**

```env
WOMPI_PUBLIC_KEY=pub_test_...
WOMPI_PRIVATE_KEY=prv_test_...
WOMPI_INTEGRITY_SECRET=...      # NO "WOMPI_INTEGRITY_KEY"
WOMPI_EVENTS_SECRET=...         # NO "WOMPI_EVENTS_KEY"
WOMPI_ENVIRONMENT=test|prod
WOMPI_WIDGET_URL=https://checkout.wompi.co/widget.js
NEQUI_CLIENT_ID=...
NEQUI_CLIENT_SECRET=...
NEQUI_API_KEY=...
NEQUI_ENVIRONMENT=sandbox
```

**Integridad del checkout:**
`integrity_signature = SHA256(transaction_uuid + amount_in_cents + currency + WOMPI_INTEGRITY_SECRET)`.

**Verificacion de firma del webhook — YA IMPLEMENTADA (no es un pendiente):**
`_verify_wompi_event_signature()` en `payment/online/api/views.py`, algoritmo oficial de Wompi
(properties + timestamp + `WOMPI_EVENTS_SECRET`, comparacion timing-safe). Si `WOMPI_EVENTS_SECRET`
esta vacio, se permite pasar (modo desarrollo) — **debe configurarse en produccion**.

**Flujo de pago (3 metodos, Wompi con 2 sub-flujos desde 2026-07-13):**
1a. Wompi/Tarjeta (backend-directo, sub-metodo "Tarjeta" del checkout): `initialize/` con `card_token`
    -> `WompiApiClient` crea la transaccion sincrona en Wompi (sin abrir widget) -> `webhook/` (sigue
    siendo la unica fuente de verdad autoritativa) -> `PaymentCommands.confirm_payment()` ->
    `confirm_order_payment()` -> `Order.status = paid` + descuento inventario + notificacion.
1b. Wompi/PSE-Otros (sub-metodo "PSE / Otros", sin cambios de comportamiento): `initialize/` sin
    `card_token` -> widget completo -> `webhook/` -> mismo `confirm_order_payment()`.
2. Nequi: `nequi/initialize/` -> push al celular -> polling `nequi/status/` -> mismo `confirm_order_payment()` al aprobarse.
3. COD: descuento de inventario y confirmacion **inmediatos** dentro de `create_from_cart()`, via `CodCommands.confirm_order()` (bug de checkout corregido 2026-07-03, ver seccion `orders`).

**Corregido 2026-07-03 (Fase 6, auditoria de BD):**
1. `Transaction.status` gano `db_index=True` (sus hermanos `CodTransaction.status`/`NequiTransaction.status` ya lo tenian).
2. `Transaction` y `NequiTransaction` ganaron un `CheckConstraint` en BD que exige exactamente uno de `order`/`rental_request` establecido — antes solo era una convencion documentada, sin proteccion real.
3. `TokenizedCard` gano `UniqueConstraint(user, condition=is_default & ~is_deleted)` para garantizar en BD "una sola tarjeta default por usuario" (antes solo lo garantizaba `cards/views.py` con dos escrituras no atomicas). `create()`/`set_default()` ahora usan `transaction.atomic()` + capturan `IntegrityError` -> `409`.
4. **Bug de produccion inedito encontrado al testear lo anterior:** `TokenizedCardViewSet.destroy()` asignaba y guardaba un campo `is_active` que **no existe** en `TokenizedCard` -> `ValueError` (500) en toda llamada real a `DELETE /api/v1/payment/cards/{uuid}/`. El endpoint nunca funciono; no habia tests que lo cubrieran. Corregido. Migracion `payment/0007_...`. Ver `[[project_db_audit_duplicate_indexes]]` para el detalle completo.

**Bug critico corregido 2026-07-03:** `_deduct_inventory_for_order()` y `_has_sufficient_stock()`
estaban stubeadas (no-ops) por un refactor incompleto — ningun pago descontaba stock real.
Restaurado, con tests de regresion en `payment/tests.py`. Tambien corregido un bug de
`@transaction.atomic` que revertia silenciosamente el `Transaction.status = 'ERROR'` al detectar
stock insuficiente. Ver `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` y
`payment/.AGENT/docs/AUDITORIA_PAYMENT_WOMPI_2026-07-03.md` para el detalle completo (5 bugs
distintos encontrados y corregidos solo en esta app).

---

### technical_services — Servicios tecnicos

Archivo: `technical_services/api/views.py` (catalogo, todo `AllowAny` en lectura) +
`orders/api/service_orders.py` (**ciclo de vida de la solicitud/orden de servicio, no vive en
`technical_services`**).

| ViewSet | Endpoint | Permiso |
|---------|----------|---------|
| `TechnicalServiceViewSet` | `/api/v1/services/services/` (+ action `quotation/`) | AllowAny |
| `ServiceCategoryViewSet` | `/api/v1/services/categories/` | AllowAny |
| `ServiceLevelViewSet` | `/api/v1/services/levels/` | AllowAny |
| `ServiceVariantViewSet` | `/api/v1/services/variants/` (+ action `price_history/`) | AllowAny (list) / IsAdminUser (`price_history`) |
| `ServiceMaterialViewSet` | `/api/v1/services/materials/` | AllowAny |
| `ServiceConfigurationViewSet` | `/api/v1/services/configurations/` | AllowAny |
| `ServiceOrderViewSet` (vive en `orders`) | `/api/v1/orders/service-orders/` | ver seccion `orders` |

Services: `ServiceAssignmentCommands` (`assign_technician`, `auto_assign_technician`),
`TechnicianSelector.get_available_for_category()`, `ServiceCommands`
(`confirm_slot_on_payment`/`release_slot_on_failure`, enlazados al flujo de pago),
`ServicePricingCalculator.calculate_breakdown()`, `ServiceSelector.get_variant_quotation()`.

**Motor de Reglas de Costo Dinamicas:** `ServiceCostRule` (contextos `SETUP`/`OPERATIONAL`/`TAX`/
`DISCOUNT`, tipos `PERCENTAGE`/`FLAT`, global o por variante via `ServiceCostAssignment`). El
endpoint `GET /api/v1/services/services/<uuid>/quotation/?variant_uuid=&duration=&discount_pct=`
retorna un `breakdown` estructurado (base_amount, cost_rules, additions, discounts, IVA, total).

**N+1 corregido parcialmente 2026-07-03 (Fase 6, afecta `/api/v1/dashboard/services/` Y el
catalogo publico `/api/v1/services/services/`, mismo serializer):**
1. `TechnicalServiceSerializer.get_variants()` hacia `obj.variants.filter(is_deleted=False)` —
   un `.filter()` explicito en un manager **ignora cualquier `prefetch_related` declarado**
   (Django solo cachea `.all()`). Corregido filtrando en Python sobre `obj.variants.all()`.
2. Faltaba `variants__materials__product_variant__product` en el prefetch de
   `ServiceSelector.list_all_for_admin()`. Agregado.
3. `LaborCostCalculator.get_active_config()` consultaba `ServiceConfiguration` (un valor
   **global**, igual para toda la peticion) **una vez por cada variante serializada**. Agregado
   cache de 5 min, invalidado por signal `post_save`/`post_delete` en
   `technical_services/signals.py` (`ServiceConfiguration` tambien es editable desde Django
   Admin, no solo desde `ServiceConfigurationCommands` — la señal cubre ambos caminos).

Medido: **31 -> 23 queries** para listar 2 servicios con 1 variante + 1 material cada uno.
**Pendiente, no corregido (fuera del alcance aprobado):** `get_calculated_price()` y
`get_price_info()` en `ServiceVariantSerializer` llaman **cada uno por separado** a
`ServiceSelector.get_variant_quotation(obj)`, duplicando todo el calculo de precio por variante.
Arreglarlo de raiz requiere cambiar como el serializer invoca el calculo (computarlo una vez y
reusarlo en ambos campos), un cambio de diseño mas alla de agregar cache.

### Checkout en modal + Service Operations (2026-07-09, nuevo)

Dos evoluciones grandes sobre el flujo de solicitud de servicio, sin tocar el modulo `payment`:

1. **Checkout dentro de la SPA (nunca navega fuera):** `ServiceRequestWizard.vue` ahora abre
   `ServiceCheckoutModal.vue` (nuevo) en vez de una UI de pago inline — reusa `useWompiWidget.js`
   (compartido con Cart/Renting) que ya abria Wompi como iframe overlay. Nuevo
   `serviceCheckoutStore.js` (Pinia).
2. **`ServiceOperation`** — FSM post-pago separado de `OrderServiceDetail` (dominio comercial),
   11 estados (`READY_FOR_PLANNING` → ... → `CLOSED`, + `CANCELLED`), con conflicto real de
   agenda contra `accounts.ProfessionalAvailability` (nunca doble-reserva un tecnico). **Se crea
   ANTES del pago** (a diferencia de "Shop Operations"), al final de
   `ServiceCommands.request_service()` — decision explicita del usuario: todo servicio solicitado
   debe llegar de inmediato al panel de Operaciones, pagado o no (el board muestra un badge "Pago
   pendiente" y no permite depachar sin pago).
3. **Centralizacion:** asignacion de tecnicos y operacion de cada servicio se maneja 100% desde
   `/panel/servicios/operaciones` (`ServiceOperationBoard.vue`) — el board viejo de solo-asignacion
   (`TechnicianAssignmentBoard.vue`, ruta `/panel/servicios/asignacion-tecnicos`) sigue existiendo
   pero ya no esta en el menu del sidebar.
4. **Bug corregido (reporte real del usuario):** `auto-assign/` y el selector manual de tecnico
   usaban el mismo filtro estricto de categoria/especialidad — el admin no podia asignar
   manualmente a un tecnico fuera de esa coincidencia exacta aunque quisiera decidirlo el mismo.
   Se separo: `auto-assign` sigue con matching estricto, la asignacion manual ahora usa
   `TechnicianSelector.get_all_active_technicians()` (todos los tecnicos activos, sin filtro) —
   el administrador decide si esta calificado.

Endpoints nuevos: `/api/v1/service-operations/` (`ServiceOperationViewSet` — `plan/`,
`assign-technician/`, `unassign-technician/`, `notify-client/`, transiciones de estado,
`report-incident/`, `resolve-incident/`, `close/`, `dashboard/`, `available-technicians/`).

Ver `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` (§18 completo) para el
detalle.

---

### quotes — Cotizaciones (sistema CPQ, no un wizard simple)

> **[ACTUALIZADO 2026-07-03]** Este ya no es un flujo lineal GET/POST/PDF. Es un sistema de
> "Configure-Price-Quote" con plantillas por categoria/subcategoria y un **Constructor de
> Cuestionarios Tecnicos** — ver `project_quotes_questionnaire_engine` en memoria del proyecto.

Archivo: `quotes/api/views.py` — `QuotationViewSet` + ViewSets de plantillas.

| Endpoint | Metodo | Permiso |
|----------|--------|---------|
| `/api/v1/quotes/quotations/` | GET, POST | IsAuthenticated (create: AllowAny para cotizacion de catalogo/custom) |
| `/api/v1/quotes/quotations/from-template/` | POST | IsAuthenticated — crea "Solicitud de Cotizacion" desde cuestionario, sin precios visibles al cliente |
| `/api/v1/quotes/quotations/<uuid>/send/` | POST | genera y envia PDF (Celery) |
| `/api/v1/quotes/quotations/<uuid>/add_attachment/` | POST | adjuntos |
| `/api/v1/quotes/quotations/<uuid>/download_pdf/` | GET | AllowAny |
| `/api/v1/quotes/quote-template-categories/` | GET | AllowAny |
| `/api/v1/quotes/quote-template-subcategories/` | GET | AllowAny (`?category=`) |
| `/api/v1/quotes/quote-templates/` | GET | AllowAny |

`Quotation.STATUS_CHOICES` tiene **10 estados**: `BORRADOR, RECIBIDA, EN_REVISION,
PENDIENTE_INFORMACION, COTIZADA, ENVIADA, ACEPTADA, RECHAZADA, VENCIDA, CANCELADA`, con
`QuotationTimeline` como historial append-only.

`QuoteTemplateModule` tiene tipos `EQUIPMENT`/`MATERIALS`/`LABOR`. `QuoteQuestion` +
`QuoteQuestionOption` son el motor del constructor de cuestionarios.

Admin: `GET /api/v1/dashboard/quotations/` — lista completa.
Services: `QuotationCommands`, `QuotationSelector`, `PdfService`

---

### marketing — Campanas y dashboards

| ViewSet | Endpoint | Permiso real |
|---------|----------|---------|
| `MarketingCampaignViewSet` | `/api/v1/marketing/campaigns/` | `IsAdminUser` (corregido 2026-07-03; ModelViewSet completo) |
| `FlashOfferViewSet` | `/api/v1/marketing/offers/` | `AllowAny` (corregido 2026-07-03; vitrina publica, selector ya filtraba `is_active=True`) |
| `AgentRunViewSet` | `/api/v1/marketing/agent-runs/` | `IsAdminUser` (corregido 2026-07-03) |
| `DashboardViewSet` | `/api/v1/marketing/dashboard/` | `IsAdminUser` (corregido 2026-07-03) |

Services: `MarketingSelector` (y comandos asociados). Existen ademas directorios `marketing/agent/`
y `marketing/channels/` con tareas Celery, sugiriendo un sistema de marketing asistido por IA
(`AgentRun`) mas alla de un CRUD de campanas — no se profundizo en esta pasada.

**Corregido 2026-07-03 (Fase 6, auditoria de BD):** `MarketingCampaign.__str__()` referenciaba un
campo `self.channel` inexistente (el real es `channels`, plural) -- `AttributeError` en cualquier
`str(campaign)`. `FlashOffer` gano un `CheckConstraint` "como maximo un target" (variant/
service_variant/equipment_variant) -- deliberadamente no "exactamente uno", porque una oferta sin
target (oferta general) es un caso valido ya presente en produccion. `db_index` agregado en
`is_active`/`start_time`/`end_time`. Ver `[[project_db_audit_duplicate_indexes]]`.

---

### renting — Equipos en alquiler

Archivo: `renting/api/views.py`

| ViewSet | Endpoint | Permiso real |
|---------|----------|-----------|
| `EquipmentViewSet` | `/api/v1/renting/equipment/` (+ `check-availability`) | AllowAny |
| `EquipmentVariantViewSet` | `/api/v1/renting/variants/` | AllowAny |
| `RentingCategoryViewSet` | `/api/v1/renting/categories/` | `AllowAny` (corregido 2026-07-03; ademas ahora excluye inactivos) |
| `RentingBrandViewSet` | `/api/v1/renting/brands/` | `AllowAny` (corregido 2026-07-03) |
| `RentalLaborViewSet` | `/api/v1/renting/labor/` | `AllowAny` (corregido 2026-07-03; ademas ahora excluye inactivos) |
| `RentalRequestViewSet` / `RentalRequestListCreateAPIView` | `/api/v1/renting/rental-requests/` | `IsBuyerOrAdmin` |
| `RentalOperationViewSet` | `/api/v1/renting/operations/` (**nuevo, 2026-07-07**) | admin — panel `/panel/ordenes/renting` |

`EquipmentVariant` confirma pricing dual: `rental_price_per_day` y/o `rental_price_per_hour`, al
menos uno obligatorio. `RentalRequest` confirma el wizard de 8 pasos (docstring literal en el
modelo) con `STATUS_CHOICES` de 8 estados (draft -> pending_validation -> pending_payment -> paid ->
confirmed -> in_operation -> finished / cancelled) y soporta pago `WOMPI`/`NEQUI`/`COD`.

Modelos adicionales no cubiertos por versiones previas de este doc: `RentalProjectAttachment`,
`RentalPeriod` (disponibilidad por solape de fechas, no descuento de stock), `EquipmentLogisticsConfig`,
`RentalCostRule`/`RentalCostAssignment`.

Services: `RentingCommands`, `EquipmentCommands`, `EquipmentVariantCommands`,
`RentingCategoryCommands`, `RentingBrandCommands`, `RentalLaborCommands`,
`RentingSelector`, `EquipmentVariantSelector`, `RentingSummaryProvider`

**Corregido 2026-07-03 (Fase 6, auditoria de BD) — bug de sobreventa real:**
`RentalRequestCommands.create_request()` verificaba disponibilidad (`RentingSelector.check_availability()`)
sin ningun bloqueo de fila; dos solicitudes concurrentes para el mismo `EquipmentVariant` y fechas
solapadas podian pasar ambas la validacion y sobrevender el mismo equipo fisico. Se agrego
`select_for_update()` sobre la variante al inicio de `create_request()`. Probado con un test de
concurrencia real (2 threads, `TransactionTestCase`). Tambien: N+1 en `RentalRequestViewSet.list()`
(`get_primary_image()` ignoraba el prefetch) y `db_index` faltante en `Equipment.is_active`/
`is_featured`. Ver `[[project_db_audit_duplicate_indexes]]`.

### `RentalOperation` + `AvailabilityEngine` (2026-07-07, nuevo) — no capturado en v7

- **`RentalOperation`** — FSM post-pago separado de `RentalRequest` (10 estados,
  `READY_FOR_SCHEDULING` → ... → `COMPLETED`), con `assigned_dispatcher` (mismo
  `operations.DispatcherProfile` que usa "Shop Operations"), dashboard de KPIs server-side,
  incidencias, emails de ciclo de vida completos. Panel `/panel/ordenes/renting`
  (`RentalOperationBoard.vue`).
- **`AvailabilityEngine`, 2 fases:** Fase 1 — `pending_payment` ya no bloquea la agenda del
  equipo; el lock de disponibilidad se movio a `confirm_payment()`/`approve_manual_validation()`,
  con manejo explicito de `payment_conflict`/`refund_required` si dos solicitudes compiten. Fase
  2 — wizard de reserva con componentes nuevos (`AvailabilityPill`/`AvailabilityCard`/
  `RentalHourSelector`), panel `/panel/renta/solicitudes`.
- **Decision de UX ya tomada dos veces** (Renting y luego Technical Services): la "agenda"/
  calendario de operaciones se muestra como lista, no como grilla/Kanban real — no volver a
  proponer un calendario visual sin que el usuario lo pida explicitamente.

---

### organization — SSoT de datos institucionales — app nueva, no listada antes (2026-07-12)

Antes de esta app, la marca/contacto/redes sociales vivian repartidos entre modelos de `core`
(`SiteBrandConfig`, `CompanyContactInfo`, `FooterLink(category='social')`) y variables de entorno
sueltas en `settings/base.py`. `organization` los consolido en un unico dueno — **ninguna otra
app puede leer estos datos directamente**, todo pasa por `OrganizationSelector`/
`OrganizationCommands` (`core` los consume asi desde 2026-07-12, ver seccion `core` abajo).

Montada en `/api/v1/organization/` via `DefaultRouter`, 8 recursos (todos requieren
`IsAdminUser` para escritura; lectura publica solo donde `core` los reexpone via `site-config`/
`footer`):

| Recurso | Modelo | Notas |
|---|---|---|
| `company/` | `Company` | Singleton — nombre comercial, descripcion, ano de fundacion |
| `branding/` | `Branding` | Singleton — logo, favicon, tagline (separado de `Company` a proposito) |
| `contact/` | `ContactInfo` | Singleton — telefono, email, direccion, horario |
| `social-links/` | `SocialLink` | Lista — reemplaza `core.FooterLink(category='social')` |
| `email-settings/` | `EmailSettings` | Singleton — solo datos de negocio (`default_from_email`, `frontend_base_url`); el password SMTP sigue en `.env` a proposito |
| `domain-settings/` | `DomainSettings` | Singleton — dominio principal/panel/API |
| `seo-settings/` | `SeoSettings` | Singleton — meta title/description, imagen Open Graph |
| `legal-entity/` | `LegalEntityInfo` | Singleton — razon social, NIT, direccion fiscal, representante legal |

Todos los singletons siguen el mismo patron (`SingletonMixin.save()` desactiva cualquier otro
registro activo), sin signals de invalidacion de cache propia — `core` invalida
`SITE_CONFIG_CACHE_KEY`/`FOOTER_CACHE_KEY` explicitamente en `dashboard/api/views.py` justo
despues de cada `OrganizationCommands.upsert_*`.

Panel admin: `OrganizationView.vue` en `/panel/organizacion`, 8 tabs (uno por recurso de arriba).
Migro datos reales existentes via data migration (`core/migrations/0017_migrate_company_data_to_organization.py`)
antes de borrar los modelos viejos de `core` — sin perdida de datos en el traspaso.

**Nota (2026-07-20):** `organization/CLAUDE.md` todavia dice "Fase 3 de 9 completada", pero los 8
recursos de arriba estan todos operativos (verificado con los 8 endpoints reales y su consumo
activo desde `OrganizationView.vue` toda esta sesion) — esa nota de fase parece desactualizada,
no se corrigio en esta pasada (fuera del archivo pedido auditar).

---

### security — Auditoria de seguridad transversal — app nueva, no listada antes (~2026-07-09)

Dominio complementario (no reemplaza) a `users.UserAuditLog` (acciones administrativas) ni
`kyc.VerificationEvent` (timeline KYC) — enfocado en senales de seguridad: logins fallidos,
rate-limit alcanzado, archivos KYC rechazados, verificacion bloqueada/rechazada, y (2026-07-16)
`AI_ACTION_EXECUTED` para cada escritura que el AI Core ejecuta en nombre de un usuario real (ver
nota de AI Core mas abajo).

| Endpoint | Metodo | Permiso |
|---|---|---|
| `/api/v1/security/health/` | GET | `IsAdminUser` — snapshot de salud (`SecurityHealthView`) |
| `/api/v1/dashboard/security/*` | — | `AdminSecurityViewSet` (BFF admin, panel `/panel/seguridad`) |

Modelo: `SecurityEvent` (append-only, nunca se edita ni se borra, ni existe un endpoint de
escritura fuera del Command). Unico punto de escritura: `SecurityCommands.log_event(...)`, que
**nunca** propaga una excepcion al caller (solo deja constancia en el logger) — cualquier app
puede llamarlo con un import diferido (`from security.services.commands import SecurityCommands`
dentro del metodo, mismo patron que `notifications.dispatch_notification`) sin arriesgar romper
su propio flujo de negocio si el logging de seguridad fallara.

Services: `SecurityCommands.log_event()`, `SecuritySelector.list_events()`/`.get_health_snapshot()`.

---

### core — Contenido publico (landing, home feed) — app nueva, no listada antes

> **[MIGRADO 2026-07-12]** `core` ya NO es dueno de marca/contacto/redes sociales — se movieron a
> la nueva app `organization` (ver seccion dedicada arriba). `core` sigue exponiendo los mismos
> endpoints publicos (`site-config`/`footer`), pero ahora **consume** esos datos via
> `OrganizationSelector` en vez de poseerlos. `core` retiene solo contenido de la propia Home
> (banners, tarjetas, modulos, CTA, slider de marcas) y navegacion del sitio (`NavbarLink`,
> `FooterLink` categoria `nav`).

Mounted en `/api/v1/core/` via un unico `HomeFeedView(GenericViewSet)`, `permission_classes = []`
(publico, sin auth):

| Endpoint | Descripcion |
|---|---|
| `GET /api/v1/core/home-feed/` | Feed agregado de la landing (cache 5 min) — incluye `card_groups`/`footer_cta`, no solo `card_group_titles` (agregado 2026-06-30) |
| `GET /api/v1/core/footer/` | Configuracion de footer |
| `GET /api/v1/core/site-config/` | Branding/config global del sitio — hoy combina `organization.Company` + `organization.Branding` |
| `GET /api/v1/core/about-us/` | **Nuevo 2026-07-19** — filosofia institucional para la pagina publica `/nosotros` (historia/mision/vision/valores), `AboutUsConfig` (singleton) + `AboutUsValue` (lista). Admin: `/panel/nosotros`. Cache propia (`sintel_about_us_v1`), no viaja dentro de `home-feed` (es su propia pagina, no un bloque de la Home) |
| `GET /api/v1/core/enums/{name}/` | Catalogo contract-first de enums compartidos (badges/labels), consumido por `useEnums.ts` en TODO el panel admin, no solo landing |

9 modelos (gano `FooterCTAConfig`, singleton del bloque CTA final — migr. `0014`, 2026-06-30)
incluyendo `HomeBanner`, `HomeModuleConfig`, `HomeCardGroup`. Los 3 ultimos + `HomeCard` ganaron
campos de un "Constructor Visual" (2026-06-30): `display_type`/`layout_config` en
`HomeModuleConfig` (18 layouts posibles), `card_type`/`animation`/`is_featured`/`priority` en
`HomeCard`, `layout_type`/`padding`/`columns`/`bg_image` en `HomeCardGroup` — editado desde
`ModuleBuilderModal.vue` (nuevo, ~1500 lineas) en `/panel/home-config`. Cache invalidado via
signals (8 de 9 modelos — `HomeCardGroup` es la unica excepcion intencional, invalidacion manual
en su ViewSet) + llamadas explicitas desde el panel admin.

**N+1 corregido 2026-07-03 (Fase 6, tercera instancia del mismo patron):**
`get_thumbnail()` en `FeaturedProductCardSerializer`/`FeaturedEquipmentCardSerializer`/
`FeaturedServiceCardSerializer` (usados por `home-feed`) hacia
`obj.images.filter(is_primary=True).first()` + fallback `obj.images.first()` — un `.filter()`
explicito en el manager **ignora el prefetch_related('images')** ya declarado en cada
`list_featured()`. Corregido reutilizando `obj.images.all()` (cache de prefetch) + busqueda en
Python, igual patron que `get_min_price()` en el mismo archivo (que ya lo hacia bien). Severidad
menor que otros N+1 de esta sesion porque `home-feed` tiene cache de 5 min — el costo se paga una
vez por ventana de cache, no por visitante. `core` no tiene suite de tests (`core/tests.py` no
existe); se verifico manualmente contra datos reales (200 OK, thumbnails resuelven bien).

---

### notifications — Notificacion multicanal centralizada — app nueva, no listada antes

Todas las apps deben llamar `NotificationCommands.dispatch_notification()` en vez de enviar
notificaciones directamente (WebSocket, Email, WhatsApp via Meta Cloud API).

| Endpoint | Permiso |
|---|---|
| `GET /api/v1/notifications/logs/` | `IsAuthenticatedActiveUser` (solo lectura, propias) |
| `GET/POST /api/v1/notifications/preferences/` + `preferences/set/` | `IsAuthenticatedActiveUser` |

Modelos: `NotificationTemplate`, `NotificationLog`. 8 `NotificationTemplate` sembradas en BD (ver
memoria del proyecto).

---

### operations — Fulfillment operativo post-pago — app nueva, no listada antes

Orquesta tickets/asignaciones/tracking/documentos/reviews **sin poseer los datos comerciales de la
orden** (esos siguen en `orders`/`payment`).

| Endpoint | Permiso |
|---|---|
| `GET /api/v1/operations/my/` | `IsAuthenticatedActiveUser` — tickets propios del cliente |
| `/api/v1/operations/tasks/` | `IsOperationalUser`/`IsAdminUser` segun accion — personal operativo |
| `/api/v1/dashboard/operations/` | BFF admin separado |
| `ws/operations/<ticket_uuid>/` | WebSocket de tracking en vivo |

Modelos: `OperationTicket`, `OperationAssignment`, `TrackingEvent`, `DispatcherProfile`,
`OperationDocument`, `OperationReview`. `OperationCommands.ensure_tickets_for_order()` es llamado
desde `payment.shared.commands.confirm_order_payment()` y `CodCommands.confirm_order()`.

---

### support — Chat de soporte en tiempo real (100% WebSocket) — app nueva, doc propio desactualizado

> **[CORREGIDO 2026-07-03]** El doc `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md`
> describe una REST API (`ChatRoomViewSet`, `/api/v1/support/rooms/`) y un WebSocket por sala
> (`ws/support/<room_uuid>/`) que **no existen en el codigo**. `support/api/` solo tiene
> `serializers.py` (sin `views.py` ni `urls.py`), y `support` no esta `include()`do en
> `ecommerce/urls.py` — no existe ninguna ruta `/api/v1/support/`.

**Lo que realmente existe:** una unica ruta WebSocket fija `ws/support/chat/` ->
`SupportChatConsumer` (`support/consumers.py`, registrado en `ecommerce/routing.py`).
`connect()` distingue: admin (`is_staff and is_superuser`) se une al grupo global
`support_admins`; cliente regular obtiene/crea su `ChatRoom` y se une a `chat_{user.uuid}`,
recibiendo el historial de mensajes al conectar. Modelos: `ChatRoom` (`user`, `status`
OPEN/CLOSED, `assigned_admin`), `ChatMessage` (`room`, `sender`, `message`, `is_read`).

UI: widget flotante para clientes (componente global, no una ruta) + consola admin
`SupportDashboardView.vue` en `/panel/soporte` (dos columnas: lista de salas + chat activo).

**Pendiente:** actualizar `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` para que
describa el flujo WebSocket real en vez de la REST API inexistente — no se hizo en esta pasada
por estar fuera del archivo que se pidio auditar.

---

## Frontend SPA — Vue 3

> **[ACTUALIZADO 2026-07-03]** La estructura de directorios de alto nivel
> (`modules/`, `views/`, `store/`, `components/`) sigue siendo correcta, pero el router y las
> rutas cambiaron sustancialmente. Verificado leyendo `frontend/src/apps/admin/router.js`
> directamente (es el unico router real de toda la SPA, pese a estar en `apps/admin/`).

### Estructura real

```
frontend/src/
  apps/
    admin/       router.js (UNICO router — define TODAS las rutas: customer + /panel/*), App.vue
    customer/    main.js — placeholder casi vacio, no se usa como app Vue separada todavia
  main.js        # entrada raiz, trivial — la app real se monta desde apps/admin/
  modules/       # modulos ADMIN: shop/, inventory/, orders/, users/, services/, quotes/,
                 # renting/, marketing/, support/ (SupportDashboardView.vue)
  views/         # auth/, admin/, customer/{shop,renting,services,quotes,account,checkout}/
  store/         # Pinia: auth.js, cart.js
  components/    # layout/, ui/, customer/
  composables/   # useApi.js, useAuth.js, useToast.js, useOffcanvas.js
  data/, renderers/, services/, shared/
```

**No existe `frontend/src/router/`** como directorio separado — todo vive en
`apps/admin/router.js`.

### Rutas reales (verificadas en `router.js`, no exhaustivas)

Publicas / portal comprador (bajo `/`): `inicio` (LandingView, **nueva, no listada antes**),
`tienda`, `tienda/producto/:uuid`, `alquiler` + subrutas, `servicios` + subrutas, `cotizar`,
`cotizar/catalogo`, `cotizar/personalizada`, `checkout`, `orden-confirmada`, `payment/result`
(retorno PSE), `checkout/nequi-espera`, `contratistas` + `:uuid` (**nuevo, marketplace de
contratistas**), `mis-tareas` (**nuevo, portal movil de personal operativo**).

`/mi-cuenta/*` (requiere auth): `perfil`, `pedidos`, `alquileres`, `wishlist` (**nuevo**),
`direcciones`, `tarjetas` (**nuevo**), `cotizaciones`, `perfil-profesional` (SSoT: wizard de
upgrade `ContractorOnboardingWizard.vue`, no un registro alterno), `verificacion` (**nuevo,
2026-07-06** — subir documentos KYC), `mi-agenda` (**nuevo**), `operaciones`, `operaciones/:uuid`.
`/registro-profesional` (top-level) es ahora solo un `redirect` a `/register` (2026-07-06) —
`RegisterContractorView.vue` se elimino, ya no existe un registro separado por tipo.

`/panel/*` (admin): agrega respecto a v7 `servicios/operaciones` (**nuevo, 2026-07-09** —
`ServiceOperationBoard.vue`, board centralizado de Operaciones de Servicios Tecnicos),
`servicios/asignacion-tecnicos` (board antiguo, ya no en el menu del sidebar pero la ruta sigue
viva), `ordenes/renting` (**nuevo, 2026-07-07** — `RentalOperationBoard.vue`), `renta/solicitudes`
(**nuevo, 2026-07-07**), `productos/operaciones` (**nuevo, 2026-07-09** — `ShopOperationBoard.vue`,
anidado en el grupo "Tienda" del sidebar), `validaciones` + `validaciones/:uuid` (**nuevo,
2026-07-06** — panel KYC), ademas de lo ya listado en v7: `home-config`, `soporte`, `operaciones`
+ `operaciones/:uuid`, `despachadores`, `dashboard`, `productos`, `categorias`, `marcas`,
`impuestos`, `ordenes`, `usuarios`, `servicios`, `s-categorias`, `s-niveles`, `profesionales`
(**nuevo, solo-lectura**), `cotizaciones` + `cotizaciones/plantillas/:uuid`, `renta` + subrutas,
`marketing`.

### Design System — `components/base/*` (2026-07-18/19, no releido a fondo esta pasada)

Biblioteca compartida cross-modulo, distinta de `components/customer/account/*` (Mi Cuenta,
2026-07-17) y de `components/shared/checkout/*` (Payment, `PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md`).
Nacio de fusionar duplicados casi-identicos entre Renting/Services/Shop/Operations/Support
(cards de catalogo, reseñas, FAQ, galerias, forms de Categoria/Marca, modales, badges de estado).
Componentes reales hoy: `BaseReviews`, `BaseAccordion`, `BaseGallery`, `BaseHorizontalCard`,
`BaseBrandForm`, `BaseCategoryForm`, `BaseModal` (dialogo centrado — deliberadamente NO fusionado
con `SintelOffcanvas`, que es panel lateral, patron distinto), `BaseContextCard`, `BaseStatusBadge`,
`BaseInput`/`BaseTextarea`/`BaseUpload` (primeros 3 del Grupo D de inputs, el resto -- `BaseSelect`,
`BaseAddress`, etc. -- no construidos todavia, solo se construyen contra un consumidor real). Ver
`ai_skills/frontend/components/cards.md` §2.1 para el catalogo completo con props, y
`frontend/.AGENT/doc/PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md` para la auditoria de
8 fases que lo origino. Migracion incremental por modulo, todavia en curso (Organization/Core/
Operations/Support ya migrados a esta fecha; Marketing/KYC/Notifications pendientes).

**Rutas nuevas no capturadas arriba:** `nosotros` (publica, `/nosotros`, AboutUsView.vue —
filosofia institucional, 2026-07-19) y su contraparte admin `nosotros` (`/panel/nosotros`,
AboutUsAdminView.vue, grupo "Sitio Web" del sidebar). El login/registro de cliente rediseñado
(2026-07-17) usa su propio `CustomerAuthLayout.vue` en vez de `CustomerLayout` para `/login` y
`/register` — ver nota en seccion `accounts` arriba.

### Notas de infraestructura frontend

- **Vite** con multi-entry (admin + customer apps, aunque customer no esta activo aun)
- **HMR en Docker/WSL2:** `watch.usePolling: true, interval: 300` en `vite.config.js` — sin esto,
  los cambios Vue/JS nunca se reflejan en el navegador (inotify no funciona en WSL2)
- **Bootstrap 5.3.3 + Bootstrap Icons 1.11.3** via CDN en `index.html`
- **Inter font** (Google Fonts, pesos 300-800) via CDN

### Regla de endpoints frontend — CRITICA

```
LECTURA  (GET)                -> shop/ | renting/ | services/ | ...  (ReadOnly, sin auth)
ESCRITURA (POST/PATCH/DELETE) -> dashboard/products/ | dashboard/categories/ | ...  (JWT admin)
```

URL de escritura usa `item.id` (PK entero). FK en payloads usa `item.uuid` (SlugRelatedField).

**NUNCA llaman a `/api/v1/dashboard/`** desde el portal del comprador — ese prefijo es exclusivo
del panel admin.

---

## Infraestructura Docker (verificado 2026-07-03 via `docker ps`)

| Servicio | Imagen | Puerto externo |
|----------|--------|----------------|
| `ecommerce_sintel_django` | `ecommerce_sintel:runtime` (Daphne ASGI) | 8000 |
| `ecommerce_sintel_celery_worker` | `ecommerce_sintel:runtime` | - |
| `ecommerce_sintel_celery_beat` | `ecommerce_sintel:runtime` | - |
| `ecommerce_sintel_db` | postgres:16-alpine | 5432 |
| `ecommerce_sintel_redis` | redis:7.2-alpine | 6380 (mapeado, interno 6379) |
| `ecommerce_sintel_nginx` | nginx:1.26-alpine | 80 |
| `ecommerce_sintel_frontend` | node:24-bookworm-slim | 5173 |
| `ecommerce_sintel_ai` | `ecommerce_sintel_ai:latest` (FastAPI, AI Engine) | 8100 |
| `ecommerce_sintel_ollama` | ollama/ollama:latest | 11434 |
| `ecommerce_sintel_chromadb` | chromadb/chroma:0.5.23 | 8200 |

**Atencion:** esta maquina aloja tambien contenedores `crm_sintel-*` (proyecto distinto) que
compiten por los puertos 80/5432. Verificar con `docker ps` antes de operar (exec/restart/stop).

Healthcheck: `GET /api/v1/health/` -> `{"status": "ok"}`

Archivos media: servidos en dev via `static(MEDIA_URL, document_root=MEDIA_ROOT)` en `urls.py`.
`MEDIA_ROOT = BASE_DIR / 'media'`, `MEDIA_URL = '/media/'`

**Para correr tests del backend:** no hay Django instalado en ningun `.venv` local — usar
`docker exec ecommerce_sintel_django python manage.py test <app>` contra el stack ya levantado.

---

## Configuracion `.env` — Variables requeridas (corregido 2026-07-03)

| Variable | Uso |
|----------|-----|
| `WOMPI_PUBLIC_KEY` | Clave publica Wompi (checkout URL) |
| `WOMPI_PRIVATE_KEY` | Clave privada Wompi |
| `WOMPI_INTEGRITY_SECRET` | Firma SHA256 del checkout — **antes decia `WOMPI_INTEGRITY_KEY`, nombre real corregido** |
| `WOMPI_EVENTS_SECRET` | Verificacion de firma del webhook — **antes decia `WOMPI_EVENTS_KEY`, nombre real corregido** |
| `WOMPI_ENVIRONMENT` | `test` \| `prod` — no listada en versiones anteriores |
| `WOMPI_WIDGET_URL` | URL del script del widget Wompi — no listada en versiones anteriores |
| `NEQUI_CLIENT_ID` / `NEQUI_CLIENT_SECRET` / `NEQUI_API_KEY` / `NEQUI_ENVIRONMENT` | Integracion Nequi Push — no listadas en versiones anteriores |
| `DJANGO_SECRET_KEY` | Clave secreta Django |
| `DATABASE_URL` / `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_PORT` | Conexion PostgreSQL (sqlite si `DB_HOST` no esta seteado, en dev local sin Docker) |
| `CORS_ALLOWED_ORIGINS` | Origenes permitidos CORS |
| `REDIS_URL` | Conexion Redis (broker Celery + channels) |

---

## API Docs

| URL | Descripcion |
|-----|-------------|
| `/api/docs/` | Swagger UI (drf-spectacular) |
| `/api/schema/` | OpenAPI 3 schema JSON |
| `/admin/` | Django Admin |

---

## Reglas criticas del proyecto

1. **No emojis en archivos .py** — causa `SyntaxError` -> 500 Internal Server Error.
2. **No cambiar `DJANGO_SETTINGS_MODULE`** sin instruccion explicita.
3. **Importar `IsAdminUser` desde `users.api.permissions`**, no desde `rest_framework.permissions`.
4. **Soft-delete siempre completo:** `is_active=False` + `is_deleted=True` (cuando el modelo tenga
   ambos campos).
5. **Selectores admin filtran `is_deleted=False`** — nunca `Model.objects.all()` en admin.
6. **Precios con `Decimal`**, nunca `float` (`min_value=Decimal('0.01')`).
7. **Toda logica de negocio en Commands/Selectors** — los ViewSets son orquestadores.
8. **Notificaciones siempre via `NotificationCommands.dispatch_notification()`** dentro de
   `transaction.on_commit(...)` — no `ws_notify` directo (app `notifications`, centralizada
   desde 2026-06).
9. **Compilar antes de hacer commit:** `python -m py_compile archivo.py`.
10. **Uploads de imagen (Category.image, Brand.logo):** usar `FormData` en el frontend — los
    ViewSets tienen `MultiPartParser, FormParser, JSONParser`.
11. **`WOMPI_EVENTS_SECRET` debe estar en `.env` en produccion** — sin ella el webhook no verifica
    firmas (nombre real, no `WOMPI_EVENTS_KEY`).
12. **La app de pagos se llama `payment`, nunca `wompi`** — verificar siempre contra
    `payment/apps.py` y `ecommerce/urls.py` antes de asumir nombres de ruta.
13. **SKU de `ProductVariant` es siempre auto-generado** (`_generate_variant_sku()`) — nunca
    aceptar SKU manual del usuario en serializers de creacion/edicion de variante.
14. **Antes de restaurar codigo desde un archivo `.bak`**, verificar que realmente representa el
    comportamiento correcto (no asumir que "mas viejo" = "correcto") — confirmar contra los
    comandos/consumidores reales del campo o funcion en cuestion.
15. **Un comentario `# ALGO_REMOVED: ... -> usar X o signal`** no es evidencia de que `X` o el
    signal existan — verificar antes de construir sobre esa base.
16. **Nunca nombrar una `@action` de DRF `dispatch`** — sobreescribe silenciosamente
    `View.dispatch()` y rompe TODAS las requests del ViewSet (solo un test HTTP real lo detecta,
    no un test de "comando" aislado). Descubierto 2026-07-08 en `technical_services`.
17. **Nunca `getattr(user, 'profile'/'technician_profile'/'dispatcher_profile', None)` directo**
    en codigo nuevo — usar `accounts.services.ProfileResolver` (`get_profile`/
    `get_technician_profile`/`get_dispatcher_profile`/`resolve*`). Ver seccion RBAC.
18. **`UserProfile.user_type` solo cambia en un lugar:** `kyc.services.commands.KycCommands._apply_requested_user_type()`,
    al aprobar un upgrade. Ningun modulo de negocio (Renting, Technical Services, Shop, Orders,
    Operations, Payment, Dashboard) debe escribirlo directamente, ni siquiera para un admin.

---

## Correcciones y mejoras aplicadas (2026-07-03 — auditoria completa payment/orders/cart/shop/dashboard/technical_services)

| App | Cambio | Severidad |
|---|---|---|
| `payment/shared/commands.py`, `payment/online/services/commands.py` | Restaurada deduccion real de inventario y validacion de stock (estaban stubeadas) | CRITICO |
| `payment/online/services/commands.py` | Corregido bug de `@transaction.atomic` que revertia `Transaction.status='ERROR'` silenciosamente | CRITICO |
| `payment/online/api/views.py`, `payment/nequi/api/views.py`, `orders/api/service_orders.py` | Corregidas 3 instancias de `order.status != 'pending'` (legacy) -> `Order.STATUS_PENDING_PAYMENT` | CRITICO (bloqueaba checkout completo) |
| `orders/services/commands.py` | Restaurada llamada a `CodCommands.confirm_order()` en `create_from_cart()` (checkout COD no confirmaba nunca) | CRITICO |
| `payment/cod/services/commands.py` | `CodCommands.confirm_order()` ahora transiciona `order.status = STATUS_PAID` | FUNCIONALIDAD |
| `cart/services/commands.py` | Restaurada validacion real de stock en `_check_availability()` y `checkout_cart()` | ALTO |
| `shop/services/summary.py` | Restaurado calculo real de estadisticas de inventario (devolvia ceros hardcodeados) | MEDIO |
| `orders/tests.py`, `cart/tests.py`, `dashboard/tests.py`, `technical_services/tests.py` | Corregidos imports/mocks rotos que causaban `NameError`/`AttributeError` antes de ejecutar los tests | ALTO (tests no detectaban regresiones) |
| `dashboard/tests.py` | Eliminada `DashboardInventoryAPITestCase` (probaba rutas `/api/v1/dashboard/inventory/` ya migradas a `/api/v1/inventory/`) | LIMPIEZA |
| Todo el proyecto | Eliminados los 8 archivos `.bak` restantes del patron `INVENTORY_REMOVED` | LIMPIEZA |
| `shop/management/commands/seed_product_sale_flow.py` | Restaurados imports + corregido `variant.fixed_price` -> `variant.price` (campo inexistente en `ProductVariant`) | BAJO (script de dev) |

Ver `payment/.AGENT/docs/AUDITORIA_PAYMENT_WOMPI_2026-07-03.md` para el informe completo con
matrices de riesgo, dependencias y estrategia de rollback.

---

## Correcciones y mejoras aplicadas (2026-06-20 — segunda ronda)

| Archivo | Cambio |
|---------|--------|
| `renting/api/views.py` | `from users.api.permissions import IsAdminUser` — reemplaza `permissions.IsAdminUser()` en `EquipmentViewSet`, `EquipmentVariantViewSet`, `RentingCategoryViewSet`, `RentingBrandViewSet`, `RentalLaborViewSet` |
| `shop/api/views.py` | Nueva action `GET /shop/products/<uuid>/reviews/` (AllowAny) — retorna resenas paginadas con `is_verified_purchase` |
| `shop/api/views.py` | Import `ProductReview` añadido |
| `CategoryForm.vue` | Upload de imagen con preview, FormData cuando hay archivo |
| `BrandForm.vue` | Upload de logo con preview, FormData cuando hay archivo |
| `ProductForm.vue` | Campos `short_description` y `video_url` en tab General |
| `ProductForm.vue` | Campos logistica (`weight`, `length`, `width`, `height`) en nueva variante y edicion inline |
| `ProductDetailView.vue` | Fix: `GET shop/products/${uuid}/` en vez de list query incorrecta |
| `ProductDetailView.vue` | Display de `short_description` como subtitulo del producto |
| `ProductDetailView.vue` | Embed de video YouTube/Vimeo (iframe) o fallback link |
| `ProductDetailView.vue` | Display de logistica de la variante seleccionada (peso, dimensiones) |
| `ProductDetailView.vue` | Seccion de resenas: lista con badge `Compra verificada` (`is_verified_purchase`) y formulario para autenticados |
| `.env` | `WOMPI_EVENTS_KEY` verificado — valor test presente, webhook signature activa |

> Nota 2026-07-03: la variable real se llama `WOMPI_EVENTS_SECRET`, no `WOMPI_EVENTS_KEY` — ver
> seccion de configuracion `.env` arriba.

---

## Correcciones y mejoras aplicadas (2026-06-20)

| Archivo | Cambio | Severidad |
|---------|--------|-----------|
| `orders/api/views.py` | `get_object_or_404` movido al bloque de imports (estaba al final del archivo) | CRITICO |
| `orders/api/views.py` | `permission_classes = [permissions.IsAuthenticated]` declarado explicitamente en `ShippingAddressViewSet` y `OrderViewSet` | ADVERTENCIA |
| `wompi/api/views.py` | Funcion `_verify_wompi_event_signature()` implementada — verifica SHA256 usando `WOMPI_EVENTS_KEY` | CRITICO (seguridad) |
| `wompi/api/views.py` | Webhook retorna 401 si la firma es invalida | CRITICO (seguridad) |
| `shop/api/serializers.py` | Cascada de campos nuevos: `Category.image`, `Brand.logo`, `Product.short_description/video_url`, `ProductVariant.weight/length/width/height`, `ProductReview.is_verified_purchase` | FUNCIONALIDAD |
| `shop/services/commands.py` | `CategoryCommands`, `BrandCommands`, `ProductCommands`, `ProductVariantCommands` actualizados con nuevos campos | FUNCIONALIDAD |
| `shop/services/selectors.py` | `CategorySelector.LIST_FIELDS` incluye `image`; `BrandSelector` incluye `logo` en `.only()` | FUNCIONALIDAD |
| `shop/api/views.py` | `search_fields` incluye `short_description`; `parser_classes` para Category/Brand | FUNCIONALIDAD |
| `dashboard/api/views.py` | `AdminCategoryViewSet` y `AdminBrandViewSet` con `parser_classes`; `create_brand` pasa `ser.validated_data` completo | FUNCIONALIDAD |
| `dashboard/services/admin_orchestrators.py` | `ShopAdminOrchestrator.create_brand(data)` delega `**data` a `BrandCommands` | FUNCIONALIDAD |
| Migracion `shop/0004` | Aplicada correctamente — 12 cambios de campo en 5 modelos | FUNCIONALIDAD |

> Nota 2026-07-03: las referencias a `wompi/api/views.py` en esta tabla historica corresponden al
> archivo que hoy es `payment/online/api/views.py` — la app nunca se llamo `wompi` en el codigo,
> pero el nombre de archivo real cambio desde entonces. Ver seccion `payment` arriba.

---

## Cambios recientes (2026-06-19)

| Estado | Cambio |
|--------|--------|
| Hecho | Implementar Wompi: firma de integridad SHA256 en `initialize_transaction()` |
| Hecho | Implementar Wompi: endpoint `transaction-status/` para post-pago |
| Hecho | Reescribir `OrderConfirmedView.vue` con 3 estados (APPROVED/PENDING/DECLINED) |
| Hecho | `goToWompi()` siempre llama `initialize` fresco (no reutiliza checkout URL) |
| Hecho | Redirect URL siempre incluye `?tx=<uuid>` sin restriccion HTTPS |
| Hecho | Fase 7: TechnicianProfile, ServiceAssignmentCommands, auto-asignacion jerarquica |
| Hecho | ServicePriceHistory — auditoria de cambios de precio con modal timeline en Vue |
| Hecho | Suite de pruebas 32/32 pasadas |

---

## Tareas pendientes (actualizado 2026-07-20)

| Prioridad | Tarea |
|-----------|-------|
| Alta | Releer a fondo `quotes`, `marketing`, `shop`, `cart`, `inventory`, `technical_services`, `ecommerce` (base) contra el estado 2026-07-20 — esta pasada se concentro en cerrar los gaps de `organization`/`security` (apps completas sin documentar) y en las rutas API raiz, no en re-auditar apps ya cubiertas en v8 |
| Media | `organization/CLAUDE.md` dice "Fase 3 de 9" pero los 8 recursos ya estan operativos — corregir esa nota (ver seccion `organization`) |
| Media | `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` sigue sin actualizar (nota de 2026-07-03 aun vigente) para reflejar que el AI Core (2026-07-16) ahora tambien atiende ese chat en "modo AI" antes del Human Handoff — ver `ai_engine/.AGENT/PLAN_DE_ACCION_AI_CORE.md` Fase 7 |
| Media | Documentar en el doc de frontend (`ARQUITECTURA_COMPLETAFRONEND.md`) el Design System `components/base/*` con el mismo nivel de detalle que ya tiene `ai_skills/frontend/components/cards.md` |
| Baja | Rate limiting en login (proteccion brute force) — verificar si el rediseno de Auth 2026-07-17 ya lo cubre, no confirmado en esta pasada |
| Baja | Implementar rol/perfil VENDOR completo (hoy reservado, sin flujo end-to-end claro) |
| Baja | Agregar test parametrizado que confirme `IsAdminUser` en las ViewSets de `dashboard` (blindaje contra regresiones de permisos, sugerido en `ARQUITECTURA_COMPLETA_DASHBOARD.md`) |
| Descartado por decision del usuario (2026-07-09) | Sistema de eventos de dominio, wizard de upgrade independiente por tipo profesional (se mantiene 1 solo wizard reutilizado), reorganizacion del dashboard de usuarios por tipo, libreria de 8 componentes Vue de identidad — sin consumidor concreto hoy, ver `accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md` seccion "Auditoria y Correcciones [2026-07-09]" |

### Completadas (2026-07-12 a 2026-07-20 — gaps de documentacion + AI Core + Design System)
- Cerrados 2 gaps reales de documentacion: `organization` (creada 2026-07-12) y `security`
  (creada ~2026-07-09) llevaban desde su creacion sin aparecer en este documento pese a estar
  operativas en produccion.
- Rutas API raiz reescritas completas contra `ecommerce/urls.py` real — la version anterior le
  faltaban 6 rutas reales (`admin-auth/forgot-password-*` x3, `internal/ai-context/`,
  `internal/ai/`, `organization/`, `security`).
- AI Engine documentado por primera vez como algo mas que "generador de codigo" — el AI Core
  (Fases 1-8, 2026-07-16) le agrego un motor conversacional completo (`/chat`, JWT real, Tool
  Registry, Agent Profiles, confirmacion humana para escrituras) usado por soporte web/WhatsApp.
  Detalle en `ai_engine/.AGENT/` (`GUIA_USO.md`/`FLIJO_COMPLETO_IA_ENGINE.md`/
  `PLAN_DE_ACCION_AI_CORE.md`), no repetido aqui.
- Referenciados (sin re-auditar a fondo): rediseno de Auth 5 fases (2026-07-17), aislamiento de
  dominio del panel ADR-001 (2026-07-13), Design System de frontend `components/base/*`
  (2026-07-18/19), modulo "Nosotros" (vive en `core`, 2026-07-19 — filosofia institucional,
  pagina publica `/nosotros`).
- Migracion a integracion API propia con Wompi (2026-07-13, 10 fases) ya estaba referenciada
  desde la v8 — confirmada vigente, no se repite el detalle.

### Completadas (2026-07-06 a 2026-07-09 — SSoT de identidad, KYC, y 3 motores de Operaciones)
- App `kyc` construida desde cero: verificacion de identidad, documentos privados, timeline,
  Habeas Data — ver seccion dedicada arriba.
- SSoT de identidad: registro siempre CUSTOMER instantaneo; upgrade a profesional solo via KYC
  aprobado; cerrado el ultimo hueco real (2026-07-09: admin ya no crea perfiles especializados
  directamente desde `/panel/usuarios`).
- Arquitectura de perfiles: `ProfileResolver`/`ProfileRegistry`, `VendorProfile` eliminado
  (codigo muerto).
- 3 motores de "Operaciones post-pago" (mismo patron FSM): `renting.RentalOperation`,
  `technical_services.ServiceOperation` (+ checkout en modal), `orders.Shipment` extendido
  ("Shop Operations").
- `renting.AvailabilityEngine` (2 fases): el lock de disponibilidad ya no lo dispara
  `pending_payment`, sino la confirmacion real del pago.
- Bug de sincronizacion Wompi corregido (`_sync_wompi_status` exigia un campo que solo poblaba el
  webhook — pagos quedaban "en proceso" para siempre sin el webhook).

### Completadas (2026-07-03, segunda ronda — cierre de pendientes detectados)
- Permisos `renting`: `RentingCategoryViewSet`/`RentingBrandViewSet`/`RentalLaborViewSet` ahora
  declaran `permission_classes = [AllowAny]` explicitamente; las dos primeras ademas dejaron de
  usar los selectores "_for_admin" (exponian items inactivos a usuarios anonimos) — 6 tests
  nuevos en `renting/tests.py` (no existia antes).
- Permisos `marketing`: `MarketingCampaignViewSet`/`AgentRunViewSet`/`DashboardViewSet` ahora
  usan `IsAdminUser` (de `users.api.permissions`); `FlashOfferViewSet` usa `AllowAny` — 6 tests
  nuevos en `marketing/tests.py` (no existia antes).
- `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` reescrito: ya no describe una REST API
  inexistente, documenta el flujo WebSocket real (`ws/support/chat/`) y la gestion admin real via
  `dashboard/api/views.py::AdminSupportChatViewSet`.
- Creado `dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` (no existia) con el
  inventario completo de las 34 ViewSets y los 10 Orchestrators reales.
- `inventory/CLAUDE.md` corregido: ya no menciona `is_available()`/`get_stock_record_for_variant()`
  (no existen); documenta la firma real de `StockAdjustmentDTO`.
- `CLAUDE.md` raiz: agregadas las entradas faltantes de `dashboard`/`operations` a la tabla de
  routing, y corregida la version de Django (decia "Django 4", es "Django 5 / 5.2.13").

### Completadas (2026-07-03, primera ronda)
Ver seccion "Correcciones y mejoras aplicadas (2026-07-03)" arriba — 10 bugs corregidos en 6 apps
distintas, todos derivados del mismo patron de refactor incompleto ("desacoplar de `inventory` via
signal"), mas la sincronizacion completa de RBAC, rutas raiz, dashboard BFF, y la identificacion de
4 apps (`core`, `notifications`, `operations`, `support`) que no aparecian en ninguna version
anterior de este documento.

### Completadas (2026-06-24)
- Integracion del motor de calculo `ServicePricingCalculator` en `ServiceSelector.get_variant_quotation` para cotizaciones dinamicas.
- Ampliacion de la suite de pruebas con `ServiceCostRulePricingTestCase` para verificar reglas de costo globales y especificas de variante.
- Aseguramiento de permisos admin `IsAdminUser` (de `users.api.permissions`) en la gestion administrativa del motor de precios.

### Completadas (2026-06-20)
- `WOMPI_EVENTS_KEY` ya estaba en `.env` — verificacion de firma webhook activa (nombre real: `WOMPI_EVENTS_SECRET`)
- Permisos `renting/api/views.py` migrados a `users.api.permissions.IsAdminUser`
- `technical_services/api/views.py` ya usaba el permiso correcto desde antes
- Upload de imagen/logo en `CategoryForm.vue` y `BrandForm.vue`
- Campos `short_description` y `video_url` en `ProductForm.vue`
- Logistica (`weight`/`length`/`width`/`height`) en variantes del ProductForm
- `ProductDetailView.vue`: fetch correcto por UUID, resumen corto, embed de video, logistica, seccion de resenas con `is_verified_purchase`
- Action `GET /shop/products/<uuid>/reviews/` para listado publico de resenas
