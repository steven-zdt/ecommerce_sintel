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
    ServicePriceHistorySerializer,
    ServiceCostRuleSerializer, ServiceCostRuleInputSerializer, ServiceCostAssignmentInputSerializer,
)

# Re-export Support Serializers
from support.api.serializers import ChatRoomListSerializer, ChatRoomSerializer, ChatMessageSerializer
