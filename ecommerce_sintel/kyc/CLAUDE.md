# App: kyc — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md
```

## Responsabilidad de esta app

Verificacion de identidad (KYC) del usuario: una sola vez por usuario
(`UserVerification` es `OneToOneField`), reutilizada durante toda su vida --
tanto para el acceso inicial como CUSTOMER como para cualquier upgrade
posterior a profesional. Incluye documentos privados, timeline append-only
y consentimiento Habeas Data (Ley 1581/2012).

**SSoT de identidad (2026-07-06):** un CUSTOMER (comprador) NO necesita
aprobacion admin -- se crea ya `APPROVED` desde el registro
(`KycCommands.bootstrap_approved`). Solo quien pide convertirse en
CONTRACTOR/PROFESSIONAL/SPECIALIST/TECHNICIAN (`KycCommands.request_upgrade`,
disparado desde el dashboard, nunca en el registro) reabre esta MISMA fila a
`PENDING` y necesita que un admin apruebe sus documentos antes de que
`accounts.UserProfile.user_type` cambie.

**No confundir con `users.EmailVerificationCode`**: esa solo prueba propiedad
del correo *antes* de crear la cuenta (OTP de registro). El KYC de esta app
ocurre *despues* de crear la cuenta y decide si puede operar.

## Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `models.py` | `UserVerification`, `VerificationDocument`, `VerificationEvent` (timeline append-only), `ConsentRecord` (Habeas Data, append-only) |
| `services/config.py` | `ALLOWED_TRANSITIONS`, `REQUIRED_DOC_TYPES_BY_TYPE` (motor de requisitos), `DOC_TYPE_LIMITS`, `CURRENT_CONSENT_DOCUMENT_VERSION` |
| `services/commands.py` | `KycCommands`: bootstrap_approved, request_upgrade, upload_document, delete_document, submit_for_review, approve, force_approve, reject, request_more_info, block, review_document |
| `services/selectors.py` | `KycSelector`: get_own_verification, list_own_documents, list_queue (filtra status/requested_user_type/search), get_verification_for_admin, get_admin_metrics |
| `services/storage.py` | `PrivateKycStorage` -- fuera de MEDIA_ROOT, `base_url=None` |
| `services/scanner.py` | `DocumentScanner` -- stub antivirus (siempre SKIPPED en esta fase) |
| `api/views.py` | `KycViewSet` (autoservicio), `VerificationDocumentViewSet` (listar/borrar/descargar propios), `AdminKycViewSet` (cola de revision + `metrics/`) |
| `tests.py` | Suite de smoke tests SSoT (registro, upgrade, panel validaciones, marketplace, regresion de seguridad) -- unica suite de tests de esta app |

## Patron obligatorio: maquina de estados

Copiado de `operations.OperationTicket/OperationDocument/TrackingEvent` (el
patron mas maduro del proyecto para esto, no el de `quotes` sin validacion ni
el de `accounts.AdminContractorViewSet` con solo un boolean):

- `ALLOWED_TRANSITIONS` (dict) valida cada cambio de estado.
- Cada transicion crea un `VerificationEvent` (append-only, nunca UPDATE/DELETE).
- Toda notificacion via `NotificationCommands.dispatch_notification(...)` dentro
  de `transaction.on_commit(...)`.
- Cada transicion de nivel `UserVerification` (submit/approve/reject/request_info/block)
  tambien hace dual-log en `users.UserAuditLog` (para que `/panel/usuarios` la muestre).

## Estados de `UserVerification.status`

`PENDING -> UNDER_REVIEW -> APPROVED | REJECTED`, mas `BLOCKED` (terminal,
alcanzable desde PENDING/UNDER_REVIEW/APPROVED) y `EXPIRED` (existe en el
modelo, nada lo dispara todavia -- reservado para una futura re-verificacion
periodica). `REJECTED`/`PENDING` (via request-info) permiten volver a
`UNDER_REVIEW` reenviando.

`approve()` exige que **todos** los documentos requeridos para el
`requested_user_type` de la verificacion tengan un documento individual con
`status=APPROVED` -- si falta alguno, lanza `ValidationError` listando
cuales.

**Motor de requisitos (2026-07-06, fase de consolidacion):**
`REQUIRED_DOC_TYPES_BY_TYPE` (`services/config.py`) es un `dict[user_type,
list[doc_type]]`, una entrada por cada `SERVICE_PROVIDER_TYPES`. Hoy los 4
tipos comparten exactamente los mismos 5 documentos (no se inventa una
diferencia falsa) -- el valor real es la forma: agregar un tipo nuevo (ej.
ACCOUNTANT con un documento propio) es sumar una entrada al dict, no tocar
`KycCommands`. `get_required_doc_types(requested_user_type)` resuelve la
entrada, con `REQUIRED_DOC_TYPES` (lista plana original) como fallback para
verificaciones sin `requested_user_type` (profesionales grandfathered antes
de este rediseno).

**`request_upgrade(verification, requested_user_type, by)`**: unico metodo
que transiciona `APPROVED -> PENDING` (bypassa `ALLOWED_TRANSITIONS`, igual
que `force_approve`, con un chequeo explicito de que el estado actual sea
`APPROVED`). Setea `requested_user_type` (campo nuevo, nunca se borra
despues) y limpia `submitted_at`. Usado por el CUSTOMER que pide convertirse
en profesional -- ver `accounts/CLAUDE.md`.

**`_apply_requested_user_type(verification)`**: llamado desde `approve()` y
`force_approve()` al final. Si `requested_user_type` esta seteado, aplica
`user.profile.user_type = requested_user_type` en la MISMA transaccion --
es el UNICO lugar del sistema que cambia `user_type` a partir de un KYC.
Dispara gratis la senal que auto-crea `TechnicianProfile`
(`accounts/models.py`).

**`first_approved_at`**: campo que se setea UNA sola vez (primera vez que
`status` pasa a `APPROVED`, via `bootstrap_approved`/`approve`/`force_approve`)
y nunca se borra despues -- ni siquiera si luego se pide un upgrade (vuelve
a `PENDING`) o es rechazado. Es la senal que usa
`AccountCommands._assert_kyc_approved` para permitir que alguien conserve su
acceso de comprador mientras se revisa un upgrade. **No usar `reviewed_at`
para esto** -- tambien lo setean `reject()`/`approve()`, no distingue
"aprobado alguna vez" de "revisado y rechazado".

## Storage privado -- CRITICO

Los documentos (`VerificationDocument.file`) usan `PrivateKycStorage`, una
carpeta **fuera de `MEDIA_ROOT`** (`KYC_PRIVATE_STORAGE_ROOT` en settings).
Ni el `static()` de Django en DEBUG ni el alias `/media/` de nginx en
produccion la exponen. `base_url=None` fuerza que el UNICO acceso posible sea
`VerificationDocumentViewSet.download` (autenticado, dueno o `IsAdminUser`).

**Nunca** agregar un `location /private_media/` (o similar) al nginx.conf --
eso volveria a exponerlos publicamente.

## Antivirus -- stub, no real todavia

`DocumentScanner.scan()` siempre retorna `SKIPPED` (`scan_status` en el
modelo). Es un punto de extension limpio para ClamAV real (via clamd) en una
fase futura -- reemplazar el cuerpo de `scan()` no requiere tocar ningun
caller.

## Registro -- siempre CUSTOMER, `KycRegistrationFieldsMixin` sigue vigente

`KycRegistrationFieldsMixin` (`api/serializers.py`) se mezcla en
`accounts.api.serializers.RegisterRequestSerializer` (flujo OTP, el activo) y
`UserRegisterSerializer` (flujo directo) -- ambos SIGUEN pidiendo identidad +
documento + Habeas Data (no se redujo el formulario), pero `user_type` YA NO
es un campo de ninguno de los dos: todo registro publico crea siempre
CUSTOMER. Valida edad >=18, numero de documento (solo digitos, 5-20
caracteres) y los 3 checkboxes obligatorios de Habeas Data.

`AccountCommands.register_user`/`create_from_verified_payload` llaman a
`KycCommands.bootstrap_approved(user, kyc_fields, consent_events)` (ya NO
`bootstrap_after_registration`, eliminado por no tener callers) dentro de la
MISMA transaccion que crea `User`+`UserProfile` -- acceso instantaneo,
conservando el snapshot de identidad y los `ConsentRecord` de Habeas Data
aunque no haya revision admin.

## Gate de login -- ya no es "APPROVED o nada"

El chequeo vive en `AccountCommands._assert_kyc_approved(user)` y se invoca desde:
1. `AccountCommands.authenticate_user` (`POST auth/login/`)
2. `GatedTokenObtainPairSerializer` (`POST auth/token/` -- SimpleJWT directo, bypasseaba el gate antes de esto)
3. **NO** desde `AccountViewSet.register_verify` (a proposito).

Logica exacta (2026-07-06): `BLOCKED` siempre bloquea, sin excepcion.
En cualquier otro caso, permite login si `status == APPROVED` **o**
`first_approved_at is not None` -- esto es lo que deja que un CUSTOMER con
un upgrade `PENDING`/`UNDER_REVIEW` en curso siga comprando sin perder
acceso mientras se revisa su ascenso. Solo alguien que JAMAS fue aprobado
queda bloqueado (caso hoy inexistente tras el registro-siempre-CUSTOMER,
salvo cuentas historicas previas al backfill de
`kyc/migrations/0006_backfill_customer_approved.py`).

Los endpoints de autoservicio KYC (`verification/`, `upload-document/`,
`submit-for-review/`, `request-upgrade/`) usan `IsAuthenticatedActiveUser`,
no un permiso "solo aprobados".

**Ya NO es un riesgo residual** (corregido el mismo dia): `IsBuyerOrAdmin`
ya incluye CUSTOMER en `BUYER_TYPES` sin necesitar KYC. Las 7 ViewSets de CV
usan `IsServiceProviderOrUpgrading` (ver `accounts/CLAUDE.md`) para permitir
completar el perfil profesional durante un upgrade en curso, sin abrir
acceso a otros dominios (agenda de tecnicos, etc.) que si siguen exigiendo
`user_type` real.

## `_apply_requested_user_type` tambien asigna un Group cosmetico

Ademas de `profile.user_type = ...`, asigna un Django `Group` con el nombre
del tipo aprobado (`Group.objects.get_or_create(name=requested_user_type)`)
-- puramente informativo para que `/panel/usuarios` lo muestre. Los Groups
**no tienen ningun efecto en la autorizacion real** (eso sigue siendo 100%
`ProfileResolver`/`user_type` via `users/api/permissions.py`) -- nunca
asumir que un Group implica un permiso.

## Endpoint de metricas (`/panel/validaciones`)

`GET auth/admin/verifications/metrics/` (`AdminKycViewSet.metrics`, usa
`KycSelector.get_admin_metrics()`) reemplaza el hack anterior del frontend
(4 requests paginados leyendo solo `.count`). Retorna `by_status`,
`by_requested_type` y `average_approval_seconds` (calculado con
`reviewed_at - submitted_at` sobre verificaciones `APPROVED` --
**no usar `first_approved_at`**, que se setea una sola vez en la vida del
usuario y no sirve para medir el ciclo de cada solicitud individual).

## Alcance de tipos upgradables (fase de consolidacion, 2026-07-06)

Solo los 4 `SERVICE_PROVIDER_TYPES` (TECHNICIAN/PROFESSIONAL/SPECIALIST/
CONTRACTOR) son destinos validos de `request_upgrade`. Decision explicita,
no un olvido:
- **TRANSPORTER** ya es un sistema separado y maduro
  (`operations.DispatcherProfile`, con su propio `dispatcher_type` y una
  prueba de regresion -- `operations/tests.py::test_create_does_not_mutate_user_profile_user_type`
  -- que garantiza que nunca toca `UserProfile.user_type`). Meterlo en este
  flujo crearia un segundo concepto paralelo de "transportista".
- **ACCOUNTANT** no tiene ningun conflicto de arquitectura, pero quedo
  fuera de esta fase (no priorizado). Agregarlo despues requiere: 1 tipo de
  documento nuevo (ej. `TARJETA_PROFESIONAL` en
  `VerificationDocument.DOC_TYPE_CHOICES`) + 1 entrada en
  `REQUIRED_DOC_TYPES_BY_TYPE` + agregar `ACCOUNTANT` a la validacion de
  `request_upgrade`/`RequestUpgradeSerializer` -- el motor de requisitos ya
  esta preparado para esto sin rediseno.

## Reglas globales

Ver `.AGENT.md` en la raiz del proyecto.
