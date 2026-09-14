"""
Template tags que construyen el <head> de templates/spa_shell.html -- unico
punto donde Django construye el HTML inicial servido en produccion (ver
ecommerce/urls.py). Todo se ejecuta 100% server-side en cada request; nunca
hay insercion via JavaScript.

render_canonical / render_seo_meta / render_organization_jsonld leen datos
institucionales via organization.services.selectors.OrganizationSelector
(SSoT obligatoria segun organization/CLAUDE.md -- "nadie consulta los
modelos directamente") en vez de duplicarlos como filas de SiteMetaTag, para
que un cambio de marca/logo/dominio en el panel de Organizacion se refleje
aqui sin tocar dos lugares.
"""
import json

from django import template
from django.core.cache import cache
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

ORG_SEO_CONTEXT_CACHE_KEY = 'sintel_org_seo_context_v1'
# TTL igual al resto de caches que leen datos de `organization` (ej.
# sintel_site_config_v1 en core) -- ese modulo no usa signals (regla
# explicita, ver organization/CLAUDE.md), asi que la invalidacion aqui es
# por expiracion, no push; staleness maxima de 300s ya es el criterio
# aceptado en el resto del proyecto para estos mismos datos.
ORG_SEO_CONTEXT_CACHE_TTL = 300

# Fallbacks neutrales (white-label F1, 2026-08-14): antes hardcodeaban "Sintel" y copy
# especifico del rubro seguridad como ultimo recurso cuando SeoSettings no tiene fila activa.
# Ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md.
DEFAULT_TITLE_SUFFIX = 'Tienda en linea'
DEFAULT_DESCRIPTION = 'Tienda en linea: productos, servicios y mas.'
DEFAULT_LOCALE = 'es_CO'
TWITTER_PLATFORM_ALIASES = ('twitter', 'x', 'x (twitter)')


def _fetch_organization_seo_data():
    from organization.services.selectors import OrganizationSelector

    company = OrganizationSelector.get_company()
    branding = OrganizationSelector.get_branding()
    seo_settings = OrganizationSelector.get_seo_settings()
    domain_settings = OrganizationSelector.get_domain_settings()
    contact_info = OrganizationSelector.get_contact_info()
    social_links = OrganizationSelector.list_social_links(active_only=True)

    image_path = None
    if seo_settings and seo_settings.og_image:
        image_path = seo_settings.og_image.url
    elif branding and branding.logo:
        image_path = branding.logo.url

    site_name = OrganizationSelector.get_display_name()
    default_title = f'{site_name} | {DEFAULT_TITLE_SUFFIX}' if site_name else DEFAULT_TITLE_SUFFIX

    return {
        'site_name': site_name,
        'title': (seo_settings.meta_title if seo_settings else '') or default_title,
        'description': (
            (seo_settings.meta_description if seo_settings else '')
            or (branding.tagline if branding else '')
            or DEFAULT_DESCRIPTION
        ),
        'image_path': image_path,
        'primary_domain': (domain_settings.primary_domain if domain_settings else '') or '',
        'contact_phone': (contact_info.phone if contact_info else '') or '',
        'contact_email': (contact_info.email if contact_info else '') or '',
        'social_links': [{'platform': l.platform, 'url': l.url} for l in social_links],
    }


def _get_organization_seo_context(request):
    """Cachea los datos de `organization` (300s) y les agrega los valores
    que dependen de la request actual (canonical_url/image_url absolutos,
    que cambian por pagina/host)."""
    cached = cache.get(ORG_SEO_CONTEXT_CACHE_KEY)
    if cached is None:
        cached = _fetch_organization_seo_data()
        cache.set(ORG_SEO_CONTEXT_CACHE_KEY, cached, ORG_SEO_CONTEXT_CACHE_TTL)

    host = cached['primary_domain'] or request.get_host()
    scheme = request.scheme
    image_url = f'{scheme}://{host}{cached["image_path"]}' if cached['image_path'] else None

    return {
        **cached,
        'host': host,
        'scheme': scheme,
        'canonical_url': f'{scheme}://{host}{request.path}',
        'image_url': image_url,
        'twitter_handle': _extract_twitter_handle(cached['social_links']),
    }


def _extract_twitter_handle(social_links):
    for link in social_links:
        platform = (link.get('platform') or '').strip().lower()
        if platform not in TWITTER_PLATFORM_ALIASES:
            continue
        handle = (link.get('url') or '').rstrip('/').rsplit('/', 1)[-1]
        if handle and not handle.lower().startswith(('http:', 'https:')):
            return handle if handle.startswith('@') else f'@{handle}'
    return ''


@register.simple_tag(takes_context=True)
def render_meta_tags(context):
    from seo.services.selectors import MetaTagSelector
    from seo.services.environment import resolve_current_environment

    request = context.get('request')
    path = getattr(request, 'path', '/') if request is not None else '/'

    html_list = MetaTagSelector.list_active_for_render(
        path=path,
        environment=resolve_current_environment(),
    )
    return mark_safe('\n'.join(html_list))


@register.simple_tag(takes_context=True)
def render_title(context):
    request = context.get('request')
    title = DEFAULT_TITLE_SUFFIX
    if request is not None:
        title = _get_organization_seo_context(request)['title']
    return format_html('<title>{}</title>', title)


@register.simple_tag(takes_context=True)
def render_site_name(context):
    """Nombre de marca para el spinner de carga inicial de spa_shell.html --
    antes hardcodeaba 'Sintel' ahi (white-label F1, 2026-08-14)."""
    request = context.get('request')
    site_name = DEFAULT_TITLE_SUFFIX
    if request is not None:
        site_name = _get_organization_seo_context(request)['site_name'] or DEFAULT_TITLE_SUFFIX
    return format_html('{}', site_name)


@register.simple_tag(takes_context=True)
def render_canonical(context):
    request = context.get('request')
    if request is None:
        return ''
    ctx = _get_organization_seo_context(request)
    return format_html('<link rel="canonical" href="{}">', ctx['canonical_url'])


@register.simple_tag(takes_context=True)
def render_seo_meta(context):
    """Open Graph + Twitter Cards completos, a partir de organization + la
    URL real de la request (og:url/twitter no pueden ser SiteMetaTag
    estaticas porque cambian por pagina)."""
    request = context.get('request')
    if request is None:
        return ''
    ctx = _get_organization_seo_context(request)

    parts = [
        format_html('<meta property="og:title" content="{}">', ctx['title']),
        format_html('<meta property="og:description" content="{}">', ctx['description']),
        format_html('<meta property="og:url" content="{}">', ctx['canonical_url']),
        '<meta property="og:type" content="website">',
        format_html('<meta property="og:site_name" content="{}">', ctx['site_name']),
        format_html('<meta property="og:locale" content="{}">', DEFAULT_LOCALE),
    ]
    if ctx['image_url']:
        parts.append(format_html('<meta property="og:image" content="{}">', ctx['image_url']))

    parts.append(format_html(
        '<meta name="twitter:card" content="{}">',
        'summary_large_image' if ctx['image_url'] else 'summary',
    ))
    parts.append(format_html('<meta name="twitter:title" content="{}">', ctx['title']))
    parts.append(format_html('<meta name="twitter:description" content="{}">', ctx['description']))
    if ctx['image_url']:
        parts.append(format_html('<meta name="twitter:image" content="{}">', ctx['image_url']))
    if ctx['twitter_handle']:
        parts.append(format_html('<meta name="twitter:site" content="{}">', ctx['twitter_handle']))

    return mark_safe('\n'.join(str(p) for p in parts))


@register.simple_tag(takes_context=True)
def render_organization_jsonld(context):
    """JSON-LD schema.org/Organization, construido desde organization (no
    admin-tipeado): name/url/logo/sameAs/contactPoint."""
    request = context.get('request')
    if request is None:
        return ''
    ctx = _get_organization_seo_context(request)

    data = {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        'name': ctx['site_name'],
        'url': f"{ctx['scheme']}://{ctx['host']}/",
    }
    if ctx['image_url']:
        data['logo'] = ctx['image_url']

    same_as = [link['url'] for link in ctx['social_links'] if link.get('url')]
    if same_as:
        data['sameAs'] = same_as

    if ctx['contact_phone'] or ctx['contact_email']:
        contact_point = {'@type': 'ContactPoint', 'contactType': 'customer service'}
        if ctx['contact_phone']:
            contact_point['telephone'] = ctx['contact_phone']
        if ctx['contact_email']:
            contact_point['email'] = ctx['contact_email']
        data['contactPoint'] = [contact_point]

    # Escapa '</' para que un valor con "</script>" (ej. un tagline
    # malicioso) no pueda cerrar el <script> anticipadamente.
    json_str = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return mark_safe(f'<script type="application/ld+json">{json_str}</script>')
