"""S-05 (auditoria enterprise): cart/ no tenia ningun admin.py."""
from django.contrib import admin

from cart.models import Cart, CartItem, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('variant', 'service_variant', 'quantity', 'created_at')
    can_delete = False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'guest_id', 'created_at', 'updated_at')
    search_fields = ('user__email',)
    inlines = [CartItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'variant', 'created_at')
    list_select_related = ('user', 'variant')
    search_fields = ('user__email', 'variant__sku')
