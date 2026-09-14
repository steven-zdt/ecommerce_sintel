# WHITE_LABEL_DECISION_RECORD.md
Fase 43, 56, 60 — Decisiones clave con evidencia, alternativas, riesgo y reversibilidad

## Decisión 1 — Migrar el proyecto actual vs. crear proyecto nuevo

**DECISIÓN: Migrar el proyecto actual.**

**EVIDENCIA:**
- `organization` ya modela identidad/legal/contacto/dominio/SEO con disciplina de acceso único (ver [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md)).
- `core` es 7/9 grupos de modelo GENERIC por esquema (mismo doc).
- Score ponderado de reusabilidad ≈47/100 — medio, no bajo; ningún hallazgo indica imposibilidad técnica.
- Ningún dato encontrado es estructuralmente inseparable (los datos "Sintel" son filas de DB o strings, no relaciones de esquema imposibles de generalizar).
- Los bloqueadores P0 (legal docs, prompt de IA) son problemas de **contenido hardcoded en 2 archivos concretos**, no de arquitectura.
- Todos los módulos de negocio (shop/services/renting/quotes/orders/payment/support/marketing/notifications/operations) ya operan sobre datos de DB, con acoplamiento de identidad ≈0 en 9 de 10.

**ALTERNATIVAS CONSIDERADAS:** Proyecto nuevo (Opción B) — descartada.

**COMPARACIÓN:**

| Criterio | Opción A: Migrar actual | Opción B: Proyecto nuevo |
|---|---|---|
| Costo | Medio — trabajo concentrado en ~15 archivos críticos + migración incremental de theme | Muy alto — reescribir Shop/Services/Renting/Quotes/Payment/Support/AI Engine desde cero |
| Riesgo | Medio, mitigable con feature flags y despliegue incremental | Alto — dos sistemas en paralelo, riesgo de divergencia y regresión |
| Tiempo | Semanas-meses por fases (ver roadmap) | Meses-años para alcanzar paridad funcional actual |
| Migración de datos | Ninguna requerida (mismo esquema) | Requiere migrar todos los datos de producción de Sintel al nuevo sistema |
| Paridad de funcionalidad | Inmediata (ya existe) | Debe reconstruirse gradualmente, riesgo de regresión |
| Reuso de frontend | Alto (Design System, componentes, router ya funcionan) | Cero |
| Reuso de backend | Alto (Service Layer, Commands/Selectors, motores de pricing) | Cero |
| Knowledge Graph / documentación | Se conserva y sigue siendo válido | Debe reconstruirse |
| Riesgo operacional (stack de prod activo) | Controlado — cambios incrementales sobre sistema en producción probado | Alto — nuevo sistema sin historial de producción |

**RIESGO:** Medio. Mitigado por: no tocar producción (`sintel_prod_*`) hasta que cada fase esté validada; mantener compatibilidad hacia atrás (adaptadores, no romper contratos); checkpoints con tests antes de avanzar.

**DEPENDENCIAS:** Ninguna decisión de este registro depende de la Decisión 2 (multi-tenancy) — son independientes.

**REVERSIBILIDAD:** Alta en cada fase individual (cambios pequeños, con git). Baja para "empezar de cero" una vez avanzada la migración — por eso se recomienda journaling estricto de checkpoints (Fase 38).

**RECOMENDACIÓN:** Proceder con Opción A.

---

## Decisión 2 — Multi-tenancy ahora o después (Gate de Fase 43)

**DECISIÓN: Después. No introducir `tenant_id` en esta etapa.**

**EVIDENCIA:**
- El prompt maestro pide explícitamente NO introducir multi-tenancy automáticamente y evaluar al final.
- No se encontró ningún requisito de negocio expresado por el usuario para operar múltiples negocios simultáneos desde una sola instalación — el caso de uso descrito (Sintel hoy, "Zapatería Nova" como prueba futura) es compatible con "una instalación por negocio" (Opción A del gate).
- Introducir `tenant_id` ahora multiplicaría el alcance de cada fase siguiente (aislamiento de datos, routing por dominio, autorización, facturación, storage, cache, jobs, contexto de IA) sin que exista todavía un solo Business Profile funcionando para validar el modelo.

**ALTERNATIVAS:** Opción B (multi-tenant desde ya) — descartada por prematura; no hay validación de que la plataforma necesite servir 2+ negocios desde el mismo despliegue/base de datos. Si el producto lo requiere en el futuro, el roadmap de multi-tenancy (tenant_id, aislamiento de datos, routing por dominio, autorización, billing, storage, cache, jobs en background, aislamiento de contexto de IA) se evalúa como iniciativa separada, después de certificar el modelo de Business Profile de instalación única.

**RIESGO:** Bajo — decisión reversible; el diseño de `BusinessProfile` de la Fase 26 no impide agregar `tenant_id` después si se decide.

**DEPENDENCIAS:** Depende de completar F0-F12 del roadmap (ver [WHITE_LABEL_MIGRATION_ROADMAP.md](WHITE_LABEL_MIGRATION_ROADMAP.md)) antes de reabrir este gate.

**REVERSIBILIDAD:** Alta — no tomar la decisión ahora no cierra ninguna puerta.

**RECOMENDACIÓN:** Confirmar Opción A (instalación única por negocio) como estado por defecto; reabrir este gate solo si aparece un requisito de negocio concreto para multi-negocio simultáneo.

---

## Decisión 3 — `organization` como núcleo de Business Identity vs. nueva app `business`

**DECISIÓN: Reutilizar y extender `organization`. No crear una app `business`.**

**EVIDENCIA:** `organization` ya centraliza Company/Branding/ContactInfo/SocialLink/EmailSettings/DomainSettings/SeoSettings/LegalEntityInfo con patrón selector/commands documentado y exigido (`organization/CLAUDE.md`). Crear una app paralela duplicaría exactamente el trabajo ya hecho y reintroduciría el problema de duplicación que la creación de `organization` resolvió (ver Fase 1.3 de [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md)).

**ALTERNATIVAS:** Nueva app `business` — descartada, evidencia arriba.

**RIESGO:** Bajo.

**REVERSIBILIDAD:** Alta.

**RECOMENDACIÓN:** REUSE para todos los modelos existentes; EXTEND solo para agregar UI de panel (dashboard) y, eventualmente, el modelo de contenido legal y `ThemeConfig` (si se decide que vivan ahí en vez de en `core`).

---

## Decisión 4 — `/panel/business` nuevo vs. evolucionar `/panel/organizacion`

**DECISIÓN: Usar `/panel/organizacion` (ya existe, no crear `/panel/business`).**

**CORRECCIÓN (2026-08-14):** esta decisión originalmente asumía que `/panel/organizacion` no existía y debía construirse desde cero. Es incorrecto — `OrganizationView.vue` (8 tabs) ya está construido y en el sidebar desde 2026-07-12, montado sobre la API propia de `organization` (`/api/v1/organization/`, fuera del patrón BFF de `dashboard` por decisión deliberada, no por omisión). Ver nota completa en [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md).

**EVIDENCIA:** `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` confirma el panel construido en su Fase 8 (2026-07-12). Queda un remanente menor: el endpoint `site-brand` en `dashboard` sigue existiendo en paralelo (duplica edición de `trade_name`/`tagline`/`logo`) — no es una ausencia de UI, es una duplicación de dos caminos para lo mismo.

**RIESGO:** Bajo.

**REVERSIBILIDAD:** Alta.

**RECOMENDACIÓN:** No crear ni "construir por primera vez" nada aquí. Si se quiere limpieza adicional, evaluar deprecar el endpoint `site-brand` de `dashboard` en favor exclusivo de `/panel/organizacion` — cambio pequeño y opcional, no bloqueante.
