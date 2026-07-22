"""
Customer 360 + Timeline unificado (Customer Experience Hub, Fase 4/5).

Agrega solo-lectura sobre los Selectors ya existentes de cada app -- support nunca posee
estos datos, ni los copia. El timeline se computa en cada request (no se persiste, para no
duplicar informacion que ya vive en Order/RentalRequest/VerificationEvent/ChatRoom).
Imports diferidos para evitar ciclos entre apps, mismo patron ya usado en el resto del proyecto.
"""


def _shipment_status(order):
    try:
        return order.shipment.status
    except Exception:
        return None


def _order_events(orders):
    events = []
    for order in orders:
        events.append({
            'type': 'order',
            'label': f'Pedido #{order.id} creado',
            'status': order.status,
            'uuid': str(order.uuid),
            'date': order.created_at,
        })
    return events


def _rental_events(rentals):
    events = []
    for rental in rentals:
        events.append({
            'type': 'rental',
            'label': f'Alquiler #{rental.id} solicitado',
            'status': rental.status,
            'uuid': str(rental.uuid),
            'date': rental.created_at,
        })
    return events


def _kyc_events(verification):
    if not verification:
        return []
    events = []
    for ev in verification.timeline_events.order_by('-created_at')[:10]:
        events.append({
            'type': 'kyc',
            'label': ev.get_event_type_display(),
            'status': ev.event_type,
            'uuid': str(ev.uuid),
            'date': ev.created_at,
        })
    return events


def _conversation_events(conversations):
    events = []
    for room in conversations:
        events.append({
            'type': 'conversation',
            'label': f'Conversacion de soporte ({room.get_status_display()})',
            'status': room.status,
            'uuid': str(room.uuid),
            'date': room.created_at,
        })
    return events


class Customer360Selector:

    @staticmethod
    def build(user) -> dict:
        from accounts.services import ProfileResolver
        from kyc.services.selectors import KycSelector
        from orders.services.selectors import OrderSelector, ShippingAddressSelector
        from renting.services.selectors import RentalRequestSelector
        from notifications.models import NotificationLog
        from support.models import ChatRoom

        profile = ProfileResolver.get_profile(user)
        verification = KycSelector.get_own_verification(user)
        orders = list(OrderSelector.list_for_user(user)[:20])
        rentals = list(RentalRequestSelector.list_for_user(user)[:20])
        addresses = list(ShippingAddressSelector.list_for_user(user))
        conversations = list(
            ChatRoom.objects.filter(user=user, is_deleted=False).order_by('-updated_at')[:10]
        )
        notifications = list(
            NotificationLog.objects.filter(user=user, is_deleted=False)
            .select_related('template').order_by('-created_at')[:15]
        )

        timeline = []
        timeline.append({
            'type': 'account',
            'label': 'Cuenta creada',
            'status': None,
            'uuid': str(user.uuid),
            'date': user.date_joined,
        })
        timeline += _order_events(orders)
        timeline += _rental_events(rentals)
        timeline += _kyc_events(verification)
        timeline += _conversation_events(conversations)
        timeline.sort(key=lambda e: e['date'], reverse=True)

        return {
            'user': {
                'uuid': str(user.uuid),
                'email': user.email,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
            },
            'profile': {
                'first_name': profile.first_name if profile else '',
                'last_name': profile.last_name if profile else '',
                'phone_number': profile.phone_number if profile else '',
                'user_type': profile.user_type if profile else None,
            } if profile else None,
            'kyc': {
                'status': verification.status,
                'requested_user_type': verification.requested_user_type,
                'first_approved_at': verification.first_approved_at,
            } if verification else None,
            'orders': [
                {
                    'uuid': str(o.uuid), 'id': o.id, 'status': o.status,
                    'total_amount': str(o.total_amount), 'created_at': o.created_at,
                    'payment_method': o.payment_method,
                    'items_count': len(o.items.all()),
                    'shipment_status': _shipment_status(o),
                }
                for o in orders
            ],
            'rentals': [
                {'uuid': str(r.uuid), 'id': r.id, 'status': r.status, 'created_at': r.created_at}
                for r in rentals
            ],
            'addresses': [
                {'uuid': str(a.uuid), 'full_name': a.full_name, 'city': a.city, 'is_default': a.is_default}
                for a in addresses
            ],
            'conversations': [
                {'uuid': str(c.uuid), 'status': c.status, 'updated_at': c.updated_at}
                for c in conversations
            ],
            'notifications': [
                {'template': n.template.slug if n.template else '', 'channel': n.channel, 'status': n.status, 'sent_at': n.sent_at}
                for n in notifications
            ],
            'timeline': timeline,
        }
