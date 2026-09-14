# Changelog — accounts

Historial de auditorías y correcciones, movido aquí desde
`ARQUITECTURA_COMPLETA_ACCOUNTS.md` el 2026-08-05 (Sprint 1 de la
[auditoría transversal](../../../core/.AGENT/docs/INFORME_AUDITORIA_TRANSVERSAL_2026-08-05.md) —
hallazgo: 37% del documento de referencia era narrativa histórica, no estado actual). El contenido
no se editó, solo se reubicó — para el estado actual del módulo ver `ARQUITECTURA_COMPLETA_ACCOUNTS.md`
(incluye "Política de arquitectura de perfiles", que se quedó ahí por ser referencia vigente, no
changelog, pese a estar fechada).

---

## Auditoria y Correcciones

### [2026-07-09] SSoT de identidad — auditoria final + cierre del ultimo hueco (creacion admin)

Se recibió un brief de 22 fases pidiendo consolidar `accounts` como única fuente de verdad
de identidad ("nadie crea perfiles especializados directamente; todo nace CUSTOMER; todo
upgrade pasa por KYC"). Antes de escribir código se auditó el estado real (no solo la
propuesta), porque las 2 entradas de 2026-07-06 indicaban que el núcleo ya estaba
implementado y probado. Confirmado con grep + lectura directa: **el único hueco real** era
que un admin SÍ podía crear un usuario con cualquier `user_type` directamente desde
`/panel/usuarios` (documentado como "vía legítima" en la auditoría del 2026-07-06, pero
el usuario decidió en esta sesión cerrarla también, endureciendo la regla a "el admin
únicamente crea CUSTOMER, sin excepción"). El resto del brief (sistema de eventos de
dominio, wizard independiente por tipo, reorganización del dashboard por tipo, librería de
8 componentes Vue nuevos) se descartó explícitamente por decisión del usuario — ver razones
al final de esta entrada.

**Hueco cerrado — creación de usuarios especializados por un admin:**
- `users/api/serializers.py::UserAdminCreateSerializer` — se retiró el campo `user_type`
  (antes `ChoiceField(default=UserProfile.TECHNICIAN)`, elegible libremente). Un admin ya
  no puede elegir el tipo al crear un usuario desde `/panel/usuarios`.
- `accounts/services/commands.py::AccountCommands.register_user()` — el default del
  `user_type` cuando el caller no lo pasa explícito cambió de `UserProfile.TECHNICIAN` a
  `UserProfile.CUSTOMER`. Esto blinda el endpoint admin (que ya no envía el campo) sin
  afectar: (a) el registro público, que ya fuerza CUSTOMER por la rama `has_kyc_data`; (b)
  el código interno (fixtures de tests, seeds) que sigue pudiendo pasar `user_type`
  explícito al llamar `register_user()` directamente en Python — ese camino no es un
  "canal de creación" alcanzable por un admin real vía producto, es construcción de datos
  de prueba, y se mantuvo sin cambios a propósito.
- `users/api/serializers.py::UserAdminUpdateSerializer` — se retiró el campo `user_type`
  también. Ya era ignorado en silencio por `AccountCommands.update_profile()` (no está en
  su allow-list de `profile_fields`), así que el campo en el serializer solo generaba una
  falsa sensación de que editar el tipo de un usuario existente desde este endpoint hacía
  algo — no hacía nada. Retirarlo hace el contrato de la API honesto.
- Frontend `frontend/src/modules/users/UserForm.vue` — el `<select>` de tipo se reemplazó
  por un badge de solo lectura en ambos modos (`create`: fijo en "Cliente (CUSTOMER)`;
  `edit`: el tipo actual del usuario, con nota de que solo cambia al aprobar un upgrade en
  Validaciones KYC). Se quitó `user_type` de ambos payloads (`POST`/`PATCH`) y el prop
  `defaultType` (ya sin consumidores tras el cambio).

**Limpieza de bypasses de solo lectura a `ProfileResolver`** (política ya documentada
arriba en "Política de arquitectura de perfiles", nunca antes verificada al 100%):
`operations/services/commands.py`, `notifications/services/commands.py`,
`technical_services/api/operation_serializers.py` y `kyc/api/serializers.py` tenían
`getattr(x, 'profile'/'technician_profile', None)` directo — sin riesgo de seguridad (solo
lectura), pero inconsistente con la regla ya escrita para código nuevo. Reemplazados por
`ProfileResolver.get_profile()`/`get_technician_profile()`, mismo comportamiento.

**Confirmado sin cambios (ya cerrado desde el 2026-07-06, re-verificado ahora):**
- `\.user_type\s*=` como escritura solo aparece en
  `kyc/services/commands.py::KycCommands._apply_requested_user_type` (grep de todo el
  proyecto). Ningún otro módulo (Renting, Technical Services, Shop, Orders, Payment,
  Operations, Marketing, Inventory, Notifications, Core, Dashboard) escribe `user_type`.
- `/admin/` de Django ya tenía `user_type` read-only (fase anterior).
- TRANSPORTER sigue siendo `operations.DispatcherProfile`, sistema separado con su propio
  test de regresión — no es un hueco, es una separación de dominio deliberada.

**Descartado explícitamente por el usuario en esta sesión (no construido, con motivo):**
- **Sistema de eventos de dominio** (`CustomerCreated`, `UpgradeRequested`, etc.) — no
  existe hoy ningún consumidor real de un bus de eventos; el sistema de notificaciones
  (`notifications.services.commands.NotificationCommands.dispatch_notification`) ya cubre
  la necesidad práctica de "avisar cuando algo cambia". Construir infraestructura de
  eventos sin un caso de uso concreto sería especulativo.
- **Wizard independiente por cada tipo profesional** — contradice una decisión ya tomada y
  confirmada el 2026-07-06: `ContractorOnboardingWizard.vue` es un único wizard reutilizado
  a propósito para los 4 `SERVICE_PROVIDER_TYPES`, precisamente para no fragmentar la UI de
  upgrade en 4-5 componentes casi idénticos.
- **Reorganización del dashboard admin por tipo de usuario** (Customers/Profesionales/
  Transportistas/Contadores/Contratistas/Especialistas, todo separado) — hoy
  `/panel/usuarios` es una lista única con filtro por tipo + columnas de estado KYC, y
  `/panel/profesionales` ya existe como vista de solo lectura para los 4 tipos de
  servicio. Separar más no tiene un consumidor concreto que lo pida hoy.
- **Librería de 8 componentes Vue nuevos** (`UserUpgradeCard`, `UserTypeSelector`,
  `KycProgress`, `ProfileTimeline`, `UpgradeHistory`, `UserProfileStatus`,
  `VerificationBadge`, `ProfessionalDashboardCard`) — ninguno existe hoy; la
  funcionalidad equivalente ya vive inline en `UserList.vue`/`KycAdminList.vue`/
  `KycVerificationPanel.vue`. Extraerlos a componentes reutilizables solo se justifica
  cuando exista un segundo consumidor real de ese markup, no antes.

### [2026-07-06] SSoT de identidad — Fase de consolidacion (auditoria completa + registry + paneles + tests)

Tras el rediseño SSoT (entrada siguiente), se pidió una fase de consolidación
funcional completa: auditar TODO el codebase para confirmar que no existe
ningún camino alterno para cambiar `user_type`, construir un motor de
requisitos por tipo, sincronizar `/panel/usuarios`/`/panel/validaciones`, y
no dar la tarea por terminada sin pruebas de humo. Se investigó con 3
agentes en paralelo (backend, frontend, marketplace/operations) antes de
implementar.

**Hallazgo más importante:** `TRANSPORTER` ya es un sistema separado y
maduro (`operations.DispatcherProfile`, con su propio `dispatcher_type` y
una prueba de regresión —
`operations/tests.py::test_create_does_not_mutate_user_profile_user_type`—
que garantiza que nunca toca `UserProfile.user_type`). Confirmado con el
usuario: esta fase se limita a los 4 `SERVICE_PROVIDER_TYPES` existentes;
TRANSPORTER sigue su propio flujo `DispatcherProfile` sin tocarse, y
ACCOUNTANT queda documentado como fuera de alcance (sin conflicto, solo no
priorizado).

**Auditoría de escritura de `user_type` (resultado):** ninguna vía
alcanzable por un usuario no-admin existe, más allá de la ya sancionada
(`KycCommands._apply_requested_user_type`). Se encontraron 2 vías
adicionales, ambas admin-only: `UserAdminCreateSerializer`/
`UserAdminUpdateSerializer` (`/panel/usuarios`, `IsAdminUser` — legítima,
sin cambios) y el admin nativo de Django (`/admin/`,
`UserProfileInline.user_type` en `users/admin.py` — un segundo camino que
NO pasaba por `AccountCommands`/`KycCommands` ni dejaba rastro en
`UserAuditLog` — **cerrado**, `readonly_fields`).

**Cambios implementados:**
- `kyc/services/config.py::REQUIRED_DOC_TYPES_BY_TYPE` — motor de
  requisitos por tipo (dict, hoy 4 entradas idénticas — no se inventó una
  diferencia falsa entre tipos que hoy comparten los mismos documentos; el
  valor es la forma, lista para agregar ACCOUNTANT sin rediseño).
- `users/admin.py::UserProfileInline.readonly_fields = ('user_type',)` +
  `read_only_fields` defensivo en `PublicContractorProfileSerializer`/
  `AdminContractorSerializer`.
- `KycCommands._apply_requested_user_type` asigna un Django `Group`
  cosmético (sin efecto en autorización real).
- `/panel/usuarios` (`UserList.vue`): columnas "Upgrade solicitado"/"Estado
  KYC" + botón "Ver Validación" — sin cambios de backend (`UserViewSet.list()`
  ya usaba `UserDetailSerializer`).
- `/panel/validaciones` (`KycAdminList.vue` + `KycSelector.get_admin_metrics()`
  + `GET auth/admin/verifications/metrics/`): filtro por
  `requested_user_type` + métricas reales (reemplaza el hack de 4 requests
  paginados leyendo solo `.count`).
- Refetch de perfil en `router.beforeEach` al navegar a `/mi-cuenta/*` (sin
  WebSocket) para que un upgrade aprobado se refleje sin relogin.
- `kyc/tests.py` (nuevo, la app no tenía ningún test) — suite permanente
  cubriendo registro/upgrade/panel-validaciones/marketplace/regresión de
  seguridad, no solo verificación manual de la sesión.

Ver `kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md` para el detalle técnico
completo (secciones 3, 7, 11, 12 actualizadas).

### [2026-07-06] SSoT de identidad — registro siempre CUSTOMER, upgrade a profesional separado

Rediseño mayor que reemplaza el diseño KYC del mismo día (banner al inicio de este documento):
antes, **todo** registro (comprador o profesional) creaba una `kyc.UserVerification` en `PENDING`
y bloqueaba el login hasta aprobación admin — un simple comprador quedaba tan bloqueado como quien
pedía ser contratista. Se corrigió con el principio "todo usuario nace CUSTOMER, con acceso
instantáneo; convertirse en profesional es un upgrade posterior explícito".

**Hallazgo crítico durante la investigación (no era parte del pedido original, se encontró
auditando antes de implementar):** ya existía un hueco de seguridad — `user_type` era un campo
editable en `UserProfileUpdateSerializer`/`AccountCommands.update_profile`, y la señal
`create_technician_profile` disparaba en cualquier `save()`. Cualquier CUSTOMER autenticado podía
auto-ascenderse a PROFESSIONAL con un solo `PATCH /auth/profile/`, sin KYC ni aprobación admin.
`ContractorOnboardingWizard.vue` usaba exactamente ese mecanismo. Cerrado quitando `user_type` de
ambos (ver secciones "Actualizacion de perfil con avatar" y "Patrones de Diseno" en el documento
de referencia).

**Decisión de diseño clave:** se reutilizó el `kyc` app completo en vez de construir una máquina de
estados paralela — la misma `UserVerification` (OneToOne por usuario) se reabre para el ciclo de
upgrade (`KycCommands.request_upgrade`, campo nuevo `requested_user_type`) en vez de crear un
concepto nuevo. Solo 1 endpoint nuevo (`request-upgrade/`); el resto (upload-document,
submit-for-review, approve, force-approve, el panel `/panel/validaciones`) se reutiliza sin
cambios de UI, solo con un pequeño efecto secundario en `approve()`/`force_approve()`
(`KycCommands._apply_requested_user_type` — el ÚNICO lugar del sistema que cambia `user_type` a
partir de un KYC).

**Consecuencia que hubo que resolver aparte:** al cerrar el hueco de seguridad, las 7 ViewSets de
CV (gateadas por `IsServiceProviderUser`) dejaron de ser accesibles para un CUSTOMER en upgrade
(su `user_type` real sigue siendo CUSTOMER hasta la aprobación). Se creó `IsServiceProviderOrUpgrading`
(`users/api/permissions.py`) — permite acceso a SERVICE_PROVIDER_TYPES ya aprobados **o** a quien
tenga `requested_user_type` seteado. Gateado SOLO a `ContractorProfileScopedMixin` (las 7 ViewSets
de CV) — no reemplaza `IsServiceProviderUser` en otros dominios (agenda de técnicos, etc.), donde
un upgrade pendiente NO debe dar acceso todavía.

**Gate de login corregido con un campo dedicado:** el primer intento de gate usaba
`reviewed_at is not None` como señal de "aprobado alguna vez" — bug real detectado antes de llegar
a producción: `reject()`/`approve()` TAMBIÉN setean `reviewed_at` (no distingue "aprobado" de
"revisado y rechazado"), y un usuario `BLOCKED` que fue `APPROVED` antes habría quedado con
`reviewed_at is not None` y se le habría permitido loguear pese al bloqueo. Se agregó
`UserVerification.first_approved_at` (se setea UNA vez, nunca se borra) + un chequeo explícito de
`BLOCKED` que siempre bloquea sin excepción. Ver `AccountCommands._assert_kyc_approved`.

**Registro:** `/registro-profesional` es ahora un `redirect` a `/register` (no 404, para no romper
enlaces/marcadores viejos); `RegisterContractorView.vue` se eliminó. `RegisterRequestSerializer`/
`UserRegisterSerializer` perdieron el campo `user_type` (ya no se pregunta) pero SIGUEN pidiendo
identidad completa + documento + Habeas Data vía `KycRegistrationFieldsMixin` — no se redujo el
formulario, solo la elección de tipo. `RegisterView.vue` redirige post-OTP directo al dashboard
(`customer-profile`), no a `kyc-verification`.

**Migración de datos:** `kyc/migrations/0006_backfill_customer_approved.py` aprobó
retroactivamente la única cuenta CUSTOMER real que había quedado en `PENDING` por el flujo
anterior — confirmado con el usuario antes de ejecutar.

Verificado end-to-end (API + Playwright): registro → CUSTOMER instantáneo → hueco de PATCH
cerrado → request-upgrade → sigue comprando durante el upgrade → 5 documentos → aprobación admin →
`user_type` cambia solo → aparece en el marketplace público. Ver detalle completo en
`kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md`.

### [2026-07-05] Marketplace de Contratistas + Asignación de Técnicos — fix Profile Resolver en ViewSets de CV

Al implementar el panel `/panel/profesionales` y el tablero `/panel/asignacion-tecnicos` se
encontró una violación residual de la política "Profile Resolver" (ver "Política de arquitectura
de perfiles" en el documento de referencia): 7 ViewSets de CV (`ContractorSpecialtyViewSet`, `ContractorSkillViewSet`,
`ProfessionalExperienceViewSet`, `AcademicTrainingViewSet`, `ProfessionalCourseViewSet`,
`ProfessionalCertificationViewSet`, `SuccessCaseViewSet`) y `AvailabilityViewSet` (en las actions
`my_schedule`/`bulk_create`) seguían haciendo `request.user.profile` directo en vez de pasar por
`ProfileResolver`.

**Corregido:**
- Las 7 ViewSets de CV ahora heredan de un mixin nuevo y compartido,
  `ContractorProfileScopedMixin` (`accounts/api/views.py`), que expone `self.own_profile` resuelto
  vía `ProfileResolver.resolve(self.request.user)` (sin `expected_types` desde 2026-07-06 — ver
  auditoría de esa fecha) y fija `permission_classes` — se elimina la duplicación de
  `getattr(request.user, 'profile', None)` en cada una.
- `AvailabilityViewSet.my_schedule`/`bulk_create` ahora usan
  `ProfileResolver.resolve(request.user, expected_types=SERVICE_PROVIDER_TYPES)` directamente.

Esto es puramente higiene de arquitectura (no cambia comportamiento observable) — mantiene la
regla "nunca `user.profile` directo en código nuevo/tocado" vigente en toda la superficie de CV.

### [2026-06] Customer Dashboard — tipos de usuario y avatar

- **Agregado** `CUSTOMER = 'CUSTOMER'` a `UserProfile.USER_TYPE_CHOICES`. Sin migracion (CharField choices).
- **Confirmado** que `first_name`, `last_name` estan en `UserProfile`, NO en `users.User`.
- **Confirmado** que `profile_picture` es el campo de avatar (`upload_to='profiles/pictures/'`).
- **Actualizado** `AccountViewSet.profile` para fusionar `request.FILES` en multipart: `data = {**request.data}; data.update(request.FILES)`.
- Customer Dashboard frontend: `/mi-cuenta/perfil`, `/mi-cuenta/pedidos`, `/mi-cuenta/wishlist`, `/mi-cuenta/direcciones`, `/mi-cuenta/tarjetas`.

### [Previo] Alineacion de respuestas de API

- `bulk-create` retorna `{'created_count': N, 'created': N, 'detail': ...}`.
- `lock` retorna `{'status': 'success', 'slot': ..., 'expires_at': ..., 'countdown_seconds': 900}`.

### [Previo] Mitigacion de errores Float/Decimal

- Motor de costos y tarifas profesionales usan `Decimal` explicito.

### [Previo] Refactor users/accounts DDD

- `IsAuthenticatedActiveUser` en `users.api.permissions` es el permiso correcto para endpoints de cliente autenticado.
- `IsCustomerUser` es alias de `IsAuthenticatedActiveUser`.
