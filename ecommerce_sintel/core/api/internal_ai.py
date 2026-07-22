"""
Endpoints internos de Core Content para el AI Engine (Fase 8 AI Core).

Lectura: banners, modulos home, navbar, footer (grupos + enlaces), brand slider.
Escritura: actualizar/crear banner, actualizar enlace navbar, actualizar item
brand slider. Toda escritura exige IsAdminUser y queda auditada en
security.SecurityEvent (AI_ACTION_EXECUTED).

Ruteados bajo /api/v1/internal/ai/ (ecommerce/internal_ai_urls.py).
La restriccion dura del plan: ninguna Tool accede a modelos directamente --
este endpoint es la unica fachada sancionada (Fase 1).
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status

from core.services.selectors import HomeConfigSelector
from core.services.commands import (
    HomeConfigCommands,
    NavbarLinkSelector,
    NavbarLinkCommands,
    FooterGroupSelector,
    FooterSelector,
    BrandSliderSelector,
    BrandSliderCommands,
)
from users.api.permissions import IsAdminUser, IsAuthenticatedActiveUser


from ecommerce.internal_ai_utils import log_ai_action as _log_ai_action


# ─── Lectura ─────────────────────────────────────────────────────────────────

class AiCoreHomeConfigView(APIView):
    """GET /api/v1/internal/ai/core/home/ -> banners + modulos activos."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        banners = HomeConfigSelector.list_banners_for_admin()
        modules = HomeConfigSelector.list_module_configs()
        return Response({
            'banners': [
                {
                    'uuid': str(b.uuid),
                    'title': b.title,
                    'subtitle': b.subtitle,
                    'link_url': b.link_url,
                    'link_label': b.link_label,
                    'display_order': b.display_order,
                    'is_active': b.is_active,
                    'has_image': bool(b.image),
                    'has_video': bool(b.video),
                }
                for b in banners
            ],
            'modules': [
                {
                    'uuid': str(m.uuid),
                    'module_key': m.module_key,
                    'custom_label': m.custom_label,
                    'is_visible': m.is_visible,
                    'display_order': m.display_order,
                }
                for m in modules
            ],
        })


class AiCoreNavbarView(APIView):
    """GET /api/v1/internal/ai/core/navbar/ -> enlaces de navegacion."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        links = NavbarLinkSelector.list_all()
        return Response({
            'links': [
                {
                    'uuid': str(lnk.uuid),
                    'label': lnk.label,
                    'url': lnk.url,
                    'icon_class': lnk.icon_class,
                    'display_order': lnk.display_order,
                    'is_visible': lnk.is_visible,
                    'open_in_new_tab': lnk.open_in_new_tab,
                }
                for lnk in links
            ]
        })


class AiCoreFooterView(APIView):
    """GET /api/v1/internal/ai/core/footer/ -> grupos + enlaces del footer."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        groups = FooterGroupSelector.list_all()
        links = FooterSelector.list_all_links()
        return Response({
            'groups': [
                {
                    'uuid': str(g.uuid),
                    'title': g.title,
                    'is_active': g.is_active,
                    'display_order': g.display_order,
                }
                for g in groups
            ],
            'links': [
                {
                    'uuid': str(lnk.uuid),
                    'title': lnk.title,
                    'url': lnk.url,
                    'category': lnk.category,
                    'is_active': lnk.is_active,
                }
                for lnk in links
            ],
        })


class AiCoreBrandSliderView(APIView):
    """GET /api/v1/internal/ai/core/brand-slider/ -> items del slider de marcas."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        items = BrandSliderSelector.list_items_for_admin()
        config = BrandSliderSelector.get_config()
        return Response({
            'config': {
                'title': config.title if config else '',
                'is_visible': config.is_visible if config else False,
                'autoplay': config.autoplay if config else True,
            } if config else None,
            'items': [
                {
                    'uuid': str(item.uuid),
                    'name': item.name,
                    'website': item.website,
                    'display_order': item.display_order,
                    'is_active': item.is_active,
                    'has_logo': bool(item.logo),
                }
                for item in items
            ],
        })


# ─── Escritura ───────────────────────────────────────────────────────────────

class AiCoreBannerUpdateView(APIView):
    """
    POST /api/v1/internal/ai/core/banners/update/
    Actualiza titulo/subtitulo/link/visibilidad de un banner existente.
    No maneja upload de imagen (la AI no sube archivos; eso sigue siendo tarea humana).
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)

        banner = HomeConfigSelector.get_banner_by_uuid(uuid)
        allowed_fields = ('title', 'subtitle', 'link_url', 'link_label', 'display_order', 'is_active')
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)

        HomeConfigCommands.update_banner(banner, data)
        _log_ai_action(request, 'CoreBannerUpdateTool', {'banner_uuid': uuid, 'fields': list(data.keys())})
        return Response({
            'success': True,
            'uuid': str(banner.uuid),
            'title': banner.title,
            'is_active': banner.is_active,
        })


class AiCoreBannerCreateView(APIView):
    """POST /api/v1/internal/ai/core/banners/create/ -> crea un nuevo banner de texto."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        title = (request.data.get('title') or '').strip()
        if not title:
            return Response({'error': 'title requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)

        banner = HomeConfigCommands.create_banner(
            title=title,
            subtitle=request.data.get('subtitle', ''),
            link_url=request.data.get('link_url', ''),
            link_label=request.data.get('link_label', ''),
            display_order=int(request.data.get('display_order', 0)),
        )
        _log_ai_action(request, 'CoreBannerCreateTool', {'banner_uuid': str(banner.uuid), 'title': title})
        return Response({'success': True, 'uuid': str(banner.uuid), 'title': banner.title},
                        status=http_status.HTTP_201_CREATED)


class AiCoreNavbarLinkUpdateView(APIView):
    """POST /api/v1/internal/ai/core/navbar/update/ -> actualiza un enlace de la navbar."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)

        link = NavbarLinkSelector.get_by_uuid(uuid)
        allowed_fields = ('label', 'url', 'icon_class', 'display_order', 'is_visible', 'open_in_new_tab')
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)

        NavbarLinkCommands.update(link, data)
        _log_ai_action(request, 'CoreNavbarLinkUpdateTool', {'link_uuid': uuid, 'fields': list(data.keys())})
        return Response({'success': True, 'uuid': str(link.uuid), 'label': link.label, 'url': link.url})


class AiCoreNavbarLinkCreateView(APIView):
    """POST /api/v1/internal/ai/core/navbar/create/ -> crea un enlace en la navbar."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        label = (request.data.get('label') or '').strip()
        url = (request.data.get('url') or '').strip()
        if not label or not url:
            return Response({'error': 'label y url son requeridos.'}, status=http_status.HTTP_400_BAD_REQUEST)

        link = NavbarLinkCommands.create(
            label=label,
            url=url,
            icon_class=request.data.get('icon_class', ''),
            display_order=int(request.data.get('display_order', 0)),
            is_visible=bool(request.data.get('is_visible', True)),
            open_in_new_tab=bool(request.data.get('open_in_new_tab', False)),
        )
        _log_ai_action(request, 'CoreNavbarLinkCreateTool', {'link_uuid': str(link.uuid), 'label': label})
        return Response({'success': True, 'uuid': str(link.uuid), 'label': link.label, 'url': link.url},
                        status=http_status.HTTP_201_CREATED)


class AiCoreBrandSliderItemUpdateView(APIView):
    """POST /api/v1/internal/ai/core/brand-slider/update/ -> actualiza un item del slider de marcas."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        uuid = request.data.get('uuid')
        if not uuid:
            return Response({'error': 'uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)

        item = BrandSliderSelector.get_item_by_uuid(uuid)
        allowed_fields = ('name', 'website', 'display_order', 'is_active', 'open_new_tab')
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        if not data:
            return Response({'error': 'Sin campos validos para actualizar.'}, status=http_status.HTTP_400_BAD_REQUEST)

        BrandSliderCommands.update_item(item, data)
        _log_ai_action(request, 'CoreBrandSliderUpdateTool', {'item_uuid': uuid, 'fields': list(data.keys())})
        return Response({'success': True, 'uuid': str(item.uuid), 'name': item.name, 'is_active': item.is_active})
