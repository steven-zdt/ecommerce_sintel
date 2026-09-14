# WHITE_LABEL_CORE_ORGANIZATION_AUDIT.md
Fase 2 y 3 — Auditoría de `organization` y `core`

Solo lectura.

> **CORRECCIÓN (2026-08-14, durante ejecución de F1/F2 del roadmap):** este documento y sus
> hermanos ([WHITE_LABEL_MODULE_AUDIT.md](WHITE_LABEL_MODULE_AUDIT.md),
> [WHITE_LABEL_READINESS_AUDIT.md](WHITE_LABEL_READINESS_AUDIT.md),
> [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md)) afirmaban que
> `organization` **no tenía UI de panel** y que el sidebar/frontend no la consumía. Es
> **incorrecto** — al leer `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`
> (paso obligatorio antes de modificar código, que el barrido de grep automático de la
> auditoría inicial se saltó) se confirmó que `/panel/organizacion` con
> `OrganizationView.vue` (8 tabs, uno por agregado) existe desde 2026-07-12, está en el
> sidebar ("Empresa e Institucional") y consume los 8 ViewSets de `organization/api/views.py`
> directamente (montados en `/api/v1/organization/`, fuera del patrón BFF de `dashboard` por
> decisión deliberada documentada, no por omisión). La sección §1.4 de abajo queda corregida
> en el punto 5; el resto del documento (defaults hardcoded, seeds, duplicación de fallback)
> sigue siendo correcto y ya fue remediado en F1/F2 del roadmap de migración. Lección para
> futuras auditorías: verificar contra el `.AGENT/docs` de cada app antes de reportar
> ausencia de una feature, no solo contra resultados de grep del frontend.

## Parte 1 — `organization` (Business Identity hub candidato)

### 1.1 Inventario de modelos

| Modelo | Campos clave | ¿Default específico de negocio? | Acceso |
|---|---|---|---|
| `Company` | trade_name, description, founded_year, is_active | **Sí** — `trade_name` default `'Sintel'` | `OrganizationSelector.get_company()` |
| `Branding` | logo, favicon, tagline, is_active | No | `get_branding()` |
| `ContactInfo` | phone, email, address, working_hours, is_active | No | `get_contact_info()` |
| `SocialLink` | platform, url, icon_class, display_order, is_active (no singleton) | No | `list_social_links()`, `get_social_link_by_uuid()` |
| `EmailSettings` | default_from_email, frontend_base_url, admin_login_url, is_active | No default de campo, pero **sembrado** con valor real (`sintel.technology@gmail.com`) en `migrations/0002_seed_email_settings.py` | `get_email_settings()` (cacheado) |
| `DomainSettings` | primary_domain, admin_panel_domain, api_domain, is_active | No default de campo, pero **sembrado** con `sintel.net.co`/`panel.sintel.net.co`/`api.sintel.net.co` en `migrations/0004_seed_domain_settings.py` | `get_domain_settings()` |
| `SeoSettings` | meta_title, meta_description, og_image, is_active | No | `get_seo_settings()` |
| `LegalEntityInfo` | legal_name, tax_id, fiscal_address, legal_representative, city, department, is_active | No | `get_legal_entity_info()` |
| `CommunicationEvent` | event_type, channel, module, user, metadata (log append-only) | N/A | `log_communication_event()` |

Todos los singleton usan `SingletonMixin` + `UniqueConstraint` parcial (corregida 2026-08-01 por condición de carrera). Patrón de acceso único documentado explícitamente en `organization/CLAUDE.md`: *"nadie consulta los modelos directamente… toda lectura pasa por OrganizationSelector."* API: 8 `ViewSet`s en `organization/api/views.py`, todos `IsAdminUser` salvo `CommunicationEventViewSet` (público, throttled). Integraciones (tokens Meta/YouTube/TikTok/X/Google Business) deliberadamente fuera de DB, en `.env`, expuestas solo como dict de solo-lectura vía `get_integration_settings()`.

### 1.2 Acceso cruzado desde otras apps

| Origen | Qué hace | Clasificación |
|---|---|---|
| `notifications/tasks.py`, `accounts/services/commands.py`, `users/services/commands.py`, `users/api/admin_auth.py`, `quotes/services/pdf_service.py`, `core/api/views.py`, `core/services/commands.py`, `seo/templatetags/seo_tags.py`, `marketing/channels/*.py` (8 archivos) | `OrganizationSelector.get_*()` | **VALID** |
| `dashboard/api/views.py:2339-2373` (`AdminFooterViewSet`) | `from organization.models import SocialLink; SocialLink.objects.filter(...)` | **DIRECT_ACCESS** — bypass documentado como puente legacy hasta que el frontend migre del contrato combinado nav+social |
| `dashboard/api/views.py:2489` (`AdminSiteBrandViewSet`) | `company.trade_name if company else 'Sintel'` | **DIRECT_ACCESS / violación menor** — duplica el mismo literal `'Sintel'` que ya es default del modelo |
| `core/migrations/0001_initial_squashed_...py:37-52` | `Company.objects.create(...)`, etc. | **VALID** (migración de datos histórica, backfill único de `core`→`organization`) |

Confirmado: `core`, `notifications`, `accounts`, `users`, `quotes`, `marketing` ya migrados al selector; `payment` sin referencias (no-op); `dashboard` es el único consumidor con acceso directo residual.

### 1.3 Duplicación encontrada fuera de `organization`

- `core/models.py::FooterCTAConfig.title_highlighted` — default `'Sintel Technology'`, independiente de `Company.trade_name`.
- `core/api/views.py:158` y `dashboard/api/views.py:2489` — literal `'Sintel'` duplicado en dos archivos en vez de una constante compartida.
- `seo/templatetags/seo_tags.py` — `DEFAULT_TITLE`/`DEFAULT_DESCRIPTION` con copy de marca embebido en `seo/` en vez de derivarse íntegramente de `organization.SeoSettings`/`Company`.
- `core.AboutUsConfig` — contenido narrativo institucional (historia/misión/visión) conceptualmente pertenece al dominio de "identidad de negocio" pero vive en `core`, no en `organization`. No es duplicación estricta (no existe un modelo equivalente en `organization`), pero es candidato a converger ahí.
- Confirmado **eliminado**: `core.SiteBrandConfig` y `core.CompanyContactInfo` ya no existen — la duplicación histórica que motivó crear `organization` está resuelta para esos dos modelos.

### 1.4 Veredicto — `organization`

Base **fuerte** para un futuro `BusinessIdentity`/`BusinessProfile`: disciplina de escritor único (`OrganizationCommands`), disciplina de lector único (`OrganizationSelector`, reforzada por regla explícita en `CLAUDE.md`), soft-delete + constraints singleton-safe, y una migración documentada de 9 fases que ya eliminó las dos peores duplicaciones legacy en `core`. `LegalEntityInfo` ya cubre tax_id/fiscal_address/legal_representative — algo que muchos codebases e-commerce no modelan.

Brechas antes de ser un verdadero `BusinessProfile` white-label:
1. **Defaults de tenant horneados en el modelo/seeds es el mayor bloqueador** — `Company.trade_name` default `'Sintel'`, y `EmailSettings`/`DomainSettings` sembrados vía migraciones de datos con valores reales de producción. Cualquier despliegue nuevo hereda la identidad de Sintel de fábrica.
2. `dashboard/api/views.py` sigue importando `organization.models.SocialLink` directamente en 2 puntos — debe migrar a `OrganizationSelector.get_social_link_by_uuid()`.
3. El literal `'Sintel'` y los defaults de SEO están duplicados en `core/api/views.py`, `dashboard/api/views.py` y `seo/templatetags/seo_tags.py` en vez de derivar de una sola constante.
4. `FooterCTAConfig.title_highlighted` en `core` tiene un default de marca independiente, desconectado de `organization.Company`.
5. ~~Sin UI de panel dedicada~~ **[CORREGIDO]** — `/panel/organizacion` (`OrganizationView.vue`, 8 tabs) sí existe, montado directamente en `/api/v1/organization/` (fuera del patrón BFF de `dashboard`, decisión deliberada documentada en el `.AGENT/docs` de la app, no una omisión). Sigue existiendo el puente legacy paralelo `site-brand` en `dashboard` (cubre solo `trade_name`/`tagline`/`logo`) — es una duplicación de UI menor (dos lugares para editar el nombre de marca), no una ausencia de UI. La propia app se autodescribe "Fases 1-5 completas, Fase 6 completa para varios consumidores, Fase 8 (panel) completa" en su `.AGENT/docs` — más avanzada que "Fase 3 de 9" como decía la cabecera de `organization/CLAUDE.md` al momento de esta auditoría (otro caso de `DOCUMENTATION_DRIFT`, esta vez entre el propio `CLAUDE.md` de la app y su doc de arquitectura detallado).

## Parte 2 — `core` (capa de contenido/config del sitio)

### 2.1 Inventario de modelos

| Modelo | Veredicto | Evidencia |
|---|---|---|
| `HomeBanner` | GENERIC | Campos libres texto/imagen/video/link, sin supuestos de negocio |
| `HomeModuleConfig` | PARTIALLY_GENERIC | `MODULE_META` hardcodea exactamente 4 módulos — shop(`/tienda`), renting(`/alquiler`), services(`/servicios`), quotes(`/cotizar`) — el mix de negocio actual de Sintel. `custom_label/custom_icon/custom_url/custom_color` permiten override total y `clean()` acepta `module_key` fuera de `MODULE_META` si se llenan los campos custom → reconfigurable sin tocar código, pero los 4 defaults sembrados (`HomeConfigSelector.get_or_create_default_modules`) privilegian el mix específico de Sintel; un negocio de un solo vertical debe ocultar 3 de 4 filas manualmente |
| `HomeCard` / `HomeCardGroup` | GENERIC | `stats` JSON deliberadamente libre de esquema |
| `FeatureBannerSection`/`Block` | GENERIC | Documentado explícitamente como reutilizable "para cualquier proposito comercial" |
| `FooterCTAConfig` | HARDCODED (solo defaults) | Singleton con copy de Sintel horneado como default de campo: `title_highlighted='Sintel Technology'`, `subtitle=...`, `btn_primary_url='/cotizar'`, `btn_ghost_url='/tienda'`. Editable, pero un deploy fresco muestra branding de Sintel hasta que un admin lo sobreescribe |
| `FooterGroup`/`FooterLink` | GENERIC | Categoría "social" ya migrada a `organization.SocialLink` |
| `NavbarLink` | GENERIC | Lista libre label/url/icon |
| `BrandSliderItem`/`Config` | GENERIC | Default title `'Marcas y clientes'`, neutral |
| `AboutUsConfig`/`Value` | GENERIC | Texto libre, default title `'Sobre Nosotros'` neutral, sin estructura fija atada al rubro seguridad |

Ningún `SiteConfig` vive en `core` — esa responsabilidad ya está en `organization` (`Company`, `Branding`); `core.api.views.site_config` compone desde ahí. SEO confirmado movido a la app dedicada `seo` (`SiteMetaTag`, `SiteVerificationFile`, `SeoMetaTagAuditLog`). Un `core.SiteBrandConfig` histórico (con default `site_name='Sintel'`) fue creado y eliminado dentro de la misma migración squasheada — muerto, no vivo.

### 2.2 Superficie API

| Endpoint | Existe | Dinámico o hardcoded |
|---|---|---|
| `home-feed` | Sí | Totalmente dinámico, cache 5 min |
| `footer` | Sí | Dinámico, delega contacto/social a `organization` |
| `site-config` | Sí | Mayormente dinámico, con un fallback hardcoded: `'site_name': company.trade_name if company else 'Sintel'` |
| `about-us` | Sí | Totalmente dinámico |
| `enums` | Sí | ~15 subcatálogos hardcodeados en Python (estados de pedido/pago/renta/cotización/KYC/envío, métodos de pago incluyendo Nequi/PSE/Bancolombia/Efecty, `user-types` con roles TECHNICIAN/CONTRACTOR/TRANSPORTER). Metadata de estados, no contenido editable — pero el *contenido* asume mercado colombiano y un modelo operativo multi-vertical específico de este negocio |

### 2.3 Defaults de seed/migración

- **Hallazgo más grave**: `seed_renting_home_cards` (dentro de `core` migración squasheada) siembra en cada instalación fresca `HomeCardGroup`/`HomeCard` con copy real del rubro seguridad — nombres de marcas (Hikvision, Dahua, Ubiquiti, Cisco, Dell, APC) y textos como "Seguridad temporal", "CCTV, control perimetral y monitoreo". Requiere limpieza manual o squash de migración para un despliegue white-label.
- `seo/migrations/0002_seed_meta_business_verification.py` siembra un código real de verificación de Meta Business Suite atado al dominio de Sintel — heredado literalmente por cualquier despliegue nuevo.
- `seo/migrations/0005_seed_robots_meta.py` siembra `robots: index, follow` — neutral, sin problema.

### 2.4 Sistema de theming

No existe modelo de tema/color en el backend de `core`. El único concepto de "tema" es `FeatureBannerSection.theme` (`light/dark/corporate/minimal/glass`) — un preset visual por sección, no un sistema de tokens de marca a nivel de sitio. Colores por campo son strings hex libres con defaults hardcodeados (`#2563eb`, `#3b82f6`, etc.) dispersos en varios modelos, sin `ThemeConfig` central.

### 2.5 Veredicto — `core`

Arquitectónicamente cerca de ser una capa de contenido agnóstica de negocio — la mayoría de modelos son genéricos por esquema. El bloqueador #1 no es el esquema, es **el contenido sembrado y un par de fallbacks hardcodeados**: (a) `seed_renting_home_cards` inyecta copy/marca real de Sintel en cada instalación nueva, (b) los defaults de `FooterCTAConfig` son copy/rutas de marca Sintel, (c) el fallback `'Sintel'` en `site-config` filtra identidad cuando `organization.Company` no está configurado. Ninguno requiere rediseño de esquema — requieren: despoblar/parametrizar la migración de seed, mover defaults de `FooterCTAConfig` a strings neutrales, y eliminar el literal `'Sintel'` en `views.py:158`.
