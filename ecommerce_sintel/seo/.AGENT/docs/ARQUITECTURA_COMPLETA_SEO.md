# ARQUITECTURA COMPLETA — APP seo

**Ultima actualizacion:** 2026-07-31 (agrega `SiteVerificationFile` — metodo de verificacion "Subir archivo HTML")

## Responsabilidad

Sistema empresarial de administracion de metaetiquetas del `<head>` del sitio
publico (`https://sintel.net.co`): verificacion de dominio (Meta Business
Suite, Google Search Console...), analytics (GA4, GTM), pixels de conversion
(Meta Pixel, TikTok Pixel, LinkedIn Insight...), y cualquier proveedor futuro.
Nace de un requerimiento explicito: **nunca** volver a hardcodear un codigo de
verificacion en un template — todo vive en base de datos, administrable desde
`/panel/seo/meta-tags`.

**Punto critico de arquitectura:** en produccion, TODO el HTML (excepto
`/api/`, `/admin/`, `/static/`) pasa por una unica vista Django
(`ecommerce/urls.py` → `TemplateView.as_view(template_name='spa_shell.html')`,
confirmado tambien en `nginx-common.conf`: todo trafico no-estatico se
proxea a Django). `templates/spa_shell.html` es por lo tanto el unico lugar
donde se construye el `<head>` real que ve el navegador, y ahi es donde este
modulo inserta `{% render_meta_tags %}` — un template tag que consulta la
base de datos **server-side, en cada request**. Nunca hay insercion via
JavaScript ni manipulacion del DOM post-carga.

---

## Estructura de Directorios

```
seo/
├── models.py                    # SiteMetaTag, SeoMetaTagAuditLog, SiteVerificationFile
├── apps.py                      # SeoConfig.ready() importa seo.signals
├── signals.py                   # Invalida cache de render en post_save/post_delete
├── views.py                     # serve_verification_file -- sirve SiteVerificationFile en la raiz del dominio
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_seed_meta_business_verification.py  # seed sin hardcodear (data migration)
│   ├── 0003_verification_files.py               # modelo SiteVerificationFile
│   └── 0004_seed_meta_verification_file.py      # seed del archivo HTML (mismo codigo que 0002)
├── services/
│   ├── sanitizer.py             # sanitize_meta_html() -- allowlist de <meta>, sin deps nuevas
│   ├── environment.py           # resolve_current_environment()
│   ├── selectors.py             # MetaTagSelector
│   └── commands.py              # MetaTagCommands (= "Service Layer")
├── templatetags/
│   └── seo_tags.py              # {% render_meta_tags %}
├── api/
│   └── serializers.py           # SiteMetaTagSerializer, SiteMetaTagInputSerializer, ...
└── tests/
    └── test_meta_tags.py        # 23 tests -- incluye el check end-to-end del <head>
```

El ViewSet admin (`AdminSeoMetaTagViewSet`) vive en `dashboard/api/views.py`
junto a los otros 38+ ViewSets admin del proyecto (mismo criterio que
`AdminAboutUsViewSet`) — no en `seo/api/views.py` — para no introducir un
segundo patron de ubicacion de ViewSets admin en el proyecto.

**Adaptacion deliberada de nomenclatura:** el requerimiento original pedia
`MetaTagCommands`/`MetaTagSelectors`/`MetaTagService`/`MetaTagRepository`/
`MetaTagViewSet`/`MetaTagPermissions` como capas separadas. Este proyecto no
usa ese patron en ninguna de sus 19 apps — el "Service Layer" real son
siempre dos clases (`XxxSelector` + `XxxCommands`), y los permisos admin se
reutilizan desde `dashboard.api.views.ADMIN_PERMISSIONS`
(`[IsAuthenticated, IsAdminUser]`, de `users.api.permissions`). `seo` sigue
ese mismo patron real en vez de fragmentar en capas que ningun otro modulo
tiene — el requisito de fondo ("cero logica de negocio en views/serializers/
signals/frontend") se cumple igual: toda la logica vive en
`MetaTagSelector`/`MetaTagCommands`.

---

## Modelos

### SiteMetaTag

```python
class SiteMetaTag(SintelBaseModel):
    name          = CharField(255)                 # nombre administrativo
    provider      = CharField(choices=PROVIDER_CHOICES)   # meta, facebook, instagram,
                                                            # google_search_console, google_tag_manager,
                                                            # google_analytics, bing, pinterest, tiktok,
                                                            # linkedin, apple, cloudflare, custom
    tag_type      = CharField(choices=TYPE_CHOICES)       # domain_verification, analytics, pixel,
                                                            # seo, social, custom
    description   = TextField(blank=True)
    meta_name     = CharField(blank=True)           # atributo name= (modo "simple")
    meta_content  = CharField(blank=True)            # atributo content= (modo "simple")
    html_snippet  = TextField(blank=True)             # alternativa: HTML crudo, sanitizado al guardar
    priority      = PositiveIntegerField(default=0)   # orden de render (menor = primero)
    is_active     = BooleanField(default=True)
    target_page   = CharField(blank=True)              # prefijo de ruta ('' = todas las paginas)
    environment   = CharField(choices=ENV_CHOICES, default='all')  # all/development/testing/staging/production
    created_by / updated_by = FK(AUTH_USER_MODEL, null=True, SET_NULL)
```

`clean()` exige `(meta_name AND meta_content)` o un `html_snippet` no vacio
(nunca ambos vacios). `to_html()` construye el fragmento final: usa
`html_snippet` si esta presente (ya sanitizado), si no arma
`<meta name="..." content="...">` con `django.utils.html.format_html`
(auto-escape).

### SeoMetaTagAuditLog

Append-only, mismo patron que `users.UserAuditLog`: `meta_tag` FK nullable +
`meta_tag_name` (snapshot, sobrevive si el tag se borra), `action`
(created/updated/activated/deactivated/duplicated/deleted/reordered/
imported/exported), `user` FK nullable, `ip_address`, `changes` JSONField.
Poblado exclusivamente desde `MetaTagCommands` (nunca `.objects.create()`
directo fuera de ese archivo).

### Seed sin hardcodear

`seo/migrations/0002_seed_meta_business_verification.py` (data migration,
`get_or_create` idempotente) crea el primer registro:
`provider='meta'`, `meta_name='facebook-domain-verification'`,
`meta_content='0c6qg0sg1qsfxhoth3srzf53i62neb'`. El valor vive en la base de
datos desde el primer `migrate` — editable/eliminable libremente por un
admin, nunca en un template ni en `settings`.

---

## Sanitizacion (`seo/services/sanitizer.py`)

`sanitize_meta_html(raw) -> str` — sin dependencias nuevas (no bleach/nh3),
usa `html.parser.HTMLParser` (stdlib) + `format_html` para reconstruir cada
etiqueta con una allowlist de atributos (`name`, `content`, `property`,
`charset`, `http-equiv`). Rechaza con `ValidationError` (todo el snippet, no
solo el atributo) si aparece:
- Cualquier etiqueta que no sea `<meta>`.
- Un atributo `on*=` (evento HTML).
- Un valor con `javascript:`, `data:text/html` o `vbscript:`.
- Texto fuera de las etiquetas `<meta>`.

Se invoca en `SiteMetaTagInputSerializer.validate_html_snippet()` — toda
escritura pasa por el serializer (incluida `import/`, que reusa el mismo
serializer por item), asi que `MetaTagCommands` nunca recibe HTML sin
sanitizar. Mismo criterio de "rechazar entero ante cualquier senal de XSS"
que ya usa `core/api/serializers.py::_strip_html_fields` para campos de
texto plano (duplicado localmente en `seo/api/serializers.py`, 4 lineas, no
amerita modulo compartido).

---

## Renderizado

```python
# seo/templatetags/seo_tags.py
@register.simple_tag(takes_context=True)
def render_meta_tags(context):
    request = context.get('request')
    return mark_safe('\n'.join(MetaTagSelector.list_active_for_render(
        path=getattr(request, 'path', '/'),
        environment=resolve_current_environment(),
    )))
```

`templates/spa_shell.html`: `{% load seo_tags %}` + `{% render_meta_tags %}`
dentro de `<head>`. El context processor `django.template.context_processors.
request` (ya activo en `ecommerce/settings/base.py`) garantiza que
`context['request']` este disponible sin cambios adicionales.

### Cache

`SEO_META_TAGS_CACHE_KEY = 'sintel_seo_meta_tags_v1'`, TTL 300s (mismo
criterio que `HOME_FEED_CACHE_KEY` de `core`). Se cachea la lista de HTML
**ya renderizado** (`tag.to_html()` se ejecuta una vez al poblar el cache,
no en cada request) junto con `target_page`/`environment` para filtrar en
Python al momento de servir — evita explosion de cache keys por combinacion
de ruta. Invalidacion automatica via `seo/signals.py`
(`post_save`/`post_delete` sobre `SiteMetaTag`), registrado en
`SeoConfig.ready()`.

### Entorno

`seo/services/environment.py::resolve_current_environment()` — usa
`settings.SEO_ACTIVE_ENVIRONMENT` (env var opcional, `ecommerce/settings/
base.py`) si esta seteada; si no, infiere `development`/`production` de
`DEBUG` (el proyecto hoy solo tiene `settings/development.py` y
`settings/production.py`, sin modulos de testing/staging). Es el unico punto
de extension si en el futuro se agregan esos entornos — ningun otro archivo
de este modulo necesita cambiar.

---

## Service Layer

### MetaTagSelector (`seo/services/selectors.py`)

```python
list_for_admin(filters)     # provider, tag_type, environment, is_active, search (icontains)
get_by_uuid(uuid)           # get_object_or_404
list_active_for_render(path, environment)   # cacheado, ver "Renderizado"
list_history(meta_tag)      # SeoMetaTagAuditLog ordenado -created_at
```

### MetaTagCommands (`seo/services/commands.py`)

```python
create(data, request)               # valida duplicados, full_clean(), audit CREATED
update(tag, data, request)          # valida duplicados (excluye self), audit UPDATED
delete(tag, request)                # soft-delete, audit DELETED
duplicate(tag, request)             # copia nace is_active=False, audit DUPLICATED
toggle_active(tag, request)         # valida duplicados si pasa a True, audit ACTIVATED/DEACTIVATED
reorder(ordered_uuids, request)     # @transaction.atomic, audit REORDERED
export(queryset, request)           # audit EXPORTED
log_import(count, request)          # audit IMPORTADO (el ViewSet crea cada item via create())
```

Extraccion de usuario/IP identica a `security/services/commands.py::
log_event` (`request.META.get('REMOTE_ADDR')`). Deduplicacion: rechaza crear/
activar un tag si ya existe otro `(provider, meta_name)` activo (case-
insensitive).

---

## API Admin

`AdminSeoMetaTagViewSet` (`dashboard/api/views.py`), `permission_classes =
ADMIN_PERMISSIONS`, `lookup_field = 'uuid'`. Registrado en
`dashboard/api/urls.py` como `router.register(r'seo/meta-tags', ...,
basename='admin-seo-meta-tags')`.

| Metodo | Path | Accion |
|--------|------|--------|
| GET | `/api/v1/dashboard/seo/meta-tags/` | Lista (filtros: provider, tag_type, environment, is_active, search) |
| POST | `/api/v1/dashboard/seo/meta-tags/` | Crea |
| GET | `.../{uuid}/` | Detalle |
| PATCH | `.../{uuid}/` | Actualiza |
| DELETE | `.../{uuid}/` | Elimina (soft) — tambien deja `SecurityEvent.ADMIN_RESOURCE_DELETED` (D-02) |
| POST | `.../{uuid}/duplicate/` | Duplica (copia inactiva) |
| POST | `.../{uuid}/toggle/` | Activa/desactiva |
| POST | `.../reorder/` | Reordena por prioridad (`{items: [uuid, ...]}`) |
| GET | `.../{uuid}/preview/` | HTML real que se renderizaria (`tag.to_html()`, no un mock) |
| GET | `.../export/` | Exporta todas en JSON |
| POST | `.../import/` | Importa desde JSON (cada item pasa por el mismo serializer que create) |
| GET | `.../{uuid}/history/` | Historial de auditoria del tag |

`AdminSiteVerificationFileViewSet` (`/api/v1/dashboard/seo/verification-files/`)
expone el mismo CRUD basico + `<uuid>/toggle/` para `SiteVerificationFile` —
ver seccion "Archivos de verificacion" mas abajo.

---

## Frontend Admin

`/panel/seo/meta-tags` (grupo de sidebar "Sitio Web", junto a Home Publica y
Nosotros — no se creo un grupo nuevo, ya encajaba en la IA existente).

```
frontend/src/apps/admin/routes/adminSeo.routes.js   # lazy route
frontend/src/modules/seo/
├── SeoMetaTagList.vue   # tabla + filtros + buscador (debounce 400ms) + import/export + reorder
└── SeoMetaTagForm.vue   # offcanvas create/edit, modo simple (name/content) o HTML avanzado + preview local
```

Patrones obligatorios del proyecto respetados: `useApi()` (sin store Pinia
dedicado — modulo simple, un solo recurso CRUD), `useOffcanvas()` +
`SintelOffcanvas.vue`, `useErrorHandler()`, confirmacion de borrado inline
(`bg-danger-subtle`), debounce 400ms en busqueda.

---

## Archivos de verificacion (`SiteVerificationFile`)

**[NUEVO 2026-07-31]** Meta Business Suite (y otros proveedores: Google
Search Console, Bing...) tambien ofrecen un metodo de verificacion
alternativo al de metaetiqueta: "Subir archivo HTML" — un archivo estatico
con nombre y contenido exactos, servido en la RAIZ del dominio
(`https://sintel.net.co/<filename>.html`), no bajo `/static/`.

```python
class SiteVerificationFile(SintelBaseModel):
    name       = CharField(255)             # nombre administrativo
    provider   = CharField(choices=SiteMetaTag.PROVIDER_CHOICES)
    filename   = CharField(unique=True, validators=[FILENAME_VALIDATOR])  # ^[A-Za-z0-9._-]+\.html$
    content    = TextField()                # contenido EXACTO a devolver, sin sanitizar
    is_active  = BooleanField(default=True)
    created_by / updated_by = FK(AUTH_USER_MODEL, null=True, SET_NULL)
```

**Por que `content` no pasa por `sanitize_meta_html`:** a diferencia de
`SiteMetaTag.html_snippet` (que se inyecta dentro del `<head>` de TODAS las
paginas), este archivo es un recurso aislado que solo se sirve si alguien
pide esa URL exacta — el proveedor externo puede exigir contenido que no es
una etiqueta `<meta>` (texto plano, un documento HTML completo). Queda
detras de `ADMIN_PERMISSIONS` (staff+superuser), no es un input de usuario
final — el trust boundary es el mismo que ya usa el proyecto para otros
campos de texto libre solo-admin.

**Servido:** `seo/views.py::serve_verification_file` (vista Django plana,
no DRF) registrada en `ecommerce/urls.py` como
`path('<str:filename>.html', seo_views.serve_verification_file, ...)`
**antes** del catch-all de la SPA (`re_path(r'^(?!api/|admin/|static/|media/).*$', ...)`)
— de lo contrario ese catch-all interceptaria la request y devolveria
`spa_shell.html` en vez del archivo real. Filename inexistente/inactivo →
`Http404` (no cae al catch-all: un `.html` en la raiz nunca es una ruta
valida de la SPA). Cache por filename (`sintel_seo_verification_file_v1:
<filename>`, TTL 300s, invalidado por signal igual que `SiteMetaTag`).

**Seed:** `seo/migrations/0004_seed_meta_verification_file.py` siembra
`0c6qg0sg1qsfxhoth3srzf53i62neb-meta.html` (mismo codigo que la metaetiqueta
de 0002 — Meta solo exige UNO de los dos metodos, se dejan ambos activos
por redundancia).

**Service layer:** `VerificationFileSelector` (`list_for_admin`,
`get_by_uuid`, `get_active_content_by_filename`) +
`VerificationFileCommands` (`create`/`update`/`delete`/`toggle_active`),
ambos en los mismos archivos que `MetaTagSelector`/`MetaTagCommands`.
Auditoria: reusa `SeoMetaTagAuditLog` con `meta_tag=None` y
`meta_tag_name='[verification_file] <filename>'` (mismo criterio que
`reorder`/`export`/`import` de `MetaTagCommands` para acciones sin un
`SiteMetaTag` puntual — no se creo un modelo de auditoria nuevo).

**API admin:** `AdminSiteVerificationFileViewSet`
(`dashboard/api/views.py`), `/api/v1/dashboard/seo/verification-files/`
(list/create/retrieve/partial_update/destroy + `<uuid>/toggle/`).

**Frontend:** pestaña "Archivos de verificacion" dentro de la misma vista
`/panel/seo/meta-tags` (`SeoMetaTagList.vue` con tabs Bootstrap), componente
`frontend/src/modules/seo/SeoVerificationFilesPanel.vue` — tabla + modal
CRUD simple (no offcanvas: menos campos que una metaetiqueta, no amerita el
mismo patron).

---

## Compatibilidad futura

El modelo (`provider`/`tag_type` como choices abiertos + `html_snippet`
libre-pero-sanitizado) permite agregar Canonical, robots, Open Graph,
Twitter Cards, Schema.org/JSON-LD, Meta Pixel, TikTok Pixel, LinkedIn
Insight, etc. sin cambios estructurales: son simplemente nuevos valores de
`provider`/`tag_type` y, si el proveedor requiere un `<script>` en vez de
`<meta>` (ej. GTM, un pixel), el unico punto que tocar es ampliar la
allowlist de `sanitize_meta_html`/`ALLOWED_ATTRS` (o crear una variante
`sanitize_script_html` equivalente) — el resto del pipeline (modelo, cache,
render, API, frontend) no cambia.

## Tests

36 tests en total, `python manage.py test seo` (no pytest: la imagen Docker
actual no tiene `pytest-django` instalado pese a que `pytest.ini`/
`conftest.py` existen en la raiz; tampoco `manage.py test` sin argumentos —
ver `.AGENT.md` seccion 18.9 sobre discovery roto entre apps hermanas).

- `seo/tests/test_meta_tags.py` (23) — seed, filtros de render (activo/
  entorno/target_page/soft-delete), sanitizer (script/on*/javascript:/texto
  suelto), Commands (duplicados, audit log, soft-delete, duplicate,
  toggle+cache), ViewSet completo (permisos + ciclo de vida + rechazo de
  HTML malicioso). Incluye el test end-to-end central: `GET /` vía `Client`
  de Django debe traer la metaetiqueta de Meta exactamente una vez, dentro
  de `<head>`, antes de `<body`.
- `seo/tests/test_verification_files.py` (13) — seed del archivo HTML,
  servido real en la raiz (`GET /<filename>.html`) con contenido exacto,
  404 para filename desconocido/inactivo, validador de filename (rechaza
  `../` y extensiones distintas de `.html`), Commands + audit log, ViewSet
  completo (permisos + ciclo de vida, incluye verificar que el archivo deja
  de servirse tras desactivarlo via API), y que las rutas de la SPA
  (`/tienda`) siguen funcionando sin verse afectadas por la nueva ruta.
