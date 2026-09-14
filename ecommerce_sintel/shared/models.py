"""
shared/models.py

Modelos genericos, reutilizables por cualquier app de catalogo (Product/Equipment/
TechnicalService), creados para la Fase 3 de la reingenieria UX/UI del modulo Shop
(ver DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md). En esta fase solo se conectan
endpoints/serializers para Shop -- el diseno generico es intencional para que
Renting/Technical Services puedan sumarse despues sin duplicar estos modelos
(Regla 6 del brief).
"""
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.contenttypes.models import ContentType
from ecommerce.base_models import SintelBaseModel


class SingletonMixin(models.Model):
    """
    Desactiva cualquier otro registro activo al guardar uno nuevo como activo.
    Requiere que el modelo concreto tenga un campo `is_active`.

    Consolidado aqui 2026-08-05 (Sprint 2, auditoria transversal) -- antes existian
    4 copias identicas de este mismo `save()` de 3 lineas: `organization.SingletonMixin`
    (original), `core.FooterCTAConfig.save()`, `payment.PaymentFeatureFlags.save()`, y
    la ausencia total del patron en `core.AboutUsConfig`/`BrandSliderConfig` (que usaban
    "get-or-create" sin proteccion de carrera -- ver auditoria transversal, hallazgo de
    Fase 3). Vive en `shared` (no en `organization`) a proposito: `organization.CLAUDE.md`
    prohibe explicitamente que otra app importe sus modelos (regla SSoT de datos
    institucionales), y `payment.PaymentFeatureFlags` ya documentaba por que evitaba ese
    import cruzado ("se duplica aqui en vez de importarlo... para no crear dependencias
    cruzadas"). `shared` es el lugar ya establecido para mixins/modelos genericos
    reutilizables entre apps (mismo criterio que `ContentBlockConfig`/`CatalogRelation`
    arriba) -- no es dato de negocio de ninguna app, asi que no viola esa regla.
    `organization.models.SingletonMixin` ahora reexporta este mismo mixin en vez de
    definirlo por segunda vez.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.is_active:
            type(self).objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class AbstractCostRule(SintelBaseModel):
    """
    Base compartida de las reglas de costo por variante (IVA/descuento/deposito/etc.)
    usadas por Shop/Renting/Technical Services. Consolidado 2026-08-05 (Sprint 2,
    auditoria transversal) -- `name`/`description`/`cost_type`/`value`/`is_active` y el
    tipo de costo (fijo/porcentaje) eran identicos byte a byte en las 3 apps.

    `context` (CharField con CONTEXT_CHOICES) y `applies_globally` (solo en Shop/Services;
    Renting lo elimino deliberadamente en la migracion 0027, ver renting/CLAUDE.md) NO
    estan aqui a proposito -- cada app tiene su propia taxonomia de contexto (Renting
    incluye DEPOSIT/INSURANCE/SURCHARGE que Shop/Services no tienen) y su propia regla de
    negocio sobre reglas globales; unificarlos seria un cambio de comportamiento, no de
    arquitectura, y esta fuera del alcance de este sprint (solo documentacion/estructura,
    sin tocar reglas de negocio). Cada subclase concreta declara su propio `context`.
    """
    TYPE_FIXED = 'FIXED'
    TYPE_PERCENTAGE = 'PERCENTAGE'
    COST_TYPE_CHOICES = [
        (TYPE_FIXED, 'Valor fijo (COP)'),
        (TYPE_PERCENTAGE, 'Porcentaje (%)'),
    ]

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    cost_type = models.CharField(max_length=10, choices=COST_TYPE_CHOICES, db_index=True)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.name} ({self.context})"


class AbstractCostAssignment(SintelBaseModel):
    """
    Base compartida de la asignacion de una regla de costo a una variante. `rule`/
    `variant` no estan aqui -- cada app apunta a su propio modelo de regla/variante
    (`RentalCostRule`/`EquipmentVariant`, etc.), y Django no soporta una FK abstracta con
    destino dinamico sin GenericForeignKey (deliberadamente evitado en este proyecto, ver
    docstring de `ContentBlockConfig`). Cada subclase concreta declara ambas FKs y su
    propio `Meta.unique_together = ('rule', 'variant')`.
    """

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.rule.name} -> {self.variant.sku}"


class AbstractReview(SintelBaseModel):
    """
    Base compartida de las resenas de catalogo (Sprint 6, evaluacion 2026-08-05, ver
    PLAN_SPRINT6_EVALUACION_2026-08-05.md #1.3) -- consolida `rating`/`comment`/`user`,
    identicos byte a byte en `ProductReview`/`EquipmentReview`/`ServiceReview`. Deliberadamente
    NO via ContentType+uuid (el patron de ContentBlockConfig): 2 de los 3 dominios agregan
    `Avg('reviews__rating')` sobre la relacion inversa por FK, que se rompe si se pasa a un
    modelo generico -- mismo criterio ya usado en Sprint 2 para AbstractCostRule. Cada
    subclase concreta declara su propio FK a la entidad calificada (con
    `related_name='reviews'`, sin cambios respecto al codigo pre-Sprint-6) y su propio
    `Meta.unique_together`.

    `accounts.ContractorReview` NO hereda de esta clase a proposito -- califica una persona en
    5 dimensiones independientes (calidad/puntualidad/profesionalismo/comunicacion/
    cumplimiento), no una sola escala 1-5 sobre un item de catalogo; forzarlo aqui habria sido
    una unificacion superficial de nombre, no de forma real (ver PLAN_SPRINT6_EVALUACION
    #1.2).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.user_id} -> {self.rating}"


class ContentBlockConfig(SintelBaseModel):
    """
    Orquesta orden y visibilidad de los bloques de contenido del detalle publico
    (PDP) de una entidad de catalogo. No almacena contenido -- el contenido real
    sigue viviendo en los modelos ya existentes de cada catalogo enriquecido
    (ProductIncludedItem, ProductFAQ, etc.). Sin fila para un
    (content_type, object_uuid, block_type) dado, el bloque se considera visible
    con el orden por defecto de BLOCK_TYPE_CHOICES -- asi los productos existentes
    no requieren backfill al desplegar esto.

    object_uuid guarda el `uuid` de la entidad (Product.uuid), NUNCA su `pk`
    autoincremental -- todo el proyecto identifica entidades publicamente por uuid.
    Por eso deliberadamente NO se usa GenericForeignKey (Django la empareja contra
    `pk`, no contra `uuid` -- mismo problema ya documentado en
    inventory.StockRecord.item_variant). Resolver el objeto real con un
    `.filter(uuid=object_uuid)` explicito sobre `content_type.model_class()`.
    """
    BLOCK_DESCRIPTION = 'description'
    BLOCK_SCOPE = 'scope'
    BLOCK_INCLUDED = 'included'
    BLOCK_EXCLUDED = 'excluded'
    BLOCK_INSTALLATION = 'installation'
    BLOCK_FUNCTIONING = 'functioning'
    BLOCK_SUPPORT = 'support'
    BLOCK_BENEFITS = 'benefits'
    BLOCK_WARRANTY = 'warranty'
    BLOCK_SPECS = 'specs'
    BLOCK_DOCUMENTS = 'documents'
    BLOCK_VIDEOS = 'videos'
    BLOCK_FAQ = 'faq'
    BLOCK_COMPATIBLE = 'compatible'
    BLOCK_ACCESSORIES = 'accessories'
    BLOCK_RELATED = 'related'
    # Bloques propios de Technical Services (2026-08-05, reingenieria SDP) -- sin
    # equivalente en Shop, agregados aca (no en un segundo modelo) para que
    # ContentBlockConfig siga siendo el unico catalogo de tipos de bloque,
    # independiente del content_type que lo use (Regla 6 del brief: generico).
    BLOCK_COVERAGE = 'coverage'
    BLOCK_PROCESS = 'process'
    BLOCK_MATERIALS = 'materials'
    BLOCK_TECHNICIANS = 'technicians'
    BLOCK_RECOMMENDED_PRODUCTS = 'recommended_products'

    # Orden por defecto de Shop -- tabla de 15 bloques de
    # DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md SS2.
    BLOCK_TYPE_CHOICES = [
        (BLOCK_DESCRIPTION, 'Descripcion general'),
        (BLOCK_SCOPE, 'Alcance'),
        (BLOCK_INCLUDED, 'Que incluye'),
        (BLOCK_EXCLUDED, 'Que NO incluye'),
        (BLOCK_INSTALLATION, 'Instalacion'),
        (BLOCK_FUNCTIONING, 'Como funciona'),
        (BLOCK_SUPPORT, 'Soporte'),
        (BLOCK_BENEFITS, 'Beneficios'),
        (BLOCK_WARRANTY, 'Garantia'),
        (BLOCK_SPECS, 'Ficha tecnica'),
        (BLOCK_DOCUMENTS, 'Documentacion'),
        (BLOCK_VIDEOS, 'Videos'),
        (BLOCK_FAQ, 'FAQ'),
        (BLOCK_COMPATIBLE, 'Productos compatibles'),
        (BLOCK_ACCESSORIES, 'Accesorios recomendados'),
        (BLOCK_RELATED, 'Productos relacionados'),
        (BLOCK_COVERAGE, 'Cobertura'),
        (BLOCK_PROCESS, 'Proceso del servicio'),
        (BLOCK_MATERIALS, 'Materiales utilizados'),
        (BLOCK_TECHNICIANS, 'Tecnicos especializados'),
        (BLOCK_RECOMMENDED_PRODUCTS, 'Productos recomendados'),
    ]
    DEFAULT_ORDER = [choice[0] for choice in BLOCK_TYPE_CHOICES[:16]]

    # Orden por defecto de Technical Services -- mismo mecanismo, taxonomia propia
    # (ver technical_services/.AGENT/docs/UI_MODULO_SERVICES.md). resolve_for()
    # recibe esto explicitamente via el parametro `default_order` -- DEFAULT_ORDER
    # de arriba sigue siendo el default implicito para no romper el call site de
    # Shop (shop/api/serializers.py::get_content_blocks no pasa default_order).
    #
    # BLOCK_SUPPORT deliberadamente NO esta en esta lista (auditoria FASE 7,
    # 2026-08-14): en Shop "Soporte" tiene backing real (Product.services_included/
    # optional_services) y ServiceDetailContent.vue no. Estaba incluido antes sin
    # backing data para Services -- el admin podia reordenar/ocultar un bloque
    # "Soporte" en ContentBlocksTab que ServiceDetailContent.vue nunca renderizaba
    # (ningun blockVisible('support') en el .vue) y sin tab propio para editarlo
    # (ENTITY_CONFIG.service.ownTab no lo mapea). Bloque fantasma sin efecto real,
    # eliminado en vez de inventarle contenido -- mismo principio que elimino
    # SERVICE_FALLBACK en la reingenieria SDP 2026-08-05.
    SERVICE_DEFAULT_ORDER = [
        BLOCK_DESCRIPTION, BLOCK_SCOPE, BLOCK_INCLUDED, BLOCK_EXCLUDED,
        BLOCK_INSTALLATION, BLOCK_BENEFITS, BLOCK_WARRANTY,
        BLOCK_COVERAGE, BLOCK_SPECS, BLOCK_PROCESS, BLOCK_MATERIALS,
        BLOCK_TECHNICIANS, BLOCK_DOCUMENTS, BLOCK_VIDEOS, BLOCK_FAQ,
        BLOCK_COMPATIBLE, BLOCK_RELATED, BLOCK_RECOMMENDED_PRODUCTS,
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_uuid = models.UUIDField(db_index=True)
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPE_CHOICES, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'configuracion de bloque de contenido'
        verbose_name_plural = 'configuraciones de bloques de contenido'
        unique_together = ('content_type', 'object_uuid', 'block_type')
        ordering = ['display_order']

    def __str__(self):
        return f"{self.content_type.model}:{self.object_uuid} -- {self.block_type}"


class CatalogRelation(SintelBaseModel):
    """
    Relacion entre dos entidades de catalogo, para los bloques "Productos
    compatibles", "Accesorios recomendados" y "Productos relacionados" -- un solo
    modelo para los 3 porque son la misma forma de dato (referencia a otra entidad
    + tipo de relacion), no 3 conceptos distintos. Ver
    DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md SS3.3.

    Igual que ContentBlockConfig: identifica ambos lados por uuid, no por pk, y no
    usa GenericForeignKey por la misma razon (ver docstring de arriba).

    related_content_type/related_object_uuid permiten relacion cruzada entre
    modulos (ej. accesorio de Renting para un producto de Shop) sin cambiar el
    esquema a futuro -- en esta fase solo se usa Shop-a-Shop (Regla 6 del brief).
    """
    RELATION_RELATED = 'related'
    RELATION_COMPATIBLE = 'compatible'
    RELATION_ACCESSORY = 'accessory'
    RELATION_TYPE_CHOICES = [
        (RELATION_RELATED, 'Relacionado'),
        (RELATION_COMPATIBLE, 'Compatible'),
        (RELATION_ACCESSORY, 'Accesorio'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='catalog_relations_from')
    object_uuid = models.UUIDField(db_index=True)
    related_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='catalog_relations_to')
    related_object_uuid = models.UUIDField(db_index=True)
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPE_CHOICES, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'relacion de catalogo'
        verbose_name_plural = 'relaciones de catalogo'
        unique_together = (
            'content_type', 'object_uuid', 'related_content_type', 'related_object_uuid', 'relation_type',
        )
        ordering = ['display_order']

    def __str__(self):
        return f"{self.content_type.model}:{self.object_uuid} -- {self.relation_type} -> {self.related_content_type.model}:{self.related_object_uuid}"
