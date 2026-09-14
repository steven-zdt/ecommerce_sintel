# WHITE_LABEL_TRANSFORMATION_MASTER_PLAN.md
Documento ejecutivo — Auditoría de viabilidad White-Label / Business-Agnostic

Generado: 2026-08-14 · Commit base: `5a9f642` · Branch: `fix/audit-p0-remediation` · Auditoría inicial de solo lectura; F1/F2 del roadmap (§27) ya se ejecutaron el mismo día a pedido explícito del usuario — ver nota de corrección abajo y el estado real en `AUDITORIA/WHITE_LABEL/WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md`.

> **CORRECCIÓN (2026-08-14):** varias secciones de este documento (§9, §12, bloqueador #4 del
> checkpoint) afirmaban que `organization` no tenía UI de panel administrativo. Es incorrecto
> — `/panel/organizacion` ya existía desde 2026-07-12. Se detectó al ejecutar F1/F2 y leer
> `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` (paso obligatorio antes de
> tocar código). El texto original queda abajo sin reescribir por completo para mantener
> trazabilidad; tratar cualquier mención a "falta UI de panel para organization" en este
> documento como superada — ver [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md)
> para el estado corregido.

## 1. Executive Summary

`ecommerce_sintel` puede transformarse en una plataforma white-label **migrando el proyecto actual**, sin crear un proyecto nuevo. El score de viabilidad arquitectónica es **≈47/100 (MEDIO)**: el backend tiene fundaciones reales (`organization` como SSoT de identidad, `core` como capa de contenido en su mayoría genérica, Service Layer/Commands/Selectors consistente), pero **dos bloqueadores P0 concretos** — documentos legales 100% hardcodeados a "Sintel" sin modelo de datos, y el prompt del chatbot de soporte que se presenta textualmente como "el asistente de Sintel (Colombia)" — impiden declarar el sistema white-label hoy. Ninguno de los dos requiere rediseño arquitectónico: son problemas de contenido concentrado en 2 archivos.

## 2. Estado actual

Monorepo Django+DRF / Vue 3+Vite+Pinia, con dashboard BFF, Service Layer, `organization` (identidad), `core` (contenido/config del sitio), 10 apps de dominio de negocio (shop, technical_services, renting, quotes, orders, payment, support, marketing, notifications, operations), AI Engine + AI Editor + Project Knowledge Graph. Dos stacks Docker corriendo (`ecommerce_sintel_*` dev, `sintel_prod_*` prod). Working tree con ~710 líneas de trabajo preexistente no relacionado con esta auditoría (ver [WHITE_LABEL_BASELINE.md](WHITE_LABEL_BASELINE.md)) — no tocado.

## 3. Evidencia

Recolectada por 6 investigaciones paralelas de solo-lectura (grep dirigido + lectura de código) más el trabajo de síntesis. Documentos de evidencia completos: [WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md](WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md), [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md), [WHITE_LABEL_FRONTEND_AUDIT.md](WHITE_LABEL_FRONTEND_AUDIT.md), [WHITE_LABEL_MODULE_AUDIT.md](WHITE_LABEL_MODULE_AUDIT.md), [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md).

## 4. Viabilidad

**VIABLE.** Ver comparación completa Opción A (migrar) vs. Opción B (proyecto nuevo) en [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md), Decisión 1. Ningún hallazgo demuestra imposibilidad técnica, datos inseparables, arquitectura incompatible, o dependencia crítica no extraíble — los criterios que el prompt maestro exige para siquiera considerar un proyecto nuevo.

## 5. Diagnóstico

El patrón dominante: **el backend está más preparado que el frontend/contenido**. `organization` y `core` son fundaciones reales y reutilizables. Los bloqueadores duros están concentrados en: (a) contenido legal hardcodeado en un archivo frontend, (b) un prompt de IA hardcodeado en un archivo backend, (c) ausencia total de theming runtime, (d) ausencia de UI de panel para editar identidad. Ninguno de los 10 módulos de negocio tiene acoplamiento de identidad significativo; el acoplamiento de reglas de negocio real se reduce a un único archivo (`LaborConditionsEvaluator` en `quotes`).

## 6. Arquitectura actual

Ver [WHITE_LABEL_ARCHITECTURE_TARGET.md](WHITE_LABEL_ARCHITECTURE_TARGET.md) Fase 25 para el diagrama "lo que ya existe" vs. "lo que debe evolucionar/crearse".

## 7. Arquitectura objetivo

```
PLATFORM → BUSINESS PROFILE (Identity/Organization/Theme/Modules/Features/Navigation/Content/SEO/Legal/Domains) → BUSINESS RUNTIME (Shop/Services/Renting/Quotes/Support)
```
Detalle completo en [WHITE_LABEL_ARCHITECTURE_TARGET.md](WHITE_LABEL_ARCHITECTURE_TARGET.md).

## 8. Business Identity

`organization.Company`+`Branding` ya modelan esto. Bloqueador: default de campo `'Sintel'`, sin UI de panel, sin lectura consistente desde frontend (ver §16).

## 9. Organization

Base sólida — selector/commands pattern documentado y exigido, singleton-safe, soft-delete. Marcado "Fase 3 de 9" en su propio `CLAUDE.md`: falta UI de panel y limpieza de defaults. Detalle: [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md) §1.

## 10. Core

7 de 9 grupos de modelo GENERIC por esquema. Bloqueador real: seeds de datos (`seed_renting_home_cards` con marcas Hikvision/Dahua/etc.), no el esquema. Detalle: mismo documento, §2.

## 11. Frontend

El área con más trabajo pendiente: router sin flags de módulo, ~95 strings "Sintel" hardcoded (muchos sin ningún lookup a modelo), theming 93% hardcoded en hex (ratio 14:1 vs. CSS vars). Arquitectura de runtime-config (site-config/home-feed/footer) es sólida y reutilizable. Detalle: [WHITE_LABEL_FRONTEND_AUDIT.md](WHITE_LABEL_FRONTEND_AUDIT.md).

## 12. Dashboard

BFF puro, patrón Orchestrator consistente en ~40 secciones ya BUSINESS_CONFIGURATION. Gap: `organization` no está cableada a este patrón — no existe hoy ninguna sección de panel para identidad. Detalle: [WHITE_LABEL_MODULE_AUDIT.md](WHITE_LABEL_MODULE_AUDIT.md) Parte A.

## 13. Modules

Ranking de acoplamiento (0=agnóstico, 32=crítico): notifications(1) < marketing(2) < payment/orders/support(3) < operations(4) < shop(6) < renting(9) < technical_services(11) < quotes(14). Ningún módulo tiene acoplamiento de identidad significativo; el único hallazgo fuerte de regla de negocio hardcodeada es `quotes.LaborConditionsEvaluator`. Detalle: [WHITE_LABEL_MODULE_AUDIT.md](WHITE_LABEL_MODULE_AUDIT.md) Parte B.

## 14. Theme

No existe hoy. Diseño propuesto en [WHITE_LABEL_ARCHITECTURE_TARGET.md](WHITE_LABEL_ARCHITECTURE_TARGET.md) Fase 28 — capa `ThemeConfig` + inyección runtime sobre los ~220 usos existentes de `var(--landing-*)`, migración incremental de los ~3100 hex hardcoded.

## 15. Content

CMS sólido para Home/Footer/Navbar/AboutUs/BrandSlider vía `core` + dashboard. Gap real: contenido legal (T&C/Privacidad) sin ningún modelo — 100% hardcoded. Ver §19.

## 16. Navigation

`core.NavbarLink`/`FooterGroup`/`FooterLink` ya son genéricos y reutilizables sin cambios de código. El único gap es que el router del frontend no consulta ningún flag de activación por módulo (Fase 29 del architecture target).

## 17. Domains

`organization.DomainSettings` existe pero tiene **cero consumidores reales** — la config de dominio real vive estática en 6 archivos de infraestructura (nginx×3, docker-compose×2, env×2). No es un defecto de diseño (infra se redespliega por tenant, es esperado), sí es costo operativo documentado en [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md) §4.

## 18. SEO

App `seo` + `organization.SeoSettings` cubren SEO dinámico por página correctamente. Gap menor: `frontend/index.html` (shell estático) sigue con `<title>`/spinner hardcoded, visible a crawlers y en el primer pintado.

## 19. Legal

**El bloqueador más grande de toda la auditoría.** `organization.LegalEntityInfo` cubre bien la *metadata* legal (razón social, NIT, dirección, representante legal). El *contenido* legal vinculante (Términos, Privacidad, Garantía) vive 100% hardcodeado en `frontend/src/components/auth/kyc/legalDocs.js`, sin modelo de datos, con un placeholder de razón social sin resolver incluso para el negocio actual. Detalle: [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md) §6.

## 20. Business Rules

Casi nula dependencia real del rubro de seguridad electrónica en lógica de negocio. Única excepción confirmada: `quotes.LaborConditionsEvaluator` (umbrales de trabajo en altura hardcodeados). Todo lo demás encontrado bajo términos como CCTV/vigilancia/Hikvision es contenido de catálogo en DB (reemplazable sin tocar código) o texto de ayuda/placeholder (bajo impacto).

## 21. AI / RAG

Mecanismo RAG/ingesta es agnóstico. **El prompt de sistema del chatbot de soporte al cliente en producción hardcodea "Sintel (Colombia)"** sin derivar de `organization` — segundo bloqueador P0. Los prompts del Engineering Agent (`ai_engine`/`ai_editor`) también hardcodean "Sintel" pero son herramientas internas de desarrollo, no cara al cliente — riesgo bajo. `ai_engine` confirmado sin imports de `project_knowledge_graph` (desacoplamiento previo intacto).

## 22. Knowledge Graph

CLI capaz (`app-summary`, `data-flow`, `impact`, `change-impact`, etc.), documentado y previamente validado con corridas reales. Artefacto actual desactualizado — `GRAPH_COVERAGE_GAP` de vigencia, no de diseño; debe refrescarse (`audit`) antes de usarse para impact analysis en la migración real.

## 23. Technical Debt

Ver deuda específica de esta auditoría en el Gap Matrix (§24). Deuda general del proyecto ya está cubierta por la serie `AUDITORIA/01-33_*.md` existente — fuera de alcance de esta auditoría white-label, no duplicada aquí.

## 24. Gap Matrix

Matriz completa de acoplamiento y matriz de gaps con prioridad P0-P4: [WHITE_LABEL_GAP_MATRIX.md](WHITE_LABEL_GAP_MATRIX.md).

## 25. Risk Matrix

Riesgo/blast-radius/rollback/downtime por fase futura: [WHITE_LABEL_MIGRATION_ROADMAP.md](WHITE_LABEL_MIGRATION_ROADMAP.md) Fase 46.

## 26. Migration Strategy

LEGACY → ADAPTER → NEW CONFIG → DEPRECATION → REMOVAL. Nunca eliminar configuración actual sin este camino. Disciplina de 10 pasos por fase (baseline→checkpoint) en Fase 38 del roadmap.

## 27. Phase Roadmap

F0 (este audit) → F1 Identity → F2 Business Profile → F3 Modules → F4 Theme → F5 Content Legal → F6 Runtime Config → F7 Frontend → F8 Dashboard → F9 Hardcoding removal → F10 Business Profile Sintel (snapshot) → F11 Segundo negocio de prueba ("Zapatería Nova") → F12 Certificación white-label → F13 Gate de decisión multi-tenancy. Detalle completo: [WHITE_LABEL_MIGRATION_ROADMAP.md](WHITE_LABEL_MIGRATION_ROADMAP.md) Fase 45.

## 28. Compatibility Strategy

Ver §26 — ningún endpoint/contrato actual se rompe sin adapter; todo cambio es aditivo primero.

## 29. Rollback Strategy

Cada fase F1-F13 es reversible individualmente (commits pequeños, feature flags apagados por defecto). La única fase con reversibilidad limitada una vez publicada es F5 (contenido legal) — requiere validación legal humana antes de publicar, no solo revert de código.

## 30. Business A / Current Configuration (Sintel)

Antes de tocar identidad visible, capturar snapshot `BUSINESS_PROFILE_SINTEL` (logo, colores, contenido, SEO, datos legales — incluyendo resolver el placeholder de razón social con el negocio real, dominios, navegación, los 4 módulos activos hoy). Detalle: Fase 39 del roadmap.

## 31. Business B / Zapatería Test

Perfil hipotético "Zapatería Nova" (Shop: zapatos/botas/sandalias; Services: limpieza/restauración/cambio de suela/cambio de tacón; Renting: zapatos para eventos/accesorios), configurado con los mismos modelos que Business A, sin tocar producción. Criterio de aceptación de F11. Detalle: Fase 40 del roadmap.

## 32. Multi-Tenancy Decision

**Diferida.** Opción A (una instalación por negocio) confirmada como estado por defecto; Opción B (multi-tenant) solo si aparece un requisito de negocio concreto, reevaluada en F13. Justificación completa: [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md) Decisión 2.

## 33. Success Criteria

Las 15 preguntas de la Fase 47 respondidas con evidencia en [WHITE_LABEL_READINESS_AUDIT.md](WHITE_LABEL_READINESS_AUDIT.md).

## 34. Final Recommendation

**Migrar el proyecto actual (Opción A).** Empezar por F1 (Identity) y, en paralelo dada su independencia, planificar F5 (contenido legal) ya que requiere involucrar a alguien con autoridad sobre el contenido legal real del negocio (no es una tarea puramente técnica). No introducir multi-tenancy todavía. No crear una app `business` nueva — extender `organization`. No reconstruir el router ni el Design System — extenderlos.

---

## Checkpoint final

**VIABILITY:** MEDIUM-HIGH — viable con bloqueadores concretos y acotados, no arquitectónicos.

**CURRENT_READINESS:** ≈47/100 (cálculo transparente en [WHITE_LABEL_READINESS_AUDIT.md](WHITE_LABEL_READINESS_AUDIT.md))

**MAIN BLOCKERS:**
1. Contenido legal (T&C/Privacidad) 100% hardcodeado a "Sintel" en `frontend/src/components/auth/kyc/legalDocs.js`, sin modelo, con placeholder sin resolver.
2. Prompt del chatbot de soporte (`ai_engine/action_graph.py:383,680`) hardcodea "asistente de Sintel (Colombia)".
3. Theming 93% hardcoded en hex, sin `ThemeConfig` backend ni inyección runtime.
4. `organization` (SSoT de identidad) sin UI de panel — inaccesible para un admin no-técnico.
5. Router sin flags de activación por módulo/vertical.

**MAIN STRENGTHS:**
1. `organization` — SSoT de identidad con disciplina de acceso única, ya documentada y exigida.
2. `core` — 7/9 grupos de modelo genéricos por esquema, API dinámica y cacheada.
3. Casi nula dependencia de reglas de negocio del rubro de seguridad electrónica (1 archivo real de 10 módulos).
4. Arquitectura de runtime-config del frontend (site-config/home-feed/footer) ya funcional y reutilizable.
5. Dashboard BFF con patrón Orchestrator consistente en ~40 secciones ya configurables.
6. Documentación/gobernanza fuerte (.AGENT/CLAUDE.md por app) y Knowledge Graph operativo (aunque desactualizado).

**MAIN RISKS:**
1. F5 (contenido legal) tiene implicaciones legales reales, no solo técnicas — requiere validación humana externa.
2. Blast radius grande en F7 (frontend) por volumen de hex hardcoded (~3100 ocurrencias).
3. Dos stacks Docker activos simultáneamente (dev + prod) — cualquier cambio de infraestructura debe evitar impactar `sintel_prod_*`.
4. Trabajo preexistente sin commitear en el branch actual (~710 líneas) — cualquier fase de migración real debe coordinarse para no mezclarse con ese trabajo en curso.

**RECOMMENDED OPTION:** MIGRATE CURRENT PROJECT.

**WHY:** Score medio (no bajo), sin bloqueadores arquitectónicos, backend ya reusable en un 55-65% por capa, ningún dato inseparable, alto costo/riesgo de reescribir desde cero módulos de negocio ya maduros (pricing engines, Service Layer, AI Engine).

**FIRST IMPLEMENTATION PHASE:** F1 — Identity (quitar default `'Sintel'` de `Company.trade_name`, consolidar el fallback duplicado en una sola constante, resolver el placeholder de razón social con el negocio real antes de tocar `legalDocs.js`).

**EXPECTED MIGRATION ORDER:** F1 Identity → F2 Business Profile → F3 Modules → F4 Theme → F5 Content Legal → F6 Runtime Config → F7 Frontend → F8 Dashboard → F9 Hardcoding removal → F10 Snapshot Sintel → F11 Zapatería Nova → F12 Certificación → F13 Gate multi-tenancy.

---

**Nota de sincronización documental (Fase 62):** Esta auditoría es exclusivamente diagnóstico + diseño de arquitectura + roadmap. No se modificó código, modelos, migraciones, API, frontend, branding, ni se eliminó ninguna referencia existente. Los documentos canónicos de arquitectura de producción (`Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` y los `.AGENT` docs por app) no fueron modificados; se registró `DOCUMENTATION_DRIFT` donde el prompt maestro asumía nombres de archivo que no coinciden con los reales (ver [WHITE_LABEL_BASELINE.md](WHITE_LABEL_BASELINE.md)).
