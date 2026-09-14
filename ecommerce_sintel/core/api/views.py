from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from operations.models import OperationTicket
from orders.models import Order, Shipment
from technical_services.models import OrderServiceTimeline, ServiceOperation
from payment.models import Transaction
from quotes.models import Quotation
from renting.models import RentalRequest
from accounts.models import TechnicianProfile, UserProfile
from kyc.models import UserVerification, VerificationDocument

from core.services.selectors import HomeConfigSelector
from core.services.commands import (
    HomeFeedSelector, HomeConfigCommands,
    HomeCardSelector, HomeCardGroupSelector, FooterSelector, NavbarLinkSelector,
    FooterCTASelector, BrandSliderSelector, AboutUsSelector,
    FeatureBannerSectionSelector,
)
from core.api.serializers import (
    FlashOfferCardSerializer,
    FeaturedProductCardSerializer,
    FeaturedEquipmentCardSerializer,
    FeaturedServiceCardSerializer,
    HomeBannerSerializer,
    HomeBannerInputSerializer,
    HomeModuleConfigSerializer,
    HomeModuleConfigInputSerializer,
    HomeCardSerializer,
    FooterLinkSerializer,
    social_link_to_footer_link_shape,
    NavbarLinkSerializer,
    FooterCTAConfigSerializer,
    BrandSliderItemSerializer,
    BrandSliderConfigSerializer,
    FooterGroupPublicSerializer,
    AboutUsConfigSerializer,
    AboutUsValueSerializer,
    FeatureBannerSectionSerializer,
)
from organization.services.selectors import OrganizationSelector
from organization.api.serializers import ContactInfoSerializer

HOME_FEED_CACHE_KEY    = 'sintel_home_feed_v1'
HOME_FEED_CACHE_TTL    = 60 * 5
FOOTER_CACHE_KEY       = 'sintel_footer_v1'
FOOTER_CACHE_TTL       = 60 * 5
SITE_CONFIG_CACHE_KEY  = 'sintel_site_config_v3'
SITE_CONFIG_CACHE_TTL  = 60 * 5
ABOUT_US_CACHE_KEY     = 'sintel_about_us_v1'
ABOUT_US_CACHE_TTL     = 60 * 5


class HomeFeedView(GenericViewSet):
    """
    Endpoint publico (sin autenticacion) que consolida los datos para la Home.
    Cache manual con key conocida para que el admin pueda invalidarla al guardar banners.
    """
    permission_classes = []
    authentication_classes = []

    @action(detail=False, methods=['get'], url_path='home-feed')
    def home_feed(self, request):
        cached = cache.get(HOME_FEED_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        ctx = {'request': request}

        banners            = HomeConfigSelector.list_banners_active()
        flash_offers       = HomeFeedSelector.get_flash_offers()
        featured_products  = HomeFeedSelector.get_featured_products()
        featured_equipment = HomeFeedSelector.get_featured_equipment()
        featured_services  = HomeFeedSelector.get_featured_services()
        modules            = HomeFeedSelector.get_module_configs(request)
        cards              = HomeCardSelector.list_active()

        card_group_titles = HomeCardGroupSelector.get_titles_map()
        card_groups       = HomeCardGroupSelector.list_all()

        feature_banner_sections = FeatureBannerSectionSelector.list_active_with_blocks()

        footer_cta = FooterCTASelector.get_active()

        brand_slider_items  = BrandSliderSelector.list_items_active()
        brand_slider_config = BrandSliderSelector.get_or_create_config()

        from core.api.serializers import HomeCardGroupSerializer
        data = {
            'banners':            HomeBannerSerializer(banners, many=True, context=ctx).data,
            'modules':            modules,
            'flash_offers':       FlashOfferCardSerializer(flash_offers, many=True, context=ctx).data,
            'featured_products':  FeaturedProductCardSerializer(featured_products, many=True, context=ctx).data,
            'featured_equipment': FeaturedEquipmentCardSerializer(featured_equipment, many=True, context=ctx).data,
            'featured_services':  FeaturedServiceCardSerializer(featured_services, many=True, context=ctx).data,
            'home_cards':         HomeCardSerializer(cards, many=True, context=ctx).data,
            'card_group_titles':  card_group_titles,
            'card_groups':        HomeCardGroupSerializer(card_groups, many=True, context=ctx).data,
            'feature_banner_sections': FeatureBannerSectionSerializer(feature_banner_sections, many=True, context=ctx).data,
            'footer_cta':         FooterCTAConfigSerializer(footer_cta).data if footer_cta else None,
            'brand_slider': {
                'config': BrandSliderConfigSerializer(brand_slider_config).data,
                'items':  BrandSliderItemSerializer(brand_slider_items, many=True, context=ctx).data,
            },
        }
        cache.set(HOME_FEED_CACHE_KEY, data, HOME_FEED_CACHE_TTL)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='footer')
    def footer(self, request):
        cached = cache.get(FOOTER_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        payload = FooterSelector.build_footer_payload()
        contact      = payload['contact']
        social_links = payload['social_links']
        groups       = payload['groups']

        data = {
            'contact': ContactInfoSerializer(contact).data if contact else None,
            'social_links': [social_link_to_footer_link_shape(l) for l in social_links],
            'groups': FooterGroupPublicSerializer(groups, many=True).data,
        }
        cache.set(FOOTER_CACHE_KEY, data, FOOTER_CACHE_TTL)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='site-config')
    def site_config(self, request):
        cached = cache.get(SITE_CONFIG_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        company  = OrganizationSelector.get_company()
        branding = OrganizationSelector.get_branding()
        navbar_links = NavbarLinkSelector.list_visible()
        seo = OrganizationSelector.get_seo_settings()
        modules = HomeConfigSelector.get_or_create_default_modules()

        ctx = {'request': request}
        logo_url = None
        if branding and branding.logo:
            logo_url = branding.logo.url
            if request is not None:
                logo_url = request.build_absolute_uri(logo_url)
        seo_og_image_url = None
        if seo and seo.og_image:
            seo_og_image_url = seo.og_image.url
            if request is not None:
                seo_og_image_url = request.build_absolute_uri(seo_og_image_url)
        data = {
            # Forma identica a la que emitia core.SiteBrandConfig antes de la
            # migracion 2026-07-12 -- ahora combina organization.Company +
            # organization.Branding (2 modelos separados por decision del
            # usuario, ver ARQUITECTURA_COMPLETA_ORGANIZATION.md).
            'brand': {
                'uuid': str(company.uuid) if company else None,
                'site_name': OrganizationSelector.get_display_name(),
                'logo': logo_url,
                'tagline': branding.tagline if branding else '',
                'updated_at': company.updated_at if company else None,
            },
            # White-label F4 (2026-08-14): tokens de tema minimos (ver
            # organization.Branding.primary_color/accent_color). '' = sin
            # override, el frontend se queda con los defaults estaticos de
            # landing-design-system.css -- ver WHITE_LABEL_ARCHITECTURE_TARGET.md Fase 28.
            'theme': {
                'primary_color': branding.primary_color if branding else '',
                'accent_color': branding.accent_color if branding else '',
            },
            'navbar_links': NavbarLinkSerializer(navbar_links, many=True).data,
            'seo': {
                'meta_title':       seo.meta_title if seo else '',
                'meta_description': seo.meta_description if seo else '',
                'og_image':         seo_og_image_url,
            },
            # White-label F3 (2026-08-14): expone is_visible/module_url por modulo para que
            # el router del frontend pueda ocultar verticales (tienda/renting/servicios/
            # cotizaciones) sin tocar codigo -- antes solo se exponia en home-feed (util para
            # la home, pero el router necesita el dato ANTES de navegar, no solo al visitar
            # '/'). Reusa HomeModuleConfigSerializer para no duplicar el merge custom_*/MODULE_META.
            'modules': [
                {
                    'module_key':  m['module_key'],
                    'is_visible':  m['is_visible'],
                    'module_url':  m['module_url'],
                    'module_label': m['module_label'],
                }
                for m in HomeModuleConfigSerializer(modules, many=True).data
            ],
        }
        cache.set(SITE_CONFIG_CACHE_KEY, data, SITE_CONFIG_CACHE_TTL)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='about-us')
    def about_us(self, request):
        """
        Contenido publico de la pagina 'Sobre Nosotros' (filosofia, historia,
        mision/vision, valores institucionales). Devuelve is_visible=False
        igual (el frontend decide si oculta la pagina), para que el admin
        pueda previsualizar antes de publicar.
        """
        cached = cache.get(ABOUT_US_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        cfg    = AboutUsSelector.get_or_create_config()
        values = AboutUsSelector.list_values_active()

        ctx = {'request': request}
        data = {
            'config': AboutUsConfigSerializer(cfg, context=ctx).data,
            'values': AboutUsValueSerializer(values, many=True, context=ctx).data,
        }
        cache.set(ABOUT_US_CACHE_KEY, data, ABOUT_US_CACHE_TTL)
        return Response(data)

    @action(detail=False, methods=['get'], url_path=r'enums/(?P<name>[^/.]+)')
    def enums(self, request, name=None):
        """
        Endpoint contract-first de enums compartidos para frontend.
        Ejemplos:
        - /api/v1/core/enums/order-statuses/
        - /api/v1/core/enums/payment-statuses/
        - /api/v1/core/enums/payment-methods/
        - /api/v1/core/enums/service-priorities/
        """
        order_statuses = {
            'CREATED': {'label': 'Creado', 'class': 'bg-secondary-subtle text-secondary border border-secondary-subtle'},
            'PENDING_PAYMENT': {'label': 'Pendiente de pago', 'class': 'bg-warning-subtle text-warning border border-warning-subtle'},
            'pending': {'label': 'Pendiente', 'class': 'bg-warning-subtle text-warning border border-warning-subtle'},
            'processing': {'label': 'En proceso', 'class': 'bg-info-subtle text-info border border-info-subtle'},
            'paid': {'label': 'Pagado', 'class': 'bg-success-subtle text-success border border-success-subtle'},
            'PREPARING': {'label': 'Preparando', 'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
            'READY_FOR_DISPATCH': {'label': 'Listo para despacho', 'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
            'ASSIGNED': {'label': 'Asignado', 'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
            'PICKED_UP': {'label': 'Recogido', 'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
            'IN_TRANSIT': {'label': 'En transito', 'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
            'OUT_FOR_DELIVERY': {'label': 'En reparto', 'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
            'delivered': {'label': 'Entregado', 'class': 'bg-success text-white'},
            'COMPLETED': {'label': 'Completado', 'class': 'bg-success text-white'},
            'cancelled': {'label': 'Cancelado', 'class': 'bg-secondary-subtle text-secondary border border-secondary-subtle'},
            'RETURN_REQUESTED': {'label': 'Devolucion solicitada', 'class': 'bg-warning-subtle text-warning border border-warning-subtle'},
            'RETURNED': {'label': 'Devuelto', 'class': 'bg-secondary-subtle text-secondary border border-secondary-subtle'},
            'FAILED_DELIVERY': {'label': 'Entrega fallida', 'class': 'bg-danger-subtle text-danger border border-danger-subtle'},
            'LOST': {'label': 'Perdido', 'class': 'bg-danger-subtle text-danger border border-danger-subtle'},
        }

        payment_statuses = {
            code: {'label': label, 'class': (
                'bg-success text-white' if code == 'APPROVED' else
                'bg-warning text-dark' if code == 'PENDING' else
                'bg-danger text-white' if code in ('DECLINED', 'VOIDED', 'ERROR') else
                'bg-secondary text-white'
            )}
            for code, label in Transaction.STATUS_CHOICES
        }
        payment_statuses['REJECTED'] = {
            'label': 'Rechazado',
            'class': 'bg-danger text-white',
        }

        payment_methods = {
            'CARD': {'label': 'Tarjeta de credito/debito', 'icon': 'bi bi-credit-card text-primary'},
            'PSE': {'label': 'PSE - Debito bancario', 'icon': 'bi bi-bank text-success'},
            'NEQUI': {'label': 'Nequi', 'icon': 'bi bi-phone text-danger'},
            'BANCOLOMBIA': {'label': 'Bancolombia', 'icon': 'bi bi-building text-warning'},
            'EFECTY': {'label': 'Efecty', 'icon': 'bi bi-cash text-success'},
            'CARD_INSTALLMENT': {'label': 'Tarjeta en cuotas', 'icon': 'bi bi-credit-card text-primary'},
            'WOMPI': {'label': 'Wompi (online)', 'icon': 'bi bi-wallet2 text-secondary'},
            'COD': {'label': 'Pago contra entrega', 'icon': 'bi bi-cash-stack text-warning'},
        }

        service_priorities = {
            'low': {'label': 'Baja', 'class': 'bg-secondary-subtle text-secondary'},
            'medium': {'label': 'Media', 'class': 'bg-info-subtle text-info'},
            'high': {'label': 'Alta', 'class': 'bg-warning-subtle text-warning'},
            'critical': {'label': 'Critica', 'class': 'bg-danger-subtle text-danger'},
        }

        service_order_statuses = {
            OrderServiceTimeline.STATUS_CHOICES[0][0]: {'label': 'Pendiente', 'class': 'bg-secondary-subtle text-secondary border border-secondary-subtle'},
            OrderServiceTimeline.STATUS_CHOICES[1][0]: {'label': 'Asignado', 'class': 'bg-info-subtle text-info border border-info-subtle'},
            OrderServiceTimeline.STATUS_CHOICES[2][0]: {'label': 'En progreso', 'class': 'bg-warning-subtle text-warning border border-warning-subtle'},
            OrderServiceTimeline.STATUS_CHOICES[3][0]: {'label': 'Completado', 'class': 'bg-success-subtle text-success border border-success-subtle'},
            OrderServiceTimeline.STATUS_CHOICES[4][0]: {'label': 'Cancelado', 'class': 'bg-danger-subtle text-danger border border-danger-subtle'},
        }

        rental_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code == RentalRequest.STATUS_DRAFT else
                'bg-info-subtle text-info border border-info-subtle' if code in (RentalRequest.STATUS_PENDING_VALIDATION, RentalRequest.STATUS_CONFIRMED) else
                'bg-warning-subtle text-warning border border-warning-subtle' if code == RentalRequest.STATUS_PENDING_PAYMENT else
                'bg-success-subtle text-success border border-success-subtle' if code in (RentalRequest.STATUS_PAID, RentalRequest.STATUS_FINISHED) else
                'bg-primary-subtle text-primary border border-primary-subtle' if code == RentalRequest.STATUS_IN_OPERATION else
                'bg-danger-subtle text-danger border border-danger-subtle' if code == RentalRequest.STATUS_CANCELLED else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in RentalRequest.STATUS_CHOICES
        }

        quote_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code == 'DRAFT' else
                'bg-primary-subtle text-primary border border-primary-subtle' if code == 'SENT' else
                'bg-success-subtle text-success border border-success-subtle' if code == 'ACCEPTED' else
                'bg-danger-subtle text-danger border border-danger-subtle' if code in ('REJECTED', 'EXPIRED') else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in Quotation.STATUS_CHOICES
        }

        operation_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code in (OperationTicket.STATUS_CREATED, OperationTicket.STATUS_DOCS_PENDING) else
                'bg-primary-subtle text-primary border border-primary-subtle' if code in (OperationTicket.STATUS_READY, OperationTicket.STATUS_ASSIGNED, OperationTicket.STATUS_SCHEDULED) else
                'bg-warning-subtle text-warning border border-warning-subtle' if code in (OperationTicket.STATUS_EN_ROUTE, OperationTicket.STATUS_IN_PROGRESS) else
                'bg-success-subtle text-success border border-success-subtle' if code == OperationTicket.STATUS_COMPLETED else
                'bg-danger-subtle text-danger border border-danger-subtle' if code == OperationTicket.STATUS_CANCELLED else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in OperationTicket.STATUS_CHOICES
        }

        operation_types = {
            code: {'label': label}
            for code, label in OperationTicket.TYPE_CHOICES
        }

        quote_types = {
            'product': {'label': 'Producto'},
            'rental': {'label': 'Alquiler'},
            'service': {'label': 'Servicio'},
            'custom': {'label': 'Personalizado'},
        }

        kyc_verification_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code == UserVerification.STATUS_PENDING else
                'bg-info-subtle text-info border border-info-subtle' if code == UserVerification.STATUS_UNDER_REVIEW else
                'bg-success-subtle text-success border border-success-subtle' if code == UserVerification.STATUS_APPROVED else
                'bg-danger-subtle text-danger border border-danger-subtle' if code == UserVerification.STATUS_REJECTED else
                'bg-dark-subtle text-dark border border-dark-subtle' if code == UserVerification.STATUS_BLOCKED else
                'bg-warning-subtle text-warning border border-warning-subtle' if code == UserVerification.STATUS_EXPIRED else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in UserVerification.STATUS_CHOICES
        }

        service_operation_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code == ServiceOperation.READY_FOR_PLANNING else
                'bg-info-subtle text-info border border-info-subtle' if code in (ServiceOperation.PLANNED, ServiceOperation.TECHNICIAN_ASSIGNED, ServiceOperation.CUSTOMER_NOTIFIED, ServiceOperation.READY_TO_VISIT) else
                'bg-primary-subtle text-primary border border-primary-subtle' if code in (ServiceOperation.ON_THE_WAY, ServiceOperation.ARRIVED) else
                'bg-warning-subtle text-warning border border-warning-subtle' if code == ServiceOperation.IN_PROGRESS else
                'bg-success-subtle text-success border border-success-subtle' if code in (ServiceOperation.COMPLETED, ServiceOperation.CLOSED) else
                'bg-danger-subtle text-danger border border-danger-subtle' if code == ServiceOperation.CANCELLED else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in ServiceOperation.STATUS_CHOICES
        }

        shipment_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code == Shipment.STATUS_PREPARING else
                'bg-info-subtle text-info border border-info-subtle' if code in (Shipment.STATUS_READY_FOR_DISPATCH, Shipment.STATUS_ASSIGNED) else
                'bg-primary-subtle text-primary border border-primary-subtle' if code in (Shipment.STATUS_PICKED_UP, Shipment.STATUS_IN_TRANSIT, Shipment.STATUS_OUT_FOR_DELIVERY) else
                'bg-success-subtle text-success border border-success-subtle' if code in (Shipment.STATUS_DELIVERED, Shipment.STATUS_COMPLETED) else
                'bg-danger-subtle text-danger border border-danger-subtle' if code in (Shipment.STATUS_FAILED_DELIVERY, Shipment.STATUS_LOST) else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in Shipment.STATUS_CHOICES
        }

        kyc_document_statuses = {
            code: {'label': label, 'class': (
                'bg-secondary-subtle text-secondary border border-secondary-subtle' if code == VerificationDocument.STATUS_PENDING else
                'bg-success-subtle text-success border border-success-subtle' if code == VerificationDocument.STATUS_APPROVED else
                'bg-danger-subtle text-danger border border-danger-subtle' if code == VerificationDocument.STATUS_REJECTED else
                'bg-secondary-subtle text-secondary border border-secondary-subtle'
            )}
            for code, label in VerificationDocument.STATUS_CHOICES
        }

        catalog = {
            'order-statuses': order_statuses,
            'payment-statuses': payment_statuses,
            'payment-methods': payment_methods,
            'service-priorities': service_priorities,
            'service-order-statuses': service_order_statuses,
            'rental-statuses': rental_statuses,
            'quote-statuses': quote_statuses,
            'operation-statuses': operation_statuses,
            'operation-types': operation_types,
            'quote-types': quote_types,
            'kyc-verification-statuses': kyc_verification_statuses,
            'kyc-document-statuses': kyc_document_statuses,
            'service-operation-statuses': service_operation_statuses,
            'shipment-statuses': shipment_statuses,
            'order-payment-methods': {code: {'label': label} for code, label in Order.PAYMENT_METHOD_CHOICES},
            'contractor-types': {
                code: {'label': label}
                for code, label in UserProfile.USER_TYPE_CHOICES
            },
            # Usado por el panel admin de usuarios (/panel/usuarios) -- mismo catalogo que
            # 'contractor-types', expuesto con un nombre generico ya que hoy cubre los 7 tipos
            # reales de usuario, no solo contratistas. Incluye 'class' (a diferencia de
            # 'contractor-types') para que useEnums().cssClass() pinte un badge distinto por tipo.
            'user-types': {
                'CUSTOMER':     {'label': 'Cliente',        'class': 'bg-secondary-subtle text-secondary border border-secondary-subtle'},
                'TECHNICIAN':   {'label': 'Técnico',        'class': 'bg-info-subtle text-info border border-info-subtle'},
                'PROFESSIONAL': {'label': 'Profesional',    'class': 'bg-warning-subtle text-warning border border-warning-subtle'},
                'SPECIALIST':   {'label': 'Especialista',   'class': 'bg-success-subtle text-success border border-success-subtle'},
                'CONTRACTOR':   {'label': 'Contratista',    'class': 'bg-dark-subtle text-dark border border-dark-subtle'},
                'TRANSPORTER':  {'label': 'Transportista',  'class': 'bg-primary-subtle text-primary border border-primary-subtle'},
                'ACCOUNTANT':   {'label': 'Contador',       'class': 'bg-danger-subtle text-danger border border-danger-subtle'},
            },
        }

        if name not in catalog:
            return Response({'detail': f'Enum "{name}" no encontrado.'}, status=404)

        return Response({'name': name, 'values': catalog[name]})
