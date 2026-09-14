from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404

from seo.models import SiteMetaTag, SeoMetaTagAuditLog, SiteVerificationFile

# Debe coincidir con seo/signals.py::SEO_META_TAGS_CACHE_KEY -- mismo criterio
# de duplicacion deliberada de constantes que core/signals.py (comentario
# "must match values in views.py").
SEO_META_TAGS_CACHE_KEY = 'sintel_seo_meta_tags_v1'
SEO_META_TAGS_CACHE_TTL = 300
VERIFICATION_FILE_CACHE_PREFIX = 'sintel_seo_verification_file_v1:'
VERIFICATION_FILE_CACHE_TTL = 300


class MetaTagSelector:

    @staticmethod
    def list_for_admin(filters: dict | None = None):
        filters = filters or {}
        qs = SiteMetaTag.objects.filter(is_deleted=False)

        provider = filters.get('provider')
        tag_type = filters.get('tag_type')
        environment = filters.get('environment')
        is_active = filters.get('is_active')
        search = filters.get('search')

        if provider:
            qs = qs.filter(provider=provider)
        if tag_type:
            qs = qs.filter(tag_type=tag_type)
        if environment:
            qs = qs.filter(environment=environment)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(meta_name__icontains=search)
                | Q(description__icontains=search)
            )
        return qs

    @staticmethod
    def get_by_uuid(uuid):
        return get_object_or_404(SiteMetaTag, uuid=uuid, is_deleted=False)

    @staticmethod
    def _cached_active_rows():
        """
        Cachea el HTML ya renderizado (tag.to_html()) de cada metaetiqueta
        activa junto con los criterios de filtrado (target_page/environment).
        El render ocurre una sola vez por TTL, no en cada request.
        """
        cached = cache.get(SEO_META_TAGS_CACHE_KEY)
        if cached is not None:
            return cached

        tags = SiteMetaTag.objects.filter(is_active=True, is_deleted=False).order_by('priority', 'created_at')
        rows = [
            {
                'html': tag.to_html(),
                'target_page': tag.target_page,
                'environment': tag.environment,
            }
            for tag in tags
        ]
        cache.set(SEO_META_TAGS_CACHE_KEY, rows, SEO_META_TAGS_CACHE_TTL)
        return rows

    @staticmethod
    def list_active_for_render(path: str = '/', environment: str = SiteMetaTag.ENV_PRODUCTION) -> list:
        """Devuelve la lista de fragmentos <meta> ya listos para insertar en el <head>."""
        path = path or '/'
        html_list = []
        for row in MetaTagSelector._cached_active_rows():
            row_env = row['environment']
            if row_env != SiteMetaTag.ENV_ALL and row_env != environment:
                continue
            target_page = row['target_page']
            if target_page and not path.startswith(target_page):
                continue
            html_list.append(row['html'])
        return html_list

    @staticmethod
    def list_history(meta_tag=None):
        qs = SeoMetaTagAuditLog.objects.all()
        if meta_tag is not None:
            qs = qs.filter(meta_tag=meta_tag)
        return qs


class VerificationFileSelector:

    @staticmethod
    def list_for_admin():
        return SiteVerificationFile.objects.filter(is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid):
        return get_object_or_404(SiteVerificationFile, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_active_content_by_filename(filename: str):
        """Usado por seo.views.serve_verification_file -- cacheado porque se
        sirve en la raiz del dominio y puede recibir trafico de bots/crawlers
        de verificacion repetidamente."""
        cache_key = f'{VERIFICATION_FILE_CACHE_PREFIX}{filename}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached or None

        try:
            record = SiteVerificationFile.objects.get(
                filename=filename, is_active=True, is_deleted=False,
            )
            content = record.content
        except SiteVerificationFile.DoesNotExist:
            content = ''

        cache.set(cache_key, content, VERIFICATION_FILE_CACHE_TTL)
        return content or None
