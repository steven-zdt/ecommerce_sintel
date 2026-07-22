"""
CORE v4, Fase 5 (Opcion B, Paso 1) -- puebla los 3 FKs de trazabilidad nuevos de
OperationTicket (service_operation/rental_operation/shipment) para los tickets ya
existentes, usando source_order/source_rental_request como puente.

Solo lectura sobre ServiceOperation/RentalOperation/Shipment; solo UPDATE de los 3
campos nuevos en OperationTicket. No cambia is_active, status, ni ningun otro campo.
Idempotente -- correrlo varias veces no duplica ni sobreescribe enlaces ya poblados.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from operations.models import OperationTicket
from technical_services.models import ServiceOperation
from renting.models import RentalOperation
from orders.models import Shipment


class Command(BaseCommand):
    help = (
        'Puebla OperationTicket.service_operation/rental_operation/shipment para '
        'tickets existentes (CORE v4, Fase 5, Opcion B, Paso 1).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo reporta que se enlazaria, sin escribir en la base de datos.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        matched = {'SERVICE': 0, 'RENTAL': 0, 'SHOP_DELIVERY': 0}
        unmatched = {'SERVICE': 0, 'RENTAL': 0, 'SHOP_DELIVERY': 0}

        with transaction.atomic():
            service_tickets = OperationTicket.objects.filter(
                operation_type=OperationTicket.SERVICE,
                service_operation__isnull=True,
                source_order__isnull=False,
            )
            for ticket in service_tickets:
                op = ServiceOperation.objects.filter(order=ticket.source_order).first()
                if op:
                    matched['SERVICE'] += 1
                    if not dry_run:
                        ticket.service_operation = op
                        ticket.save(update_fields=['service_operation'])
                else:
                    unmatched['SERVICE'] += 1

            rental_tickets = OperationTicket.objects.filter(
                operation_type=OperationTicket.RENTAL,
                rental_operation__isnull=True,
                source_rental_request__isnull=False,
            )
            for ticket in rental_tickets:
                op = RentalOperation.objects.filter(rental_request=ticket.source_rental_request).first()
                if op:
                    matched['RENTAL'] += 1
                    if not dry_run:
                        ticket.rental_operation = op
                        ticket.save(update_fields=['rental_operation'])
                else:
                    unmatched['RENTAL'] += 1

            shipment_tickets = OperationTicket.objects.filter(
                operation_type=OperationTicket.SHOP_DELIVERY,
                shipment__isnull=True,
                source_order__isnull=False,
            )
            for ticket in shipment_tickets:
                sh = Shipment.objects.filter(order=ticket.source_order).first()
                if sh:
                    matched['SHOP_DELIVERY'] += 1
                    if not dry_run:
                        ticket.shipment = sh
                        ticket.save(update_fields=['shipment'])
                else:
                    unmatched['SHOP_DELIVERY'] += 1

            if dry_run:
                transaction.set_rollback(True)

        mode = 'DRY-RUN (sin escribir)' if dry_run else 'APLICADO'
        self.stdout.write(self.style.SUCCESS(f'[{mode}] Backfill de enlaces de operacion:'))
        for op_type in ('SERVICE', 'RENTAL', 'SHOP_DELIVERY'):
            self.stdout.write(f'  {op_type}: {matched[op_type]} enlazados, {unmatched[op_type]} sin satelite correspondiente')
