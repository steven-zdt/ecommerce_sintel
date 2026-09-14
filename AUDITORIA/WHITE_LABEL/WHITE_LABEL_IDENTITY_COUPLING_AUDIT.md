# WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md
Fase 1 — Inventario de identidad empresarial

Solo lectura. Evidencia recolectada por grep dirigido + lectura de código (no exhaustivo carácter por carácter — ver nota de alcance en [WHITE_LABEL_BASELINE.md](WHITE_LABEL_BASELINE.md)).

## Resumen por categoría

| Categoría | Hallazgos aprox. | Archivos principales |
|---|---|---|
| IDENTITY | ~60+ | `frontend/src/components/auth/kyc/legalDocs.js` (29), `Sidebar.vue`, `useSeoStructuredData.js`, `CustomerFooter.vue`, `ai_engine/action_graph.py` |
| TECHNICAL_DEFAULT | 3 | `organization/models.py` (`Company.trade_name` default), `core/api/views.py:158`, `dashboard/api/views.py:2489`, `frontend/store/appConfig.js` |
| INFRASTRUCTURE | ~90 | `docker-compose.yml`/`.prod.yml`, `nginx.prod.conf`, `nginx-common.conf`, `.env.production.example` |
| BUSINESS_DATA | bajo (solo seeds) | `organization/migrations/0004_seed_domain_settings.py`, `core` `seed_renting_home_cards`, `seo/migrations/0002_seed_meta_business_verification.py` |
| DOCUMENTATION | muy alto (cientos) | `.AGENT/docs/*.md`, `AUDITORIA/*.md`, `Documentacion/*.md` — nomenclatura de repo, no comportamiento en runtime |
| TEST_DATA | bajo | `ai_provider/tests*.py`, `organization/tests.py`, `dashboard/tests.py`, `users/tests.py` |
| UNKNOWN (nombres, no marca) | decenas | `SintelBaseModel`, `SintelOffcanvas.vue`, `SintelArchitectureGuard` — nombres de clase/componente, no fugas de marca al cliente |
| BUSINESS_RULE (lógica real del rubro seguridad) | ~0 confirmados | Ninguna regla de negocio encontrada que dependa de CCTV/vigilancia/alarmas — las menciones son ejemplos de docstring o texto de ayuda, no gating de lógica |

## Hallazgos más preocupantes (hardcoded, requieren editar código)

1. **`organization/models.py:48`** — `Company.trade_name` default `'Sintel'` a nivel de columna DB. HARDCODED (default de campo), no bloqueante por sí solo porque es editable, pero es el origen de varios fallbacks duplicados aguas abajo.
2. **`frontend/src/components/auth/kyc/legalDocs.js`** — 29 apariciones literales de "Sintel" dentro de Términos, Privacidad y Garantía. Incluye un placeholder sin resolver: `razonSocial: 'Sintel Corp [PENDIENTE: razon social exacta segun Camara de Comercio]'`. **Sin modelo de datos detrás — contenido legal 100% hardcodeado en JS.** Ver detalle en [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md).
3. **`frontend/src/composables/useSeoStructuredData.js`** — "Sintel" hardcodeado en 4 lugares para JSON-LD (`og:site_name`, `schema.org name`), independiente de `organization.Branding`/`SeoSettings`, que ya existen para este propósito.
4. **`frontend/src/components/layout/Sidebar.vue`, `CustomerAuthLayout.vue`, `AdminAuthLayout.vue`, `FooterCTA.vue`, `CustomerFooter.vue`** — literales `"Sintel Panel"`, `"Sintel UI"`, `"Sintel Technology"`, `"© {{year}} Sintel Ecosystem"` en templates Vue, **sin ningún lookup a un modelo de branding** — no es un fallback, es la única salida posible hoy.
5. **`ai_engine/action_graph.py:383,680`** — prompt del sistema del **chatbot de soporte al cliente** (no la herramienta de ingeniería): `"Eres el asistente de Sintel..."`, `"...atencion al cliente de Sintel (Colombia)..."`. No consulta `organization.Company`/`ContactInfo`. Riesgo real: el bot afirmará ser de "Sintel" aunque el tenant sea otro negocio — mismo patrón de riesgo que el hallazgo previo de fabricación de horarios de tienda (ver memoria `project_support_agent_separation_plan`).
6. **`ai_engine/chains.py`/`chains_frontend.py`, `ai_editor/generation/prompts.py`, `ai_editor/intent/prompts.py`** — prompts del "Engineering Agent" (herramienta de desarrollo interna, no cara al cliente) también hardcodean "Sintel". Riesgo bajo — no afecta al negocio en producción, pero si el codebase se reutiliza como plantilla, estos también necesitan actualizarse.
7. **Infraestructura** (`docker-compose*.yml`, `nginx.prod.conf`, `nginx-common.conf`, `.env.production.example`) — dominios `sintel.net.co`/`panel.sintel.net.co`/`api.sintel.net.co`, nombres de contenedor `sintel_prod_*`, `DB_NAME=sintel_ecommerce`, `noreply@sintel.net.co`. **Esperado y aceptable** — la infraestructura se redespliega por instalación; no es un defecto de arquitectura de aplicación, es costo operativo de despliegue (editar ~6 archivos por tenant nuevo).
8. **`core/api/views.py:158`** y **`dashboard/api/views.py:2489`** — ambos hardcodean `'Sintel'` como fallback final cuando `Company` no tiene fila activa — literal duplicado en dos lugares en vez de una constante/config compartida.
9. **`seo/templatetags/seo_tags.py`** — `DEFAULT_TITLE = 'Sintel | E-Commerce Ecosystem'`, `DEFAULT_DESCRIPTION` (copy específico del negocio), y otro fallback `or 'Sintel'` para `site_name`.
10. **`frontend/index.html`** — shell estático de la SPA: `<title>Sintel | E-Commerce Ecosystem</title>` y spinner de carga "Sintel"/"Cargando ecosistema inteligente...". Es lo que ven los crawlers y el primer pintado antes de que cargue el JS.
11. **`organization/migrations/0004_seed_domain_settings.py`**, **`core` `seed_renting_home_cards`** (dentro de `0001_initial_squashed_...py`), **`seo/migrations/0002_seed_meta_business_verification.py`** — datos sembrados en migraciones (no constantes de código) con valores reales de producción: dominios `sintel.net.co`, tarjetas de inicio nombrando marcas del rubro seguridad (Hikvision, Dahua, Ubiquiti, Cisco, Dell, APC) y textos como "CCTV, control perimetral y monitoreo", y un código real de verificación de Meta Business Suite. Cualquier instalación nueva desde este código hereda estos datos hasta que alguien los borre manualmente.

## Buenas noticias — identidad ya aislada

- **`organization` es una SSoT real**: `Company`, `Branding` (logo/favicon/tagline como `ImageField`, sin ruta hardcodeada), `ContactInfo`, `SocialLink`, `EmailSettings`, `DomainSettings`, `SeoSettings`, `LegalEntityInfo` — todos singleton, editables vía API/admin, con regla documentada en `organization/CLAUDE.md`: "nadie consulta los modelos directamente, todo pasa por `OrganizationSelector`".
- **`logo_sintel.png`** (raíz del repo) — **cero referencias en código** (grep sin resultados fuera del propio archivo). Es un activo huérfano, no cableado a ningún render de marca. El logo real es un `ImageField` en `Branding.logo`.
- **Ninguna regla de negocio real** depende de términos de CCTV/vigilancia/Hikvision/Dahua/alarmas — ni en flujo de pedidos, ni pricing, ni permisos. Un `FeatureBannerSection` incluso documenta explícitamente en su docstring que es reutilizable "para cualquier proposito comercial (Seguridad Electronica, Marketplace, IA...)".
- Catálogo/pricing de `technical_services` es agnóstico de dominio — "CCTV" aparece una sola vez, en un docstring de ejemplo, no en un `choices=` de campo.
- `ai_engine` confirmado con **cero imports** de `project_knowledge_graph` — el desacoplamiento previo (memoria `project_knowledge_graph_fase0_full_decoupling`) sigue intacto.

## Respuesta explícita: ¿existe un fallback hardcodeado `"Sintel"` cuando no hay datos de marca?

Sí, en tres niveles distintos:

1. **Default de campo en DB**: `organization/models.py:48` — `Company.trade_name` cae en `'Sintel'` si nadie lo configura.
2. **Fallback en runtime del frontend**: `frontend/store/appConfig.js` (estado inicial y `reset()`: `{ site_name: 'Sintel', logo: null, tagline: '', uuid: null }`) y `RentalDetailView.vue:441` (`detail.value.hero.brand_name || 'Sintel'`) — se activa cuando la API falla o el dato falta.
3. **Sin ningún lookup a modelo, ni siquiera como fallback**: la mayoría de plantillas Vue (Sidebar, layouts de auth, footer, documentos legales) simplemente hardcodean "Sintel" sin ninguna ruta de código que pudiera mostrar otro nombre — esto es más profundo que un fallback, es ausencia total de mecanismo de configuración en esos puntos.
