# Arquitectura completa — app `kyc`

> **SUPERSEDED PARCIALMENTE (2026-07-06, SSoT de identidad):** este
> documento describe el diseno ORIGINAL (todo registro bloqueado hasta
> aprobacion admin). Eso ya NO es cierto -- un CUSTOMER (comprador) se crea
> ya `APPROVED` de inmediato, sin bloqueo. Solo quien pide convertirse en
> profesional (`KycCommands.request_upgrade`) pasa por el flujo de
> aprobacion descrito aqui. Ver `kyc/CLAUDE.md` para el resumen actualizado
> completo; las secciones 3, 4, 7, 11 y 12 de este documento tienen notas
> puntuales de correccion agregadas donde aplica.

## 1. Proposito

Verificacion de identidad (KYC) de cada usuario, **una sola vez**, reutilizada
por todos los `user_type` (CLIENTE/PROVEEDOR/CONTRATISTA/TECNICO). Hoy (ver
banner arriba) solo bloquea a quien esta en medio de un upgrade a
profesional -- un CUSTOMER nunca necesita que un administrador apruebe su
`UserVerification` para poder comprar.

No reemplaza ni se confunde con `users.EmailVerificationCode` (OTP de
registro -- prueba de propiedad del correo, *antes* de crear la cuenta). El
KYC de esta app ocurre *despues* de crear la cuenta.

## 2. Modelos (`kyc/models.py`)

Todos extienden `ecommerce.base_models.SintelBaseModel` (uuid, created_at,
updated_at, is_deleted). Sin manager de soft-delete automatico -- todo
selector filtra `is_deleted=False` explicitamente.

### `UserVerification`

OneToOne a `User` (`related_name='kyc_verification'`). Campo `status`:
`PENDING | UNDER_REVIEW | APPROVED | REJECTED | BLOCKED | EXPIRED`.

Campos de identidad KYC-only (capturados una vez en el registro, snapshot):
`primer_nombre`, `segundo_nombre`, `primer_apellido`, `segundo_apellido`,
`sexo` (opcional), `nacionalidad`, `fecha_expedicion_documento`,
`lugar_expedicion_documento`. Los campos que YA existian en
`accounts.UserProfile` (`document`, `document_type`, `birth_date`, `address`,
`city`, `country`, `phone_number`) se reutilizan tal cual -- no se duplican.

`submitted_at`, `reviewed_by` (FK SET_NULL), `reviewed_at`, `admin_message`
(ultimo mensaje del admin; el historial completo vive en `VerificationEvent`).

### `VerificationDocument`

FK a `UserVerification` (`related_name='documents'`). `doc_type`:
`CEDULA_FRONTAL | CEDULA_REVERSO | RUT | HOJA_VIDA | DIPLOMA | CERTIFICACION |
ANTECEDENTES_POLICIA | ANTECEDENTES_CONTRALORIA | ANTECEDENTES_PROCURADURIA | OTRO`.

`file` usa `PrivateKycStorage` (ver seccion 5). `original_filename`,
`content_type`, `file_hash_sha256` (SHA256 real del contenido -- nunca se
confia solo en el nombre/extension declarados por el cliente). `status`:
`PENDING | APPROVED | REJECTED` (igual convencion que `operations.OperationDocument`).
`scan_status`: `SKIPPED | CLEAN | INFECTED | ERROR` (siempre `SKIPPED` en
esta fase -- ver seccion 6). `uploaded_by`, `reviewed_by` (FK SET_NULL),
`reviewed_at`, `rejection_reason`.

### `VerificationEvent`

Timeline **append-only** (nunca UPDATE/DELETE, solo INSERT) -- igual
convencion que `operations.TrackingEvent`/`quotes.QuotationTimeline`. FK a
`UserVerification`, `event_type` (CREATED, SUBMITTED_FOR_REVIEW, APPROVED,
REJECTED, INFO_REQUESTED, BLOCKED, DOC_UPLOADED, DOC_DELETED, DOC_OPENED,
DOC_APPROVED, DOC_REJECTED, NOTE), FK opcional a `VerificationDocument`,
`actor` (FK SET_NULL) + `actor_email` denormalizado, `metadata` JSONField.

### `ConsentRecord`

Habeas Data (Ley 1581/2012 Colombia). **Append-only** -- jamas se actualiza
ni se borra una fila. Una nueva version del documento legal siempre es un
INSERT nuevo. FK a `User`, `consent_type` (`POLITICA_TRATAMIENTO_DATOS |
AUTORIZACION_TRATAMIENTO_DATOS | TERMINOS_CONDICIONES` -- uno por checkbox
obligatorio), `document_version` (`CURRENT_CONSENT_DOCUMENT_VERSION` en
`services/config.py`, hoy `'1.0'`), `accepted`, `ip_address`, `user_agent`.

## 3. Maquina de estados (`services/config.py` + `services/commands.py::KycCommands`)

Patron copiado de `operations.services.config.ALLOWED_TRANSITIONS` +
`OperationCommands.transition_status`/`review_document` -- el mas maduro del
proyecto para esto (select_for_update, validar contra tabla de transiciones,
guardar, crear evento append-only, notificar via `transaction.on_commit`).

```
PENDING      -> UNDER_REVIEW, BLOCKED
UNDER_REVIEW -> APPROVED, REJECTED, PENDING, BLOCKED
REJECTED     -> UNDER_REVIEW, BLOCKED
APPROVED     -> BLOCKED
BLOCKED      -> (terminal)
EXPIRED      -> PENDING
```

`REQUIRED_DOC_TYPES` = CEDULA_FRONTAL, CEDULA_REVERSO, RUT, HOJA_VIDA, DIPLOMA
(DIPLOMA = "uno o varios", satisfecho por >=1 no eliminado). `OPTIONAL_DOC_TYPES`
= CERTIFICACION + 3 tipos de ANTECEDENTES. `DOC_TYPE_LIMITS` define
(max_size_mb, extensiones permitidas) por tipo.

**Actualizado 2026-07-06:** `REQUIRED_DOC_TYPES_BY_TYPE` (dict `user_type ->
list[doc_type]`) reemplazo a `REQUIRED_DOC_TYPES` como fuente real que
consultan `_missing_required_doc_types`/`_all_required_docs_approved`, clave
por `verification.requested_user_type`. `REQUIRED_DOC_TYPES` sigue
existiendo como fallback para verificaciones sin `requested_user_type`
(profesionales grandfathered). Hoy los 4 `SERVICE_PROVIDER_TYPES` comparten
la misma lista -- ver `kyc/CLAUDE.md` para el detalle del motor de
requisitos.

### Metodos de `KycCommands`

- **[ELIMINADO 2026-07-06]** ~~`bootstrap_after_registration`~~ -- ya no
  tiene callers. Reemplazado por `bootstrap_approved(user, kyc_fields=None,
  consent_events=None)`: crea `UserVerification` ya `APPROVED` (con
  `first_approved_at`), conservando opcionalmente el snapshot de identidad
  + `ConsentRecord` de Habeas Data si se pasan. Llamado dentro de la MISMA
  transaccion que crea `User`+`UserProfile`
  (`accounts.services.commands.register_user`/`create_from_verified_payload`).
- **`request_upgrade(verification, requested_user_type, by)` [NUEVO
  2026-07-06]** -- unico metodo que transiciona `APPROVED -> PENDING`
  (bypassa `ALLOWED_TRANSITIONS`, igual que `force_approve`). Setea
  `requested_user_type` (nunca se borra despues). Ver `kyc/CLAUDE.md`.
- `upload_document(verification, doc_type, file, uploaded_by)` -- valida
  tamano/extension/magic-bytes (`accounts.services.commands.validate_file`),
  calcula SHA256, llama a `DocumentScanner.scan()`, crea el registro + evento
  `DOC_UPLOADED`.
- `delete_document(document, requesting_user)` -- solo si
  `verification.status in (PENDING, REJECTED)`. **Soft-delete unicamente**
  (el archivo nunca se borra del disco -- nunca se destruye evidencia de lo
  subido). Evento `DOC_DELETED`.
- `submit_for_review(verification, by)` -- valido desde PENDING/REJECTED;
  exige que todos los `REQUIRED_DOC_TYPES` tengan al menos un documento no
  eliminado; transiciona a UNDER_REVIEW; notifica `ws_group='admin_notifications'`;
  dual-log `UserAuditLog(action='kyc_submitted')`.
- `approve(verification, reviewed_by)` -- valido solo desde UNDER_REVIEW;
  **precondicion**: todos los documentos requeridos para
  `requested_user_type` (ver `REQUIRED_DOC_TYPES_BY_TYPE`) deben tener un
  documento individual `APPROVED` (si no, `ValidationError` listando los que
  faltan); transiciona a APPROVED; **llama a `_apply_requested_user_type()`**
  (cambia `UserProfile.user_type` + asigna un Group cosmetico, 2026-07-06);
  notifica `kyc_approved`; dual-log.
- `reject(verification, reviewed_by, reason)` -- valido solo desde
  UNDER_REVIEW; `reason` obligatorio; notifica `kyc_rejected`; dual-log.
- `request_more_info(verification, reviewed_by, message)` -- valido solo
  desde UNDER_REVIEW; transiciona a PENDING; notifica `kyc_info_requested`;
  dual-log.
- `block(verification, reviewed_by, reason)` -- valido desde
  PENDING/UNDER_REVIEW/APPROVED; **no toca `user.is_active`** (eso sigue
  siendo una decision admin separada, ya existente en `UserViewSet`);
  notifica `kyc_blocked`; dual-log.
- `review_document(document, approved, reviewed_by, reason='')` -- accion
  por documento individual (copia `OperationCommands.review_document`, sin
  auto-avance del padre -- el avance de `UserVerification` completa es
  siempre la decision explicita de `approve()`/`reject()`).
- `mark_document_opened(document, admin_user)` -- evento `DOC_OPENED`,
  llamado desde el endpoint de descarga cuando quien pide no es el dueno.

## 4. Registro -- integracion con `accounts`

`kyc.api.serializers.KycRegistrationFieldsMixin` se mezcla en
`accounts.api.serializers.RegisterRequestSerializer` (flujo OTP, el activo
hoy) y `UserRegisterSerializer` (flujo directo) -- **ambos** capturan los
mismos campos de identidad y consentimiento, para que ninguno quede como
bypass silencioso del KYC. Valida:

- `fecha_nacimiento`: edad >= 18 anos (`validate_fecha_nacimiento`).
- `numero_documento`: solo digitos, 5-20 caracteres.
- Los 3 checkboxes de Habeas Data: los 3 son obligatorios (`validate()`).

`first_name`/`last_name` de `UserProfile` se derivan en el backend:
`f'{primer_nombre} {segundo_nombre}'.strip()` / analogo para apellidos.

`AccountViewSet.register_request` (paso 1 del flujo OTP) captura
`REMOTE_ADDR`/`HTTP_USER_AGENT` en el momento real en que el usuario marco
los checkboxes -- se guardan en el `registration_payload` de
`EmailVerificationCode` (con las fechas serializadas a ISO string, porque es
un `JSONField`) y se usan recien al crear la cuenta en
`create_from_verified_payload` (`register_verify`, paso 2).

`accounts.services.commands._pop_kyc_registration_data(data)` es el helper
compartido que separa, de un dict de datos de registro, los campos que van a
`UserProfile`, los que van a `UserVerification` (kyc_fields) y los 3 eventos
de consentimiento -- usado por `register_user` y `create_from_verified_payload`.

## 5. Storage privado + descarga autenticada

`KYC_PRIVATE_STORAGE_ROOT` (settings) -- por defecto `private_media/kyc/` en
la raiz del repo, **fuera de `MEDIA_ROOT`**. Ni el `static()` de Django en
DEBUG ni el `location /media/ { alias /code/media/; }` de nginx en
produccion la exponen.

`kyc.services.storage.PrivateKycStorage` (subclase de `FileSystemStorage`,
`base_url=None`) + `kyc_upload_path(instance, filename)` (ruta con UUID, no
el nombre original).

Descarga: `VerificationDocumentViewSet.download`
(`GET auth/documents/{uuid}/download/`) -- verifica que quien pide sea el
dueno del documento o `IsAdminUser`; si es admin y no es el dueno, registra
`VerificationEvent(DOC_OPENED)`; responde `FileResponse(as_attachment=True)`.

Sin URLs firmadas/expirables en esta fase (mejora futura razonable).

## 6. Antivirus -- stub

`kyc.services.scanner.DocumentScanner.scan(file)` siempre retorna
`ScanResult(status='SKIPPED')` en esta fase. Punto de extension limpio para
ClamAV real (via clamd) despues -- solo `KycCommands.upload_document` llama a
esto, ningun otro caller necesita cambiar cuando se reemplace.

`accounts.services.commands.validate_file` se extendio con
`magic_bytes_check: bool = False` (default preserva el comportamiento de los
callers existentes de CV/certificaciones) -- verifica los primeros bytes del
archivo contra la extension declarada (PDF `%PDF`, JPG `\xff\xd8\xff`, PNG
`\x89PNG`). `kyc` llama siempre con `magic_bytes_check=True`.

## 7. Gate de login -- ya no es "APPROVED o nada" (actualizado 2026-07-06)

El chequeo vive en `accounts.services.commands.AccountCommands._assert_kyc_approved(user)`.
Logica actual (reemplaza el bloque de codigo original de este documento,
que solo comparaba `status != APPROVED`):

```python
verification = ProfileResolver.get_verification(user)
if verification is None:
    raise AuthenticationFailed(...)
if verification.status == UserVerification.STATUS_BLOCKED:
    raise AuthenticationFailed("Tu cuenta ha sido bloqueada...")
if verification.status == UserVerification.STATUS_APPROVED or verification.first_approved_at is not None:
    return  # permite el login
raise AuthenticationFailed(...)
```

`first_approved_at` (campo nuevo, se setea UNA vez y nunca se borra) es lo
que permite que un CUSTOMER con un upgrade `PENDING`/`UNDER_REVIEW` en curso
siga comprando sin perder acceso mientras se revisa su ascenso -- **no usar
`reviewed_at`** para esto, tambien lo setean `reject()`/`approve()`, no
distingue "aprobado alguna vez" de "revisado y rechazado". `BLOCKED` siempre
bloquea, sin excepcion, independientemente del historial.

Se invoca desde:

1. `AccountCommands.authenticate_user` -- `POST auth/login/`.
2. `GatedTokenObtainPairSerializer`/`GatedTokenObtainPairView` (`accounts/api/views.py`,
   montado en `accounts/urls.py` como `POST auth/token/`) -- SimpleJWT
   directo bypasseaba el gate antes de esto.
3. **NO** se invoca desde `AccountViewSet.register_verify` -- a proposito:
   todo registro publico crea ya un CUSTOMER `APPROVED` (ver banner al
   inicio del documento), asi que este caso ya no es relevante salvo para
   quien esta en medio de un upgrade. Los endpoints de autoservicio KYC
   (`verification/`, `submit-for-review/`, `upload-document/`, `documents/`,
   `request-upgrade/`) usan `IsAuthenticatedActiveUser`, no un permiso
   "solo aprobados".

**Riesgo residual CERRADO (2026-07-06):** `IsBuyerOrAdmin` ya incluye
CUSTOMER en `BUYER_TYPES` sin necesitar KYC. Las 7 ViewSets de CV
(`ContractorProfileScopedMixin`) usan `IsServiceProviderOrUpgrading` (nueva
permission class, `users/api/permissions.py`) para permitir completar el
perfil profesional durante un upgrade en curso, sin abrir acceso a otros
dominios (agenda de tecnicos, etc.) que si siguen exigiendo `user_type` real.
Ver `accounts/CLAUDE.md` para el detalle completo.

`ProfileResolver.get_verification(user)` (accounts/services/profile_resolver.py)
es el unico punto de acceso -- nunca `getattr(user, 'kyc_verification', None)`
disperso en el codigo.

## 8. Auditoria

Dual-log: ademas del `VerificationEvent` (detalle fino, propio de `kyc`),
las 5 transiciones de nivel `UserVerification` (submit/approve/reject/
request_info/block) tambien registran en `users.UserAuditLog` (nuevas
choices: `kyc_submitted`, `kyc_approved`, `kyc_rejected`,
`kyc_info_requested`, `kyc_blocked`) via
`kyc.services.commands._audit_log()` -> `UserAuditCommands.log(...)`, para
que el tab de auditoria de `/panel/usuarios` tambien muestre estos eventos.

## 9. Notificaciones

6 plantillas sembradas por migracion de datos (`kyc/migrations/0002_seed_notification_templates.py`,
mismo patron que `operations/migrations/0002_seed_notification_templates.py`):
`kyc_registered_pending`, `kyc_submitted_for_review`, `kyc_approved`,
`kyc_rejected`, `kyc_info_requested`, `kyc_blocked`. Todas dispatchadas via
`NotificationCommands.dispatch_notification(...)` dentro de
`transaction.on_commit(...)`.

## 10. Grandfathering de usuarios existentes

`kyc/migrations/0003_grandfather_approve_existing_users.py`: para cada
usuario `is_active=True` sin `kyc_verification` (es decir, todos los que
existian antes de esta app), crea retroactivamente una `UserVerification(APPROVED)`
+ un `VerificationEvent(APPROVED, actor=None)`. Idempotente (`get_or_create`).
**No** fabrica `ConsentRecord` para estos usuarios (seria deshonesto simular
un consentimiento que nunca dieron -- backfill de eso es un ejercicio legal
aparte). Migracion irreversible por diseno (`reverse_code = RunPython.noop`).

## 11. Endpoints (montados en `api/v1/auth/`, `kyc/api/urls.py`)

| Metodo + path | Permiso | Accion |
|---|---|---|
| `GET auth/verification/` | IsAuthenticatedActiveUser | Mi propia verificacion + documentos |
| `POST auth/submit-for-review/` | IsAuthenticatedActiveUser | Enviar a revision |
| `POST auth/upload-document/` | IsAuthenticatedActiveUser | Subir un documento |
| `GET auth/documents/` | IsAuthenticatedActiveUser | Listar mis documentos |
| `DELETE auth/documents/{uuid}/` | IsAuthenticatedActiveUser | Eliminar (soft) un documento propio |
| `GET auth/documents/{uuid}/download/` | dueno o IsAdminUser | Descargar (FileResponse) |
| `GET auth/admin/verifications/` (+ `{uuid}/`) | IsAdminUser | Cola de revision / detalle. Acepta filtros `status`/`requested_user_type`/`search` |
| `GET auth/admin/verifications/metrics/` **[NUEVO 2026-07-06]** | IsAdminUser | `KycSelector.get_admin_metrics()` -- by_status, by_requested_type, average_approval_seconds |
| `POST auth/admin/verifications/{uuid}/approve\|force-approve\|reject\|request-info\|block/` | IsAdminUser | Transiciones admin |
| `POST auth/admin/verifications/{uuid}/documents/{doc_uuid}/review/` | IsAdminUser | Aprobar/rechazar un documento |
| `POST auth/request-upgrade/` **[NUEVO 2026-07-06]** | IsAuthenticatedActiveUser | `{requested_user_type}` -- reabre la verificacion propia a PENDING |

## 12. Explicitamente fuera de alcance

**Fase 1 (original):** OCR, biometria/liveness, ClamAV real (solo el stub de
la seccion 6), S3/URLs firmadas, bloqueo real por intentos fallidos de login
(solo `ScopedRateThrottle` de ventana rodante), UI del wizard de registro y
panel "Validaciones" (construido en Fase 2), flujo de re-verificacion para
`EXPIRED` (el estado existe, nada lo dispara todavia), backfill de
`ConsentRecord` para usuarios grandfathered.

**Fase de consolidacion SSoT (2026-07-06):** `TRANSPORTER` como destino de
`request_upgrade` -- ya es un sistema separado y maduro
(`operations.DispatcherProfile`, con su propio `dispatcher_type` y una
prueba de regresion que garantiza que nunca toca `UserProfile.user_type`).
`ACCOUNTANT` tampoco esta incluido (sin conflicto de arquitectura, pero no
priorizado -- el motor de requisitos por tipo ya esta preparado para
agregarlo despues, ver seccion 3). Autorizacion real basada en Django
Groups (se mantiene 100% `ProfileResolver`/`user_type`, los Groups asignados
en la aprobacion son puramente cosmeticos). Notificaciones WebSocket en
tiempo real para que el propio usuario vea su upgrade aprobado sin navegar
(se opto por un refetch de perfil al entrar a `/mi-cuenta/*`).

## Reglas globales

Ver `.AGENT.md` en la raiz del proyecto.
