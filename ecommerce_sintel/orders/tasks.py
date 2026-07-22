import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Count

logger = logging.getLogger(__name__)

# Fase 11 AI Core (Proactividad, cierre): cross-sell minimo -- sin motor de
# recomendacion (no existe en este proyecto, ver investigacion de la fase),
# solo un gesto de reconocimiento a clientes recurrentes.
_FREQUENT_CUSTOMER_MIN_ORDERS = 3
_PROACTIVE_SLUG = 'cliente_recurrente_cross_sell'


@shared_task
def notify_frequent_customers_cross_sell() -> None:
    """
    Fase 11 AI Core (Proactividad, cierre): clientes con
    _FREQUENT_CUSTOMER_MIN_ORDERS o mas Order pagadas -- el asistente deja un
    mensaje de reconocimiento generico en la sala de soporte del cliente via
    el Event Bus (NotificationCommands.dispatch_notification_once ->
    AI_PROACTIVE_SLUGS). No se recomienda ningun producto especifico (no hay
    motor de recomendacion en este proyecto) ni se crea un PersonalOffer --
    solo un CTA generico invitando a escribir. Dedupe por cliente (no por
    Order): cada cliente recibe este nudge una sola vez en su vida.
    """
    from notifications.services.commands import NotificationCommands
    from orders.models import Order

    User = get_user_model()
    frequent = (
        Order.objects.filter(status=Order.STATUS_PAID, is_deleted=False)
        .values('user').annotate(n=Count('id'))
        .filter(n__gte=_FREQUENT_CUSTOMER_MIN_ORDERS)
    )

    notified = 0
    for row in frequent:
        user = User.objects.filter(pk=row['user']).first()
        if user is None:
            continue
        sent = NotificationCommands.dispatch_notification_once(
            user=user,
            template_slug=_PROACTIVE_SLUG,
            context={
                'message': (
                    f"Gracias por confiar en Sintel ya {row['n']} veces. Tenemos "
                    "ofertas y novedades para clientes frecuentes -- escribinos "
                    "si queres conocerlas."
                ),
                'orders_count': row['n'],
            },
            dedupe_key=f"customer_cross_sell:{user.uuid}",
        )
        if sent:
            notified += 1

    if notified:
        logger.info(
            "notify_frequent_customers_cross_sell: %s cliente(s) recurrente(s) notificado(s) "
            "(%s+ ordenes pagadas)", notified, _FREQUENT_CUSTOMER_MIN_ORDERS,
        )
