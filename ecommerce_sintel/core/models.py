from django.db import models
from django.core.exceptions import ValidationError
from ecommerce.base_models import SintelBaseModel


class HomeBanner(SintelBaseModel):
    """Banner de cabecera para la pagina principal publica."""
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True, default='')
    eyebrow = models.CharField(max_length=150, blank=True, default='')
    image = models.ImageField(upload_to='home_banners/images/', null=True, blank=True)
    video = models.FileField(upload_to='home_banners/videos/', null=True, blank=True)
    background_color = models.CharField(max_length=30, blank=True, default='')
    link_url = models.CharField(max_length=500, blank=True, default='')
    link_label = models.CharField(max_length=150, blank=True, default='')
    cta_ghost_label = models.CharField(max_length=150, blank=True, default='')
    cta_ghost_url = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = 'banner de inicio'
        verbose_name_plural = 'banners de inicio'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        """Validar que link_label es requerido si link_url existe."""
        errors = {}
        
        if self.link_url and not self.link_label:
            errors['link_label'] = 'El texto del enlace es requerido cuando se proporciona una URL.'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class HomeModuleConfig(SintelBaseModel):
    """Visibilidad y orden de los modulos mostrados en la Home publica."""
    MODULE_SHOP     = 'shop'
    MODULE_RENTING  = 'renting'
    MODULE_SERVICES = 'services'
    MODULE_QUOTES   = 'quotes'

    MODULE_CHOICES = [
        (MODULE_SHOP,     'Tienda'),
        (MODULE_RENTING,  'Alquiler de Equipos'),
        (MODULE_SERVICES, 'Servicios Tecnicos'),
        (MODULE_QUOTES,   'Cotizaciones'),
    ]

    MODULE_META = {
        MODULE_SHOP:     {'label': 'Tienda',       'url': '/tienda',    'icon': 'bi-shop',             'color': '#3b82f6'},
        MODULE_RENTING:  {'label': 'Alquiler',     'url': '/alquiler',  'icon': 'bi-truck',            'color': '#8b5cf6'},
        MODULE_SERVICES: {'label': 'Servicios',    'url': '/servicios', 'icon': 'bi-tools',            'color': '#f59e0b'},
        MODULE_QUOTES:   {'label': 'Cotizaciones', 'url': '/cotizar',   'icon': 'bi-file-earmark-text','color': '#10b981'},
    }

    module_key = models.CharField(max_length=40, unique=True)
    is_visible = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    featured_items_limit = models.PositiveIntegerField(default=8)
    custom_label      = models.CharField(max_length=255, blank=True, default='')
    custom_icon       = models.CharField(max_length=100, blank=True, default='')
    custom_url        = models.CharField(max_length=300, blank=True, default='')
    custom_color      = models.CharField(max_length=30,  blank=True, default='')
    background_image  = models.ImageField(upload_to='home_modules/images/', null=True, blank=True)

    # Visual Builder fields
    DISPLAY_GRID        = 'grid'
    DISPLAY_GRID_MODERN = 'grid_modern'
    DISPLAY_SLIDER      = 'slider'
    DISPLAY_CAROUSEL    = 'carousel'
    DISPLAY_CARDS_H     = 'cards_h'
    DISPLAY_CARDS_V     = 'cards_v'
    DISPLAY_HERO        = 'hero'
    DISPLAY_BANNER      = 'banner'
    DISPLAY_LIST        = 'list'
    DISPLAY_TIMELINE    = 'timeline'
    DISPLAY_ACCORDION   = 'accordion'
    DISPLAY_TABS        = 'tabs'
    DISPLAY_MASONRY     = 'masonry'
    DISPLAY_HIGHLIGHT   = 'highlight'
    DISPLAY_PREMIUM     = 'premium'
    DISPLAY_COMPACT     = 'compact'
    DISPLAY_SPLIT       = 'split'
    DISPLAY_MINIMAL     = 'minimal'
    DISPLAY_CHOICES = [
        (DISPLAY_GRID,        'Grid'),
        (DISPLAY_GRID_MODERN, 'Grid moderno'),
        (DISPLAY_SLIDER,      'Slider'),
        (DISPLAY_CAROUSEL,    'Carrusel'),
        (DISPLAY_CARDS_H,     'Cards Horizontales'),
        (DISPLAY_CARDS_V,     'Cards Verticales'),
        (DISPLAY_HERO,        'Hero'),
        (DISPLAY_BANNER,      'Banner'),
        (DISPLAY_LIST,        'Lista'),
        (DISPLAY_TIMELINE,    'Timeline'),
        (DISPLAY_ACCORDION,   'Accordion'),
        (DISPLAY_TABS,        'Tabs'),
        (DISPLAY_MASONRY,     'Masonry'),
        (DISPLAY_HIGHLIGHT,   'Destacados'),
        (DISPLAY_PREMIUM,     'Premium Cards'),
        (DISPLAY_COMPACT,     'Compacto'),
        (DISPLAY_SPLIT,       'Split Layout'),
        (DISPLAY_MINIMAL,     'Minimalista'),
    ]
    display_type  = models.CharField(max_length=30, default=DISPLAY_GRID, choices=DISPLAY_CHOICES)
    layout_config = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'configuracion de modulo en home'
        verbose_name_plural = 'configuracion de modulos en home'
        ordering = ['display_order']

    def __str__(self):
        return f"{self.module_key} (visible={self.is_visible})"

    def clean(self):
        """Validar que module_key es valido O que custom fields estan configurados."""
        errors = {}
        valid_keys = list(self.MODULE_META.keys())
        
        if self.module_key not in valid_keys:
            # Si la clave no es válida, los custom fields deben estar completos
            missing_fields = []
            if not self.custom_label:
                missing_fields.append('custom_label')
            if not self.custom_url:
                missing_fields.append('custom_url')
            if not self.custom_icon:
                missing_fields.append('custom_icon')
            
            if missing_fields:
                errors['module_key'] = (
                    f"El módulo '{self.module_key}' no es válido. "
                    f"Opciones válidas: {', '.join(valid_keys)}. "
                    f"O completa estos campos: {', '.join(missing_fields)}"
                )
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class HomeCard(SintelBaseModel):
    """Tarjeta informativa flat-design para la pagina principal publica."""
    title            = models.CharField(max_length=255)
    subtitle         = models.CharField(max_length=500, blank=True, default='')
    description      = models.TextField(blank=True, default='')
    group_name       = models.CharField(max_length=150, db_index=True)
    icon_class       = models.CharField(max_length=100, default='bi-star')
    background_color = models.CharField(max_length=30, default='#3b82f6')
    image            = models.ImageField(upload_to='home_cards/images/', null=True, blank=True)
    video            = models.FileField(upload_to='home_cards/videos/', null=True, blank=True)
    redirect_url     = models.CharField(max_length=500, blank=True, default='')
    display_order    = models.PositiveIntegerField(default=0, db_index=True)
    is_active        = models.BooleanField(default=True, db_index=True)

    # Visual Builder fields
    CARD_TYPE_VERTICAL   = 'vertical'
    CARD_TYPE_HORIZONTAL = 'horizontal'
    CARD_TYPE_PREMIUM    = 'premium'
    CARD_TYPE_COMPACT    = 'compact'
    CARD_TYPE_GLASS      = 'glass'
    CARD_TYPE_DARK       = 'dark'
    CARD_TYPE_GRADIENT   = 'gradient'
    CARD_TYPE_IMAGE_BG   = 'image_bg'
    CARD_TYPE_LOGO       = 'logo'
    CARD_TYPE_CHOICES = [
        (CARD_TYPE_VERTICAL,   'Vertical'),
        (CARD_TYPE_HORIZONTAL, 'Horizontal'),
        (CARD_TYPE_PREMIUM,    'Premium'),
        (CARD_TYPE_COMPACT,    'Compacta'),
        (CARD_TYPE_GLASS,      'Glass'),
        (CARD_TYPE_DARK,       'Dark'),
        (CARD_TYPE_GRADIENT,   'Gradient'),
        (CARD_TYPE_IMAGE_BG,   'Imagen de fondo'),
        (CARD_TYPE_LOGO,       'Logo de cliente'),
    ]
    card_type   = models.CharField(max_length=30, default=CARD_TYPE_VERTICAL, choices=CARD_TYPE_CHOICES)
    animation   = models.CharField(max_length=30, blank=True, default='')
    is_featured = models.BooleanField(default=False, db_index=True)
    priority    = models.PositiveIntegerField(default=0)
    badge_text  = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        verbose_name = 'tarjeta de inicio'
        verbose_name_plural = 'tarjetas de inicio'
        ordering = ['group_name', 'display_order']

    def __str__(self):
        return f"[{self.group_name}] {self.title}"


class HomeCardGroup(SintelBaseModel):
    """Titulo editable y configuracion visual de cada grupo de tarjetas."""
    LAYOUT_GRID      = 'grid'
    LAYOUT_SLIDER    = 'slider'
    LAYOUT_CARDS     = 'cards'
    LAYOUT_TIMELINE  = 'timeline'
    LAYOUT_TABS      = 'tabs'
    LAYOUT_ACCORDION = 'accordion'
    LAYOUT_LOGOS     = 'logos'
    LAYOUT_MARQUEE   = 'marquee'
    LAYOUT_CHOICES = [
        (LAYOUT_GRID,      'Grid'),
        (LAYOUT_SLIDER,    'Slider'),
        (LAYOUT_CARDS,     'Cards'),
        (LAYOUT_TIMELINE,  'Timeline'),
        (LAYOUT_TABS,      'Tabs'),
        (LAYOUT_ACCORDION, 'Accordion'),
        (LAYOUT_LOGOS,     'Logos de clientes'),
        (LAYOUT_MARQUEE,   'Marquee (rotacion automatica)'),
    ]

    HOVER_LIFT = 'lift'
    HOVER_SCALE = 'scale'
    HOVER_GLOW = 'glow'
    HOVER_NONE = 'none'
    HOVER_CHOICES = [
        (HOVER_LIFT,  'Elevar'),
        (HOVER_SCALE, 'Escalar'),
        (HOVER_GLOW,  'Resplandor'),
        (HOVER_NONE,  'Ninguno'),
    ]

    PADDING_NONE   = 'none'
    PADDING_SM     = 'sm'
    PADDING_NORMAL = 'normal'
    PADDING_LG     = 'lg'
    PADDING_XL     = 'xl'
    PADDING_CHOICES = [
        (PADDING_NONE,   'Sin padding'),
        (PADDING_SM,     'Pequeno'),
        (PADDING_NORMAL, 'Normal'),
        (PADDING_LG,     'Grande'),
        (PADDING_XL,     'Extra grande'),
    ]

    name          = models.CharField(max_length=150, unique=True, db_index=True)
    title         = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_visible    = models.BooleanField(default=True, db_index=True)

    # Visual Builder fields
    subtitle     = models.CharField(max_length=500, blank=True, default='')
    description  = models.TextField(blank=True, default='')
    bg_color     = models.CharField(max_length=30, blank=True, default='')
    bg_image     = models.ImageField(upload_to='home_groups/', null=True, blank=True)
    layout_type  = models.CharField(max_length=30, default=LAYOUT_GRID, choices=LAYOUT_CHOICES)
    padding      = models.CharField(max_length=20, default=PADDING_NORMAL, choices=PADDING_CHOICES)
    divider      = models.BooleanField(default=False)
    columns      = models.PositiveSmallIntegerField(default=3)
    glass        = models.BooleanField(default=False)
    hover        = models.CharField(max_length=20, default=HOVER_LIFT, choices=HOVER_CHOICES)

    class Meta:
        verbose_name = 'grupo de tarjetas'
        verbose_name_plural = 'grupos de tarjetas'
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} -> {self.title}"


class FooterCTAConfig(SintelBaseModel):
    """Bloque CTA final antes del footer. Singleton (solo un registro activo)."""
    eyebrow           = models.CharField(max_length=150, blank=True, default='Empieza hoy')
    title_prefix      = models.CharField(max_length=255, blank=True, default='Impulsa tu empresa con')
    title_highlighted = models.CharField(max_length=255, blank=True, default='Sintel Technology')
    subtitle          = models.CharField(max_length=500, blank=True,
                            default='Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.')
    btn_primary_label = models.CharField(max_length=150, blank=True, default='Solicitar cotizacion')
    btn_primary_url   = models.CharField(max_length=300, blank=True, default='/cotizar')
    btn_ghost_label   = models.CharField(max_length=150, blank=True, default='Explorar catalogo')
    btn_ghost_url     = models.CharField(max_length=300, blank=True, default='/tienda')
    is_active         = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'config CTA final'
        verbose_name_plural = 'config CTA final'

    def __str__(self):
        return self.title_highlighted

    def save(self, *args, **kwargs):
        if self.is_active:
            FooterCTAConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class FooterGroup(SintelBaseModel):
    """Columna del footer publico: agrupa FooterLink(category='nav')."""
    title            = models.CharField(max_length=150)
    icon_class       = models.CharField(max_length=100, blank=True, default='bi-folder')
    description      = models.CharField(max_length=500, blank=True, default='')
    background_color = models.CharField(max_length=30, blank=True, default='')
    text_color       = models.CharField(max_length=30, blank=True, default='')
    display_order    = models.PositiveIntegerField(default=0, db_index=True)
    is_active        = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'grupo del footer'
        verbose_name_plural = 'grupos del footer'
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title


class FooterLink(SintelBaseModel):
    """Enlace dinamico del footer: red social o columna de navegacion."""
    CATEGORY_SOCIAL = 'social'
    CATEGORY_NAV    = 'nav'
    CATEGORY_CHOICES = [
        (CATEGORY_SOCIAL, 'Red Social'),
        (CATEGORY_NAV,    'Navegacion'),
    ]

    title         = models.CharField(max_length=255)
    url           = models.CharField(max_length=500)
    category      = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default=CATEGORY_NAV, db_index=True)
    group         = models.ForeignKey(FooterGroup, related_name='links', on_delete=models.CASCADE)
    icon_class    = models.CharField(max_length=100, blank=True, default='')
    open_new_tab  = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active     = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'enlace del footer'
        verbose_name_plural = 'enlaces del footer'
        ordering = ['category', 'display_order']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class NavbarLink(SintelBaseModel):
    """Enlace del navbar publico principal."""
    label           = models.CharField(max_length=150)
    url             = models.CharField(max_length=300)
    icon_class      = models.CharField(max_length=100, blank=True, default='')
    display_order   = models.PositiveIntegerField(default=0, db_index=True)
    is_visible      = models.BooleanField(default=True, db_index=True)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'enlace del navbar'
        verbose_name_plural = 'enlaces del navbar'
        ordering = ['display_order']

    def __str__(self):
        return self.label


class BrandSliderItem(SintelBaseModel):
    """Logo individual del slider de marcas/clientes de la Home publica."""
    name          = models.CharField(max_length=150)
    logo          = models.ImageField(upload_to='brand_slider/logos/', null=True, blank=True)
    website       = models.CharField(max_length=500, blank=True, default='')
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active     = models.BooleanField(default=True, db_index=True)
    open_new_tab  = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'logo de slider de marcas'
        verbose_name_plural = 'logos de slider de marcas'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.name


class AboutUsConfig(SintelBaseModel):
    """Contenido de la pagina publica 'Sobre Nosotros'. Singleton (una unica fila)."""
    title      = models.CharField(max_length=255, blank=True, default='Sobre Nosotros')
    subtitle   = models.CharField(max_length=500, blank=True, default='')
    hero_image = models.ImageField(upload_to='about_us/hero/', null=True, blank=True)
    history    = models.TextField(blank=True, default='')
    mission    = models.TextField(blank=True, default='')
    vision     = models.TextField(blank=True, default='')
    is_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'config de Sobre Nosotros'
        verbose_name_plural = 'config de Sobre Nosotros'

    def __str__(self):
        return self.title


class AboutUsValue(SintelBaseModel):
    """Valor/pilar de la filosofia institucional mostrado en 'Sobre Nosotros'."""
    title         = models.CharField(max_length=150)
    description   = models.TextField(blank=True, default='')
    icon_class    = models.CharField(max_length=100, default='bi-gem')
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active     = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'valor institucional'
        verbose_name_plural = 'valores institucionales'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title


class BrandSliderConfig(SintelBaseModel):
    """Configuracion del slider de marcas/clientes. Singleton (una unica fila)."""
    DIRECTION_LEFT = 'left'
    DIRECTION_RIGHT = 'right'
    DIRECTION_CHOICES = [
        (DIRECTION_LEFT,  'Izquierda'),
        (DIRECTION_RIGHT, 'Derecha'),
    ]

    PADDING_CHOICES = HomeCardGroup.PADDING_CHOICES

    title            = models.CharField(max_length=255, blank=True, default='Marcas y clientes')
    subtitle         = models.CharField(max_length=500, blank=True, default='')
    autoplay         = models.BooleanField(default=True)
    speed            = models.PositiveIntegerField(default=3500)
    direction        = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default=DIRECTION_LEFT)
    loop             = models.BooleanField(default=True)
    pause_on_hover   = models.BooleanField(default=True)
    items_desktop    = models.PositiveSmallIntegerField(default=6)
    items_tablet     = models.PositiveSmallIntegerField(default=4)
    items_mobile     = models.PositiveSmallIntegerField(default=2)
    background_color = models.CharField(max_length=30, blank=True, default='')
    padding_top      = models.CharField(max_length=20, choices=PADDING_CHOICES, default=HomeCardGroup.PADDING_NORMAL)
    padding_bottom   = models.CharField(max_length=20, choices=PADDING_CHOICES, default=HomeCardGroup.PADDING_NORMAL)
    is_visible       = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'config de slider de marcas'
        verbose_name_plural = 'config de slider de marcas'

    def __str__(self):
        return self.title
