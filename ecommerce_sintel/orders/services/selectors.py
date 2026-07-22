from django.db.models import QuerySet
from orders.models import Order, ShippingAddress

class ShippingAddressSelector:
    LIST_FIELDS = ('id', 'uuid', 'label', 'full_name', 'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country', 'phone_number', 'is_default')
    
    @staticmethod
    def list_for_user(user) -> QuerySet:
        return ShippingAddress.objects.filter(user=user, is_deleted=False).only(*ShippingAddressSelector.LIST_FIELDS)

    @staticmethod
    def get_by_uuid(uuid: str) -> ShippingAddress:
        return ShippingAddress.objects.get(uuid=uuid, is_deleted=False)

class OrderSelector:
    # Relaciones que OrderSerializer siempre serializa (items, shipping_address, shipment
    # + shipment.dispatch_center/carrier/driver) -- sin esto, list()/retrieve() de OrderViewSet
    # generan un N+1 real (verificado: 19 queries para listar solo 2 ordenes antes del fix).
    # user/user__profile agregados junto con el campo 'user' del serializer (get_full_name()
    # y ProfileResolver.get_profile() acceden a user.profile en cada fila).
    RELATED = (
        'user', 'user__profile', 'shipping_address', 'shipment',
        'shipment__dispatch_center', 'shipment__carrier', 'shipment__driver',
    )

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return (
            Order.objects.filter(is_deleted=False)
            .select_related(*OrderSelector.RELATED)
            .prefetch_related('items')
            .order_by('-created_at')
        )

    @staticmethod
    def list_for_user(user) -> QuerySet:
        return (
            Order.objects.filter(user=user, is_deleted=False)
            .select_related(*OrderSelector.RELATED)
            .prefetch_related('items')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> Order:
        """
        Returns order with items prefetched.
        """
        return (
            Order.objects
            .filter(is_deleted=False)
            .select_related(*OrderSelector.RELATED)
            .prefetch_related('items')
            .get(uuid=uuid)
        )
