# WHITE_LABEL_GAP_MATRIX.md
Fase 22, 59 — Matriz de acoplamiento y matriz de gaps

Solo lectura. Estados: READY / PARTIAL / GAP / BLOCKED / LEGACY. Acoplamiento: GENERIC / CONFIGURABLE / BUSINESS_COUPLED / CRITICAL.

## Matriz global de acoplamiento

| Área | Generic | Configurable | Business Coupled | Critical |
|---|---|---|---|---|
| Identity (marca/nombre) | Modelo `organization.Company`/`Branding` | Vía API/admin | Defaults 'Sintel' duplicados en 3 archivos backend | ~65 strings frontend sin ningún lookup a modelo |
| Organization (app) | Selector/Commands pattern | 8 ViewSets API | Seeds con datos reales de prod (dominios, email) | Sin UI de panel — inaccesible para un admin no-técnico |
| Core | 7 de 9 grupos de modelo | API home-feed/footer/about-us dinámica | `FooterCTAConfig` defaults de marca, `enums` sesgado a Colombia | Seed `seed_renting_home_cards` inyecta marcas de terceros del rubro seguridad |
| Frontend (router/layout) | HomeView/HomeRenderer | Navbar/Footer vía site-config/footer API | ~35 rutas hardcoded sin flag por módulo | Ninguno individual, pero acumulativo con Theme |
| Dashboard | Patrón BFF/Orchestrator limpio | ~40 secciones ya BUSINESS_CONFIGURATION | — | `organization` no cableada al panel |
| Shop | Catálogo casi agnóstico | Total vía dashboard | Placeholder de ayuda sesgado | — |
| Services (technical_services) | Motor de pricing genérico | Total vía dashboard | Naming de paquetes/altura sesgado a instalación | — |
| Renting | FSM genérica | Total vía dashboard | Campos de instalación física | — |
| Quotes | Constructor de cuestionario configurable | Total vía dashboard | — | `LaborConditionsEvaluator` hardcoded, sin config |
| Orders/Payment/Support/Marketing/Notifications/Operations | Genéricos en su mayoría | Total vía dashboard | Wompi/COP hardcoded en `payment` | — |
| AI / RAG (soporte al cliente) | Mecanismo RAG/ingesta | Perfiles de agente por YAML | — | Prompt del chatbot hardcodea "Sintel"/Colombia |
| AI / RAG (Engineering Agent) | — | — | Prompts hardcodean "Sintel" (dev-tool, no producción) | — |
| Knowledge Graph | CLI capaz (app-summary/data-flow/impact) | — | — | Artefacto desactualizado (`GRAPH_COVERAGE_GAP`) |
| Theme System | — | 25 CSS vars en 1 archivo | ~3100 hex hardcoded vs 220 `var()` (14:1) | Sin `ThemeConfig` backend, sin inyección runtime |
| Content System (CMS) | Home/Footer/Navbar/AboutUs/BrandSlider/FeatureBanner | Total vía dashboard | `index.html` shell estático | — |
| Domain Configuration | Modelo `DomainSettings` existe | — | — | Cero consumidores del modelo; 6 archivos infra hardcoded, edición manual por deploy |
| SEO | App `seo` + `organization.SeoSettings`, dinámico por página vía `useSeo.js` | — | `index.html` title/spinner estático | — |
| Legal / Contact (metadata) | `LegalEntityInfo`/`ContactInfo` cubren razón social/NIT/dirección/tel/correo/repr. legal/dominios | — | — | — |
| Legal (contenido T&C/Privacidad) | — | — | — | 100% hardcoded en `legalDocs.js`, sin modelo, placeholder sin resolver |
| Infraestructura (nginx/docker/env) | — | — | Esperado por diseño (redeploy por tenant) | — |
| Documentación / Gobernanza | `.AGENT`/`CLAUDE.md` por app, KG documentado | — | `DOCUMENTATION_DRIFT`: nombres de doc del prompt maestro no coinciden con archivos reales | — |

## Matriz de gaps con prioridad

| Área | Estado | Acoplamiento | Acción | Prioridad |
|---|---|---|---|---|
| Documentos legales (T&C/Privacidad) | BLOCKED | CRITICAL | Crear modelo de contenido legal versionado en `organization` (o nueva tabla ligada), migrar `legalDocs.js` a consumirlo, resolver placeholder de razón social | **P0** |
| Prompt del chatbot de soporte (`ai_engine/action_graph.py`) | GAP | CRITICAL | Reemplazar literal "Sintel"/Colombia por interpolación desde `OrganizationSelector` | **P0** |
| Theme System (colores) | GAP | CRITICAL | Diseñar `ThemeConfig` backend + tokens CSS runtime; migración incremental de hex a `var()` | **P1** |
| Dashboard UI para `organization` | GAP | BUSINESS_COUPLED | Envolver `organization` en el patrón BFF de `dashboard`, construir `/panel/organizacion` completo | **P1** |
| Fallbacks/textos hardcoded en frontend (Sidebar, AuthLayout, Footer copyright, `useSeoStructuredData.js`) | GAP | BUSINESS_COUPLED | Reemplazar por lookup a `appConfigStore`/`organization`, eliminar fallback silencioso a "Sintel" | **P1** |
| Seed `seed_renting_home_cards` (core) | LEGACY | CRITICAL (dato, no código) | Nueva migración que vacíe/neutralice el contenido sembrado, o mover a fixture opcional de demo | **P1** |
| Router sin flags por módulo | GAP | BUSINESS_COUPLED | Diseñar Module Registry con enable/disable consumido por guards de router | **P1** |
| Fallback duplicado `'Sintel'` (`core/api/views.py`, `dashboard/api/views.py`, `seo_tags.py`) | LEGACY | CONFIGURABLE | Consolidar en una sola constante/config neutral | **P2** |
| `LaborConditionsEvaluator` hardcoded (quotes) | GAP | BUSINESS_COUPLED | Externalizar umbrales/labels a configuración admin | **P2** |
| `core.enums` sesgado a mercado colombiano/roles específicos | PARTIAL | BUSINESS_COUPLED | Evaluar si debe ser configurable por instalación o documentarse como supuesto de plataforma aceptado | **P2** |
| `index.html` title/spinner estático | GAP | CONFIGURABLE | Server-render o post-build inyección desde `organization.SeoSettings` | **P2** |
| `DomainSettings` sin consumidores reales | PARTIAL | CONFIGURABLE | Documentar como registro informativo o conectar a scripts de generación de config de infra | **P2** |
| Seed real de verificación Meta Business (`seo`) | LEGACY | BUSINESS_COUPLED (dato) | Nueva migración que limpie el valor sembrado | **P2** |
| Acceso directo residual `dashboard`→`organization.SocialLink` | LEGACY | CONFIGURABLE | Migrar a `OrganizationSelector.get_social_link_by_uuid()` | **P3** |
| Placeholders de texto sesgados (`shop`, `technical_services`, `renting`) | PARTIAL | CONFIGURABLE | Cambiar copy de ayuda, sin impacto funcional | **P3** |
| `logo_sintel.png` huérfano | READY (no-issue) | GENERIC | Eliminar archivo sin uso (limpieza, no bloqueante) | **P3** |
| Artefacto de Knowledge Graph desactualizado | PARTIAL | — | Ejecutar `audit` antes de usarlo para impact analysis real | **P4** |
| Multi-tenancy / `tenant_id` | N/A (decisión diferida) | — | No implementar aún — ver Fase 43 en el master plan | **P4** |
