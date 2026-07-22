# shop/management/commands/seed_product_sale_flow.py

from decimal import Decimal
import hashlib
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from shop.models import Category, Product, ProductVariant
from inventory.models import StockRecord
from inventory.services.selectors import InventorySelector
from inventory.services.commands import InventoryCommands
from inventory.services.dtos import StockAdjustmentDTO
from cart.models import Cart
from cart.services.commands import CartCommands
from orders.models import ShippingAddress
from orders.services.commands import OrderCommands

class Command(BaseCommand):
    help = 'Seed product sale flow'

    def handle(self, *args, **options):
        try:
            User = get_user_model()
            # PASO 1: Crear Producto como superusuario
            vendor = User.objects.filter(is_superuser=True).first()
            category, _ = Category.objects.get_or_create(
                name='Test Electronica',
                defaults={'slug': 'test-electronica', 'is_active': True}
            )
            product, created = Product.objects.get_or_create(
                slug='producto-test-cli',
                defaults={
                    'vendor': vendor, 'category': category,
                    'name': 'Producto Test CLI', 'condition': 'new', 'is_active': True
                }
            )
            variant, _ = ProductVariant.objects.get_or_create(
                sku='TEST-CLI-001',
                defaults={
                    'product': product,
                    'price': Decimal('150000'),
                }
            )

            # PASO 2: Crear StockRecord e ingresar inventario
            ct = ContentType.objects.get_for_model(ProductVariant)
            stock_record, sr_created = StockRecord.objects.get_or_create(
                content_type=ct,
                object_id=variant.uuid,
                defaults={'sku': variant.sku, 'is_active': True}
            )
            if sr_created or stock_record.stock == 0:
                dto = StockAdjustmentDTO(
                    stock_record_uuid=stock_record.uuid,
                    quantity=10,
                    reference='Seed CLI'
                )
                InventoryCommands.register_entry(dto)

            # PASO 3: Crear usuario cliente de prueba
            customer, _ = User.objects.get_or_create(
                email='cliente.test@sintel.co',
                defaults={
                    'first_name': 'Cliente', 'last_name': 'Test',
                    'is_active': True, 'user_type': 'CUSTOMER'
                }
            )
            if _:
                customer.set_password('TestPass123!')
                customer.save(update_fields=['password'])

            # PASO 4: Agregar al carrito del cliente
            cart, _ = Cart.objects.get_or_create(user=customer)
            cart.items.all().delete()  # limpiar para idempotencia
            CartCommands.add_item(cart=cart, variant=variant, quantity=2)

            # PASO 5: Crear direccion de envio
            address, _ = ShippingAddress.objects.get_or_create(
                user=customer,
                address_line_1='Calle 123 # 45-67',
                defaults={
                    'full_name': 'Cliente Test',
                    'city': 'Bogota',
                    'country': 'Colombia',
                    'phone_number': '3001234567',
                    'is_default': True,
                }
            )

            # PASO 6: Crear la Orden (COD - sin necesitar pasarela de pago)
            order = OrderCommands.create_from_cart(
                user=customer,
                shipping_address=address,
                payment_method='COD',
            )

            # PASO 7: Imprimir resumen
            self.stdout.write(self.style.SUCCESS('--- FLUJO COMPLETADO ---'))
            self.stdout.write(f'Producto: {product.name} (slug={product.slug})')
            self.stdout.write(f'Variante: {variant.sku} | Precio: {variant.price}')
            self.stdout.write(f'Stock actual: {InventorySelector.get_stock_for_variant(variant)}')
            self.stdout.write(f'Cliente: {customer.email}')
            self.stdout.write(f'Orden UUID: {order.uuid}')
            self.stdout.write(f'Orden status: {order.status}')
            self.stdout.write(f'Orden total: {order.total_amount}')
            self.stdout.write(f'Items en orden: {order.items.count()}')

        except Exception as e:
            self.stderr.write(self.style.ERROR('Error al ejecutar el flujo de creación de producto y venta'))
            self.stderr.write(str(e))
