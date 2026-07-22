import logging
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db import IntegrityError
from renting.models import (
    Equipment, EquipmentVariant, RentingCategory, RentingBrand,
    RentalLabor, RentalRequest, RentalPeriod, EquipmentLogisticsConfig,
    EquipmentBlock, EquipmentReturnInspection, EquipmentReview, EquipmentMarketing,
)
from orders.models import Order, OrderItem

logger = logging.getLogger(__name__)


class RentingCommands:
    """Flujo legacy de creacion de ordenes de renta directa (sin wizard)."""

    @staticmethod
    @transaction.atomic
    def process_rental_order(user, equipment_variant, start_date, end_date, mode, shipping_address):
        from renting.services.selectors import RentingSelector

        total_days = (end_date - start_date).days
        if total_days < 1:
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio.")

        if not RentingSelector.check_availability(equipment_variant.id, start_date, end_date):
            raise ValueError("No hay disponibilidad para el equipo en las fechas seleccionadas.")

        if mode == 'days':
            if not equipment_variant.rental_price_per_day:
                raise ValueError("Este equipo no admite renta por dias.")
            base_price = equipment_variant.rental_price_per_day * total_days
        elif mode == 'hours':
            if not equipment_variant.rental_price_per_hour:
                raise ValueError("Este equipo no admite renta por horas.")
            base_price = equipment_variant.rental_price_per_hour * (total_days * 8)
        else:
            raise ValueError("Modo de renta no valido.")

        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            total_amount=base_price,
            status='pending',
        )

        order_item = OrderItem.objects.create(
            order=order,
            equipment_variant=equipment_variant,
            item_name=f"{equipment_variant.equipment.name} (Renta por {mode})",
            sku=equipment_variant.sku,
            quantity=1,
            price=base_price,
        )

        from notifications.services.commands import NotificationCommands
        _user = user
        _ctx  = {
            'order_uuid':   str(order.uuid),
            'total_amount': str(base_price),
            'item':         equipment_variant.equipment.name,
            'user_name':    user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_order_created',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )

        return order


class EquipmentCommands:
    @staticmethod
    @transaction.atomic
    def create_equipment(user, category, name, description='', brand=None, is_active=True, is_featured=False):
        return Equipment.objects.create(
            vendor=user,
            category=category,
            brand=brand,
            name=name,
            description=description,
            is_active=is_active,
            is_featured=is_featured,
        )

    @staticmethod
    @transaction.atomic
    def update_equipment(equipment: Equipment, **fields):
        allowed = (
            'name', 'description', 'category', 'brand', 'is_active', 'is_featured',
            'meta_title', 'meta_description', 'meta_keywords', 'og_image',
        )
        for key, val in fields.items():
            if key in allowed:
                setattr(equipment, key, val)
        equipment.save()
        return equipment

    @staticmethod
    @transaction.atomic
    def delete_equipment(equipment: Equipment) -> None:
        equipment.is_active = False
        equipment.is_deleted = True
        equipment.save()


class EquipmentVariantCommands:
    @staticmethod
    @transaction.atomic
    def create_variant(equipment: Equipment, sku: str, rental_price_per_day=None,
                       rental_price_per_hour=None, stock=0, is_active=True):
        return EquipmentVariant.objects.create(
            equipment=equipment,
            sku=sku,
            rental_price_per_day=rental_price_per_day,
            rental_price_per_hour=rental_price_per_hour,
            stock=stock,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_variant(variant: EquipmentVariant, **fields):
        allowed = ('sku', 'rental_price_per_day', 'rental_price_per_hour', 'stock', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(variant, key, val)
        variant.save()
        return variant

    @staticmethod
    @transaction.atomic
    def delete_variant(variant: EquipmentVariant) -> None:
        variant.is_deleted = True
        variant.save()


class EquipmentReviewCommands:
    """
    Reseñas de equipo. A diferencia de shop.ProductReviewCommands (cualquier
    usuario autenticado puede calificar), aqui se exige que el usuario haya
    tenido al menos una RentalRequest en STATUS_FINISHED para el equipo --
    mismo patron de "ownership + estado terminal" que
    operations.OperationCommands.submit_review(). El unique_together del
    modelo es la segunda capa de defensa contra duplicados (carrera).
    """

    @staticmethod
    @transaction.atomic
    def create_review(user, equipment: Equipment, rating: int, comment: str) -> EquipmentReview:
        has_finished_rental = RentalRequest.objects.filter(
            user=user,
            equipment_variant__equipment=equipment,
            status=RentalRequest.STATUS_FINISHED,
        ).exists()
        if not has_finished_rental:
            raise ValueError(
                "Solo puedes calificar equipos que hayas alquilado y cuya renta ya haya finalizado."
            )
        if EquipmentReview.objects.filter(user=user, equipment=equipment).exists():
            raise ValueError("Ya has calificado este equipo.")

        try:
            return EquipmentReview.objects.create(
                user=user, equipment=equipment, rating=rating, comment=comment,
            )
        except IntegrityError:
            raise ValueError("Ya has calificado este equipo.")


class EquipmentBlockCommands:
    """
    Bloqueo/liberacion manual de una EquipmentVariant (mantenimiento, daño,
    conteo de inventario). Es un override admin: a diferencia de
    RentalRequestCommands.confirm_payment()/approve_manual_validation(), NO valida
    contra AvailabilityEngine.is_available() -- un equipo puede necesitar bloquearse
    aunque ya este rentado (ej. se daño en campo).
    """

    @staticmethod
    @transaction.atomic
    def create_block(equipment_variant: EquipmentVariant, block_type: str, start_date,
                      end_date, reason: str, quantity: int = 1, admin_user=None) -> EquipmentBlock:
        if end_date < start_date:
            raise ValueError("La fecha de fin debe ser igual o posterior a la fecha de inicio.")
        if quantity < 1:
            raise ValueError("La cantidad bloqueada debe ser al menos 1.")

        return EquipmentBlock.objects.create(
            equipment_variant=equipment_variant,
            block_type=block_type,
            start_date=start_date,
            end_date=end_date,
            quantity=quantity,
            reason=reason,
            created_by=admin_user,
        )

    @staticmethod
    @transaction.atomic
    def release_block(block: EquipmentBlock, admin_user=None, reason: str = '') -> EquipmentBlock:
        if block.status == EquipmentBlock.STATUS_RELEASED:
            return block

        block.status = EquipmentBlock.STATUS_RELEASED
        block.released_by = admin_user
        block.released_at = timezone.now()
        block.release_reason = reason
        block.save(update_fields=['status', 'released_by', 'released_at', 'release_reason', 'updated_at'])
        return block


class EquipmentReturnInspectionCommands:
    """
    Inspeccion de devolucion (2026-07-14). Registro opcional/aparte: NO gatea
    RentalRequestCommands.complete_period() -- solo exige que la RentalRequest ya
    este en STATUS_FINISHED (el equipo ya volvio). Si marca daño, crea
    automaticamente un EquipmentBlock TYPE_DAMAGE sobre la variante (decision del
    usuario) con un horizonte generoso (ver _DAMAGE_BLOCK_HORIZON_DAYS): el bloqueo
    queda activo hasta que un admin lo libere manualmente tras reparar el equipo,
    la fecha de fin exacta no importa mientras sea lo bastante lejana.
    """

    _DAMAGE_BLOCK_HORIZON_DAYS = 365

    @staticmethod
    @transaction.atomic
    def create_inspection(rental_request: RentalRequest, has_damage: bool, condition_notes: str = '',
                           missing_accessories: str = '', admin_user=None) -> EquipmentReturnInspection:
        if rental_request.status != RentalRequest.STATUS_FINISHED:
            raise ValueError("Solo se puede registrar una inspeccion sobre una renta finalizada (equipo devuelto).")
        if EquipmentReturnInspection.objects.filter(rental_request=rental_request).exists():
            raise ValueError("Esta solicitud ya tiene una inspeccion de devolucion registrada.")

        resulting_block = None
        if has_damage:
            today = timezone.localdate()
            resulting_block = EquipmentBlockCommands.create_block(
                equipment_variant=rental_request.equipment_variant,
                block_type=EquipmentBlock.TYPE_DAMAGE,
                start_date=today,
                end_date=today + timedelta(days=EquipmentReturnInspectionCommands._DAMAGE_BLOCK_HORIZON_DAYS),
                reason=(
                    f"Bloqueo automatico por daño detectado en inspeccion de devolucion "
                    f"de la renta {rental_request.uuid}. Liberar manualmente tras reparar."
                ),
                admin_user=admin_user,
            )

        return EquipmentReturnInspection.objects.create(
            rental_request=rental_request,
            has_damage=has_damage,
            condition_notes=condition_notes,
            missing_accessories=missing_accessories,
            inspected_by=admin_user,
            resulting_block=resulting_block,
        )


class RentingCategoryCommands:
    @staticmethod
    @transaction.atomic
    def create_category(name: str, description: str = '', is_active: bool = True, parent=None):
        return RentingCategory.objects.create(
            name=name, description=description, is_active=is_active, parent=parent,
        )

    @staticmethod
    @transaction.atomic
    def update_category(category: RentingCategory, **fields):
        allowed = ('name', 'description', 'is_active', 'parent')
        for key, val in fields.items():
            if key in allowed:
                setattr(category, key, val)
        category.save()
        return category

    @staticmethod
    @transaction.atomic
    def delete_category(category: RentingCategory) -> None:
        category.is_active = False
        category.is_deleted = True
        category.save()


class RentingBrandCommands:
    @staticmethod
    @transaction.atomic
    def create_brand(name: str):
        return RentingBrand.objects.create(name=name)

    @staticmethod
    @transaction.atomic
    def update_brand(brand: RentingBrand, name: str):
        brand.name = name
        brand.slug = ''
        brand.save()
        return brand

    @staticmethod
    @transaction.atomic
    def delete_brand(brand: RentingBrand) -> None:
        brand.is_deleted = True
        brand.save()


class RentalLaborCommands:
    @staticmethod
    @transaction.atomic
    def create_labor(name: str, price_per_hour: Decimal, description: str = '', is_active: bool = True):
        return RentalLabor.objects.create(
            name=name, price_per_hour=price_per_hour,
            description=description, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_labor(labor: RentalLabor, **fields):
        allowed = ('name', 'price_per_hour', 'description', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(labor, key, val)
        labor.save()
        return labor

    @staticmethod
    @transaction.atomic
    def delete_labor(labor: RentalLabor) -> None:
        labor.is_active = False
        labor.is_deleted = True
        labor.save()


class RentalRequestCommands:

    @staticmethod
    @transaction.atomic
    def create_request(user, validated_data: dict) -> RentalRequest:
        """
        Crea una RentalRequest de forma atomica. Ya NO crea un RentalPeriod: la
        solicitud queda en pending_payment, que NUNCA bloquea el calendario (Plan
        Maestro Fase 1/2). El RentalPeriod que efectivamente bloquea la agenda se
        crea recien en confirm_payment() o approve_manual_validation(), que son los
        unicos dos puntos autoritativos de lock+disponibilidad.

        Flujo:
          1. Verifica disponibilidad por fechas (best-effort, fail-fast de UX).
          2. Calcula costos: base desde variante + logistica desde EquipmentLogisticsConfig.
          3. Crea RentalRequest con status PENDING_PAYMENT.

        Regla del modulo (PaymentResult como unico punto de decision): esta
        solicitud es solo una intencion de compra -- NO dispara ningun correo
        ni WhatsApp al cliente. La unica comunicacion posible ocurre despues,
        cuando llega el PaymentResult (ver confirm_payment/
        approve_manual_validation/release_on_payment_failure).
        """
        from renting.services.selectors import RentingSelector

        variant: EquipmentVariant = EquipmentVariant.objects.get(
            pk=validated_data['equipment_variant'].pk
        )
        start   = validated_data['start_date']
        end     = validated_data['end_date']
        quantity: int = validated_data.get('quantity', 1)
        mode: str     = validated_data.get('rental_mode', RentalRequest.RENTAL_MODE_DAYS)
        total_days: int = (end - start).days

        if not RentingSelector.check_availability(variant.id, start, end, quantity):
            raise ValueError(
                "No hay disponibilidad para el equipo en las fechas seleccionadas. "
                "Por favor elige otras fechas."
            )

        # Precio base
        if mode == RentalRequest.RENTAL_MODE_DAYS:
            base_cost = (variant.rental_price_per_day or Decimal('0')) * total_days * quantity
        else:
            hours = validated_data.get('estimated_hours') or Decimal(str(total_days * 8))
            base_cost = (variant.rental_price_per_hour or Decimal('0')) * hours * quantity

        # Costos de logistica desde el modelo (configurados por el admin)
        try:
            lc: EquipmentLogisticsConfig = variant.equipment.logistics_config
        except EquipmentLogisticsConfig.DoesNotExist:
            lc = None

        def _d(val) -> Decimal:
            return Decimal(str(val)) if val else Decimal('0')

        delivery_cost      = _d(lc.delivery_cost)      if lc else Decimal('0')
        pickup_cost        = _d(lc.pickup_cost)        if lc else Decimal('0')
        installation_cost  = _d(lc.installation_cost)  if lc else Decimal('0')
        calibration_cost   = _d(lc.calibration_cost)   if lc else Decimal('0')
        training_cost      = _d(lc.training_cost)      if lc else Decimal('0')
        startup_cost       = _d(lc.startup_cost)       if lc else Decimal('0')

        transport_total = delivery_cost + pickup_cost
        setup_total     = installation_cost + calibration_cost + training_cost + startup_cost

        subtotal = base_cost + transport_total + setup_total
        from renting.services.pricing import RentalPricingCalculator
        tax_rate   = RentalPricingCalculator.get_tax_rate(variant)
        tax_amount = (subtotal * tax_rate).quantize(Decimal('0.01'))
        grand_total = subtotal + tax_amount

        terms_accepted: bool = validated_data.get('terms_accepted', False)

        rental_request = RentalRequest.objects.create(
            user=user,
            equipment_variant=variant,
            status=RentalRequest.STATUS_PENDING_PAYMENT,
            priority=validated_data.get('priority', RentalRequest.PRIORITY_LOW),
            # Paso 2
            location_address=validated_data.get('location_address', ''),
            location_city=validated_data.get('location_city', ''),
            location_department=validated_data.get('location_department', ''),
            location_coordinates=validated_data.get('location_coordinates', ''),
            project_type=validated_data.get('project_type', ''),
            access_conditions=validated_data.get('access_conditions', ''),
            location_notes=validated_data.get('location_notes', ''),
            # Paso 3
            contact_full_name=validated_data.get('contact_full_name', ''),
            contact_doc_type=validated_data.get('contact_doc_type', RentalRequest.DOC_CC),
            contact_doc_number=validated_data.get('contact_doc_number', ''),
            contact_email=validated_data.get('contact_email', ''),
            contact_phone=validated_data.get('contact_phone', ''),
            contact_company=validated_data.get('contact_company', ''),
            contact_position=validated_data.get('contact_position', ''),
            # Paso 4
            start_date=start,
            end_date=end,
            quantity=quantity,
            estimated_hours=validated_data.get('estimated_hours'),
            rental_mode=mode,
            delivery_time=validated_data.get('delivery_time'),
            pickup_time=validated_data.get('pickup_time'),
            operational_notes=validated_data.get('operational_notes', ''),
            # Paso 5
            terms_accepted=terms_accepted,
            terms_accepted_at=timezone.now() if terms_accepted else None,
            # Costos del modelo (no del usuario)
            delivery_cost=delivery_cost,
            pickup_cost=pickup_cost,
            installation_cost=installation_cost,
            calibration_cost=calibration_cost,
            training_cost=training_cost,
            startup_cost=startup_cost,
            # Totales
            total_rental_days=total_days,
            base_cost=base_cost,
            transport_total=transport_total,
            setup_total=setup_total,
            tax_amount=tax_amount,
            grand_total=grand_total,
        )

        return rental_request

    @staticmethod
    @transaction.atomic
    def process_payment_selection(
        rental_request: RentalRequest,
        payment_method: str,
        extra_data: dict = None,
    ) -> dict:
        """
        Procesa la seleccion de metodo de pago para una RentalRequest en estado pending_payment.

        Retorna un dict con los datos necesarios para que el frontend continue el flujo:
          - WOMPI: datos para inicializar el widget de Wompi
          - NEQUI:  {'nequi_tx_uuid': str}
          - COD:    {'status': 'pending_validation', 'rental_uuid': str}
        """
        from django.conf import settings

        if rental_request.status != RentalRequest.STATUS_PENDING_PAYMENT:
            raise ValueError("La solicitud no esta pendiente de pago.")

        rental_request.payment_method = payment_method
        rental_request.save(update_fields=['payment_method', 'updated_at'])

        if payment_method == RentalRequest.PAYMENT_COD:
            # No se bloquea la agenda aqui: COD queda pendiente de aprobacion manual
            # de un admin (approve_manual_validation), que es el punto autoritativo
            # de lock+disponibilidad para este metodo de pago.
            rental_request.status = RentalRequest.STATUS_PENDING_VALIDATION
            rental_request.save(update_fields=['status', 'updated_at'])

            from notifications.services.commands import NotificationCommands
            _user = rental_request.user
            _ctx  = {
                'request_uuid':   str(rental_request.uuid),
                'equipment_name': rental_request.equipment_variant.equipment.name,
                'grand_total':    str(rental_request.grand_total),
                'user_name':      _user.get_short_name(),
            }
            transaction.on_commit(
                lambda: NotificationCommands.dispatch_notification(
                    user=_user,
                    template_slug='rental_cod_review_pending',
                    context=_ctx,
                    ws_group='admin_notifications',
                )
            )
            return {'status': 'pending_validation', 'rental_uuid': str(rental_request.uuid)}

        if payment_method == RentalRequest.PAYMENT_NEQUI:
            from payment.nequi.services.commands import NequiCommands
            from payment.nequi.client import NequiApiError
            phone = (extra_data or {}).get('phone_number', '')
            if not phone:
                raise ValueError("El numero de celular es obligatorio para Nequi.")
            nequi_tx = NequiCommands.initialize_rental_transaction(
                rental_request=rental_request,
                phone_number=phone,
            )
            return {'nequi_tx_uuid': str(nequi_tx.uuid)}

        # WOMPI: crea la Transaction real (misma infraestructura que ordenes de tienda)
        # para que el webhook y /payment/result puedan encontrarla por su uuid.
        # card_token (tarjeta, ADR-001): si viene, WompiCommands.initialize_transaction()
        # crea la transaccion SINCRONA en Wompi -- sin abrir el widget completo, mismo
        # camino ya probado en el checkout de Tienda y Servicios Tecnicos.
        from payment.online.services.commands import WompiCommands
        card_token = (extra_data or {}).get('card_token')
        wompi_tx = WompiCommands.initialize_transaction(rental_request=rental_request, card_token=card_token)
        rental_request.wompi_reference = str(wompi_tx.uuid)
        rental_request.save(update_fields=['wompi_reference', 'updated_at'])

        return {
            'uuid':               str(wompi_tx.uuid),
            'transaction_uuid':   str(wompi_tx.uuid),
            'status':             wompi_tx.status,
            'wompi_id':           wompi_tx.wompi_id,
            'amount_in_cents':    wompi_tx.amount_in_cents,
            'currency':           wompi_tx.currency,
            'public_key':         getattr(settings, 'WOMPI_PUBLIC_KEY', ''),
            'integrity_signature': wompi_tx.integrity_signature,
            'widget_url':         getattr(settings, 'WOMPI_WIDGET_URL', 'https://checkout.wompi.co/widget.js'),
        }

    # Estados en los que una RentalRequest ya quedo resuelta (pagada, aprobada,
    # rechazada o en conflicto) y por lo tanto un webhook/aprobacion duplicados
    # deben ser un no-op silencioso en vez de reintentar reservar el calendario.
    _RESOLVED_STATUSES = (
        RentalRequest.STATUS_PAID,
        RentalRequest.STATUS_CONFIRMED,
        RentalRequest.STATUS_IN_OPERATION,
        RentalRequest.STATUS_FINISHED,
        RentalRequest.STATUS_CANCELLED,
        RentalRequest.STATUS_PAYMENT_CONFLICT,
    )

    @staticmethod
    def _create_blocking_period(rental_request: RentalRequest, variant: EquipmentVariant) -> RentalPeriod:
        return RentalPeriod.objects.create(
            rental_request=rental_request,
            equipment_variant=variant,
            start_date=rental_request.start_date,
            end_date=rental_request.end_date,
            start_time=rental_request.delivery_time,
            end_time=rental_request.pickup_time,
            rental_mode=rental_request.rental_mode,
            quantity=rental_request.quantity,
            status=RentalPeriod.STATUS_SCHEDULED,
        )

    @staticmethod
    def _flag_payment_conflict(rental_request: RentalRequest, note: str, refund_required: bool) -> None:
        """
        Marca la solicitud como payment_conflict: perdio la carrera de disponibilidad
        frente a otra solicitud que confirmo/aprobo primero para las mismas fechas.
        No crea RentalPeriod. Requiere seguimiento manual de un admin (reembolso si
        refund_required=True).
        """
        rental_request.status = RentalRequest.STATUS_PAYMENT_CONFLICT
        rental_request.refund_required = refund_required
        stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
        rental_request.admin_notes = (f"{rental_request.admin_notes}\n[{stamp}] {note}").strip()
        rental_request.save(update_fields=['status', 'refund_required', 'admin_notes', 'updated_at'])

        from notifications.services.commands import NotificationCommands
        _user = rental_request.user
        _ctx = {
            'request_uuid':   str(rental_request.uuid),
            'equipment_name': rental_request.equipment_variant.equipment.name,
            'grand_total':    str(rental_request.grand_total),
            'user_name':      _user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_payment_conflict_customer',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_payment_conflict_admin',
                context=_ctx,
                ws_group='admin_notifications',
            )
        )

    @staticmethod
    @transaction.atomic
    def confirm_payment(rental_request: RentalRequest) -> None:
        """
        Marca la RentalRequest como pagada (Nequi o Wompi aprobados). Este es uno de
        los DOS unicos puntos autoritativos de lock+disponibilidad (el otro es
        approve_manual_validation): aqui, y solo aqui para el flujo de pago online,
        se crea el RentalPeriod que efectivamente bloquea el calendario.

        select_for_update() sobre la variante serializa confirmaciones concurrentes
        para el mismo equipo/fechas -- sin este lock, dos RentalRequest en
        pending_payment para fechas solapadas podrian confirmar su pago en paralelo
        y ninguna veria el RentalPeriod de la otra hasta guardar. La que pierde la
        carrera queda en payment_conflict (ver _flag_payment_conflict) para que un
        admin gestione el reembolso.

        Guard de idempotencia ampliado a todo estado ya resuelto (no solo PAID): un
        webhook duplicado que llega despues de que esta solicitud ya perdio la
        carrera (payment_conflict) no debe reintentar reservar.
        """
        rental_request = RentalRequest.objects.select_for_update().get(pk=rental_request.pk)
        if rental_request.status in RentalRequestCommands._RESOLVED_STATUSES:
            logger.info(
                "Confirmacion de pago ignorada, la solicitud ya esta resuelta | rental_request=%s status=%s",
                rental_request.uuid, rental_request.status,
            )
            return

        variant = EquipmentVariant.objects.select_for_update().get(pk=rental_request.equipment_variant_id)
        from renting.services.availability import AvailabilityEngine
        if not AvailabilityEngine.is_available(
            variant.id, rental_request.start_date, rental_request.end_date,
            rental_request.quantity, rental_request.rental_mode,
            rental_request.delivery_time, rental_request.pickup_time,
        ):
            RentalRequestCommands._flag_payment_conflict(
                rental_request,
                note=(
                    "Conflicto de disponibilidad al confirmar el pago; las fechas ya "
                    "fueron tomadas por otra solicitud. Requiere reembolso manual al cliente."
                ),
                refund_required=True,
            )
            return

        RentalRequestCommands._create_blocking_period(rental_request, variant)
        rental_request.status = RentalRequest.STATUS_PAID
        rental_request.paid_at = timezone.now()
        rental_request.save(update_fields=['status', 'paid_at', 'updated_at'])

        # A partir de aqui (pago ya confirmado) es que nace todo lo demas:
        # Order/OrderItem (fuente oficial del pedido para "Mis Pedidos"),
        # OperationTicket y RentalOperation -- nunca antes de este punto.
        from orders.services.commands import OrderCommands
        order = OrderCommands.create_from_rental(rental_request)

        from operations.services.commands import OperationCommands
        ticket = OperationCommands.ensure_ticket_for_rental(rental_request)
        from renting.services.operations import RentalOperationCommands
        RentalOperationCommands.ensure_for_request(rental_request)

        from notifications.services.commands import NotificationCommands
        _user = rental_request.user
        _ctx  = {
            'request_uuid':   str(rental_request.uuid),
            'order_uuid':     str(order.uuid),
            'equipment_name': rental_request.equipment_variant.equipment.name,
            'start_date':     str(rental_request.start_date),
            'end_date':       str(rental_request.end_date),
            'grand_total':    str(rental_request.grand_total),
            'ticket_number':  ticket.ticket_number,
            'ticket_uuid':    str(ticket.uuid),
            'user_name':      _user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_payment_confirmed',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )

    @staticmethod
    @transaction.atomic
    def approve_manual_validation(rental_request: RentalRequest, admin_user=None) -> RentalRequest:
        """
        Aprueba una RentalRequest COD que esta pending_validation. Segundo (y ultimo)
        punto autoritativo de lock+disponibilidad: aqui se crea el RentalPeriod que
        bloquea el calendario para pago contra entrega, replicando el mismo patron
        de confirm_payment (select_for_update + AvailabilityEngine.is_available +
        conflicto). No se cobro nada todavia, por eso refund_required=False.
        """
        rental_request = RentalRequest.objects.select_for_update().get(pk=rental_request.pk)
        if rental_request.status == RentalRequest.STATUS_CONFIRMED:
            return rental_request  # idempotente: ya aprobada
        if rental_request.status != RentalRequest.STATUS_PENDING_VALIDATION:
            raise ValueError("Solo se pueden aprobar solicitudes pendientes de validacion.")

        variant = EquipmentVariant.objects.select_for_update().get(pk=rental_request.equipment_variant_id)
        from renting.services.availability import AvailabilityEngine
        if not AvailabilityEngine.is_available(
            variant.id, rental_request.start_date, rental_request.end_date,
            rental_request.quantity, rental_request.rental_mode,
            rental_request.delivery_time, rental_request.pickup_time,
        ):
            RentalRequestCommands._flag_payment_conflict(
                rental_request,
                note=(
                    "Conflicto de disponibilidad al aprobar la solicitud COD; no se "
                    "realizo cobro. Contactar al cliente para reprogramar."
                ),
                refund_required=False,
            )
            return rental_request

        RentalRequestCommands._create_blocking_period(rental_request, variant)
        rental_request.status = RentalRequest.STATUS_CONFIRMED
        rental_request.save(update_fields=['status', 'updated_at'])

        # Mismo punto de nacimiento que confirm_payment(): Order/OrderItem +
        # OperationTicket + RentalOperation nacen aqui, nunca antes (COD no
        # tiene PaymentResult de pasarela, pero esta aprobacion manual del
        # admin es su equivalente autoritativo).
        from orders.services.commands import OrderCommands
        order = OrderCommands.create_from_rental(rental_request)

        from operations.services.commands import OperationCommands
        ticket = OperationCommands.ensure_ticket_for_rental(rental_request)
        from renting.services.operations import RentalOperationCommands
        RentalOperationCommands.ensure_for_request(rental_request, actor=admin_user)

        from notifications.services.commands import NotificationCommands
        _user = rental_request.user
        _ctx = {
            'request_uuid':   str(rental_request.uuid),
            'order_uuid':     str(order.uuid),
            'equipment_name': rental_request.equipment_variant.equipment.name,
            'start_date':     str(rental_request.start_date),
            'end_date':       str(rental_request.end_date),
            'grand_total':    str(rental_request.grand_total),
            'ticket_number':  ticket.ticket_number,
            'ticket_uuid':    str(ticket.uuid),
            'user_name':      _user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_cod_confirmed',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )
        return rental_request

    @staticmethod
    @transaction.atomic
    def reject_request(rental_request: RentalRequest, admin_user=None, reason: str = '') -> RentalRequest:
        """Rechaza una solicitud COD pending_validation. No existe RentalPeriod aun."""
        rental_request = RentalRequest.objects.select_for_update().get(pk=rental_request.pk)
        if rental_request.status != RentalRequest.STATUS_PENDING_VALIDATION:
            raise ValueError("Solo se pueden rechazar solicitudes pendientes de validacion.")

        rental_request.status = RentalRequest.STATUS_CANCELLED
        if reason:
            stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
            rental_request.admin_notes = (f"{rental_request.admin_notes}\n[{stamp}] Rechazada: {reason}").strip()
        rental_request.save(update_fields=['status', 'admin_notes', 'updated_at'])

        from notifications.services.commands import NotificationCommands
        _user = rental_request.user
        _ctx = {
            'request_uuid':   str(rental_request.uuid),
            'equipment_name': rental_request.equipment_variant.equipment.name,
            'reason':         reason,
            'user_name':      _user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_request_rejected',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )
        return rental_request

    @staticmethod
    @transaction.atomic
    def activate_period(rental_request: RentalRequest) -> RentalRequest:
        """Marca el equipo como entregado: paid/confirmed -> in_operation, scheduled -> active."""
        rental_request = RentalRequest.objects.select_for_update().get(pk=rental_request.pk)
        if rental_request.status == RentalRequest.STATUS_IN_OPERATION:
            return rental_request  # idempotente
        if rental_request.status not in (RentalRequest.STATUS_PAID, RentalRequest.STATUS_CONFIRMED):
            raise ValueError("Solo se puede iniciar operacion desde paid o confirmed.")

        RentalPeriod.objects.filter(
            rental_request=rental_request, status=RentalPeriod.STATUS_SCHEDULED,
        ).update(status=RentalPeriod.STATUS_ACTIVE)
        rental_request.status = RentalRequest.STATUS_IN_OPERATION
        rental_request.save(update_fields=['status', 'updated_at'])
        return rental_request

    @staticmethod
    @transaction.atomic
    def release_period(rental_request: RentalRequest, admin_user=None, reason: str = '') -> RentalRequest:
        """
        Libera la agenda de una solicitud sin cancelar la solicitud en si (override
        admin: unidad danada, reprogramacion manual). No toca RentalRequest.status.
        """
        updated = RentalPeriod.objects.filter(
            rental_request=rental_request,
            status__in=[RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE],
        ).update(status=RentalPeriod.STATUS_CANCELLED)

        if updated and reason:
            stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
            rental_request.admin_notes = (f"{rental_request.admin_notes}\n[{stamp}] Agenda liberada: {reason}").strip()
            rental_request.save(update_fields=['admin_notes', 'updated_at'])

        return rental_request

    @staticmethod
    @transaction.atomic
    def extend_period(rental_request: RentalRequest, new_end_date, admin_user=None, reason: str = '') -> RentalRequest:
        """
        Extiende una renta activa moviendo end_date hacia adelante, si hay
        disponibilidad en el rango adicional [end_date actual, new_end_date).
        Admin-only, sin cobro automatico: el admin gestiona la diferencia de forma
        manual/offline (mismo patron que COD); esta accion solo recalcula
        base_cost/tax_amount/grand_total para que el total esperado quede reflejado
        en la solicitud. Solo modo dias -- extension por horas no tiene un caso de
        uso claro (mismo dia).
        """
        rental_request = RentalRequest.objects.select_for_update().get(pk=rental_request.pk)

        if rental_request.status not in (
            RentalRequest.STATUS_PAID, RentalRequest.STATUS_CONFIRMED, RentalRequest.STATUS_IN_OPERATION,
        ):
            raise ValueError("Solo se puede extender una renta pagada, confirmada o en operacion.")
        if rental_request.rental_mode != RentalRequest.RENTAL_MODE_DAYS:
            raise ValueError("La extension de renta solo esta disponible para renta por dias.")
        if new_end_date <= rental_request.end_date:
            raise ValueError("La nueva fecha de fin debe ser posterior a la fecha de fin actual.")

        period = RentalPeriod.objects.select_for_update().filter(
            rental_request=rental_request,
            status__in=[RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE],
        ).first()
        if period is None:
            raise ValueError("La solicitud no tiene un periodo de agenda activo para extender.")

        variant = rental_request.equipment_variant
        from renting.services.availability import AvailabilityEngine
        if not AvailabilityEngine.is_available(
            variant.id, rental_request.end_date, new_end_date, period.quantity,
            RentalRequest.RENTAL_MODE_DAYS,
        ):
            raise ValueError("No hay disponibilidad para extender la renta hasta la fecha solicitada.")

        old_end_date = rental_request.end_date

        period.end_date = new_end_date
        period.save(update_fields=['end_date', 'updated_at'])

        total_days = (new_end_date - rental_request.start_date).days
        base_cost = (variant.rental_price_per_day or Decimal('0')) * total_days * rental_request.quantity
        subtotal = base_cost + rental_request.transport_total + rental_request.setup_total
        from renting.services.pricing import RentalPricingCalculator
        tax_rate = RentalPricingCalculator.get_tax_rate(variant)
        tax_amount = (subtotal * tax_rate).quantize(Decimal('0.01'))
        grand_total = subtotal + tax_amount

        rental_request.end_date = new_end_date
        rental_request.total_rental_days = total_days
        rental_request.base_cost = base_cost
        rental_request.tax_amount = tax_amount
        rental_request.grand_total = grand_total

        stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
        note = f"[{stamp}] Renta extendida de {old_end_date} a {new_end_date}"
        if reason:
            note += f": {reason}"
        rental_request.admin_notes = (f"{rental_request.admin_notes}\n{note}").strip()

        rental_request.save(update_fields=[
            'end_date', 'total_rental_days', 'base_cost', 'tax_amount', 'grand_total',
            'admin_notes', 'updated_at',
        ])

        return rental_request

    @staticmethod
    @transaction.atomic
    def release_on_payment_failure(rental_request: RentalRequest) -> None:
        """
        Libera la solicitud cuando el pago online (Wompi/Nequi) fue rechazado,
        anulado o expiro. Normalmente es un no-op sobre RentalPeriod: ya no se crea
        ningun periodo antes de la confirmacion del pago, asi que el filtro solo
        encuentra filas en la rara carrera de un webhook "aprobado" duplicado que ya
        creo un periodo antes de que llegue el evento de fallo.
        """
        rental_request = RentalRequest.objects.select_for_update().get(pk=rental_request.pk)
        if rental_request.status in RentalRequestCommands._RESOLVED_STATUSES:
            return

        rental_request.status = RentalRequest.STATUS_CANCELLED
        rental_request.save(update_fields=['status', 'updated_at'])

        RentalPeriod.objects.filter(
            rental_request=rental_request,
            status__in=[RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE],
        ).update(status=RentalPeriod.STATUS_CANCELLED)

        from notifications.services.commands import NotificationCommands
        _user = rental_request.user
        _ctx = {
            'request_uuid':   str(rental_request.uuid),
            'equipment_name': rental_request.equipment_variant.equipment.name,
            'user_name':      _user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='rental_payment_failed',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )

    @staticmethod
    @transaction.atomic
    def cancel_request(request: RentalRequest) -> RentalRequest:
        """
        Cancela la solicitud y libera los periodos de disponibilidad asociados.
        En la mayoria de los casos (cancelacion antes de pagar) este filtro es un
        no-op seguro, ya que no existe RentalPeriod hasta confirm_payment()/
        approve_manual_validation().
        """
        request.status = RentalRequest.STATUS_CANCELLED
        request.save(update_fields=['status', 'updated_at'])

        RentalPeriod.objects.filter(
            rental_request=request,
            status__in=[RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE],
        ).update(status=RentalPeriod.STATUS_CANCELLED)

        return request

    @staticmethod
    @transaction.atomic
    def complete_period(rental_request: RentalRequest) -> None:
        """Marca los periodos de la solicitud como completados (llamar al devolver el equipo)."""
        if rental_request.status == RentalRequest.STATUS_FINISHED:
            return  # idempotente
        RentalPeriod.objects.filter(
            rental_request=rental_request,
            status=RentalPeriod.STATUS_ACTIVE,
        ).update(status=RentalPeriod.STATUS_COMPLETED)
        rental_request.status = RentalRequest.STATUS_FINISHED
        rental_request.save(update_fields=['status', 'updated_at'])

    ATTACHMENT_ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.pdf']
    ATTACHMENT_MAX_SIZE_MB = 15
    ATTACHMENT_MAX_COUNT = 10

    @staticmethod
    @transaction.atomic
    def add_project_attachments(rental_request: RentalRequest, files, uploaded_by=None) -> list:
        """
        Antes esta validacion vivia inline en renting/api/views.py::attachments() (antipatron:
        logica de negocio en la vista) y solo chequeaba tamano/content-type declarado por el
        cliente. Centraliza en accounts.services.commands.validate_file (mismo validador que
        KYC/avatares) para agregar el chequeo real de magic-bytes.
        """
        from accounts.services.commands import validate_file
        from renting.models import RentalProjectAttachment

        existing = rental_request.project_attachments.filter(is_deleted=False).count()
        if existing + len(files) > RentalRequestCommands.ATTACHMENT_MAX_COUNT:
            raise ValueError(f"La reserva admite maximo {RentalRequestCommands.ATTACHMENT_MAX_COUNT} archivos.")

        for file in files:
            validate_file(
                file, max_size_mb=RentalRequestCommands.ATTACHMENT_MAX_SIZE_MB,
                allowed_extensions=RentalRequestCommands.ATTACHMENT_ALLOWED_EXTENSIONS,
                magic_bytes_check=True,
            )

        return [
            RentalProjectAttachment.objects.create(
                rental_request=rental_request,
                file=file,
                original_name=file.name[:255],
                content_type=file.content_type or '',
                uploaded_by=uploaded_by,
            ) for file in files
        ]


class EquipmentLogisticsConfigCommands:
    @staticmethod
    @transaction.atomic
    def upsert(equipment: Equipment, **fields) -> EquipmentLogisticsConfig:
        config, _ = EquipmentLogisticsConfig.objects.get_or_create(equipment=equipment)
        allowed = (
            'delivery_cost', 'pickup_cost', 'installation_cost',
            'calibration_cost', 'training_cost', 'startup_cost', 'notes',
        )
        for key, val in fields.items():
            if key in allowed:
                setattr(config, key, val)
        config.save()
        return config

    @staticmethod
    @transaction.atomic
    def delete(equipment: Equipment) -> None:
        """
        Solo elimina la config de logistica de este equipo -- el Equipment en
        si NO se toca aqui (para eso existe EquipmentCommands.delete_equipment()).

        Bug corregido (2026-07-17): esta funcion tambien soft-eliminaba el
        Equipment completo (copy-paste erroneo), asi que un admin que hacia
        click en "Eliminar configuracion" en la pestana Logistica terminaba
        borrando el equipo entero sin darse cuenta.
        """
        EquipmentLogisticsConfig.objects.filter(equipment=equipment, is_deleted=False).update(
            is_deleted=True
        )


class EquipmentMarketingCommands:
    @staticmethod
    @transaction.atomic
    def upsert(equipment: Equipment, **fields) -> EquipmentMarketing:
        marketing, _ = EquipmentMarketing.objects.get_or_create(equipment=equipment)
        allowed = (
            'reference_price', 'promo_price', 'show_discount_percentage', 'tags',
            'main_message', 'featured_benefit', 'trust_message', 'urgency_message',
            'social_proof_message', 'purchase_price_reference', 'financial_message',
            'use_cases', 'cta_label', 'promo_banner_message', 'quick_benefits',
        )
        for key, val in fields.items():
            if key in allowed:
                setattr(marketing, key, val)
        marketing.save()
        return marketing

    @staticmethod
    @transaction.atomic
    def delete(equipment: Equipment) -> None:
        EquipmentMarketing.objects.filter(equipment=equipment, is_deleted=False).update(is_deleted=True)
