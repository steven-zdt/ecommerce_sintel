# Arquitectura Completa — Módulo Accounts

> **Ultima actualizacion:** 2026-07-17 (auto-creacion de ShippingAddress principal desde
> el registro — ver seccion "Registro con verificacion OTP" mas abajo; fases previas del
> 2026-07-09 siguen vigentes sin cambios)
> **Mantenido por:** Claude Code — sincronizado con el estado real del codigo

---

## Tabla de Contenidos
1. [Descripcion General](#descripcion-general)
2. [Separacion users / accounts](#separacion-users--accounts)
3. [Estructura de Directorios](#estructura-de-directorios)
4. [Modelos de Datos](#modelos-de-datos)
5. [Flujos de la Aplicacion](#flujos-de-la-aplicacion)
6. [Endpoints Disponibles](#endpoints-disponibles)
7. [Patrones de Diseno](#patrones-de-diseno)
8. [Configuracion y Seguridad](#configuracion-y-seguridad)
9. [Senales (Signals)](#senales-signals)
10. [Auditoria y Correcciones](#auditoria-y-correcciones)

---

> **IMPORTANTE (2026-07-06, SSoT de identidad — reemplaza la nota anterior de
> este mismo dia):** el registro (`register`/`register-request`+`register-verify`)
> crea tambien una `kyc.UserVerification`, pero YA NO en `PENDING` para todos:
> todo registro publico crea siempre `UserProfile.CUSTOMER` con la
> verificacion ya `APPROVED` de inmediato (`KycCommands.bootstrap_approved`)
> — un comprador nunca espera revision admin. Convertirse en
> CONTRACTOR/PROFESSIONAL/SPECIALIST/TECHNICIAN es un **upgrade posterior**,
> disparado solo desde el dashboard ya autenticado
> (`ContractorOnboardingWizard.vue` → `POST auth/request-upgrade/` →
> `KycCommands.request_upgrade`, reabre la MISMA `UserVerification` a
> `PENDING`), que si exige documentos + aprobacion admin antes de que
> `UserProfile.user_type` cambie. El login (`AccountCommands.authenticate_user`
> + `GatedTokenObtainPairView` en `auth/token/`) bloquea solo si la
> verificacion esta `BLOCKED`, o si el usuario JAMAS fue aprobado
> (`first_approved_at is None`) — no simplemente `status != APPROVED`, para
> que alguien en medio de un upgrade no pierda su acceso de comprador. Ver la
> arquitectura completa de ese flujo en
> `kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md` -- no duplicado aqui.

## Descripcion General

El modulo **accounts** centraliza toda la logica de perfiles de usuario (compradores, contratistas, proveedores y tecnicos), estructuracion de hojas de vida, portafolios, calificaciones y el motor de disponibilidad de agenda profesional.

Se complementa directamente con **users** (autenticacion pura).

**Patron Arquitectonico:** Service Layer (Commands + Selectors) + ViewSets DRF.

---

## Separacion users / accounts

| App | Responsabilidad |
|-----|----------------|
| `users` | Cuenta base de autenticacion: `email`, `password`, `is_active`, `is_verified`. Nada mas. |
| `accounts` | Todo lo personal: `UserProfile`, `TechnicianProfile`, CV completo, agenda. `VendorProfile` se eliminó (2026-07-05): código muerto, ningún endpoint lo poblaba. |

### Campos de nombres (CRITICO)

Los campos `first_name` y `last_name` **NO existen en `users.User`**.
Estan en `accounts.UserProfile`.

```python
# INCORRECTO — genera FieldError
User.objects.create(first_name='Ana', last_name='Lopez')

# CORRECTO
user = User.objects.create(email='ana@sintel.co', is_active=True)
UserProfile.objects.create(user=user, first_name='Ana', last_name='Lopez')
```

### Acceso al perfil desde el usuario

```python
request.user.profile             # UserProfile (OneToOne, related_name='profile')
request.user.technician_profile  # TechnicianProfile (OneToOne)
```

**Código nuevo NO debe acceder a estos atributos directamente** — usar
`accounts.services.profile_resolver.ProfileResolver` (ver sección "Política de arquitectura de
perfiles" al final de este documento).

---

## Estructura de Directorios

```
ecommerce_sintel/accounts/
├── api/
│   ├── views.py          # AccountViewSet, ContractorProfileViewSet, AvailabilityViewSet,
│   │                     # AdminContractorViewSet, ContractorProfileScopedMixin, 7 ViewSets de CV, ...
│   └── serializers.py    # Todos los serializadores del modulo
├── services/
│   ├── commands.py       # AccountCommands, AvailabilityCommands
│   └── selectors.py      # AccountSelector, ContractorSearchSelector, AvailabilitySelector
├── models.py             # UserProfile, TechnicianProfile, CV models, ProfessionalAvailability (VendorProfile eliminado)
├── tasks.py              # Celery: release_expired_slot
├── urls.py               # Router del modulo
└── .AGENT/docs/
    └── ARQUITECTURA_COMPLETA_ACCOUNTS.md
```

---

## Modelos de Datos

### 1. `UserProfile`

Modelo central que extiende la informacion personal del usuario.
Relacion OneToOne con `AUTH_USER_MODEL` (`related_name='profile'`).

#### user_type choices (TODOS los tipos validos — 7 en total, verificado 2026-07-05)

```python
TECHNICIAN   = 'TECHNICIAN'   # Tecnico (default)
PROFESSIONAL = 'PROFESSIONAL' # Profesional
SPECIALIST   = 'SPECIALIST'   # Especialista
CUSTOMER     = 'CUSTOMER'     # Comprador (cliente de tienda/alquiler)
TRANSPORTER  = 'TRANSPORTER'  # Transportador (logistica)
CONTRACTOR   = 'CONTRACTOR'   # Contratista
ACCOUNTANT   = 'ACCOUNTANT'   # Contador
```

**Nota:** `CUSTOMER` se agrego para el Customer Dashboard (2026-06). No requirio migracion porque es un CharField choices. `TRANSPORTER`/`CONTRACTOR`/`ACCOUNTANT` ya existian en el modelo pero no estaban documentados aqui — corregido 2026-07-05 tras la auditoria del Marketplace de Contratistas.

**Grupos de dominio (`accounts/services/profile_registry.py`, unica fuente de verdad):**

| Constante | Tipos incluidos | Uso |
|---|---|---|
| `BUYER_TYPES` | CUSTOMER, TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR | Puede comprar/rentar/pedir servicios |
| `SERVICE_PROVIDER_TYPES` | TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR | Perfil asignable (agenda + `TechnicianProfile`), CV, marketplace público |
| `OPERATIONAL_TYPES` | `SERVICE_PROVIDER_TYPES` + TRANSPORTER | Dominio de `operations` |
| `CONTRACTOR_ASSIGNABLE_TYPES` | CONTRACTOR, PROFESSIONAL, SPECIALIST | Subconjunto usado en recomendaciones dirigidas a un contratista |

Agregar un tipo de usuario nuevo (o un nuevo grupo) solo requiere sumar una entrada en
`profile_registry.py` — ninguna clase de permiso ni el signal de `models.py` deben modificarse.

#### Campos personales

| Campo | Tipo | Notas |
|-------|------|-------|
| `user` | OneToOneField | FK a AUTH_USER_MODEL |
| `first_name` | CharField(50) | Nombre (blank OK) |
| `last_name` | CharField(50) | Apellido (blank OK) |
| `phone_number` | CharField(20) | unique=True, null=True |
| `profile_picture` | ImageField | `upload_to='profiles/pictures/'` — sirve como avatar |
| `company` | CharField(100) | null=True |
| `position` | CharField(100) | null=True |
| `address` | CharField(250) | null=True |
| `city` | CharField(50) | null=True |
| `state` | CharField(50) | null=True |
| `country` | CharField(50) | null=True |
| `postal_code` | CharField(10) | null=True |
| `document_type` | CharField(10) | Choices: CC, CE, NIT, PP |
| `document` | CharField(30) | null=True |

#### Campos profesionales

| Campo | Tipo | Notas |
|-------|------|-------|
| `user_type` | CharField(20) | Choices arriba, default=TECHNICIAN |
| `bio` | TextField | blank OK |
| `birth_date` | DateField | null=True |
| `contractor_type` | CharField(50) | blank OK |
| `hourly_rate` | DecimalField | null=True |
| `daily_rate` | DecimalField | null=True |
| `project_rate` | DecimalField | null=True |
| `currency` | CharField(10) | Choices: USD, EUR, COP, MXN |

#### Propiedades calculadas

```python
profile.average_rating      # Promedio de 5 criterios de ContractorReview
profile.total_reviews       # Cantidad de reseñas no eliminadas
profile.get_full_name()     # f"{first_name} {last_name}" o email si vacio
```

---

### 2. `VendorProfile` — ELIMINADO (2026-07-05)

Modelo de perfil de proveedor/tienda (`related_name='vendor_profile'`, campos `store_name`/
`business_license`/`address`/`business_phone`). Confirmado código muerto: se serializaba y tenía
inline en el admin, pero ningún endpoint/comando/selector de las 16 apps del proyecto lo creaba o
actualizaba. Eliminado via migración `accounts/migrations/0008_delete_vendorprofile.py`. **No
reintroducir** — si en el futuro se necesita un perfil de tienda, evaluar si cabe como un tipo más
en `UserProfile.user_type` antes de crear un modelo satélite nuevo.

---

### 3. `TechnicianProfile`

Perfil "asignable" (agenda + especialidades) compartido por los **4 tipos service-provider**
(`TECHNICIAN`, `PROFESSIONAL`, `SPECIALIST`, `CONTRACTOR`) — pese al nombre, no es exclusivo de
`TECHNICIAN`; el nombre se mantuvo sin cambios para no romper `related_name='technician_profile'`
usado en decenas de call sites. `related_name='technician_profile'`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `user` | OneToOneField | |
| `specialties` | ManyToManyField | → `technical_services.ServiceCategory`, `related_name='technician_profiles'` |
| `is_available` | BooleanField | default=True |

**Buscar tecnicos por categoria:**
```python
category.technician_profiles.all()   # CORRECTO — related_name='technician_profiles'
# NO usar 'technicians' — ese alias esta reservado pero no activo
```

**Signal:** `post_save` en `UserProfile` crea automaticamente `TechnicianProfile` cuando `user_type == TECHNICIAN`.

---

### 4. Modelos de CV / Perfil profesional

Todos hacen `FK → UserProfile` con sus `related_name` correspondientes:

| Modelo | related_name | Campos clave |
|--------|-------------|-------------|
| `ContractorSpecialty` | `contractor_specialties` | category (FK → ServiceCategory), unique_together(profile, category) |
| `ContractorSkill` | `contractor_skills` | name, level |
| `AcademicTraining` | `academic_trainings` | institution, degree, start_date, end_date, is_current |
| `ProfessionalCourse` | `professional_courses` | title, institution, completion_date, hours |
| `ProfessionalCertification` | `professional_certifications` | name, issuing_organization, document (FileField) |
| `ProfessionalExperience` | `professional_experiences` | company, position, start_date, end_date |
| `SuccessCase` | `success_cases` | title, description, images via SuccessCaseImage |
| `ContractorReview` | `contractor_reviews` | reviewer (FK User), 5 ratings, unique(contractor, reviewer) |

---

### 5. `ProfessionalAvailability`

Bloques de disponibilidad para agendamiento.

```python
STATUS_CHOICES = [
    AVAILABLE, PENDING_RESERVATION, BOOKED, BLOCKED, VACATION, SICK_LEAVE
]
unique_together = ('user_profile', 'date', 'start_time')
ordering = ['date', 'start_time']
```

| Campo | Tipo |
|-------|------|
| `user_profile` | FK → UserProfile (related_name='availabilities') |
| `date` | DateField (db_index=True) |
| `start_time` | TimeField |
| `end_time` | TimeField |
| `status` | CharField(30) |
| `booked_by` | FK → AUTH_USER_MODEL null=True (related_name='slot_bookings') |
| `notes` | TextField null=True |

---

## Flujos de la Aplicacion

### 1. Registro con verificacion OTP (2 pasos) — SIEMPRE crea CUSTOMER

```
POST /api/v1/auth/register-request/
  → VerificationCommands.request_email_verification(email, payload)
  → Envia OTP 6 digitos al correo (caduca 10 min)
  → payload incluye identidad completa + documento + Habeas Data
    (kyc.api.serializers.KycRegistrationFieldsMixin) -- NO incluye
    'user_type': ese campo se elimino de RegisterRequestSerializer/
    UserRegisterSerializer (2026-07-06), nunca se pregunta en el registro.

POST /api/v1/auth/register-verify/
  → VerificationCommands.verify_email_code(email, code)
  → AccountCommands.create_from_verified_payload(payload)
  → Crea User + UserProfile(user_type=CUSTOMER, forzado) en @transaction.atomic
  → KycCommands.bootstrap_approved(user, kyc_fields, consent_events) --
    UserVerification ya APPROVED de inmediato (conserva snapshot de
    identidad + ConsentRecord de Habeas Data, pero sin esperar revision)
  → Retorna tokens JWT + user data (201), acceso instantaneo a comprar
```

`AccountCommands.register_user()` (endpoint directo `/register/`, sin OTP)
sigue el mismo principio: si el payload trae los campos de
`KycRegistrationFieldsMixin` (`has_kyc_data`), fuerza `user_type=CUSTOMER`
igual. Si NO los trae (creacion admin via `UserAdminCreateSerializer` desde
`/panel/usuarios`, o codigo/tests internos con el dict plano
`first_name`/`last_name`), respeta el `user_type` explicito que paso el
caller -- un admin siempre pudo crear cuentas de cualquier tipo
directamente. En ambos casos la cuenta queda `APPROVED` de inmediato.

**Auto-creacion de la direccion de envio principal (2026-07-17):** si el
payload trajo una direccion estructurada (`profile_extra['address']`),
`register_user()`/`create_from_verified_payload()` tambien crean, justo
despues del `UserProfile`, la primera fila en `orders.ShippingAddress`
(`is_default=True`, `label='Principal'`) via el nuevo helper de modulo
`_create_default_shipping_address_from_registration()` (import lazy de
`orders.services.commands.ShippingAddressCommands`, mismo patron de import
cruzado entre apps que ya usa `PricingEngineSelector`). Antes de este fix,
la direccion del registro solo quedaba en `UserProfile.address`/`.city`/
`.country` y el usuario tenia que volver a escribirla en "Mi Cuenta > Mis
Direcciones" -- ver el fix completo (incluye el 404 de ese endpoint) en
`orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md`, seccion "Historial de
Cambios" 2026-07-17. Si el payload no trae direccion (casos legacy/admin),
no se crea nada.

### 1b. Upgrade a profesional (nuevo, 2026-07-06) — unico lugar donde nace un profesional

```
Dashboard autenticado (CTA "Conviertete en Profesional" en AccountSidebar.vue,
visible solo si user_type === CUSTOMER)
  → /mi-cuenta/perfil-profesional (ContractorOnboardingWizard.vue)
  → Paso 1: selector de tipo (TECHNICIAN/PROFESSIONAL/SPECIALIST/CONTRACTOR)

POST /api/v1/auth/request-upgrade/  {requested_user_type}
  → kyc.services.commands.KycCommands.request_upgrade(verification, tipo, by)
  → Reabre la MISMA UserVerification (OneToOne) -- bypassa ALLOWED_TRANSITIONS
    igual que force_approve -- setea requested_user_type, status -> PENDING
  → El usuario SIGUE pudiendo comprar mientras tanto (ver gate de login)

  → Completa el resto del wizard (empresa/experiencia/especialidades/
    tarifas/bio/CV -- gateado por IsServiceProviderOrUpgrading, no
    IsServiceProviderUser, para permitir esto ANTES de la aprobacion)
  → Redirige a /mi-cuenta/verificacion (KycVerificationView.vue, ya
    existente) -- sube los 5 documentos de siempre, submit-for-review

Admin aprueba desde /panel/validaciones (o el atajo en /panel/usuarios)
  → KycCommands.approve()/force_approve() -> si requested_user_type esta
    seteado, aplica UserProfile.user_type = requested_user_type
    (KycCommands._apply_requested_user_type) -- UNICO lugar del sistema que
    cambia user_type a partir de un KYC. Dispara la senal que auto-crea
    TechnicianProfile.
```

**No confundir con `/registro-profesional`:** esa ruta se retiro como
formulario de registro (2026-07-06) -- ahora es solo un `redirect` a
`/register` en `router.js`, para no romper enlaces/marcadores viejos.
`RegisterContractorView.vue` se elimino; su selector de tipo se reciclo
dentro del paso 1 del wizard de arriba.

### 2. Actualizacion de perfil con avatar

```
PATCH /api/v1/auth/profile/   (multipart/form-data)
  → request.data + request.FILES fusionados en data dict
  → UserProfileUpdateSerializer(data=data, partial=True)
  → AccountCommands.update_profile(user, validated_data)
  → Si profile_picture en data → ImageField guarda en 'profiles/pictures/'
  → Retorna UserDetailSerializer(updated_user).data
```

**Importante:** El frontend debe enviar `Content-Type: multipart/form-data` para incluir la imagen. El campo se llama `profile_picture`.

**`user_type` NO es editable aqui (2026-07-06):** se quito de
`UserProfileUpdateSerializer` y de `AccountCommands.update_profile` a
proposito -- antes de esto, cualquier CUSTOMER autenticado podia
auto-ascenderse a PROFESSIONAL con un simple `PATCH` (la senal de
`create_technician_profile` disparaba igual, sin KYC). El unico camino
valido ahora es el flujo de upgrade de la sección 1b arriba.

### 3. Bloqueo temporal de disponibilidad (Slot Reservation)

```
POST /api/v1/auth/availability/{id}/lock/
  → AvailabilityCommands.lock_slot_temporarily(slot_id, requesting_user)
  → select_for_update() → previene race conditions
  → slot.status = PENDING_RESERVATION
  → Celery task release_expired_slot con countdown=900s (15 min)
  → Respuesta: { status:'success', slot:..., expires_at:..., countdown_seconds:900 }
```

---

## Endpoints Disponibles

Todos bajo `/api/v1/auth/` (prefijo configurado en `ecommerce/urls.py`).

### Autenticacion y Perfil

| Metodo | Endpoint | Permiso | Descripcion |
|--------|----------|---------|-------------|
| POST | `/register-request/` | AllowAny | Envia OTP al email. Payload sin `user_type` -- siempre crea CUSTOMER |
| POST | `/register-verify/` | AllowAny | Verifica OTP, crea cuenta CUSTOMER ya APPROVED, retorna tokens |
| POST | `/register-resend/` | AllowAny | Reenvio OTP (cooldown 60s) |
| POST | `/register/` | AllowAny | Registro directo (sin OTP — flujo legacy) |
| POST | `/login/` | AllowAny | Autenticacion, retorna tokens JWT (bloquea solo si BLOCKED o nunca aprobado) |
| POST | `/logout/` | IsAuthenticated | Invalida refresh token |
| GET/PATCH | `/profile/` | IsAuthenticated | Obtiene o actualiza perfil. PATCH soporta multipart para avatar. `user_type` NO editable aqui |
| POST | `/change-password/` | IsAuthenticated | Cambia contrasena |
| POST | `/token/refresh/` | AllowAny | Nuevo access token desde refresh token |
| POST | `/request-upgrade/` | IsAuthenticatedActiveUser | **Nuevo (2026-07-06)**, ver `kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md`. `{requested_user_type}` -- reabre la UserVerification propia a PENDING |

### Marketplace de contratistas (publico)

| Metodo | Endpoint | Permiso |
|--------|----------|---------|
| GET | `/contractors/` | AllowAny |
| GET | `/contractors/{uuid}/` | AllowAny |
| GET | `/contractors/search/?category=&max_hourly_rate=&user_type=&min_rating=` | AllowAny |
| GET | `/contractors/recommendations/?category_id=&limit=10&priority=` | AllowAny |
| POST | `/contractors/{uuid}/review/` | IsAuthenticated |

**CONTRACTOR incluido en el marketplace público (2026-07-05):** `ContractorProfileViewSet.queryset`,
`ContractorSearchSelector` y `ContractorRecommendationSelector` filtraban `user_type__in`
solo con `TECHNICIAN`/`PROFESSIONAL`/`SPECIALIST`. Ahora incluyen `CONTRACTOR` — cualquier
usuario cuyo upgrade a Contratista sea aprobado (ver sección 1b, "Upgrade a
profesional") aparece en `/contratistas` y en las recomendaciones del wizard
de servicios. (Nota: `RegisterContractorView.vue`, que originaba este tipo
directo en el registro, se eliminó el 2026-07-06 -- ver banner al inicio de
este documento.)

### Panel admin de profesionales (`AdminContractorViewSet`, NUEVO 2026-07-05)

Base `/api/v1/auth/admin/professionals/`. `IsAdminUser`, paginado (`AdminContractorPagination`),
`lookup_field='uuid'` sobre `UserProfile`. Consumido por `/panel/profesionales`
(`ProfessionalsAdminList.vue`).

| Metodo | Endpoint | Descripcion |
|--------|----------|--------------|
| GET | `/admin/professionals/?user_type=&is_active=&is_active=&is_available=&search=` | Lista paginada — usa `ContractorAdminSelector.list_all_for_admin()`, NO filtra por activos/disponibles por defecto (a diferencia del marketplace público) |
| GET | `/admin/professionals/metrics/` | `ContractorAdminSelector.get_metrics()` — KPIs para las tarjetas del panel |
| PATCH | `/admin/professionals/{uuid}/toggle-availability/` | Body `{"is_available": bool}` → `AccountCommands.set_technician_availability(user, is_available)` |
| GET | `/admin/professionals/{uuid}/schedule/` | Agenda completa (todos los estados) del profesional — reusa `AvailabilitySelector.get_full_schedule(profile_uuid)`, antes solo consumido por el propio profesional en "mi-agenda" |

### CV del contratista (requiere autenticacion)

| Endpoint | Descripcion |
|----------|-------------|
| `/specialties/` | Categorias de trabajo |
| `/skills/` | Habilidades |
| `/experiences/` | Historial laboral |
| `/academic-training/` | Educacion academica |
| `/courses/` | Cursos adicionales |
| `/certifications/` | Certificaciones (con documento adjunto) |
| `/success-cases/` | Portafolio (con imagenes before/after) |

### Disponibilidad de agenda

| Metodo | Endpoint | Permiso | Descripcion |
|--------|----------|---------|-------------|
| GET | `/availability/?profile=<uuid>&start=&end=` | AllowAny | Slots AVAILABLE de un profesional |
| GET | `/availability/my-schedule/?start=&end=` | IsAuthenticated | Agenda completa del profesional autenticado |
| POST | `/availability/bulk-create/` | IsAuthenticated | Creacion masiva de bloques horarios |
| POST | `/availability/{id}/lock/` | IsAuthenticated | Bloqueo temporal 15 min |
| PATCH | `/availability/{id}/update-status/` | IsAuthenticated | Cambio de estado por el profesional |

---

## Patrones de Diseno

### Service Layer (DDD)

- **Commands** (`services/commands.py`): Operaciones de escritura, siempre `@transaction.atomic`.
  - `AccountCommands.register_user()` — crea User + UserProfile en un solo atomic. Fuerza
    `user_type=CUSTOMER` cuando el payload trae campos KYC (autoregistro publico real);
    respeta el `user_type` explicito solo para creacion admin/interna (ver sección 1)
  - `AccountCommands.update_profile()` — actualiza `user.profile`, NO el modelo User.
    `user_type` deliberadamente excluido de `profile_fields` (2026-07-06) — ver sección
    "Actualizacion de perfil con avatar"
  - `AccountCommands.change_password()` — usa `set_password()` + `save()`
  - `AccountCommands.admin_reset_password(user)` — nuevo (2026-07-05): genera contraseña temporal,
    `set_password()` + notificación `admin_password_reset` (usado por `/panel/usuarios`)
  - `AccountCommands.resend_verification_email(user)` / `confirm_email_verification_link(token)` —
    nuevo (2026-07-05): enlace firmado con `django.core.signing` (sin modelo nuevo, expira 24h,
    idempotente) para re-verificar un usuario YA existente — distinto del OTP de
    `EmailVerificationCode` (solo pre-registro)
  - `AccountCommands.set_user_groups(user, group_ids)` — nuevo (2026-07-05): asigna Django Groups;
    sin efecto en la autorización real del sistema hoy
  - `AccountCommands.set_technician_availability(user, is_available)` — nuevo (2026-07-05): usa
    `ProfileResolver.get_technician_profile(user)`, lanza `ValidationError` si el usuario no tiene
    perfil de técnico configurado. Usado por el toggle de disponibilidad de
    `AdminContractorViewSet.toggle_availability`
  - `AvailabilityCommands.lock_slot_temporarily()` — `select_for_update()` + Celery countdown

- **Selectors** (`services/selectors.py`): Lecturas optimizadas con `select_related`/`prefetch_related`.
  - `AccountSelector.get_profile(user)` — perfil del usuario autenticado
  - `AccountSelector.get_tokens_for_user(user)` — genera tokens JWT
  - `ContractorSearchSelector.search_contractors(category_slug, filters)` — busqueda filtrada (marketplace público, filtra activos/disponibles)
  - `ContractorRecommendationSelector.get_compatible_professionals(category_id, priority, limit)` — recomendaciones
  - `ContractorAdminSelector` — nuevo (2026-07-05), panel `/panel/profesionales`:
    - `list_all_for_admin(user_type='', is_active='', is_available='', search='')` — a diferencia
      de `ContractorSearchSelector`, NO filtra por activos/disponibles por defecto (el admin
      necesita ver TODOS los perfiles service-provider, incluidos inactivos/no disponibles)
    - `get_metrics()` — retorna `{total, by_type, active_count, inactive_count, available_count,
      unavailable_count, average_rating}`; `average_rating` promedia los 5 factores de
      `ContractorReview` con `Avg` agregado sobre toda la base (no itera en Python)

### Seguridad

- **Nunca** `is_staff=True` ni `is_superuser=True` desde la API de registro
- Passwords: siempre `set_password()` / `check_password()` — nunca texto plano
- JWT: access 15min + refresh 7 dias
- Logout invalida el refresh token en BD
- `select_for_update()` en reservas de agenda para prevenir race conditions

---

## Senales (Signals)

```python
# En models.py — al final del archivo
@receiver(post_save, sender=UserProfile)
def create_technician_profile(sender, instance, created, **kwargs):
    # Import diferido para evitar el ciclo profile_registry -> accounts.models
    from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
    if instance.user_type in SERVICE_PROVIDER_TYPES:
        TechnicianProfile.objects.get_or_create(user=instance.user)
```

**Generalizado 2026-07-05:** antes solo se disparaba para `user_type == TECHNICIAN`. Ahora se
dispara para los **4 tipos service-provider** (`TECHNICIAN`, `PROFESSIONAL`, `SPECIALIST`,
`CONTRACTOR`) vía `accounts.services.profile_registry.SERVICE_PROVIDER_TYPES` — motivo: el
Marketplace de Contratistas + Asignación de Técnicos necesita que Profesionales, Especialistas y
Contratistas también tengan `is_available`/`specialties` para poder ser candidatos de
`TechnicianSelector`/`ServiceAssignmentCommands`, no solo los usuarios `TECHNICIAN`. El modelo
`TechnicianProfile` no se renombró — sigue siendo el "perfil asignable" compartido por los 4
tipos (ver sección de modelos arriba).

---

## Auditoria y Correcciones

> **[Reorganizado 2026-08-05, auditoría transversal]** El historial detallado de auditorías y
> correcciones (5 entradas fechadas 2026-06 a 2026-07-09, ~237 líneas) se movió a
> [`CHANGELOG_ACCOUNTS.md`](CHANGELOG_ACCOUNTS.md) — este documento se mantiene como referencia
> del estado actual, no como bitácora histórica (hallazgo: era 37% del archivo). La sección
> "Política de arquitectura de perfiles" que sigue abajo NO es changelog pese a tener fecha —
> es la regla vigente, se queda aquí.

---

## Política de arquitectura de perfiles (2026-07-05 — inmutable)

Fase fundacional de una arquitectura de identidades/perfiles pedida explícitamente para que el
sistema soporte, a largo plazo, muchos tipos de usuario sin que sus dominios se contaminen entre
sí. Antes de implementar se auditó todo el proyecto (16 apps): la mayoría (`renting`, `marketing`,
`orders`, `cart`, `dashboard`, `shop`, `payment`, `quotes`, `support`, `core`, `inventory`) **ya
estaban desacopladas** de `UserProfile` — solo dependen de las clases de permiso de
`users/api/permissions.py`, nunca de `user_type` o de los campos del modelo directamente. Los
puntos débiles reales estaban concentrados en `operations` (que llegaba a **escribir**
`UserProfile.user_type` desde otro dominio) y en la ausencia total de un resolver/registro/
excepciones central — no en los 12 dominios ya mencionados.

**Decisión de alcance:** esta fase construye el mecanismo de extensión (resolver + registro +
excepciones) reutilizando el `UserProfile` compartido actual — **no** se dividió físicamente en un
modelo por tipo (eso requeriría migrar datos reales y reescribir ~17 vistas del frontend, con 4 de
riesgo alto por mezclar campos compartidos y específicos en el mismo objeto plano). Si en el futuro
se decide encarar esa separación física, el resolver ya deja el punto de indirección necesario para
hacerlo tipo por tipo, sin big-bang rewrite.

### Piezas nuevas

| Archivo | Responsabilidad |
|---|---|
| `accounts/exceptions.py` | `ProfileError`, `MissingRequiredProfile`, `ProfileMismatchError` — nunca continuar silenciosamente ante un perfil ausente o de tipo incorrecto. |
| `accounts/services/profile_registry.py` | `BUYER_TYPES`, `SERVICE_PROVIDER_TYPES`, `OPERATIONAL_TYPES`, `CONTRACTOR_ASSIGNABLE_TYPES` — única fuente de verdad de qué tipos pertenecen a qué grupo de dominio. Agregar un tipo nuevo = sumarlo acá, no tocar clases de permiso. |
| `accounts/services/profile_resolver.py` | `ProfileResolver` — único punto de acceso a `user.profile` / `user.technician_profile` / `user.dispatcher_profile` (operations). Métodos que no lanzan (`get_profile`, `get_type`, `has_type`) para call sites tolerantes, y métodos que lanzan (`resolve`, `resolve_technician`, `resolve_dispatcher`) para los que requieren el perfil sí o sí. |

### Regla para código nuevo

Prohibido `getattr(user, 'profile', None)` / `user.profile` / `user.technician_profile` /
`user.dispatcher_profile` directo en código nuevo. Usar siempre `ProfileResolver`. Las clases de
permiso de `users/api/permissions.py` (nombres sin cambios, comportamiento sin cambios) ya fueron
migradas a este patrón, incluida la base reutilizable `RequiresProfileType` para permisos que solo
necesitan "usuario activo + user_type en un conjunto".

### Bugs corregidos en el camino

1. `technical_services/services/commands.py` leía `technician_profile.professional_type` — campo
   que nunca existió en `TechnicianProfile` (solo tiene `specialties`/`is_available`). Crasheaba
   con `AttributeError` en cualquier pedido de servicio con técnico pre-seleccionado. Corregido
   usando `ProfileResolver.get_type()` (la fuente real de "tipo profesional" es
   `UserProfile.user_type`).
2. `operations/services/commands.py::DispatcherCommands.create()` mutaba
   `accounts.UserProfile.user_type` al crear un `DispatcherProfile` — exactamente el tipo de
   contaminación cross-domain que esta política prohíbe. `assign_resource(ROLE_CONTRACTOR)` ahora
   valida contra `DispatcherProfile.dispatcher_type == FIELD_OPS` directamente en vez de depender
   de esa mutación; `operations/api/views.py::available_staff` se actualizó en paralelo para
   seguir listando esos dispatchers como candidatos `CONTRACTOR`.

### `VendorProfile` eliminado

Confirmado código muerto: se serializaba (`users/api/serializers.py`) y tenía inline en el admin
(`users/admin.py`), pero ningún endpoint, comando o selector en las 16 apps lo creaba o
actualizaba. El frontend tampoco lo referenciaba. Migración `accounts/migrations/0008_delete_vendorprofile.py`.

### Fase 2 (pendiente, no ejecutada)

Separación física de `UserProfile` en modelos 100% independientes por tipo real
(`TECHNICIAN`/`PROFESSIONAL`/`SPECIALIST`/`CUSTOMER`/`TRANSPORTER`/`CONTRACTOR`/`ACCOUNTANT`), con
migración de datos y actualización de los ~4 componentes Vue de riesgo alto (wizard de onboarding
de contratista, perfil público de contratista, listados de contratistas). Solo tiene sentido si
aparece una necesidad de negocio concreta que lo justifique (ej. campos verdaderamente exclusivos
que generen fricción en el modelo compartido) — no crear modelos vacíos para tipos sin ningún caso
de uso hoy (VENDOR, INSTALLER, ENGINEER, etc.).
- `TechnicianProfile.specialties` usa `related_name='technician_profiles'` (confirmar antes de usar 'technicians').
