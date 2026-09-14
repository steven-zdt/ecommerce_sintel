import logging
import uuid as uuid_lib

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from orders.models import Order
from payment.models import Transaction, TransactionEvent, PaymentFeatureFlags
from payment.online.api.serializers import TransactionSerializer
from payment.online.services.commands import WompiCommands
from payment.online.wompi_client import WompiApiError

# [Sprint 3, 2026-08-05] _sync_wompi_status y _verify_wompi_event_signature se
# extrajeron a sync.py/signature.py (reconciliacion activa y validacion HMAC del
# webhook, cada una un bloque autocontenido sin relacion con la capa HTTP del
# ViewSet). Reexportadas aqui sin cambio de comportamiento para que los call sites
# existentes (`from payment.online.api.views import _sync_wompi_status` en
# dashboard/services/admin_orchestrators.py, payment/tasks.py, payment/tests.py, y
# `_verify_wompi_event_signature` en payment/api/views.py) sigan funcionando.
from payment.online.api.sync import _sync_wompi_status  # noqa: F401
from payment.online.api.signature import _verify_wompi_event_signature  # noqa: F401

logger = logging.getLogger(__name__)


def _is_nequi_configured() -> bool:
    """Credenciales reales presentes (ni vacias ni el placeholder de .env.example)."""
    required = (settings.NEQUI_CLIENT_ID, settings.NEQUI_CLIENT_SECRET, settings.NEQUI_API_KEY)
    return all(required) and not any(str(v).startswith('your_') for v in required)


def _build_rental_confirmation(wompi_tx: Transaction) -> dict:
    """Arma la misma envoltura que la confirmacion de ordenes, con un bloque
    'rental' en vez de 'order'/'shipping'/'service' para pagos Wompi de Renting."""
    rental = wompi_tx.rental_request
    user   = rental.user

    full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
    full_name = full_name or user.email

    next_steps = [
        {
            "label": "Ver mis solicitudes",
            # Bug real (2026-07-29, encontrado simulando una compra de renting
            # completa contra produccion): esta confirmacion es de RENTING
            # (rental_request), no de un pedido de tienda -- /mi-cuenta/pedidos
            # es la lista de ordenes de shop, la solicitud vive en
            # /mi-cuenta/alquileres. Mismo bug que se encontro y corrigio en el
            # lado de PaymentResultView.vue (rama isCodRenting).
            "path": "/mi-cuenta/alquileres",
            "variant": "primary" if wompi_tx.status == "APPROVED" else "warning",
        },
        {"label": "Ver mas equipos", "path": "/alquiler", "variant": "outline-secondary"},
    ]

    return {
        "payment": {
            "uuid":                str(wompi_tx.uuid),
            "wompi_id":            wompi_tx.wompi_id,
            "status":              wompi_tx.status,
            "payment_method_type": wompi_tx.payment_method_type,
            "amount_in_cents":     wompi_tx.amount_in_cents,
            "amount_cop":          str(wompi_tx.amount_in_cents / 100),
            "currency":            wompi_tx.currency,
            "created_at":          wompi_tx.created_at.isoformat(),
        },
        "order":      None,
        "customer": {
            "email":     user.email,
            "full_name": full_name,
        },
        "shipping":   None,
        "service":    None,
        "rental": {
            "uuid":           str(rental.uuid),
            "status":         rental.status,
            "status_display": rental.get_status_display(),
            "equipment_name": rental.equipment_variant.equipment.name,
            "start_date":     str(rental.start_date) if rental.start_date else None,
            "end_date":       str(rental.end_date) if rental.end_date else None,
            "location_city":  rental.location_city,
            "grand_total":    str(rental.grand_total) if rental.grand_total is not None else None,
        },
        "timeline":   [],
        "order_type": "rental",
        "next_steps": next_steps,
    }


@extend_schema(tags=["payments-online"])
class WompiPaymentViewSet(viewsets.ViewSet):
    """
    Endpoints del modulo Wompi Online (widget de pago: tarjeta, PSE, etc.).

    - initialize         → crea Transaction pendiente + firma de integridad.
    - transaction_status → estado post-pago (pagina de confirmacion).
    - webhook            → listener de eventos Wompi.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class   = TransactionSerializer

    # F-03 (auditoria enterprise): initialize() no tenia ningun limite de
    # tasa -- solo `initialize` lo necesita (es la accion que dispara dinero/
    # cobro); el resto de acciones son lectura o publicas por diseno.
    # [CORREGIDO 2026-08-04, hallazgo C1 de AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md]:
    # transaction_status/confirmation SI necesitan throttle -- disparan
    # _sync_wompi_status(), que consulta Wompi con un wompi_id controlado por el cliente.
    # Defensa en profundidad ademas de la validacion de reference/monto ya agregada ahi.
    ACTION_THROTTLE_SCOPES = {
        'initialize': 'payment_initialize',
        'transaction_status': 'payment_reconciliation',
        'confirmation': 'payment_reconciliation',
    }

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    @extend_schema(request=None, responses={200: dict})
    @action(
        detail=False, methods=["get"],
        url_path="feature-flags", permission_classes=[permissions.AllowAny],
    )
    def feature_flags(self, request):
        """
        Flags operativos de pagos (ADR-001 Fase 5, migracion gradual). Publico
        (AllowAny) a proposito: se consulta ANTES de que el usuario inicie
        sesion/pague, desde CheckoutView.vue al montar. Editable desde
        /admin/ sin desplegar codigo nuevo -- ver PaymentFeatureFlagsAdmin.
        """
        flags = PaymentFeatureFlags.get_active()
        return Response({
            "card_api_flow_enabled": flags.card_api_flow_enabled,
            "widget_flow_enabled": flags.widget_flow_enabled,
            # Nequi Push queda oculto en el selector de metodos de pago mientras
            # no haya credenciales reales configuradas -- sin esto se le ofrecia
            # a cualquier cliente una opcion de pago que siempre fallaba (ver
            # payment/nequi/client.py, que llama directo al sandbox real de
            # Nequi y no tiene modo de simulacion).
            "nequi_enabled": _is_nequi_configured(),
        })

    @extend_schema(request=None, responses={200: TransactionSerializer})
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def initialize(self, request):
        order_uuid: str = request.data.get("order_uuid", "")
        order: Order    = get_object_or_404(Order, uuid=order_uuid, user=request.user)

        if order.status != Order.STATUS_PENDING_PAYMENT:
            return Response(
                {"detail": "La orden no esta pendiente de pago."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Campos OPCIONALES (ADR-001 Sec.4): presentes cuando el checkout usa el
        # sub-metodo "Tarjeta" (Fase 3b); ausentes cuando usa "PSE / Otros", que
        # sigue exactamente el comportamiento de siempre (Widget completo).
        card_token: str = request.data.get("card_token") or None
        payment_source_id_raw = request.data.get("payment_source_id") or None
        payment_source_id = int(payment_source_id_raw) if payment_source_id_raw else None

        # Kill-switch real (ADR-001 Fase 5): el flag no es solo una senal para
        # que el frontend oculte el boton -- si esta desactivado, el backend
        # rechaza el flujo nuevo aunque alguien llame a este endpoint
        # directamente con card_token/payment_source_id.
        flags = PaymentFeatureFlags.get_active()
        if (card_token or payment_source_id) and not flags.card_api_flow_enabled:
            return Response(
                {"detail": "El pago con tarjeta via API esta deshabilitado temporalmente. Usa PSE/Otros."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Simetrico al kill-switch de arriba (plan hibrido Widget+API): si el
        # Widget esta desactivado, un intento de iniciar el flujo widget (sin
        # card_token/payment_source_id) tambien debe rechazarse en el backend.
        if not (card_token or payment_source_id) and not flags.widget_flow_enabled:
            return Response(
                {"detail": "El pago via Widget esta deshabilitado temporalmente. Usa Tarjeta."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Correlation ID (ADR-001 Fase 4): mintado aqui, una vez por intento de
        # pago, y propagado a traves de toda la Transaction (creacion, sync por
        # polling, webhook) via Transaction.correlation_id -- ver
        # payment/.AGENT/docs/FASE4_OBSERVABILIDAD.md.
        correlation_id = str(uuid_lib.uuid4())

        with transaction.atomic():
            # Idempotencia de inicio de pago (F-02): el select_for_update
            # sobre la orden serializa dos initialize() concurrentes del
            # mismo checkout (doble clic / reintento). El segundo espera al
            # primero y, al re-verificar bajo el lock, reutiliza la
            # Transaction PENDING ya creada en vez de crear una segunda (y,
            # en el flujo Tarjeta, en vez de cobrar dos veces). El lock es
            # por-fila de ESTA orden -- justo el doble-submit que frenamos.
            locked_order = Order.objects.select_for_update().get(pk=order.pk)
            if locked_order.status != Order.STATUS_PENDING_PAYMENT:
                return Response(
                    {"detail": "La orden no esta pendiente de pago."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            existing_tx = (
                Transaction.objects
                .filter(order=locked_order, status='PENDING')
                .order_by('-created_at')
                .first()
            )
            if existing_tx is not None:
                wompi_tx: Transaction = existing_tx
            else:
                # Los except van DENTRO del bloque atomico (bug propio,
                # corregido antes de comitear): WompiCommands.initialize_transaction()
                # persiste una Transaction marcada ERROR y luego relanza la
                # excepcion cuando la pasarela falla -- si el except vive
                # fuera del `with`, la excepcion que escapa del bloque fuerza
                # un rollback de TODA la transaccion, incluida esa fila
                # ERROR que debia sobrevivir (asi lo prueba
                # WompiSyncTransactionCreationTestCase). Manejando la
                # excepcion aqui adentro, el bloque sale sin excepcion y
                # Django comitea normalmente.
                try:
                    wompi_tx = WompiCommands.initialize_transaction(
                        locked_order, card_token=card_token, payment_source_id=payment_source_id,
                        correlation_id=correlation_id,
                    )
                except ValueError as exc:
                    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
                except WompiApiError as exc:
                    return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "uuid":                str(wompi_tx.uuid),
            "transaction_uuid":    str(wompi_tx.uuid),
            "amount_in_cents":     wompi_tx.amount_in_cents,
            "currency":            wompi_tx.currency,
            "status":              wompi_tx.status,
            "wompi_id":            wompi_tx.wompi_id,
            "correlation_id":      wompi_tx.correlation_id,
            "public_key":          settings.WOMPI_PUBLIC_KEY,
            "widget_url":          settings.WOMPI_WIDGET_URL,
            # Sin esto, useWompiWidget.js arma wompiConfig.signature.integrity
            # como undefined y Wompi rechaza CUALQUIER pago via Widget (PSE/Otros)
            # con "La firma es invalida" -- el flujo Tarjeta no lo necesitaba aqui
            # (se envia server-to-server en _create_transaction_sync), por eso
            # este bug pasaba desapercibido mientras Tarjeta seguia funcionando.
            "integrity_signature": wompi_tx.integrity_signature,
        })

    @extend_schema(request=None, responses={200: dict})
    @action(
        detail=False, methods=["get"],
        url_path="transaction-status",
        permission_classes=[permissions.IsAuthenticated],
    )
    def transaction_status(self, request):
        tx_uuid: str = request.query_params.get("tx", "").strip()
        tx_wompi_id: str = request.query_params.get("id", "").strip()
        if not tx_uuid:
            return Response({"detail": "Parametro tx requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wompi_tx = (
                Transaction.objects
                .select_related("order", "rental_request")
                .prefetch_related("order__items")
                .get(
                    Q(order__user=request.user) | Q(rental_request__user=request.user),
                    uuid=tx_uuid,
                )
            )
        except Transaction.DoesNotExist:
            return Response({"detail": "Transaccion no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if wompi_tx.status == "PENDING":
            _sync_wompi_status(wompi_tx, wompi_id_hint=tx_wompi_id or None)

        base = {
            "transaction_uuid":    str(wompi_tx.uuid),
            "wompi_id":            wompi_tx.wompi_id,
            "tx_status":           wompi_tx.status,
            "status_label":        dict(Transaction.STATUS_CHOICES).get(wompi_tx.status, wompi_tx.status),
            "payment_method_type": wompi_tx.payment_method_type,
            "amount_in_cents":     wompi_tx.amount_in_cents,
            "currency":            wompi_tx.currency,
            "tx_created_at":       wompi_tx.created_at,
        }

        if wompi_tx.rental_request_id:
            rental = wompi_tx.rental_request
            base["order"] = {
                "uuid":            str(rental.uuid),
                "status":          rental.status,
                "total_amount":    str(rental.grand_total) if rental.grand_total is not None else None,
                "tracking_number": None,
                "created_at":      rental.created_at,
                "items":           [],
                "service_detail":  None,
            }
            return Response(base)

        order = wompi_tx.order
        items = [
            {"item_name": i.item_name, "sku": i.sku, "quantity": i.quantity, "price": str(i.price)}
            for i in order.items.all()
        ]

        service_detail = None
        sd = getattr(order, "service_detail", None)
        if sd:
            service_detail = {
                "description":  sd.description,
                "address":      sd.address,
                "scheduled_at": sd.scheduled_at.isoformat() if sd.scheduled_at else None,
                "priority":     sd.priority,
                "contact_person": sd.contact_person,
            }

        base["order"] = {
            "uuid":            str(order.uuid),
            "status":          order.status,
            "total_amount":    str(order.total_amount),
            "tracking_number": order.tracking_number,
            "created_at":      order.created_at,
            "items":           items,
            "service_detail":  service_detail,
        }
        return Response(base)

    @extend_schema(request=None, responses={200: dict})
    @action(
        detail=False, methods=["get"],
        url_path="confirmation",
        permission_classes=[permissions.IsAuthenticated],
    )
    def confirmation(self, request):
        """
        Devuelve el resultado consolidado de una transaccion Wompi.
        Acepta:
          ?tx=<transaction_uuid>      — UUID interno (generado en initialize) -- clave
                                        primaria de busqueda, siempre disponible desde
                                        que se crea la Transaction.
          ?id=<wompi_transaction_id>  — ID de Wompi (agregado por el redirect, o pasado
                                        por el callback del widget) -- usado como hint
                                        para _sync_wompi_status cuando wompi_id aun no
                                        esta guardado en BD (antes de que llegue el
                                        webhook), NUNCA como fuente de verdad del status.
        GET /api/v1/payment/payments/confirmation/?tx=<uuid>
        GET /api/v1/payment/payments/confirmation/?tx=<uuid>&id=11508268-1782830552-83116
        """
        tx_wompi_id: str = request.query_params.get("id", "").strip()
        tx_uuid:     str = request.query_params.get("tx", "").strip()

        if not tx_wompi_id and not tx_uuid:
            return Response(
                {"detail": "Parametro id o tx requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = (
            Transaction.objects
            .select_related("order", "order__user", "rental_request", "rental_request__user")
            .prefetch_related("order__items", "order__timeline")
        )
        owner_filter = Q(order__user=request.user) | Q(rental_request__user=request.user)
        try:
            if tx_uuid:
                wompi_tx = qs.get(owner_filter, uuid=tx_uuid)
            else:
                wompi_tx = qs.get(owner_filter, wompi_id=tx_wompi_id)
        except Transaction.DoesNotExist:
            return Response({"detail": "Transaccion no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if wompi_tx.status == "PENDING":
            _sync_wompi_status(wompi_tx, wompi_id_hint=tx_wompi_id or None)
            # Bug real (2026-07-29, probando el flujo de Tarjeta de Tienda contra
            # produccion): _sync_wompi_status(), cuando el pago se aprueba dentro
            # de esta misma request, confirma la orden via confirm_order_payment()
            # -- pero esa funcion relee la Order con select_for_update() (necesario
            # para el lock de fila), asi que muta y guarda una instancia DISTINTA a
            # wompi_tx.order (cacheada por el select_related de la query de arriba,
            # ANTES de la confirmacion). El UPDATE en BD queda correcto, pero la
            # respuesta de este endpoint seguia mostrando la Order en
            # 'pending_payment' -- pantalla contradictoria (Transaccion Aprobada /
            # Orden Pendiente de pago) en el primer request que alcanza a disparar
            # la reconciliacion. refresh_from_db() limpia el cache de relaciones
            # (order/rental_request) ademas de los campos propios, forzando una
            # lectura fresca mas abajo.
            wompi_tx.refresh_from_db()

        if wompi_tx.rental_request_id:
            return Response(_build_rental_confirmation(wompi_tx))

        order = wompi_tx.order
        user  = order.user

        items = [
            {
                "item_name": i.item_name,
                "sku":       i.sku,
                "quantity":  i.quantity,
                "price":     str(i.price),
                "subtotal":  str(i.price * i.quantity),
            }
            for i in order.items.all()
        ]

        service_data = None
        sd = getattr(order, "service_detail", None)
        if sd:
            service_data = {
                "address":                sd.address,
                "preferred_date":         str(sd.preferred_date)  if sd.preferred_date  else None,
                "preferred_time":         str(sd.preferred_time)  if sd.preferred_time  else None,
                "scheduled_at":           sd.scheduled_at.isoformat() if sd.scheduled_at else None,
                "priority":               sd.priority,
                "service_notes":          sd.service_notes,
                "contact_person":         sd.contact_person,
                "allow_schedule_changes": sd.allow_schedule_changes,
                "neighborhood":           sd.neighborhood,
                "location_reference":     sd.location_reference,
            }

        shipping_data = None
        try:
            sa = order.shipping_address
            if sa:
                shipping_data = {
                    "address_line_1": sa.address_line_1,
                    "city":           sa.city,
                    "department":     getattr(sa, "department", ""),
                    "postal_code":    getattr(sa, "postal_code", ""),
                    "country":        getattr(sa, "country", "CO"),
                }
        except Exception:
            pass

        timeline = [
            {
                "status":     e.status,
                "notes":      e.notes or "",
                "created_at": e.created_at.isoformat(),
            }
            for e in order.timeline.all()
        ]

        order_type = "service" if sd else "product"

        next_steps_map = {
            ("service", "APPROVED"): [
                {"label": "Ver mi solicitud", "path": "/mi-cuenta/pedidos", "variant": "primary"},
                {"label": "Ver mas servicios", "path": "/servicios", "variant": "outline-secondary"},
            ],
            ("product", "APPROVED"): [
                {"label": "Ver mis pedidos", "path": "/mi-cuenta/pedidos", "variant": "primary"},
                {"label": "Seguir comprando", "path": "/tienda", "variant": "outline-secondary"},
            ],
            ("service", "PENDING"): [
                {"label": "Ver mis solicitudes", "path": "/mi-cuenta/pedidos", "variant": "warning"},
                {"label": "Ver mas servicios", "path": "/servicios", "variant": "outline-secondary"},
            ],
            ("product", "PENDING"): [
                {"label": "Ver mis pedidos", "path": "/mi-cuenta/pedidos", "variant": "warning"},
                {"label": "Seguir comprando", "path": "/tienda", "variant": "outline-secondary"},
            ],
        }
        next_steps = next_steps_map.get(
            (order_type, wompi_tx.status),
            [
                {"label": "Ir a la tienda", "path": "/tienda", "variant": "primary"},
                {"label": "Ver mis pedidos", "path": "/mi-cuenta/pedidos", "variant": "outline-secondary"},
            ],
        )

        full_name = ""
        if hasattr(user, "get_full_name"):
            full_name = user.get_full_name() or user.email
        else:
            full_name = user.email

        return Response({
            "payment": {
                "uuid":                str(wompi_tx.uuid),
                "wompi_id":            wompi_tx.wompi_id,
                "status":              wompi_tx.status,
                "payment_method_type": wompi_tx.payment_method_type,
                "amount_in_cents":     wompi_tx.amount_in_cents,
                "amount_cop":          str(wompi_tx.amount_in_cents / 100),
                "currency":            wompi_tx.currency,
                "created_at":          wompi_tx.created_at.isoformat(),
            },
            "order": {
                "uuid":            str(order.uuid),
                "status":          order.status,
                "total_amount":    str(order.total_amount),
                "tracking_number": order.tracking_number,
                "created_at":      order.created_at.isoformat(),
                "items":           items,
            },
            "customer": {
                "email":     user.email,
                "full_name": full_name,
            },
            "shipping":   shipping_data,
            "service":    service_data,
            "timeline":   timeline,
            "order_type": order_type,
            "next_steps": next_steps,
        })

    @extend_schema(request=None, responses={200: dict})
    @action(detail=False, methods=["post"], url_path="webhook")
    def webhook(self, request):
        logger.info(
            "Wompi webhook recibido | event_type=%s",
            request.data.get("event", "unknown"),
        )

        if not _verify_wompi_event_signature(request.data, request=request):
            logger.warning(
                "Wompi webhook: firma INVALIDA. payload=%s",
                str(request.data)[:500],
            )
            return Response({"detail": "Firma de evento invalida."}, status=status.HTTP_400_BAD_REQUEST)

        WompiCommands.process_webhook_notification(request.data)
        return Response({"status": "received"}, status=status.HTTP_200_OK)
