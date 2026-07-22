from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from shop.models import ProductVariant
from technical_services.models import ServiceVariant
from renting.models import EquipmentVariant
from ecommerce.base_models import SintelBaseModel

class ShippingAddress(SintelBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shipping_addresses')
    label = models.CharField(max_length=50, blank=True, default='')  # "Casa", "Oficina", etc.
    full_name = models.CharField(max_length=255)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, default='')
    postal_code = models.CharField(max_length=20, blank=True, default='')
    country = models.CharField(max_length=100, default='Colombia')
    phone_number = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"

class Coupon(SintelBaseModel):
    code = models.CharField(max_length=20, unique=True)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    is_percentage = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def __str__(self):
        return self.code

class Order(SintelBaseModel):
    STATUS_CREATED            = 'CREATED'
    STATUS_PENDING_PAYMENT    = 'PENDING_PAYMENT'
    STATUS_PAID               = 'paid'
    STATUS_PREPARING          = 'PREPARING'
    STATUS_READY_FOR_DISPATCH = 'READY_FOR_DISPATCH'
    STATUS_ASSIGNED           = 'ASSIGNED'
    STATUS_PICKED_UP          = 'PICKED_UP'
    STATUS_IN_TRANSIT         = 'IN_TRANSIT'
    STATUS_OUT_FOR_DELIVERY   = 'OUT_FOR_DELIVERY'
    STATUS_DELIVERED          = 'delivered'
    STATUS_COMPLETED          = 'COMPLETED'
    STATUS_CANCELLED          = 'cancelled'
    STATUS_RETURN_REQUESTED   = 'RETURN_REQUESTED'
    STATUS_RETURNED           = 'RETURNED'
    STATUS_FAILED_DELIVERY    = 'FAILED_DELIVERY'
    STATUS_LOST               = 'LOST'

    STATUS_CHOICES = [
        (STATUS_CREATED,            'Creado'),
        (STATUS_PENDING_PAYMENT,    'Pendiente de pago'),
        ('pending',                 'Pending (legacy)'),
        ('processing',              'En procesamiento (legacy)'),
        (STATUS_PAID,               'Pagado'),
        (STATUS_PREPARING,          'Preparando'),
        (STATUS_READY_FOR_DISPATCH, 'Listo para despacho'),
        (STATUS_ASSIGNED,           'Asignado'),
        (STATUS_PICKED_UP,          'Recogido'),
        (STATUS_IN_TRANSIT,         'En tránsito'),
        (STATUS_OUT_FOR_DELIVERY,   'En reparto'),
        (STATUS_DELIVERED,          'Entregado'),
        (STATUS_COMPLETED,          'Completado'),
        (STATUS_CANCELLED,          'Cancelado'),
        (STATUS_RETURN_REQUESTED,   'Devolución solicitada'),
        (STATUS_RETURNED,           'Devuelto'),
        (STATUS_FAILED_DELIVERY,    'Entrega fallida'),
        (STATUS_LOST,               'Perdido'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('WOMPI',  'Wompi (online)'),
        ('COD',    'Pago contra entrega'),
        ('NEQUI',  'Nequi Push'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='WOMPI',
        db_index=True,
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    LOGISTICS_STATUS_CHOICES = {
        STATUS_PREPARING,
        STATUS_READY_FOR_DISPATCH,
        STATUS_ASSIGNED,
        STATUS_PICKED_UP,
        STATUS_IN_TRANSIT,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_DELIVERED,
        STATUS_COMPLETED,
    }

    PAYMENT_PENDING_STATUSES = {
        STATUS_PENDING_PAYMENT,
        'pending',
        'processing',
    }

    def __str__(self):
        return f"Order {self.uuid} - {self.status}"

    def is_pending_payment(self):
        return self.status in self.PAYMENT_PENDING_STATUSES

    def is_fulfillment_active(self):
        return self.status in self.LOGISTICS_STATUS_CHOICES or self.status == self.STATUS_PAID

class DispatchCenter(SintelBaseModel):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    address = models.CharField(max_length=300)
    hours = models.CharField(max_length=200, blank=True, default='')
    daily_capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dispatch_centers',
    )

    class Meta:
        verbose_name = 'centro de despacho'
        verbose_name_plural = 'centros de despacho'

    def __str__(self):
        return self.name


class Carrier(SintelBaseModel):
    name = models.CharField(max_length=255, unique=True)
    contact_phone = models.CharField(max_length=20, blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    tracking_url_template = models.CharField(max_length=300, blank=True, default='')
    sla = models.CharField(max_length=255, blank=True, default='')
    active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'transportadora'
        verbose_name_plural = 'transportadoras'

    def __str__(self):
        return self.name


class DeliveryDriver(SintelBaseModel):
    EMPLOYEE = 'EMPLOYEE'
    EXTERNAL = 'EXTERNAL'
    CONTRACTOR = 'CONTRACTOR'
    TYPE_CHOICES = [
        (EMPLOYEE, 'Empleado'),
        (EXTERNAL, 'Externo'),
        (CONTRACTOR, 'Contratista'),
    ]

    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, blank=True, default='')
    driver_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=EMPLOYEE)
    vehicle = models.CharField(max_length=100, blank=True, default='')
    plate = models.CharField(max_length=30, blank=True, default='')
    active = models.BooleanField(default=True, db_index=True)
    carrier = models.ForeignKey(
        Carrier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='drivers',
    )
    current_location = models.CharField(max_length=255, blank=True, default='')
    capacity = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'repartidor'
        verbose_name_plural = 'repartidores'

    def __str__(self):
        return self.name


class Shipment(SintelBaseModel):
    STATUS_PREPARING = 'PREPARING'
    STATUS_READY_FOR_DISPATCH = 'READY_FOR_DISPATCH'
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_PICKED_UP = 'PICKED_UP'
    STATUS_IN_TRANSIT = 'IN_TRANSIT'
    STATUS_OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY'
    STATUS_DELIVERED = 'delivered'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED_DELIVERY = 'FAILED_DELIVERY'
    STATUS_LOST = 'LOST'

    STATUS_CHOICES = [
        (STATUS_PREPARING,          'Preparando'),
        (STATUS_READY_FOR_DISPATCH, 'Listo para despacho'),
        (STATUS_ASSIGNED,           'Asignado'),
        (STATUS_PICKED_UP,          'Recogido'),
        (STATUS_IN_TRANSIT,         'En tránsito'),
        (STATUS_OUT_FOR_DELIVERY,   'En reparto'),
        (STATUS_DELIVERED,          'Entregado'),
        (STATUS_COMPLETED,          'Completado'),
        (STATUS_FAILED_DELIVERY,    'Entrega fallida'),
        (STATUS_LOST,               'Perdido'),
    ]

    METHOD_OWN_DELIVERY     = 'OWN_DELIVERY'
    METHOD_INTERNAL_DISPATCHER = 'INTERNAL_DISPATCHER'
    METHOD_URBAN_COURIER    = 'URBAN_COURIER'
    METHOD_CARRIER_COMPANY  = 'CARRIER_COMPANY'
    METHOD_CERTIFIED_MAIL   = 'CERTIFIED_MAIL'
    METHOD_STORE_PICKUP     = 'STORE_PICKUP'
    METHOD_SCHEDULED_DELIVERY = 'SCHEDULED_DELIVERY'
    SHIPPING_METHOD_CHOICES = [
        (METHOD_OWN_DELIVERY,       'Entrega propia'),
        (METHOD_INTERNAL_DISPATCHER, 'Transportista interno'),
        (METHOD_URBAN_COURIER,      'Mensajería urbana'),
        (METHOD_CARRIER_COMPANY,    'Empresa transportadora'),
        (METHOD_CERTIFIED_MAIL,     'Correo certificado'),
        (METHOD_STORE_PICKUP,       'Recogida en tienda'),
        (METHOD_SCHEDULED_DELIVERY, 'Entrega programada'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment')
    shipment_number = models.CharField(max_length=60, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PREPARING, db_index=True)
    dispatch_center = models.ForeignKey(
        DispatchCenter,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipments',
    )
    carrier = models.ForeignKey(
        Carrier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipments',
    )
    driver = models.ForeignKey(
        DeliveryDriver,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipments',
    )
    # Camino NUEVO de asignacion (2026-07-09): usa el mismo pool de despachadores
    # registrados que Renting (accounts.UserProfile.user_type='TRANSPORTER' ->
    # operations.DispatcherProfile, gestionado en /panel/despachadores) en vez del
    # `driver`/`carrier` standalone de arriba (sin FK a User, no reutilizable).
    # Ambos campos coexisten sin romper el flujo legado -- ver AGENT doc de orders.
    assigned_dispatcher = models.ForeignKey(
        'operations.DispatcherProfile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipments',
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='responsible_shipments',
    )
    vehicle = models.CharField(max_length=100, blank=True, default='')
    tracking_code = models.CharField(max_length=120, blank=True, null=True)
    shipping_method = models.CharField(max_length=30, choices=SHIPPING_METHOD_CHOICES, blank=True, default='')
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    dispatch_scheduled_at = models.DateTimeField(null=True, blank=True)
    route = models.TextField(blank=True, default='')

    # Empaque (Fase 6)
    package_type = models.CharField(max_length=100, blank=True, default='')
    package_weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    package_volume = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    package_dimensions = models.CharField(max_length=100, blank=True, default='')

    # Evidencias y cierre (campos listos; sin widget de UI todavia, mismo patron
    # que ServiceOperation.customer_signature)
    evidence_photos = models.JSONField(default=list, blank=True)
    delivery_signature = models.TextField(blank=True, default='')
    customer_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'envío'
        verbose_name_plural = 'envíos'

    def __str__(self):
        return self.shipment_number


class ShipmentTimeline(SintelBaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='shipment_timeline',
    )
    shipment = models.ForeignKey(
        Shipment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='timeline',
    )
    event_type = models.CharField(max_length=100)
    comment = models.TextField(blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = 'evento de línea de tiempo de envío'
        verbose_name_plural = 'eventos de línea de tiempo de envíos'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order.uuid} - {self.event_type}"


class ShipmentTrackingEvent(SintelBaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='tracking_events',
    )
    shipment = models.ForeignKey(
        Shipment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='tracking_points',
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField()
    accuracy = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'evento de tracking de envío'
        verbose_name_plural = 'eventos de tracking de envíos'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.order.uuid} @ {self.timestamp.isoformat()}"


class OrderItem(SintelBaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Can be a physical product variant or a technical service variant
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, null=True, blank=True)
    service_variant = models.ForeignKey(ServiceVariant, on_delete=models.PROTECT, null=True, blank=True)
    equipment_variant = models.ForeignKey(EquipmentVariant, on_delete=models.PROTECT, null=True, blank=True)
    
    # Snapshots for immutability
    item_name = models.CharField(max_length=255) # Unified name
    sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2) # Snapshotted price at creation

    def __str__(self):
        return f"{self.sku} x {self.quantity}"


class OrderItemCostSnapshot(SintelBaseModel):
    """
    Snapshot inmutable de un AdditionalCost aplicado a un OrderItem.
    Permite mostrar el desglose de precio en el historial de ordenes sin depender
    de los valores actuales de AdditionalCost (que pueden haber cambiado).
    """
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name='cost_snapshots'
    )
    cost_name = models.CharField(max_length=150)
    context = models.CharField(max_length=20)
    cost_type = models.CharField(max_length=10)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    computed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_discount = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Snapshot de Costo en Orden'
        verbose_name_plural = 'Snapshots de Costos en Ordenes'

    def __str__(self):
        return f"{self.cost_name} - {self.computed_amount}"
