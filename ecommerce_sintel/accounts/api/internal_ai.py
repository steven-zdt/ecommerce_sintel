"""
Endpoint interno para el AI Engine (Fase 5 AI Core) — CRM Context
(Componente 9), la parte de datos del Customer Context Builder.

Decision de la fase (registrada en el plan): NO se crea una tabla nueva de
"memoria de cliente" — el riesgo señalado por el propio plan era duplicar
datos que ya viven en Django. Este endpoint AGREGA (no almacena) los
selectors reales y cachea el dict resultante en el cache de Django
(Redis, TTL 5 min, misma estrategia documentada en core) — Componente 14.

Fuentes (exactamente las que el plan nombra):
- MarketingSelector.get_user_marketing_profile(user)  (total_spent/orders_count/preference)
- ShippingAddressSelector.list_for_user(user)
- payment.TokenizedCard del usuario (mismo query del TokenizedCardViewSet;
  jamas se expone token_id, solo marca y ultimos 4 digitos)
"""
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response

from users.api.permissions import IsAuthenticatedActiveUser

CUSTOMER_CONTEXT_CACHE_TTL = 300  # 5 min, igual que home-feed
CUSTOMER_CONTEXT_CACHE_KEY = 'ai_customer_context_{user_id}'


def _build_customer_context(user) -> dict:
    from marketing.services.selectors import MarketingSelector
    from orders.services.selectors import ShippingAddressSelector
    from payment.models import TokenizedCard

    marketing = MarketingSelector.get_user_marketing_profile(user)
    marketing['total_spent'] = str(marketing.get('total_spent', 0))

    addresses = [
        {
            'uuid': str(a.uuid),
            'full_name': a.full_name,
            'city': a.city,
            'state': a.state,
            'phone_number': a.phone_number,
            'is_default': a.is_default,
        }
        for a in ShippingAddressSelector.list_for_user(user)[:5]
    ]
    cards = [
        {
            'brand': c.brand,
            'last4': c.masked_number[-4:],
            'is_default': c.is_default,
        }
        for c in TokenizedCard.objects.filter(user=user, is_deleted=False)
        .order_by('-is_default', '-created_at')[:5]
    ]
    return {'marketing': marketing, 'addresses': addresses, 'payment_methods': cards}


class AiCustomerContextView(APIView):
    """GET /api/v1/internal/ai/customer-context/ -> CRM context compacto, cacheado."""
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        key = CUSTOMER_CONTEXT_CACHE_KEY.format(user_id=request.user.id)
        data = cache.get(key)
        cached = data is not None
        if data is None:
            data = _build_customer_context(request.user)
            cache.set(key, data, CUSTOMER_CONTEXT_CACHE_TTL)
        return Response({**data, 'cached': cached})
