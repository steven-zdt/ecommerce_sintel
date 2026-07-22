# CORE v4 — Arquitectura por Dominios: Fase 9 (Certificación Arquitectónica)

**Fecha:** 2026-07-12
**Objetivo:** Declarar el alcance real de esta migración frente al principio de Single Source
of Truth (SSoT) y Domain-Driven Design (DDD) — con honestidad sobre qué quedó completo y qué
queda como trabajo futuro documentado, no una certificación "100%" que no reflejaría la
realidad.

---

## 1. Checklist contra los criterios de aceptación definidos por el usuario

| Criterio | Estado | Evidencia |
|---|---|---|
| "Una entidad de negocio → un único propietario" | ✅ **Cumplido para `organization`** (8 agregados: Empresa, Branding, Contacto, Redes Sociales, Correos, Dominios, SEO, Info Legal). ⚠️ **No evaluado para el resto de los 15 dominios** — solo se auditaron completamente (Fase 1/3), no se refactorizaron | `MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md` + Fases 1-7 de esa migración |
| "Una configuración → una única fuente de verdad (SSoT)" | ✅ Cumplido para todo lo migrado. 🔴 **Excepción conocida y documentada, NO resuelta**: 4 máquinas de estado (`OperationTicket`/`ServiceOperation`/`RentalOperation`/`Shipment`) siguen siendo 4 fuentes de estado — mitigado (Fase 5, `effective_status` deriva del satélite) pero no eliminado | `MIGRACION_CORE_V4_DOMINIOS_FASE1_AUDITORIA.md`, sección 3.1 |
| "Ninguna aplicación almacena datos institucionales que pertenecen a otra" | ✅ Cumplido — `core` ya no posee `SiteBrandConfig`/`CompanyContactInfo`/`FooterLink(social)` (eliminados físicamente, no solo dejados de usar) | `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md`, entrada 2026-07-12 |
| "Las demás aplicaciones únicamente consumen información mediante OrganizationService" | ✅ Cumplido — grep de 231 imports cross-app confirmó **cero** imports directos de `organization.models` fuera de la propia app (Fase 7) | `MIGRACION_CORE_V4_DOMINIOS_FASE7_INTEGRACION.md`, sección 1 |
| "No se introducen redundancias de configuración ni lógica de negocio durante la migración" | ✅ Cumplido para el código nuevo — las 2 incidencias reales que sí aparecieron (caché sin invalidar, serializer equivocado) se encontraron y corrigieron en Fase 8, no llegaron a quedar como deuda oculta | `MIGRACION_CORE_V4_DOMINIOS_FASE8_REGRESION.md`, sección 4 |

**Veredicto: CERTIFICADO CON ALCANCE ACOTADO.** Los 5 criterios se cumplen estrictamente
dentro del alcance que efectivamente se ejecutó (ver sección 2) — no se certifica el proyecto
completo de 15 dominios, que era un plan más ambicioso del que solo se completó una porción
real y verificada.

---

## 2. Alcance real ejecutado (qué se certifica, exactamente)

### Completado y verificado end-to-end
- **`organization`**: app nueva, 8 modelos, `OrganizationSelector`/`OrganizationCommands`,
  API admin propia (`/api/v1/organization/`), frontend (`OrganizationView.vue`,
  `/panel/organizacion`, primer ítem del sidebar). Migración de datos reales desde `core`
  (marca, contacto, redes sociales) con eliminación física de los modelos viejos.
- **6 consumidores migrados a leer de `organization`**: `core`, `notifications`, `accounts`,
  `users`, `quotes` (parcial), `marketing` (8 canales). `payment` confirmado no-op.
- **`operations`**: 3 FKs de trazabilidad nuevos + `get_effective_status()` (Opción B,
  Pasos 1-2) — mitiga sin eliminar la duplicación de las 4 FSMs.
- **Navegación del panel**: reorganizada por 9 dominios con contenido real (de los 15
  propuestos), sin cambiar ninguna ruta existente.

### Auditado pero NO ejecutado (backlog documentado, no deuda oculta)
- **CRM, Compras, RRHH**: dominios propuestos sin ninguna app ni modelo — quedan como diseño
  a futuro, no como "migración a medias".
- **Consolidación real de las 4 FSMs de Operaciones** (fusionar o reestructurar
  `ServiceOperation`/`RentalOperation`/`Shipment`/`OperationTicket`): evaluado, con 3 opciones
  de diseño documentadas (Fase 5), se ejecutó la mitigación de bajo riesgo (Opción B), NO la
  consolidación física completa — decisión explícita para no arriesgar datos operativos en
  vivo sin una fase dedicada propia.
- **6 hallazgos menores de patrón de acceso** (Fase 3, severidad baja/media): `payment` con
  `select_for_update()` directo, 3 `summary.py` importando `OrderItem` directo, `quotes`
  importando variantes directo, `core.enums()` con acoplamiento de metadata, `orders`
  importando `Cart` directo, `dashboard` orchestrators con imports directos. Todos revisados y
  aceptados como excepciones de bajo riesgo o backlog de limpieza, no como bugs.
- **"Reorganizar vistas" físicamente** (mover archivos de componentes Vue a carpetas que
  coincidan 1:1 con los dominios, más allá de `ProfessionalsAdminList.vue`): no ejecutado,
  mayor riesgo/menor urgencia.
- **Verificación visual del panel autenticado**: bloqueada por restricción de seguridad sobre
  el uso automatizado de credenciales — pendiente de confirmación manual del usuario.

---

## 3. Documentación consolidada — índice de las 9 fases

| Fase | Documento | Estado |
|---|---|---|
| Migración `organization` 1-9 | `MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md` (+ actualizaciones en `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`) | ✅ Completa |
| CORE v4 Fase 1 — Auditoría de dominio | `MIGRACION_CORE_V4_DOMINIOS_FASE1_AUDITORIA.md` | ✅ Completa |
| CORE v4 Fase 2 — Navegación | `MIGRACION_CORE_V4_DOMINIOS_FASE2_NAVEGACION.md` | ✅ Completa + implementada |
| CORE v4 Fase 3 — Propiedad de datos | `MIGRACION_CORE_V4_DOMINIOS_FASE3_PROPIEDAD_DATOS.md` | ✅ Completa |
| CORE v4 Fase 4 — Redundancias | `MIGRACION_CORE_V4_DOMINIOS_FASE4_REDUNDANCIAS.md` | ✅ No-op confirmado |
| CORE v4 Fase 5 — Operaciones | `MIGRACION_CORE_V4_DOMINIOS_FASE5_PROPUESTA_OPERACIONES.md` | ✅ Pasos 1-2 ejecutados |
| CORE v4 Fase 6 — Frontend | (sin doc propio — cambios documentados dentro de Fase 2 y Fase 5) | ✅ Completa |
| CORE v4 Fase 7 — Integración | `MIGRACION_CORE_V4_DOMINIOS_FASE7_INTEGRACION.md` | ✅ Completa |
| CORE v4 Fase 8 — Regresión | `MIGRACION_CORE_V4_DOMINIOS_FASE8_REGRESION.md` | ✅ Completa, 2 incidencias corregidas |
| CORE v4 Fase 9 — Certificación | Este documento | ✅ Completa |

Todos viven en `Documentacion/Arquitectura_general/`, referenciados desde
`ecommerce_sintel/.AGENT.md` (fuente única de verdad de módulo→doc, ver
`feedback_hierarchical_doc_lookup` en memoria del agente) vía la entrada de `organization` y
`operations`.

---

## 4. Checklist final

- [x] Cada dato migrado tiene un único propietario verificado
- [x] Ninguna app almacena datos institucionales ajenos (verificado, no solo declarado)
- [x] Todo consumo de `organization` pasa por Selectors/Commands (0 excepciones)
- [x] Suite de regresión completa corrida (308/314, 0 regresiones nuevas)
- [x] 2 incidencias reales encontradas en regresión, corregidas y re-verificadas
- [x] Documentación de cada app tocada actualizada (`core`, `organization`, `operations`,
      `quotes`, `marketing`, `.AGENT.md`, `CLAUDE.md`)
- [ ] Verificación visual del panel autenticado (pendiente, requiere al usuario)
- [ ] Los 6 dominios restantes de los 15 propuestos (CRM, Compras, RRHH, y refactor físico
      completo de Catálogo/Servicios/Renting) quedan fuera de este alcance certificado

---

## Certificado

**Se certifica que el subconjunto efectivamente migrado en esta sesión — el dominio
`organization` completo, la trazabilidad de `operations`, y la reorganización de navegación del
panel — cumple los principios de Single Source of Truth y separación de dominios definidos por
el usuario, verificado con auditoría de código, pruebas automatizadas y pruebas manuales de
endpoints reales.**

**No se certifica** la migración completa a 15 dominios del plan original — eso permanece como
hoja de ruta documentada (Fase 1, secciones 5 y 8), no como trabajo iniciado y abandonado a
medias. La distinción entre "auditado y planificado" vs. "ejecutado y verificado" se mantuvo
explícita en cada documento de fase para que una sesión futura pueda retomar el trabajo sin
tener que volver a auditar lo ya hecho.
