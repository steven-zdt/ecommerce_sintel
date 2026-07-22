"""
Management command: test_rental_to_operations_flow

Comprueba el flujo E2E completo:
  URL inicio: /alquiler/equipo/259ff0c8-1d58-44ff-86b1-01b15641686b
  URL fin:    /mi-cuenta/operaciones

Uso:
  docker exec ecommerce_sintel_django python manage.py test_rental_to_operations_flow
  docker exec ecommerce_sintel_django python manage.py test_rental_to_operations_flow --equipment-uuid <uuid>
  docker exec ecommerce_sintel_django python manage.py test_rental_to_operations_flow --rollback
"""
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()

EQUIPMENT_UUID = '259ff0c8-1d58-44ff-86b1-01b15641686b'


class Command(BaseCommand):
    help = 'Prueba el flujo E2E: alquiler → pago COD → OperationTicket → /mi-cuenta/operaciones'

    def add_arguments(self, parser):
        parser.add_argument('--equipment-uuid', default=EQUIPMENT_UUID)
        parser.add_argument(
            '--rollback',
            action='store_true',
            help='Eliminar la RentalRequest y el ticket creados al FINAL del test.',
        )
        parser.add_argument(
            '--cleanup-only',
            action='store_true',
            help='Solo elimina datos de tests previos (contact_doc_number=000000001) sin correr el test.',
        )

    def handle(self, *args, **options):
        eq_uuid = options['equipment_uuid']
        do_rollback = options['rollback']

        if options['cleanup_only']:
            self._cleanup_all_test_data()
            return

        results = {}
        rental_request = None
        ticket = None

        # ── Paso 1: EquipmentVariant ──────────────────────────────────────────
        variant = self._step1_get_variant(eq_uuid, results)

        # ── Paso 2: Usuario de prueba ─────────────────────────────────────────
        user = self._step2_get_user(results)

        # ── Paso 3: RentalRequest ─────────────────────────────────────────────
        if variant and user:
            rental_request = self._step3_create_request(variant, user, results)

        # ── Paso 4: Seleccionar pago COD (pending_validation, no bloquea agenda) ──
        if rental_request:
            self._step4_confirm_cod(rental_request, results)

        # ── Paso 4.5: Admin aprueba la solicitud (crea el RentalPeriod) ──────────
        if rental_request:
            self._step4b_approve_manual_validation(rental_request, results)

        # ── Paso 5: Verificar OperationTicket ────────────────────────────────
        if rental_request:
            ticket = self._step5_verify_ticket(rental_request, user, results)

        # ── Paso 6: Verificar TrackingEvents ─────────────────────────────────
        if ticket:
            self._step6_verify_events(ticket, results)

        # ── Paso 7: Verificar endpoint /mi-cuenta/operaciones ────────────────
        if user:
            self._step7_verify_list_endpoint(user, results)

        # ── Resumen ───────────────────────────────────────────────────────────
        self._print_summary(results)

        # ── Rollback opcional ─────────────────────────────────────────────────
        if do_rollback and rental_request:
            self._rollback(rental_request, ticket)

    # ── Pasos ─────────────────────────────────────────────────────────────────

    def _step1_get_variant(self, eq_uuid, results):
        from renting.models import Equipment, EquipmentVariant
        step = 'Paso 1 — EquipmentVariant'
        try:
            equipment = Equipment.objects.get(uuid=eq_uuid, is_deleted=False)
            variant = (
                EquipmentVariant.objects
                .filter(equipment=equipment, is_active=True)
                .first()
            )
            if not variant:
                raise ValueError(f"No hay variantes activas para el equipo {eq_uuid}")
            self.stdout.write(
                f"  Equipo : {equipment.name}\n"
                f"  Variante SKU: {variant.sku}\n"
                f"  Precio/dia  : {variant.rental_price_per_day}"
            )
            results[step] = 'PASS'
            return variant
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'
            return None

    def _step2_get_user(self, results):
        step = 'Paso 2 — Usuario de prueba'
        try:
            user = User.objects.filter(is_staff=True, is_superuser=True, is_active=True).first()
            if not user:
                raise ValueError("No hay superusuarios activos en la BD")
            self.stdout.write(f"  Usuario: {user.email}")
            results[step] = 'PASS'
            return user
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'
            return None

    def _step3_create_request(self, variant, user, results):
        from renting.services.commands import RentalRequestCommands
        step = 'Paso 3 — RentalRequest.create_request()'
        try:
            validated_data = {
                'equipment_variant':  variant,
                'start_date':         date.today() + timedelta(days=3),
                'end_date':           date.today() + timedelta(days=6),
                'quantity':           1,
                'rental_mode':        'days',
                'location_address':   'Calle 85A Sur # 45 - 20',
                'location_city':      'Bogota',
                'location_department': 'Cundinamarca',
                'location_coordinates': '',
                'project_type':       '',
                'access_conditions':  '',
                'location_notes':     '',
                'contact_full_name':  'Test Usuario E2E',
                'contact_doc_type':   'CC',
                'contact_doc_number': '000000001',
                'contact_email':      user.email,
                'contact_phone':      '3001234567',
                'contact_company':    '',
                'contact_position':   '',
                'operational_notes':  'Test automatico E2E',
                'terms_accepted':     True,
            }
            rr = RentalRequestCommands.create_request(user, validated_data)
            self.stdout.write(
                f"  RentalRequest UUID  : {rr.uuid}\n"
                f"  Status              : {rr.status}\n"
                f"  Grand total         : {rr.grand_total}"
            )
            results[step] = 'PASS'
            return rr
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'
            return None

    def _step4_confirm_cod(self, rental_request, results):
        from renting.services.commands import RentalRequestCommands
        step = 'Paso 4 — process_payment_selection(COD)'
        try:
            result = RentalRequestCommands.process_payment_selection(
                rental_request=rental_request,
                payment_method='COD',
            )
            rental_request.refresh_from_db()
            self.stdout.write(
                f"  Resultado COD : {result}\n"
                f"  Status actual : {rental_request.status}"
            )
            results[step] = 'PASS'
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'

    def _step4b_approve_manual_validation(self, rental_request, results):
        from renting.services.commands import RentalRequestCommands
        step = 'Paso 4.5 — approve_manual_validation()'
        try:
            RentalRequestCommands.approve_manual_validation(rental_request)
            rental_request.refresh_from_db()
            self.stdout.write(f"  Status actual : {rental_request.status}")
            results[step] = 'PASS'
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'

    def _step5_verify_ticket(self, rental_request, user, results):
        from operations.models import OperationTicket
        from operations.services.selectors import OperationSelector
        step = 'Paso 5 — OperationTicket creado'
        try:
            ticket = OperationTicket.objects.filter(
                source_rental_request=rental_request,
                is_deleted=False,
            ).first()
            if not ticket:
                raise ValueError("No se creo el OperationTicket para la RentalRequest")

            self.stdout.write(
                f"  Ticket numero    : {ticket.ticket_number}\n"
                f"  Tipo             : {ticket.operation_type}\n"
                f"  Status           : {ticket.status}\n"
                f"  UUID             : {ticket.uuid}"
            )

            # Verificar que aparece en el selector del cliente
            qs = OperationSelector.list_for_user(user)
            uuids = list(qs.values_list('uuid', flat=True))
            if ticket.uuid not in uuids:
                raise ValueError("El ticket NO aparece en OperationSelector.list_for_user()")
            self.stdout.write(
                f"  Visible en /mi-cuenta/operaciones: SI ({len(uuids)} ticket(s) total)"
            )

            results[step] = 'PASS'
            return ticket
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'
            return None

    def _step6_verify_events(self, ticket, results):
        from operations.models import TrackingEvent
        step = 'Paso 6 — TrackingEvents en el ticket'
        try:
            events = TrackingEvent.objects.filter(
                ticket=ticket,
                is_deleted=False,
            ).order_by('created_at')
            if not events.exists():
                raise ValueError("El ticket no tiene TrackingEvents")
            self.stdout.write(f"  {events.count()} evento(s) encontrados:")
            for ev in events:
                self.stdout.write(f"    [{ev.milestone}] {ev.description or '(sin descripcion)'}")
            results[step] = 'PASS'
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'

    def _step7_verify_list_endpoint(self, user, results):
        from operations.services.selectors import OperationSelector
        step = 'Paso 7 — GET /api/v1/operations/my/ (OperationSelector)'
        try:
            qs = OperationSelector.list_for_user(user)
            count = qs.count()
            self.stdout.write(
                f"  Operaciones visibles para {user.email}: {count}"
            )
            if count == 0:
                raise ValueError("El usuario no tiene operaciones visibles — el ticker no se listaria en /mi-cuenta/operaciones")
            results[step] = 'PASS'
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
            results[step] = f'FAIL — {exc}'

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _print_summary(self, results):
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('RESUMEN DEL FLUJO E2E')
        self.stdout.write('─' * 60)
        all_pass = True
        for step, status in results.items():
            if status == 'PASS':
                self.stdout.write(self.style.SUCCESS(f'  PASS  {step}'))
            else:
                self.stdout.write(self.style.ERROR(f'  FAIL  {step}'))
                self.stdout.write(self.style.ERROR(f'        {status}'))
                all_pass = False
        self.stdout.write('─' * 60)
        if all_pass:
            self.stdout.write(self.style.SUCCESS(
                '\n  FLUJO COMPLETO: OK\n'
                '  /alquiler/equipo/... → wizard → COD → /mi-cuenta/operaciones ✓\n'
            ))
        else:
            self.stdout.write(self.style.ERROR('\n  FLUJO CON ERRORES — revisar pasos fallidos\n'))

    def _cleanup_all_test_data(self):
        from operations.models import OperationTicket, TrackingEvent, OperationDocument, OperationAssignment
        from renting.models import RentalRequest, RentalPeriod
        rrs = RentalRequest.objects.filter(contact_doc_number='000000001')
        count = 0
        for rr in rrs:
            try:
                t = OperationTicket.objects.get(source_rental_request=rr)
                TrackingEvent.objects.filter(ticket=t).delete()
                OperationDocument.objects.filter(ticket=t).delete()
                OperationAssignment.objects.filter(ticket=t).delete()
                t.delete()
            except OperationTicket.DoesNotExist:
                pass
            RentalPeriod.objects.filter(rental_request=rr).delete()
            rr.delete()
            count += 1
        self.stdout.write(self.style.WARNING(f'Cleanup: {count} RentalRequest(s) de prueba eliminadas.'))

    def _rollback(self, rental_request, ticket):
        self.stdout.write('\nRollback solicitado...')
        try:
            with transaction.atomic():
                if ticket:
                    from operations.models import TrackingEvent, OperationDocument, OperationAssignment
                    TrackingEvent.objects.filter(ticket=ticket).delete()
                    OperationDocument.objects.filter(ticket=ticket).delete()
                    OperationAssignment.objects.filter(ticket=ticket).delete()
                    ticket.delete()
                from renting.models import RentalPeriod
                RentalPeriod.objects.filter(rental_request=rental_request).delete()
                rental_request.delete()
            self.stdout.write(self.style.WARNING('  Rollback completado — datos de prueba eliminados.'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  Error en rollback: {exc}'))
