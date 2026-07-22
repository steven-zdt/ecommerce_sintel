# App: accounts — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md
```

## Responsabilidad de esta app

Perfiles de usuario (UserProfile, TechnicianProfile) y flujos de
autenticacion publica: registro, login, logout, cambio de contrasena y perfil propio.

`VendorProfile` se eliminó (2026-07-05): código muerto, ningún endpoint/comando lo poblaba.

**SSoT de identidad (2026-07-06, reemplaza el diseno KYC original del mismo dia):**
todo registro publico (`RegisterRequestSerializer`/`UserRegisterSerializer`,
via `create_from_verified_payload`/`register_user`) crea SIEMPRE un
`UserProfile.CUSTOMER` con `kyc.UserVerification` ya `APPROVED` de inmediato
(`KycCommands.bootstrap_approved`, ahora acepta `kyc_fields`/`consent_events`
opcionales para conservar el snapshot de identidad + Habeas Data aunque no
haya revision admin). `user_type` YA NO es un campo client-suppliable en
esos 2 serializers — nunca se pregunta en el registro. `/registro-profesional`
quedo como simple `redirect` a `/register` (router.js) — `RegisterContractorView.vue`
se elimino.

Convertirse en profesional (CONTRACTOR/PROFESSIONAL/SPECIALIST/TECHNICIAN)
es un upgrade posterior, disparado SOLO desde el dashboard autenticado
(`ContractorOnboardingWizard.vue`, ruta `mi-cuenta/perfil-profesional`, CTA
en `AccountSidebar.vue` visible solo si `user_type === CUSTOMER`): llama a
`POST auth/request-upgrade/` (`KycCommands.request_upgrade`, ver `kyc/CLAUDE.md`)
que reabre la MISMA `UserVerification` (OneToOne) a `PENDING` para que suba
los 5 documentos de siempre y un admin apruebe -- recien ahi, y solo ahi,
`UserProfile.user_type` cambia (`KycCommands._apply_requested_user_type`,
invocado desde `approve()`/`force_approve()`).

**Hueco de seguridad cerrado (mismo dia):** antes de esto, `user_type` era
un campo editable en `UserProfileUpdateSerializer` (`PATCH auth/profile/`) y
`AccountCommands.update_profile` lo aplicaba sin ninguna validacion --
cualquier CUSTOMER autenticado podia auto-ascenderse a PROFESSIONAL al
instante (la senal de `accounts/models.py` que auto-crea `TechnicianProfile`
disparaba igual). `user_type` ya NO esta en los campos editables de ninguno
de los dos -- el UNICO camino valido para cambiarlo es el upgrade de arriba.
Las 7 ViewSets de CV (`ContractorProfileScopedMixin`) usan
`IsServiceProviderOrUpgrading` (no `IsServiceProviderUser` a secas) para que
un CUSTOMER con upgrade en curso (`requested_user_type` seteado) pueda
completar su perfil profesional ANTES de que el KYC del upgrade se apruebe.

El login (`authenticate_user`, y `GatedTokenObtainPairView` en `auth/token/`)
bloquea solo si `verification.status == BLOCKED`, o si nunca hubo una
aprobacion (`first_approved_at is None`) -- NO simplemente `status !=
APPROVED`. Esto es lo que permite que un CUSTOMER con un upgrade
`PENDING`/`UNDER_REVIEW` en curso siga comprando sin perder acceso mientras
se revisa su ascenso. `register_verify` sigue emitiendo tokens sin este
chequeo a proposito. `RegisterRequestSerializer`/`UserRegisterSerializer`
ya NO tienen `first_name`/`last_name` sueltos — vienen de
`kyc.api.serializers.KycRegistrationFieldsMixin` (primer/segundo nombre y
apellido, fecha de nacimiento con validacion >=18, documento, consentimiento
Habeas Data) -- estos SI se siguen pidiendo en el registro de un CUSTOMER
(no se redujeron los campos del formulario, solo se quito la eleccion de
`user_type`).

`phone_number` es obligatorio en `RegisterRequestSerializer`/`UserRegisterSerializer`
(2026-07-06) y acepta celular o fijo en el mismo campo — validado por
`accounts.api.serializers.validate_colombian_phone_number` (celular: 10
digitos empieza en 3; fijo: 7 digitos locales o 10 digitos con indicativo
`6XXXXXXXXX`; tolera `+57`/`57` y espacios/guiones). El modelo
`UserProfile.phone_number` sigue siendo `null=True` a nivel de BD (no se
migro retroactivamente) — la obligatoriedad es solo del flujo de registro.

`fecha_expedicion_documento` (`KycRegistrationFieldsMixin`) es **opcional**
(2026-07-06, `required=False, allow_null=True, default=None`) en los 2
formularios de registro — el modelo `UserVerification.fecha_expedicion_documento`
ya era `null=True` desde el inicio, no cambio. `AccountViewSet.register_request`
maneja el caso `None` explicitamente antes de llamar `.isoformat()` (bug real
corregido el mismo dia: un `None` sin chequear rompia el endpoint con 500).

**UI de registro (2026-07-06):** para minimizar el ingreso manual, el campo
`nacionalidad` ya no se muestra en el formulario — se auto-completa desde
`pais` (mapa `COUNTRY_TO_NATIONALITY` en
`frontend/src/components/auth/kyc/latamData.js`), pero sigue viajando en el
payload al backend sin cambios ahi. `pais` es un `<select>` de paises de
Latinoamerica (default `Colombia`); `ciudad` es un `<select>` de ciudades
colombianas *unicamente* (limitacion aceptada "inicialmente" — si se elige
otro pais, la lista de ciudades sigue siendo la de Colombia). El campo
telefono en la UI ahora fuerza indicativo `+57` fijo y solo acepta celular
(10 digitos, empieza en 3) — el validador de backend
(`validate_colombian_phone_number`) no cambio, sigue aceptando tambien fijo,
asi que no se rompe nada si otro caller (admin, tests) sigue enviando un
fijo directamente a la API.

**Fase de consolidacion (2026-07-06, mismo dia -- auditoria completa +
cierre de huecos):** se audito TODO el codebase (backend + frontend, 3
agentes en paralelo) buscando cualquier camino alterno para cambiar
`user_type`. Unico hallazgo adicional (mas alla del hueco ya cerrado
arriba): el admin nativo de Django (`/admin/`, `UserProfileInline` en
`users/admin.py`) permitia editarlo sin pasar por `AccountCommands`/
`KycCommands` ni dejar rastro en `UserAuditLog` -- **cerrado**
(`readonly_fields = ('user_type',)`). Tambien se agrego `read_only_fields`
defensivo en `PublicContractorProfileSerializer`/`AdminContractorSerializer`
(hoy solo se usan para lectura, pero sin la marca explicita quedarian
escribibles si un dev los conecta a un POST/PUT a futuro).

`KycCommands._apply_requested_user_type` ahora TAMBIEN asigna un Django
`Group` con el nombre del tipo aprobado -- puramente cosmetico para que
`/panel/usuarios` lo refleje, sin ningun efecto en la autorizacion real
(que sigue siendo 100% `ProfileResolver`/`user_type`).

**Alcance de tipos upgradables, decision explicita:** solo los 4
`SERVICE_PROVIDER_TYPES` son destino valido de `request_upgrade`.
`TRANSPORTER` ya es un sistema separado (`operations.DispatcherProfile`,
con su propio `dispatcher_type` y una prueba de regresion que garantiza que
nunca toca `UserProfile.user_type`) -- meterlo en este flujo crearia un
segundo concepto paralelo. `ACCOUNTANT` no tiene conflicto de arquitectura
pero quedo fuera de esta fase (no priorizado) -- el motor de requisitos por
tipo (`kyc/services/config.py::REQUIRED_DOC_TYPES_BY_TYPE`) ya esta
preparado para agregarlo despues sin rediseno.

**Sesion del propio usuario tras una aprobacion:** no existe push en tiempo
real -- `frontend/src/apps/admin/router.js::router.beforeEach` refresca el
perfil (`GET auth/profile/` -> `authStore.setUser(data)`) cada vez que se
navega a `/mi-cuenta/*`, para que el menu/sidebar reflejen un upgrade
aprobado sin necesidad de relogin.

**Paneles admin sincronizados:** `/panel/usuarios` (`UserList.vue`) muestra
2 columnas nuevas ("Upgrade solicitado" + "Estado KYC") y un boton "Ver
Validacion" que navega a `/panel/validaciones/{uuid}` -- sin cambios de
backend (`UserViewSet.list()` ya usaba `UserDetailSerializer`, que ya
incluye `kyc_verification`/`kyc_status`). `/panel/validaciones`
(`KycAdminList.vue`) gano un filtro por `requested_user_type` y un endpoint
real de metricas (`GET auth/admin/verifications/metrics/`,
`KycSelector.get_admin_metrics()`) que reemplazo el hack anterior de 4
requests paginados leyendo solo `.count`.

## Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `models.py` | UserProfile, TechnicianProfile (movidos desde users) |
| `exceptions.py` | `MissingRequiredProfile`, `ProfileMismatchError` — excepciones de dominio del sistema de perfiles |
| `api/views.py` | AccountViewSet: register, login, logout, profile, change-password |
| `api/serializers.py` | UserRegisterSerializer, UserLoginSerializer, LogoutSerializer, ChangePasswordSerializer |
| `services/commands.py` | AccountCommands: register_user(), update_profile(), admin_update_user(), change_password(), authenticate_user(), logout() |
| `services/selectors.py` | AccountSelector: get_profile(), get_tokens_for_user() |
| `services/profile_resolver.py` | `ProfileResolver` — punto único de acceso a `user.profile`/`.technician_profile`/`.dispatcher_profile`. Nunca usar `getattr(user, 'profile', None)` directo en código nuevo. |
| `services/profile_registry.py` | `BUYER_TYPES`, `SERVICE_PROVIDER_TYPES`, `OPERATIONAL_TYPES`, `CONTRACTOR_ASSIGNABLE_TYPES` — grupos de `user_type` por dominio, consumidos por `users/api/permissions.py` |

Ver sección "Política de arquitectura de perfiles" en `ARQUITECTURA_COMPLETA_ACCOUNTS.md` para el detalle completo.

## Modelos de Perfil (todos en esta app)

| Modelo | related_name en User | Descripcion |
|--------|---------------------|-------------|
| `UserProfile` | `user.profile` | Datos personales + user_type |
| `TechnicianProfile` | `user.technician_profile` | Especialidades + disponibilidad |

`TechnicianProfile.specialties` usa `related_name='technician_profiles'` (no 'technicians').
Para buscar tecnicos por categoria usar `category.technician_profiles.all()`.

## user_type choices (en UserProfile) — TODOS los valores validos

```python
UserProfile.TECHNICIAN   = 'TECHNICIAN'    # default
UserProfile.PROFESSIONAL = 'PROFESSIONAL'
UserProfile.SPECIALIST   = 'SPECIALIST'
UserProfile.CUSTOMER     = 'CUSTOMER'      # agregado 2026-06 — comprador/cliente
UserProfile.TRANSPORTER  = 'TRANSPORTER'
UserProfile.CONTRACTOR   = 'CONTRACTOR'
UserProfile.ACCOUNTANT   = 'ACCOUNTANT'
```

## Campos de nombre (CRITICO — no estan en users.User)

`first_name` y `last_name` SOLO existen en `UserProfile`, NO en `users.User`.

```python
# INCORRECTO — genera FieldError: Invalid field name(s) for model User
User.objects.create(first_name='Ana', last_name='Lopez')

# CORRECTO
user = User.objects.create(email='ana@sintel.co', is_active=True)
UserProfile.objects.create(user=user, first_name='Ana', last_name='Lopez')
```

## Avatar / foto de perfil

El campo `profile_picture` en `UserProfile` sirve como avatar.
`upload_to='profiles/pictures/'`.

Para actualizarlo via API: `PATCH /api/v1/auth/profile/` con `Content-Type: multipart/form-data`.
El ViewSet fusiona `request.FILES` en el dict de datos antes de pasar al serializer.

## Patrones obligatorios

- `register_user()` crea User + UserProfile en una sola `@transaction.atomic`
- La API NUNCA asigna `is_staff=True` ni `is_superuser=True` — se extraen del payload
- `update_profile()` actualiza `user.profile`, NO el modelo User directamente
- `admin_update_user()` para cambios de is_active/is_verified + campos de perfil desde admin
- Password: nunca plaintext — usar `set_password()` / `check_password()`
- Tokens JWT: access (15 min) + refresh (7 dias)
- Logout invalida el refresh token en BD
- Signal en models.py: `post_save` en UserProfile crea TechnicianProfile automaticamente si user_type==TECHNICIAN

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
