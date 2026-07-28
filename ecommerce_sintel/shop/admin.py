"""S-05 (auditoria enterprise): shop/ no tenia ningun admin.py -- ningun
modelo de catalogo era inspeccionable desde /admin/, dependiendo enteramente
del panel custom (dashboard/). Registro minimo, sin CRUD -- el CRUD real
sigue viviendo en dashboard/api/ (ver shop/CLAUDE.md)."""
from django.contrib import admin

from shop.models import (
    Category, Brand, Product, ProductVariant, ProductImage,
    ProductReview, Tax, ProductCostRule, ProductCostAssignment,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name', 'slug')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'brand', 'is_active', 'is_featured', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category', 'brand')
    search_fields = ('name', 'slug')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product', 'price', 'discounted_price', 'stock', 'created_at')
    list_select_related = ('product',)
    search_fields = ('sku', 'product__name')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'created_at')
    list_select_related = ('product', 'variant')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_select_related = ('product', 'user')
    list_filter = ('rating',)
    search_fields = ('user__email', 'product__name')


admin.site.register(Tax)
admin.site.register(ProductCostRule)
admin.site.register(ProductCostAssignment)
