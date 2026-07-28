from django.db.models import Count, QuerySet
from quotes.models import (
    Quotation, QuoteTemplateCategory, QuoteTemplateSubcategory, QuoteTemplate,
    QuoteTemplateAttribute, QuoteEquipmentType, QuoteTemplateModule,
    QuoteQuestion, QuoteQuestionOption,
)


class QuotationSelector:
    @staticmethod
    def list_all_for_admin() -> QuerySet:
        # select_related('template'): QuotationListSerializer expone template_name
        # (source='template.name') -- sin esto cada cotizacion listada disparaba 2 queries
        # extra (recarga de campo diferido de template_id + fetch del template). Verificado
        # el 2026-07-03: 7 queries para 2 cotizaciones antes del fix, 2 despues.
        return (
            Quotation.objects
            .filter(is_deleted=False)
            .select_related('template')
            .annotate(attachments_count=Count('attachments', distinct=True))
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> Quotation:
        return (
            Quotation.objects
            .select_related('template')
            .prefetch_related(
                'items__cost_snapshots',
                'services__materials',
                'rental_items',
                'attachments',
                'timeline_events__changed_by',
            )
            .get(uuid=uuid, is_deleted=False)
        )


# ─── Cuestionarios tecnicos: Selectors de definicion de plantillas ───────────

TEMPLATE_TREE_PREFETCH = (
    'modules__questions__options',
    # Evita N+1 en QuoteQuestionSerializer.get_depends_on_question_key()
    # (Fase F, PLAN_MAESTRO_QUOTES_UX.md) -- una query extra por pregunta
    # dependiente sin esto.
    'modules__questions__depends_on_question',
)


class QuoteTemplateCategorySelector:
    @staticmethod
    def list_all() -> QuerySet:
        return (
            QuoteTemplateCategory.objects
            .filter(is_deleted=False)
            .select_related('service_type')
            .order_by('display_order', 'name')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteTemplateCategory:
        return QuoteTemplateCategory.objects.get(uuid=uuid, is_deleted=False)


class QuoteTemplateSubcategorySelector:
    @staticmethod
    def list_for_category(category_uuid: str) -> QuerySet:
        return (
            QuoteTemplateSubcategory.objects
            .filter(category__uuid=category_uuid, is_deleted=False)
            .order_by('display_order', 'name')
        )

    @staticmethod
    def list_all() -> QuerySet:
        return QuoteTemplateSubcategory.objects.filter(is_deleted=False).select_related('category').order_by('display_order', 'name')

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteTemplateSubcategory:
        return QuoteTemplateSubcategory.objects.get(uuid=uuid, is_deleted=False)


TEMPLATE_ATTRIBUTE_RELATED = ('category', 'category__service_type', 'subcategory', 'installation_type', 'system_type')


class QuoteTemplateSelector:
    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return (
            QuoteTemplate.objects
            .filter(is_deleted=False)
            .select_related(*TEMPLATE_ATTRIBUTE_RELATED)
            .order_by('display_order', 'name')
        )

    @staticmethod
    def list_active() -> QuerySet:
        return (
            QuoteTemplate.objects
            .filter(
                is_deleted=False, is_active=True, is_published=True,
                is_internal=False, category__is_active=True,
            )
            .select_related(*TEMPLATE_ATTRIBUTE_RELATED)
            .order_by('display_order', 'name')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteTemplate:
        # Usado solo por el retrieve() publico de QuoteTemplateViewSet -- por
        # eso tambien excluye is_internal=True aqui (no solo en list_active),
        # para que una plantilla de QA no sea accesible ni siquiera conociendo
        # su UUID directamente (ver H5, auditoria E2E 2026-07-23).
        return (
            QuoteTemplate.objects
            .select_related(*TEMPLATE_ATTRIBUTE_RELATED)
            .prefetch_related(*TEMPLATE_TREE_PREFETCH)
            .get(uuid=uuid, is_deleted=False, is_internal=False)
        )


class QuoteTemplateAttributeSelector:
    @staticmethod
    def list_all(kind: str = None, subcategory: str = None) -> QuerySet:
        qs = (
            QuoteTemplateAttribute.objects
            .filter(is_deleted=False)
            .select_related('subcategory')
            .order_by('kind', 'display_order', 'name')
        )
        if kind:
            qs = qs.filter(kind=kind)
        if subcategory:
            qs = qs.filter(subcategory__uuid=subcategory)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteTemplateAttribute:
        return QuoteTemplateAttribute.objects.get(uuid=uuid, is_deleted=False)


class QuoteEquipmentTypeSelector:
    @staticmethod
    def list_all() -> QuerySet:
        return QuoteEquipmentType.objects.filter(is_deleted=False).order_by('display_order', 'name')

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteEquipmentType:
        return QuoteEquipmentType.objects.get(uuid=uuid, is_deleted=False)


class QuoteTemplateModuleSelector:
    @staticmethod
    def list_for_template(template_uuid: str, module_type: str = None) -> QuerySet:
        qs = (
            QuoteTemplateModule.objects
            .filter(template__uuid=template_uuid, is_deleted=False)
            .select_related('equipment_type')
            .order_by('display_order', 'id')
        )
        if module_type:
            qs = qs.filter(module_type=module_type)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteTemplateModule:
        return QuoteTemplateModule.objects.get(uuid=uuid, is_deleted=False)


class QuoteQuestionSelector:
    @staticmethod
    def list_for_module(module_uuid: str) -> QuerySet:
        return (
            QuoteQuestion.objects
            .filter(module__uuid=module_uuid, is_deleted=False)
            .select_related('depends_on_question')
            .prefetch_related('options')
            .order_by('display_order', 'id')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteQuestion:
        return QuoteQuestion.objects.get(uuid=uuid, is_deleted=False)


class QuoteQuestionOptionSelector:
    @staticmethod
    def list_for_question(question_uuid: str) -> QuerySet:
        return (
            QuoteQuestionOption.objects
            .filter(question__uuid=question_uuid, is_deleted=False)
            .order_by('display_order', 'id')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> QuoteQuestionOption:
        return QuoteQuestionOption.objects.get(uuid=uuid, is_deleted=False)
