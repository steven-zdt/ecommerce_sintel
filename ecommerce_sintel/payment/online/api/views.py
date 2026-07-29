import hashlib
import hmac
import logging
import uuid as uuid_lib

import requests as http_requests
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

logger = logging.getLogger(__name__)


def _sync_wompi_status(wompi_tx: Transaction, wompi_id_hint: str = None) -> None:
    """
    Query the Wompi API to sync a PENDING transaction status.
    Called when the user returns from Wompi's confirmation page before
    the webhook has been processed.

    `wompi_id_hint` covers the exact race this function exists for: right after
    the checkout widget closes, Wompi's own webhook (which is the only place that
    normally writes `Transaction.wompi_id`) may not have arrived yet, so
    `wompi_tx.wompi_id` is still None. The widget's own JS callback already knows
    Wompi's transaction id at that point (`result.transaction.id`) -- the frontend
    passes it through as a hint so this function can query Wompi directly instead
    of silently giving up. This is only used to know WHICH transaction to ask
    Wompi about; the actual status always comes from Wompi's API response below,
    never from the hint itself (per Wompi's own guidance: never trust the
    redirect/callback status, only the API/webhook).
    """
    wompi_id = wompi_tx.wompi_id or wompi_id_hint
    if not wompi_id:
        return

    env = getattr(settings, "WOMPI_ENVIRONMENT", "test")
    base_url = (
        "https://sandbox.wompi.co/v1"
        if env != "prod"
        else "https://production.wompi.co/v1"
    )
    private_key = getattr(settings, "WOMPI_PRIVATE_KEY", "")
    if not private_key:
        logger.warning("_sync_wompi_status: WOMPI_PRIVATE_KEY no configurado")
        return

    # Capturado ANTES de cualquier intento (ADR-001 Fase 6): las ramas de error
    # de abajo necesitan el status previo para dejar un TransactionEvent, y
    # wompi_tx.status puede haber sido mutado dentro del bloque atomic si la
    # excepcion ocurre a mitad de camino (el rollback de BD no deshace ese
    # atributo en memoria).
    original_status = wompi_tx.status

    try:
        resp = http_requests.get(
            f"{base_url}/transactions/{wompi_id}",
            headers={"Authorization": f"Bearer {private_key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning(
                "_sync_wompi_status: Wompi respondio %s para wompi_id=%s",
                resp.status_code, wompi_id,
            )
            from payment.online.services.commands import WompiCommands
            WompiCommands.record_sync_event(
                wompi_tx, previous_status=original_status,
                error_detail=f"Wompi respondio {resp.status_code} al consultar wompi_id={wompi_id}",
            )
            return

        data = resp.json().get("data", {})
        new_status = data.get("status", "")
        method_type = data.get("payment_method_type", "")

        # Se bloquea y guarda una copia separada (no se reasigna wompi_tx: el
        # caller (confirmation()/transaction_status()) mantiene su propia
        # referencia al objeto que le pasamos, y necesita ver los campos
        # actualizados para construir la respuesta -- reasignar el parametro
        # aqui solo actualizaria el nombre local, dejando el objeto del caller
        # con el status viejo en memoria aunque la fila en BD ya cambio).
        with transaction.atomic():
            locked_tx = Transaction.objects.select_for_update().get(pk=wompi_tx.pk)
            update_fields = ["updated_at"]
            previous_status = locked_tx.status

            if not locked_tx.wompi_id:
                locked_tx.wompi_id = wompi_id
                update_fields.append("wompi_id")

            if method_type and method_type != locked_tx.payment_method_type:
                locked_tx.payment_method_type = method_type
                update_fields.append("payment_method_type")

            status_changed = new_status and new_status != locked_tx.status
            if status_changed:
                locked_tx.status = new_status
                update_fields.append("status")

            locked_tx.save(update_fields=update_fields)

            wompi_tx.wompi_id            = locked_tx.wompi_id
            wompi_tx.payment_method_type = locked_tx.payment_method_type
            wompi_tx.status              = locked_tx.status

            if status_changed:
                from payment.online.services.commands import WompiCommands as _WC
                _WC.record_sync_event(
                    locked_tx, previous_status=previous_status,
                    new_status=new_status, raw_payload=data, processed=True,
                )

        if status_changed:
            logger.info(
                "_sync_wompi_status: actualizado corr=%s wompi_id=%s status=%s",
                wompi_tx.correlation_id, wompi_id, new_status,
            )
            from payment.online.services.commands import WompiCommands
            WompiCommands.handle_status_change(wompi_tx, new_status)

    except Exception as exc:
        logger.warning(
            "_sync_wompi_status: error consultando Wompi wompi_id=%s | %s",
            wompi_id, exc,
        )
        from payment.online.services.commands import WompiCommands as _WC
        _WC.record_sync_event(
            wompi_tx, previous_status=original_status,
            error_detail=str(exc)[:500],
        )


def _is_nequi_configured() -> bool:
    """Credenciales reales presentes (ni vacias ni el placeholder de .env.example)."""
    required = (settings.NEQUI_CLIENT_ID, settings.NEQUI_CLIENT_SECRET, settings.NEQUI_API_KEY)
    return all(required) and not any(str(v).startswith('your_') for v in required)


def _verify_wompi_event_signature(payload: dict, request=None) -> bool:
    """
    Valida la autenticidad de un evento Wompi usando el secreto de eventos.

    Algoritmo (doc oficial Wompi):
      1. Extraer el array `properties` del objeto `signature`.
      2. Por cada propiedad, navegar el objeto `data` y concatenar su valor.
      3. Agregar al final `str(timestamp)` y `WOMPI_EVENTS_SECRET`.
      4. SHA256 de la cadena UTF-8 resultante.
      5. Comparar con `signature.checksum` con hmac.compare_digest (timing-safe).
    """
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands

    events_secret: str = getattr(settings, "WOMPI_EVENTS_SECRET", "")
    if not events_secret:
        # Fail-CLOSED: sin el secreto NO se puede verificar la autenticidad del
        # evento, asi que se rechaza. Antes retornaba True (fail-open), lo que
        # permitia falsificar un "pago aprobado" si la variable faltaba en
        # produccion. Ver F-01 de la auditoria.
        logger.critical(
            "Wompi webhook: WOMPI_EVENTS_SECRET no configurado — "
            "evento RECHAZADO (fail-closed)."
        )
        SecurityCommands.log_event(
            SecurityEvent.PAYMENT_WEBHOOK_INVALID_SIGNATURE, request=request, severity=SecurityEvent.SEVERITY_CRITICAL,
            metadata={'reason': 'secret_not_configured'},
        )
        return False

    try:
        sig_obj: dict       = payload.get("signature", {})
        checksum: str       = sig_obj.get("checksum", "")
        properties: list    = sig_obj.get("properties", [])
        timestamp: str|int  = payload.get("timestamp", "")
        data: dict          = payload.get("data", {})

        concatenated = ""
        for prop in properties:
            value: object = data
            for key in prop.split("."):
                value = value.get(key, "") if isinstance(value, dict) else ""
            concatenated += str(value)

        concatenated += str(timestamp) + events_secret
        computed = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

        is_valid = hmac.compare_digest(computed, checksum)
        if not is_valid:
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_WEBHOOK_INVALID_SIGNATURE, request=request, severity=SecurityEvent.SEVERITY_CRITICAL,
                metadata={'event_type': payload.get('event', 'unknown')},
            )
        return is_valid

    except Exception as exc:
        logger.exception("Wompi webhook: error al validar firma | %s", exc)
        return False


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
    ACTION_THROTTLE_SCOPES = {
        'initialize': 'payment_initialize',
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
                {"error": "La orden no esta pendiente de pago."},
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
                {"error": "El pago con tarjeta via API esta deshabilitado temporalmente. Usa PSE/Otros."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Simetrico al kill-switch de arriba (plan hibrido Widget+API): si el
        # Widget esta desactivado, un intento de iniciar el flujo widget (sin
        # card_token/payment_source_id) tambien debe rechazarse en el backend.
        if not (card_token or payment_source_id) and not flags.widget_flow_enabled:
            return Response(
                {"error": "El pago via Widget esta deshabilitado temporalmente. Usa Tarjeta."},
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
                    {"error": "La orden no esta pendiente de pago."},
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
                    return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
                except WompiApiError as exc:
                    return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

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
            return Response({"error": "Parametro tx requerido."}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": "Transaccion no encontrada."}, status=status.HTTP_404_NOT_FOUND)

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
                {"error": "Parametro id o tx requerido."},
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
            return Response({"error": "Transaccion no encontrada."}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"error": "Firma de evento invalida."}, status=status.HTTP_400_BAD_REQUEST)

        WompiCommands.process_webhook_notification(request.data)
        return Response({"status": "received"}, status=status.HTTP_200_OK)
