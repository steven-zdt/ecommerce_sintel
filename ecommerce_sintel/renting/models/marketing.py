# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.db import models
from ecommerce.base_models import SintelBaseModel

from .equipment import Equipment

class EquipmentMarketing(SintelBaseModel):
    """
    Configuracion comercial/visual de un equipo para su presentacion publica
    (precio de venta, etiquetas, mensajes de conversion, CTA, banner, etc).

    NO almacena informacion tecnica, inventario, logistica ni disponibilidad
    -- eso vive en Equipment/EquipmentVariant/EquipmentLogisticsConfig. SEO
    (meta_title/meta_description/meta_keywords/og_image) tampoco se duplica
    aqui: ya existe en Equipment (migracion 0022), se reutiliza tal cual.

    OneToOne con Equipment: cada equipo tiene a lo sumo un registro de
    marketing, propio y exclusivo -- no hay herencia, plantillas ni
    configuraciones globales (mismo principio que RentalCostRule, ver
    ARQUITECTURA_COMPLETA_RENTIG.md).
    """

    TAG_OFFER        = 'OFERTA'
    TAG_NEW          = 'NUEVO'
    TAG_MOST_RENTED  = 'MAS_ALQUILADO'
    TAG_PREMIUM      = 'PREMIUM'
    TAG_RECOMMENDED  = 'RECOMENDADO'
    TAG_HOT          = 'HOT'
    TAG_TOP_SELLER   = 'TOP_VENTAS'
    TAG_EVENTS       = 'IDEAL_EVENTOS'
    TAG_LAST_UNITS   = 'ULTIMAS_UNIDADES'
    TAG_CHOICES = [
        (TAG_OFFER,       'Oferta'),
        (TAG_NEW,         'Nuevo'),
        (TAG_MOST_RENTED, 'Mas alquilado'),
        (TAG_PREMIUM,     'Premium'),
        (TAG_RECOMMENDED, 'Recomendado'),
        (TAG_HOT,         'Hot'),
        (TAG_TOP_SELLER,  'Top ventas'),
        (TAG_EVENTS,      'Ideal para eventos'),
        (TAG_LAST_UNITS,  'Ultimas unidades'),
    ]

    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.CASCADE,
        related_name='marketing',
    )

    # Precio comercial
    reference_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='precio de referencia (anterior)',
    )
    promo_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='precio promocional',
    )
    show_discount_percentage = models.BooleanField(
        default=True, verbose_name='mostrar porcentaje de descuento',
    )

    # Etiquetas comerciales -- lista de codigos de TAG_CHOICES.
    tags = models.JSONField(default=list, blank=True, verbose_name='etiquetas comerciales')

    # Mensajes de conversion (texto libre, sin catalogo cerrado -- los
    # "ejemplos" del panel son solo sugerencias, no opciones fijas).
    main_message = models.TextField(blank=True, default='', verbose_name='mensaje principal')
    featured_benefit = models.CharField(max_length=255, blank=True, default='', verbose_name='beneficio destacado')
    trust_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje de confianza')
    urgency_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje de urgencia')
    social_proof_message = models.CharField(max_length=255, blank=True, default='', verbose_name='prueba social')

    # Comparativa economica (comprar vs alquilar)
    purchase_price_reference = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='precio estimado de compra',
    )
    financial_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje financiero')

    # Casos de uso -- lista libre de strings (ej. ["Eventos", "Construccion"]).
    use_cases = models.JSONField(default=list, blank=True, verbose_name='casos de uso')

    # Call To Action del boton principal de alquiler.
    cta_label = models.CharField(max_length=100, blank=True, default='', verbose_name='texto del CTA')

    # Banner promocional -- un unico mensaje, se muestra solo si esta configurado.
    promo_banner_message = models.CharField(max_length=255, blank=True, default='', verbose_name='banner promocional')

    # Beneficios rapidos -- lista de {"icon": "bi-truck", "label": "..."}.
    quick_benefits = models.JSONField(default=list, blank=True, verbose_name='beneficios rapidos')

    class Meta:
        verbose_name = 'marketing de equipo'
        verbose_name_plural = 'marketing de equipos'

    def __str__(self):
        return f"Marketing -- {self.equipment.name}"

