# 25 — Auditoría Enterprise: Organization (Fase 10)

> **Fase 10 completada y cerrada 2026-08-01** — continúa el plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[24](24_AUDITORIA_NOTIFICATIONS_SUPPORT.md). `organization/`
> es un módulo nuevo (en construcción, Fase 8/9 de su propio plan de migración) que centraliza
> configuración institucional (branding, contacto, correos, dominios, SEO, legal). Nunca se
> había auditado su robustez interna. Alcance aprobado por el usuario: los 3 P2 más la
> inconsistencia documental menor. El P3 (historial de cambios) queda documentado como pendiente.
>
> Verificado explícitamente y **sin hallazgos**: no existe ningún concepto de roles/equipos de
> soporte en `organization/` que `support/` esté ignorando (no hay arquitectura paralela); los
> permisos de los 8 ViewSets admin son correctos (`IsAdminUser`, JWT, sin CSRF aplicable).

## P2 — Race condition real en el patrón singleton

`SingletonMixin.save()` (`organization/models.py`) desactivaba las demás filas y guardaba la
propia sin ningún lock. Dos requests concurrentes (dos pestañas del panel admin, o dos admins
editando a la vez) podían cada una ver "sin fila activa" y crear la suya — dejando **2 filas
activas simultáneas** para un agregado que se supone es un singleton. Como la mayoría de los
modelos no declaran `Meta.ordering`, `OrganizationSelector.get_*().first()` devolvería una fila
no determinística en ese estado corrupto.

**Resuelto:** se agregó un `UniqueConstraint` parcial (`condition=Q(is_active=True,
is_deleted=False)`) a los 7 modelos singleton (`Company`, `Branding`, `ContactInfo`,
`EmailSettings`, `DomainSettings`, `SeoSettings`, `LegalEntityInfo`) — migración
`0005_branding_unique_active_branding_and_more`. Convierte la condición de carrera de corrupción
silenciosa en un `IntegrityError` explícito, garantizado por Postgres incluso bajo concurrencia
real (no solo a nivel de aplicación). Se verificó que no existían ya filas activas duplicadas
antes de aplicar la migración (0 conflictos en los 7 modelos).

## P2 — `EmailSettings` sin cache, consultado en 5 sitios del flujo crítico de emails

`OrganizationSelector.get_email_settings()` hacía un `SELECT` fresco en cada llamada, invocado
sin cache desde `notifications/tasks.py`, `accounts/services/commands.py`,
`users/services/commands.py`, `marketing/channels/email_channel.py` y `users/api/admin_auth.py`
— inconsistente con `Company`/`Branding`/`ContactInfo`, que sí tienen cache (aunque a nivel del
endpoint público de `core`).

**Resuelto:** cache de 5 minutos (mismo TTL que el resto del proyecto) en el propio selector.

**Bug real encontrado durante la implementación (no en el hallazgo original, sino introducido y
corregido en el mismo fix):** la primera versión invalidaba el cache en `EmailSettingsViewSet`
(el ViewSet), pero `OrganizationCommands.upsert_email_settings()` llama a
`OrganizationSelector.get_email_settings()` **internamente** para encontrar la fila a actualizar
— eso cachea la versión **pre-update** antes de que el propio upsert la mute y guarde. Un test
nuevo (`test_get_email_settings_se_cachea_y_se_invalida_al_actualizar`) lo detectó de inmediato:
el objeto cacheado no reflejaba la actualización recién hecha. Corregido moviendo la
invalidación al **command** (`upsert_email_settings`, el único punto de escritura real), no a la
vista — así cualquier otro caller futuro del command (management commands, otros services)
también invalida correctamente, no solo el camino HTTP.

## P2 — Campos de contacto/correo sin validación de formato

`ContactInfoInputSerializer.email` y `EmailSettingsInputSerializer.default_from_email` eran
`CharField` (no `EmailField`), y `ContactInfoInputSerializer.phone` no tenía ningún validador de
formato colombiano. Se podía guardar un remitente o un número de WhatsApp mal formado sin ningún
aviso, y solo se descubría cuando el Communication Center intentaba usarlo.

**Resuelto:** `EmailField` en ambos serializers; `validate_phone()` en `ContactInfoInputSerializer`
reusando el mismo patrón `^3\d{9}$` ya usado en `notifications/services/commands.py::_PHONE_RE`.

## Doc — contradicción menor sobre el estado de la Fase 8

La cabecera del documento de arquitectura decía que el panel admin (Fase 8) ya se construyó
(2026-07-12), pero la tabla de fases seguía marcándola "Pendiente" con la misma fecha de
actualización. Corregido: la tabla ahora refleja "Completa".

## Pendiente (P3, no implementado en esta fase)

- Sin historial de cambios (`changed_by`/auditoría) para `EmailSettings`/`ContactInfo` — nadie
  puede saber qué admin cambió el remitente de email o el número de WhatsApp institucional más
  allá de `updated_at`. Requeriría un modelo de auditoría nuevo — mayor alcance del que amerita
  esta fase incremental.

## Verificación

- 1 test nuevo confirmando que el `UniqueConstraint` bloquea 2 filas activas simultáneas
  (`bulk_create` bypaseando `SingletonMixin.save()` a propósito, simulando la condición de
  carrera real).
- 2 tests nuevos de cache (invalidación manual + invalidación automática vía el endpoint).
- 4 tests nuevos de validación de formato (teléfono/email inválidos rechazados, teléfono válido
  aceptado).
- `organization/tests.py`: **18/18** (11 preexistentes + 7 nuevos).
- Regresión cruzada: `accounts/tests.py` + `users/tests.py` + `marketing/tests.py` (los 3
  consumidores de `get_email_settings()` con suite de tests) — **104/104**, sin fallos.
- `manage.py check`: limpio (solo el warning preexistente no relacionado).

## Resumen ejecutivo

El hallazgo más importante de esta fase no fue ninguno de los 3 originales, sino uno descubierto
**durante la implementación del fix de cache**: la primera versión del fix invalidaba en el lugar
equivocado (la vista) y habría dejado el cache envenenado para cualquier caller no-HTTP del
command — exactamente el tipo de bug sutil que esta auditoría busca prevenir. El test nuevo lo
atrapó antes de llegar a producción. El race condition del singleton (P2 más serio) ahora tiene
una garantía real a nivel de base de datos, no solo de aplicación.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-9 | Hechas — ver documentos 15-24 |
| 10 — Organization | **Hecha (este documento) — 3 P2 + doc menor cerrados, 1 P3 documentado** |
| 12 | Hecha — ver [26](26_AUDITORIA_CORE.md) (sin hallazgos, core/support desacoplados) |
| 13-16 | Fuera de alcance de esta sesión |
