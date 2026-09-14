from rest_framework import serializers

# Re-export Shop Serializers
from shop.api.serializers import (
    ProductSerializer, ProductInputSerializer,
    CategorySerializer, CategoryInputSerializer,
    BrandSerializer, BrandInputSerializer,
    TaxSerializer, TaxInputSerializer,
    ProductVariantSerializer, ProductVariantInputSerializer,
    ProductCostRuleSerializer, ProductCostRuleInputSerializer, ProductCostAssignmentInputSerializer,
)

# Re-export Users Serializers
from users.api.serializers import (
    UserProfileSerializer, UserDetailSerializer,
    UserAdminCreateSerializer, UserAdminUpdateSerializer
)

# Re-export Orders Serializers
from orders.api.serializers import (
    OrderSerializer, OrderItemSerializer, ShippingAddressSerializer
)

# Re-export Renting Serializers
from renting.api.serializers import (
    EquipmentSerializer, EquipmentInputSerializer,
    EquipmentVariantSerializer, EquipmentVariantInputSerializer,
    RentingCategorySerializer, RentingCategoryInputSerializer,
    RentingBrandSerializer, RentingBrandInputSerializer,
    RentalLaborSerializer, RentalLaborInputSerializer,
    EquipmentLogisticsConfigSerializer, EquipmentLogisticsConfigInputSerializer,
    EquipmentMarketingSerializer, EquipmentMarketingInputSerializer,
    EquipmentCommercialConfigSerializer, EquipmentCommercialConfigInputSerializer,
    EquipmentCommercialOptionSerializer, EquipmentCommercialOptionInputSerializer,
    RentalCostRuleSerializer, RentalCostRuleInputSerializer, RentalCostAssignmentInputSerializer,
)

# Re-export Technical Services Serializers (marketing/FAQ, unificacion con Renting)
from technical_services.api.serializers import (
    ServiceFAQSerializer, ServiceFAQInputSerializer,
    ServiceMarketingSerializer, ServiceMarketingInputSerializer,
)

# Re-export Quotes Serializers
from quotes.api.serializers import (
    QuotationSerializer, QuotationListSerializer, QuotationItemSerializer,
    QuotationServiceSerializer, QuotationMaterialSerializer,
    QuotationCreateInputSerializer,
    QuotationStatusChangeInputSerializer, QuotationAddItemInputSerializer, QuotationAddServiceInputSerializer,
    QuoteTemplateCategorySerializer, QuoteTemplateCategoryInputSerializer,
    QuoteTemplateSubcategorySerializer, QuoteTemplateSubcategoryInputSerializer,
    QuoteTemplateListSerializer, QuoteTemplateSerializer, QuoteTemplateInputSerializer,
    QuoteTemplateAttributeSerializer, QuoteTemplateAttributeInputSerializer,
    QuoteEquipmentTypeSerializer, QuoteEquipmentTypeInputSerializer,
    QuoteTemplateModuleSerializer, QuoteTemplateModuleInputSerializer, QuoteModuleReorderInputSerializer,
    QuoteQuestionSerializer, QuoteQuestionInputSerializer,
    QuoteQuestionOptionSerializer, QuoteQuestionOptionInputSerializer,
    QuoteQuestionDuplicateToModuleInputSerializer,
)

# Re-export Technical Services Serializers
from technical_services.api.serializers import (
    ServiceCategorySerializer, ServiceCategoryInputSerializer,
    ServiceLevelSerializer, ServiceLevelInputSerializer,
    ServiceConfigurationSerializer, ServiceConfigurationInputSerializer,
    ServiceVariantSerializer, ServiceVariantInputSerializer,
    ServiceMaterialSerializer, ServiceMaterialInputSerializer,
    TechnicalServiceSerializer, TechnicalServiceInputSerializer, TechnicalServiceAdminCreateSerializer,
    ServicePriceHistorySerializer, SetVariantPricingInputSerializer,
    ServiceCostRuleSerializer, ServiceCostRuleInputSerializer, ServiceCostAssignmentInputSerializer,
)

# Re-export Support Serializers
from support.api.serializers import ChatRoomListSerializer, ChatRoomSerializer, ChatMessageSerializer


class ServiceAdminRequestSummarySerializer(serializers.Serializer):
    """
    DTO administrativo de la Fachada Unificada de Solicitudes de Servicio
    (Plan "Fachada Administrativa Unificada", 2026-08-14). NO es un modelo
    persistente ni crea ownership -- combina campos de Order (orders) +
    OrderServiceDetail/ServiceOperation (technical_services) para
    /panel/servicios > Solicitudes. Ver
    technical_services/.AGENT/SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md
    para la regla de que campo pertenece a que owner (esta clase solo LEE,
    nunca escribe).

    Espera una instancia `Order` obtenida via
    dashboard.services.admin_orchestrators.ServiceAdminRequestSelector
    (select_related/prefetch_related + `current_status` ya resueltos) --
    usarla sobre un Order "pelado" reintroduce el N+1 que el selector evita.
    """
    request_id = serializers.CharField(source='uuid')
    order_id = serializers.CharField(source='uuid')
    tracking_number = serializers.CharField()
    created_at = serializers.DateTimeField()

    customer = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    variant = serializers.SerializerMethodField()
    commercial = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    request_status = serializers.SerializerMethodField()
    operation = serializers.SerializerMethodField()
    technician = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    @staticmethod
    def _service_item(obj):
        return next((i for i in obj.items.all() if i.service_variant_id), None)

    def get_customer(self, obj):
        user = obj.user
        detail = getattr(obj, 'service_detail', None)
        return {
            'uuid': str(user.uuid) if user else None,
            'name': user.get_full_name() if user else None,
            'email': user.email if user else None,
            'address': detail.address if detail else None,
            'contact_person': detail.contact_person if detail else None,
        }

    def get_service(self, obj):
        item = self._service_item(obj)
        if not item:
            return None
        service = item.service_variant.service if item.service_variant_id else None
        return {
            'name': item.item_name,
            'category': service.category.name if service and service.category_id else None,
        }

    def get_variant(self, obj):
        item = self._service_item(obj)
        if not item:
            return None
        return {'sku': item.sku, 'price': str(item.price)}

    def get_commercial(self, obj):
        detail = getattr(obj, 'service_detail', None)
        return {
            'priority': detail.priority if detail else None,
            'applied_rate_type': detail.applied_rate_type if detail else None,
            'applied_rate_amount': (
                str(detail.applied_rate_amount)
                if detail and detail.applied_rate_amount is not None else None
            ),
            'total_amount': str(obj.total_amount),
        }

    def get_payment(self, obj):
        return {'method': obj.payment_method, 'order_status': obj.status}

    def get_request_status(self, obj):
        # `current_status` viene anotado por ServiceAdminRequestSelector
        # (ultimo evento de OrderServiceTimeline -- log append-only, no un
        # campo vivo en Order, mismo patron que AdminMetricsOrchestrator).
        return getattr(obj, 'current_status', None)

    def get_operation(self, obj):
        operation = getattr(obj, 'service_operation', None)
        if operation is None:
            return None
        return {
            'uuid': str(operation.uuid),
            'status': operation.status,
            'closure_status': operation.closure_status,
            'has_incident': operation.has_incident,
        }

    def get_technician(self, obj):
        # "Tecnico asignado" real = ServiceOperation.technician (fuente de
        # verdad, ver hallazgo H1 del baseline). OrderServiceDetail.technician
        # (legacy) se expone solo como lectura de referencia -- si difiere,
        # `diverges=True` senala la inconsistencia entre los 2 sistemas de
        # asignacion que hoy coexisten sin sincronizarse.
        operation = getattr(obj, 'service_operation', None)
        technician = operation.technician if operation else None
        detail = getattr(obj, 'service_detail', None)
        legacy_technician = detail.technician if detail and detail.technician_id else None
        diverges = bool(
            technician and legacy_technician and technician.id != legacy_technician.id
        )
        return {
            'uuid': str(technician.uuid) if technician else None,
            'name': technician.get_full_name() if technician else None,
            'legacy_uuid': str(legacy_technician.uuid) if legacy_technician else None,
            'legacy_name': legacy_technician.get_full_name() if legacy_technician else None,
            'diverges': diverges,
        }

    def get_schedule(self, obj):
        operation = getattr(obj, 'service_operation', None)
        detail = getattr(obj, 'service_detail', None)
        return {
            'preferred_date': detail.preferred_date if detail else None,
            'preferred_time': detail.preferred_time if detail else None,
            'scheduled_date': operation.scheduled_date if operation else None,
            'scheduled_time': operation.scheduled_time if operation else None,
            'estimated_duration_minutes': operation.estimated_duration_minutes if operation else None,
        }

    def get_timeline(self, obj):
        # Fusiona OrderServiceTimeline (comercial) + ServiceOperationEvent
        # (tecnico) -- son 2 bitacoras independientes por diseno, con un
        # unico punto de sincronizacion (transition a COMPLETED). Ver
        # hallazgo del baseline -- no asumir espejo.
        events = [
            {
                'source': 'order',
                'status': ev.status,
                'created_at': ev.created_at,
                'actor': ev.created_by.get_full_name() if ev.created_by_id else None,
            }
            for ev in obj.timeline.all()
        ]
        operation = getattr(obj, 'service_operation', None)
        if operation is not None:
            events += [
                {
                    'source': 'operation',
                    'status': ev.event_type,
                    'created_at': ev.created_at,
                    'actor': ev.actor.get_full_name() if ev.actor_id else None,
                }
                for ev in operation.timeline.all()
            ]
        events.sort(key=lambda e: e['created_at'])
        return events
