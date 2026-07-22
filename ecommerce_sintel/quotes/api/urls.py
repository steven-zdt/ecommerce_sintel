from django.urls import path, include
from rest_framework.routers import DefaultRouter
from quotes.api.views import (
    QuotationViewSet, QuoteTemplateCategoryViewSet,
    QuoteTemplateSubcategoryViewSet, QuoteTemplateViewSet,
)

router = DefaultRouter()
router.register(r'quotations', QuotationViewSet, basename='quotation')
router.register(r'quote-template-categories', QuoteTemplateCategoryViewSet, basename='quote-template-category')
router.register(r'quote-template-subcategories', QuoteTemplateSubcategoryViewSet, basename='quote-template-subcategory')
router.register(r'quote-templates', QuoteTemplateViewSet, basename='quote-template')

urlpatterns = [
    path('', include(router.urls)),
]
