import uuid
from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from inventory.models import StockRecord, InventoryTransaction
from inventory.services.dtos import StockAdjustmentDTO
from inventory.services.commands import InventoryCommands
from inventory.services.selectors import InventorySelector, StockRecordSelector
from shop.models import ProductVariant, Product, Category

User = get_user_model()

class InventoryServicesTestCase(TransactionTestCase):
    def setUp(self):
        # Clean up cache
        cache.clear()
        
        # Create user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword"
        )
        
        # Create category
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )
        
        # Create product
        self.product = Product.objects.create(
            vendor=self.user,
            category=self.category,
            name="Test Product",
            slug="test-product"
        )
        
        # Create variant
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="TEST-SKU-123",
            price=10.0,
            stock=0
        )
        
        self.content_type = ContentType.objects.get_for_model(self.variant)
        
        # Create StockRecord
        self.stock_record = StockRecord.objects.create(
            content_type=self.content_type,
            object_id=self.variant.uuid,
            sku=self.variant.sku,
            stock=0
        )

    def test_register_entry_success(self):
        dto = StockAdjustmentDTO(
            stock_record_uuid=self.stock_record.uuid,
            quantity=10,
            reference="Initial stock entry"
        )
        
        result = InventoryCommands.register_entry(dto)
        
        # Verify DTO result
        self.assertEqual(result.quantity, 10)
        self.assertEqual(result.balance_after, 10)
        self.assertEqual(result.movement_type, 'ENTRY')
        
        # Verify DB state
        self.stock_record.refresh_from_db()
        self.assertEqual(self.stock_record.stock, 10)
        
        # Verify selector/cache
        current_stock = InventorySelector.get_current_stock(self.stock_record.id)
        self.assertEqual(current_stock, 10)

    def test_register_exit_success(self):
        # Set initial stock
        self.stock_record.stock = 15
        self.stock_record.save()
        
        # Record a matching transaction to represent the starting balance
        InventoryTransaction.objects.create(
            stock_record=self.stock_record,
            movement_type='ENTRY',
            quantity=15,
            balance_after=15
        )
        
        dto = StockAdjustmentDTO(
            stock_record_uuid=self.stock_record.uuid,
            quantity=5,
            reference="Sale transaction"
        )
        
        result = InventoryCommands.register_exit(dto)
        
        # Verify DTO result
        self.assertEqual(result.quantity, 5)
        self.assertEqual(result.balance_after, 10)
        self.assertEqual(result.movement_type, 'EXIT')
        
        # Verify DB state
        self.stock_record.refresh_from_db()
        self.assertEqual(self.stock_record.stock, 10)

    def test_register_exit_insufficient_stock(self):
        # Set initial stock to 3
        self.stock_record.stock = 3
        self.stock_record.save()
        
        InventoryTransaction.objects.create(
            stock_record=self.stock_record,
            movement_type='ENTRY',
            quantity=3,
            balance_after=3
        )
        
        dto = StockAdjustmentDTO(
            stock_record_uuid=self.stock_record.uuid,
            quantity=5,
            reference="Over-drafting stock"
        )
        
        with self.assertRaises(ValidationError) as ctx:
            InventoryCommands.register_exit(dto)
        
        self.assertIn("Insufficient stock", str(ctx.exception))

    def test_check_constraint_quantity(self):
        # Try to create a transaction with quantity 0, should fail at db constraint level
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            InventoryTransaction.objects.create(
                stock_record=self.stock_record,
                movement_type='ENTRY',
                quantity=0,
                balance_after=0
            )


from rest_framework.test import APIClient

class InventoryAPITestCase(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        # Create user
        self.user = User.objects.create_superuser(
            email="apiuser@example.com",
            password="testpassword"
        )
        self.client.force_authenticate(user=self.user)
        # Create category, product, variant, and stock record
        self.category = Category.objects.create(
            name="API Category",
            slug="api-category"
        )
        self.product = Product.objects.create(
            vendor=self.user,
            category=self.category,
            name="API Product",
            slug="api-product"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="API-SKU-123",
            price=20.0,
            stock=0
        )
        self.content_type = ContentType.objects.get_for_model(self.variant)
        self.stock_record = StockRecord.objects.create(
            content_type=self.content_type,
            object_id=self.variant.uuid,
            sku=self.variant.sku,
            stock=10
        )
        InventoryTransaction.objects.create(
            stock_record=self.stock_record,
            movement_type='ENTRY',
            quantity=10,
            balance_after=10
        )

    def test_adjust_stock_entry_api_success(self):
        url = f"/api/v1/inventory/stock-records/{self.stock_record.uuid}/adjust-stock/"
        data = {
            "movement_type": "ENTRY",
            "quantity": 5,
            "reference": "API Entry"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['movement_type'], 'ENTRY')
        self.assertEqual(response.data['quantity'], 5)
        self.assertEqual(response.data['balance_after'], 15)
        
        self.stock_record.refresh_from_db()
        self.assertEqual(self.stock_record.stock, 15)

    def test_adjust_stock_exit_api_success(self):
        url = f"/api/v1/inventory/stock-records/{self.stock_record.uuid}/adjust-stock/"
        data = {
            "movement_type": "EXIT",
            "quantity": 4,
            "reference": "API Exit"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['movement_type'], 'EXIT')
        self.assertEqual(response.data['quantity'], 4)
        self.assertEqual(response.data['balance_after'], 6)
        
        self.stock_record.refresh_from_db()
        self.assertEqual(self.stock_record.stock, 6)

    def test_adjust_stock_exit_api_insufficient_stock(self):
        url = f"/api/v1/inventory/stock-records/{self.stock_record.uuid}/adjust-stock/"
        data = {
            "movement_type": "EXIT",
            "quantity": 25,
            "reference": "API Exit Overdraft"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertIn("Insufficient stock", response.data['detail'])

    def test_adjust_stock_invalid_movement_type(self):
        url = f"/api/v1/inventory/stock-records/{self.stock_record.uuid}/adjust-stock/"
        data = {
            "movement_type": "INVALID_TYPE",
            "quantity": 5,
            "reference": "API Invalid"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)
