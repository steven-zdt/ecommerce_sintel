# WHITE_LABEL_READINESS_AUDIT.md
Fase 23, 24 — Score de viabilidad y bloqueadores

Solo lectura. Este documento consolida el score numérico y la lista de bloqueadores priorizados; el detalle de evidencia por área está en los documentos hermanos (ver índice al final).

> **CORRECCIÓN (2026-08-14):** el bloqueador P1 #4 ("`organization` sin UI de panel") de este
> documento era incorrecto — `/panel/organizacion` ya existía. Se remedió/corrigió como parte
> de F1/F2 del roadmap de migración; ver nota completa en
> [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md). El score
> ≈47/100 no se recalculó tras la corrección (el peso de ese hallazgo específico dentro de
> "Identity Separation"/"Module Configuration" era menor al de los hardcodes reales de
> frontend/AI, que siguen siendo los bloqueadores dominantes) — tratar el número como
> aproximado, no como recalculado con precisión post-corrección.

## Cálculo del ARCHITECTURAL_READINESS_SCORE (0-100)

Cada categoría se puntuó 0-100 con evidencia de los documentos de auditoría (no inventado). Metodología: 0 = capa completamente hardcoded/inexistente, 100 = totalmente config-driven de punta a punta (no solo "existe el modelo", sino que efectivamente se usa en todas las superficies relevantes).

| Categoría | Peso | Score | Ponderado | Evidencia resumida |
|---|---|---|---|---|
| Identity Separation | 15% | 35 | 5.25 | Modelo `organization.Company`/`Branding` sólido, pero ~65 strings frontend con CERO lookup a modelo (no fallback, ausencia total), 3 fallbacks `'Sintel'` duplicados en backend, prompt de chatbot hardcodeado |
| Core Configuration | 10% | 65 | 6.50 | 7/9 grupos de modelo `core` son GENERIC/CONFIGURABLE; penalizado por seed de contenido real de marca de terceros y 1 fallback hardcoded |
| Frontend Runtime | 15% | 40 | 6.00 | Arquitectura de runtime-config real (site-config/home-feed/footer) pero fallback silencioso a "Sintel", ~95 strings hardcoded, sin theming runtime |
| Module Configuration | 10% | 60 | 6.00 | ~40 secciones de dashboard ya son BUSINESS_CONFIGURATION; penalizado por falta de flags de módulo en el router y por `quotes` (14/32 acoplamiento) |
| Theme System | 10% | 15 | 1.50 | Sin `ThemeConfig` backend; ratio 14:1 hex-hardcoded vs. CSS vars; sin inyección runtime |
| Content System | 10% | 55 | 5.50 | CMS de Home/Footer/Navbar/AboutUs/BrandSlider sólido; penalizado por contenido legal 100% hardcoded (tratado aparte pero afecta esta capa) y `index.html` estático |
| Domain Configuration | 5% | 30 | 1.50 | `DomainSettings` existe pero cero consumidores reales; config real vive estática en 6 archivos de infra |
| Business Rules Isolation | 10% | 60 | 6.00 | Acoplamiento de reglas de negocio real es bajo en 9 de 10 módulos; penalizado por `LaborConditionsEvaluator` hardcoded en `quotes` y sesgo de `technical_services`/`renting` |
| Data Isolation | 10% | 45 | 4.50 | Sin `tenant_id` (aceptable, ver Fase 43), pero penalizado por seeds con datos reales de producción/terceros horneados en migraciones |
| Documentation / Governance | 5% | 75 | 3.75 | `.AGENT`/`CLAUDE.md` por app, patrón selector/commands documentado y exigido, Knowledge Graph operativo; penalizado por `DOCUMENTATION_DRIFT` frente al prompt maestro |
| **TOTAL** | **100%** | — | **≈ 46.5 / 100** | |

## ARCHITECTURAL_READINESS_SCORE: **~47/100 → VIABILIDAD MEDIA (MEDIUM)**

No es LOW: no hay ningún hallazgo que indique imposibilidad técnica (ver comparación Opción A vs B en [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md)). No es HIGH: hay bloqueadores reales P0 que impiden hoy mismo declarar el sistema white-label. El patrón dominante es "la arquitectura backend está mejor preparada que el frontend/contenido" — `organization` y `core` son fundaciones utilizables; los bloqueadores más duros (legal, prompt de IA, theming) están concentrados en el frontend y en un archivo de AI engine.

## Bloqueadores clasificados

### P0 — BLOCKER (impide declarar arquitectura white-label)

1. **`frontend/src/components/auth/kyc/legalDocs.js`** — Términos/Privacidad/Garantía 100% hardcodeados a "Sintel", sin modelo de datos, con placeholder de razón social sin resolver. Es contenido legalmente vinculante que el usuario debe aceptar para registrarse — un tenant nuevo estaría haciendo aceptar a sus clientes los términos de otra empresa.
2. **`ai_engine/action_graph.py:383,680`** — el chatbot de soporte al cliente en producción afirma textualmente ser "el asistente de Sintel... atencion al cliente de Sintel (Colombia)", sin derivar de `organization`. Riesgo de afirmaciones falsas al cliente, mismo patrón que llevó a la separación Support/Engineering Agent documentada en memoria de sesión previa.

### P1 — CRITICAL (requiere migración antes de producción white-label)

3. Theme System inexistente en backend + ratio 14:1 hex-hardcoded en frontend — cambiar de paleta requiere edición manual masiva.
4. `organization` (SSoT de identidad) sin UI de panel — un admin no-técnico no puede hoy editar Company/Branding/LegalEntityInfo/SEO/Domain.
5. Fallbacks y textos hardcoded sin ningún lookup a modelo en componentes frontend clave (Sidebar, AuthLayout, Footer copyright, `useSeoStructuredData.js`).
6. Seed de datos `seed_renting_home_cards` en `core` inyecta contenido/marcas de terceros del rubro seguridad en cada instalación nueva.
7. Router sin mecanismo de activar/desactivar módulos — todas las verticales están permanentemente compiladas.

### P2 — MAJOR (deuda relevante)

8. Fallback `'Sintel'` duplicado en 3 archivos backend en vez de una constante.
9. `LaborConditionsEvaluator` (quotes) hardcoded sin configuración admin.
10. `core.enums` sesgado a mercado colombiano y taxonomía de roles específica.
11. `index.html` con `<title>`/spinner estático.
12. `DomainSettings` sin consumidores reales (documentar o conectar).
13. Seed real de código de verificación Meta Business en `seo`.

### P3 — MINOR (mejora posterior)

14. Acceso directo residual `dashboard`→`organization.SocialLink` (2 puntos).
15. Placeholders de texto sesgados al rubro seguridad en `shop`/`technical_services`/`renting` (solo texto de ayuda).
16. `logo_sintel.png` huérfano — limpieza.

### P4 — OPTIONAL (futuro)

17. Refrescar artefacto del Knowledge Graph antes de usarlo para impact analysis real.
18. Decisión de multi-tenancy — explícitamente diferida, ver Fase 43.

## Respuestas a los 15 criterios de éxito de la Fase 47

1. **¿Es viable transformar el proyecto actual?** Sí — ningún hallazgo indica imposibilidad técnica ni datos inseparables.
2. **¿Qué porcentaje ya es reusable?** ≈47% ponderado (score arriba); por capa, `core`/`organization`/módulos de negocio están 55-65% listos, frontend de contenido/theme está 15-40%.
3. **¿Qué está atado a Sintel?** Legal docs, prompt del chatbot, ~95 strings frontend, seeds de contenido en `core`/`seo`, defaults de campo/fallback en backend. Ver [WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md](WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md).
4. **¿Qué debe extraerse a configuración?** Contenido legal, prompt de IA, paleta de colores, flags de módulo por ruta, defaults de `FooterCTAConfig`.
5. **¿Qué debe permanecer como capacidad de plataforma?** Modelos `core`/`organization`, Service Layer/Commands/Selectors, Design System (estructura, no valores), Home Builder, patrón BFF del dashboard, motor de pricing genérico de cada módulo.
6. **¿Organization ya puede ser la base de Business Identity?** Sí, en modelo de datos y disciplina de acceso; no, en superficie de administración (falta UI de panel) y en defaults (siguen siendo los de Sintel).
7. **¿Core puede evolucionar sin ser reconstruido?** Sí — 7/9 grupos de modelo ya son genéricos; requiere limpieza de seeds y defaults, no rediseño de esquema.
8. **¿Frontend puede consumir Business Runtime Config?** Parcialmente — ya lo hace para Home/Footer/Navbar; falta extenderlo a legal, tema, y a los ~95 puntos hardcoded identificados.
9. **¿El Design System soporta Theme Runtime?** No hoy — existe una capa de tokens CSS pero es estática, sin inyección desde backend.
10. **¿Shop/Services/Renting pueden operar con distintos datos?** Sí — sus modelos y catálogos ya son datos de DB, no código; scores de acoplamiento 6, 11, 9 sobre 32 respectivamente, dominados por content/workflow coupling menor, no por identity/route coupling.
11. **¿Qué módulos tienen business coupling fuerte?** `quotes` (14/32) por `LaborConditionsEvaluator`; `technical_services` (11/32) por naming/altura; `renting` (9/32) por campos de instalación física.
12. **¿Qué archivos son más peligrosos?** `frontend/src/components/auth/kyc/legalDocs.js`, `ai_engine/action_graph.py`, `core` seed migration `seed_renting_home_cards`, `frontend/index.html`.
13. **¿Cuál es el blast radius?** Alto en frontend (cientos de archivos con hex hardcoded) y bajo-medio en backend (cambios concentrados en pocos archivos: `organization`, `core/api/views.py`, `ai_engine/action_graph.py`). Ver detalle de riesgo por fase en [WHITE_LABEL_MIGRATION_ROADMAP.md](WHITE_LABEL_MIGRATION_ROADMAP.md).
14. **¿Debe introducirse multi-tenancy ahora o después?** Después — ver Fase 43 / Gate de decisión en el master plan. Nada en esta auditoría sugiere que se necesite antes de tener un solo Business Profile funcionando.
15. **¿Debe crearse un proyecto nuevo?** No — ver comparación completa en [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md).

## Índice de documentos de esta auditoría

- [WHITE_LABEL_BASELINE.md](WHITE_LABEL_BASELINE.md) — Fase 0
- [WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md](WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md) — Fase 1
- [WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md](WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md) — Fase 2-3
- [WHITE_LABEL_FRONTEND_AUDIT.md](WHITE_LABEL_FRONTEND_AUDIT.md) — Fase 4,5,12-14,16
- [WHITE_LABEL_MODULE_AUDIT.md](WHITE_LABEL_MODULE_AUDIT.md) — Fase 6,7,15,23
- [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md) — Fase 8,17-21
- [WHITE_LABEL_GAP_MATRIX.md](WHITE_LABEL_GAP_MATRIX.md) — Fase 22,59
- WHITE_LABEL_READINESS_AUDIT.md (este documento) — Fase 23-24
- [WHITE_LABEL_ARCHITECTURE_TARGET.md](WHITE_LABEL_ARCHITECTURE_TARGET.md) — Fase 25-29
- [WHITE_LABEL_MIGRATION_ROADMAP.md](WHITE_LABEL_MIGRATION_ROADMAP.md) — Fase 30-46
- [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md) — Fase 43,56,60
- [WHITE_LABEL_TRANSFORMATION_MASTER_PLAN.md](WHITE_LABEL_TRANSFORMATION_MASTER_PLAN.md) — documento ejecutivo
