# Auditoria — Identity Management Center (Fase 0)

> **Fecha:** 2026-08-07. Entregable de la Fase 0 del plan "Identity Management Center" pedido
> para `/panel/usuarios`. Alcance: `users`, `accounts`, `organization`, `dashboard`, `security`,
> `notifications`, `kyc`. Ejecutada via 3 agentes de exploracion en paralelo sobre esas apps.

---

## 1. Conclusion principal

**No se encontro duplicidad real de codigo o logica** en la superficie auditada. Lo que a
primera vista parece duplicado es, en cada caso, aislamiento deliberado y ya documentado:

| Lo que parece duplicado | Por que NO lo es |
|---|---|
| 3 flujos de "resetear contrasena" (`AccountCommands.admin_reset_password`, `CustomerPasswordResetCommands.confirm_reset`, `AdminPasswordResetCommands.confirm_reset`) | Tres audiencias distintas con garantias distintas: admin resetea a otro usuario (genera temporal + email), cliente se autorecupera via link firmado, admin se autorecupera via OTP de correo aislado en `/api/v1/admin-auth/`. Unificarlos mezclaria superficies de ataque de audiencias con confianza distinta. |
| 2 flujos OTP (admin self-service vs verificacion de registro) | `PhoneOtp` (verificacion de telefono en registro) y el OTP de `/admin-auth/forgot-password-*` resuelven problemas distintos (verificar un numero vs recuperar acceso administrativo) con modelos y expiraciones independientes. |
| `UserAuditLog` vs `kyc.VerificationEvent` vs `security.SecurityEvent` | Cada uno es propiedad de una app distinta (`users`/`kyc`/`security`), con su propio ciclo de vida y consumidores. Fusionarlos en un solo modelo cruzaria limites de dominio sin necesidad — el Lote 1 los unifica solo en lectura (`UserTimelineSelector`, ver `ARQUITECTURA_COMPLETA_USER.md` seccion 4d), no en escritura. |

## 2. Inventario de lo que NO existe hoy (necesario para el plan completo de 17 fases, no para el Lote 1)

| Concepto pedido | Estado real |
|---|---|
| Sesiones/JWT con IP, geo, dispositivo por login | No existe un modelo de "sesion". `security.SecurityEvent` ya guarda `ip_address`/`user_agent` en `LOGIN_SUCCESS`/`LOGIN_FAILED`, pero no hay tracking de sesiones activas ni geo-IP. |
| Bloqueo automatico por intentos fallidos | No existe. `LOGIN_FAILED` se registra en `SecurityEvent` pero nada lo cuenta ni actua sobre el. |
| 2FA | No existe en ningun flujo (admin ni cliente). |
| Matriz de permisos real basada en Groups | Los checkboxes de Groups en `UserDetail.vue` YA EXISTEN pero no otorgan permisos — la autorizacion real es 100% `is_staff`/`is_superuser` + `accounts.UserProfile.user_type` via `ProfileResolver`. Activar Groups como mecanismo real de autorizacion es un cambio arquitectonico, no aditivo. |
| Estados "Suspendido"/"Bloqueado" como campo de dominio | No existian. El Lote 1 los resuelve como **etiquetas visuales** sobre `is_active=False` + `UserAuditLog.metadata.reason` — decision explicita para no migrar el esquema de `User` en produccion. |
| Purga fisica validada cross-app | `UserCommands.erase_user()` ya es soft-delete (`is_deleted=True`) desde el fix de 2026-07-17 (bug real de `ProtectedError` 500, ver seccion 4c de `ARQUITECTURA_COMPLETA_USER.md`). Un hard-delete real requeriria auditar ~28 modelos con FK a `User` (Orders, Payments, Renting, Services, Quotes, Notifications, Reviews, Chat...) uno por uno. |
| Import CSV/Excel con validacion | No existe endpoint ni UI. |
| Export Excel/PDF real | Solo CSV (Lote 1, `UserList.vue::exportCSV()`), generado client-side. |
| Dashboard de KPIs de usuarios | No existe. |
| Buscador global indexado | El filtro actual (`UserSelector.list_all(search=...)`) es un `icontains` sobre unos pocos campos, no un indice. |
| Endpoints `/internal/ai/users/` | No existen. |
| `correlation_id`/`request_id` en auditoria | `UserAuditLog.metadata` es JSON libre pero no hay un id de correlacion generado por request. |

## 3. Que se reuso en el Lote 1 (en vez de construir de nuevo)

| Necesidad | Reusado de |
|---|---|
| Registrar accion sobre un usuario | `UserAuditCommands.log()` — ya existia, se le agrego `request=None` |
| Extraer IP/user-agent de un request | Patron copiado literal de `security.SecurityCommands.log_event()` |
| Eventos de login con IP/UA | `security.SecurityEvent` — se lee directo, sin tocar nada |
| Eventos KYC | `kyc.VerificationEvent` — se lee directo, sin tocar nada |
| Seleccion multiple + accion masiva + export CSV (UI) | Patron `selectedIds` Set + `exportCSV()` de `frontend/src/modules/shop/BrandList.vue`, replicado en `UserList.vue` |
| Componente de timeline | `frontend/src/components/shared/StatusTimeline.vue` (`mode="events"`) — ya era el componente unificado del proyecto, no se creo uno nuevo |

## 4. Alcance del Lote 1 vs pendiente

Ver `ARQUITECTURA_COMPLETA_USER.md` seccion 4d para el detalle tecnico completo de lo
implementado en el Lote 1 (acciones masivas, timeline unificado de lectura, auditoria
enriquecida con IP/UA, motivo de desactivacion). Todo lo listado en la seccion 2 de este
documento queda fuera de alcance hasta que se apruebe explicitamente una ronda futura.
