from django.db import models
from django.conf import settings
from django.db.models import Q
from ecommerce.base_models import SintelBaseModel


class DispatcherProfile(SintelBaseModel):
    DRIVER = 'DRIVER'
    LOGISTICS = 'LOGISTICS'
    FIELD_OPS = 'FIELD_OPS'
    TYPE_CHOICES = [
        (DRIVER,    'Conductor'),
        (LOGISTICS, 'Logistica'),
        (FIELD_OPS, 'Operario de campo'),
    ]

    user            = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dispatcher_profile',
    )
    dispatcher_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=DRIVER)
    vehicle_plate   = models.CharField(max_length=20, blank=True, default='')
    vehicle_type    = models.CharField(max_length=50, blank=True, default='')
    coverage_cities = models.JSONField(default=list, blank=True)
    is_available    = models.BooleanField(default=True, db_index=True)
    is_active       = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name        = 'perfil de despachador'
        verbose_name_plural = 'perfiles de despachadores'

    def __str__(self):
        return f"Despachador {self.user.email}"


class OperationTicket(SintelBaseModel):
    SHOP_DELIVERY = 'SHOP_DELIVERY'
    RENTAL        = 'RENTAL'
    SERVICE       = 'SERVICE'
    TYPE_CHOICES  = [
        (SHOP_DELIVERY, 'Entrega de tienda'),
        (RENTAL,        'Alquiler de equipo'),
        (SERVICE,       'Servicio tecnico'),
    ]

    STATUS_CREATED       = 'CREATED'
    STATUS_DOCS_PENDING  = 'DOCS_PENDING'
    STATUS_READY         = 'READY_TO_ASSIGN'
    STATUS_ASSIGNED      = 'ASSIGNED'
    STATUS_SCHEDULED     = 'SCHEDULED'
    STATUS_EN_ROUTE      = 'EN_ROUTE'
    STATUS_IN_PROGRESS   = 'IN_PROGRESS'
    STATUS_COMPLETED     = 'COMPLETED'
    STATUS_CANCELLED     = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_CREATED,      'Creado'),
        (STATUS_DOCS_PENDING, 'Documentos pendientes'),
        (STATUS_READY,        'Listo para asignar'),
        (STATUS_ASSIGNED,     'Asignado'),
        (STATUS_SCHEDULED,    'Programado'),
        (STATUS_EN_ROUTE,     'En camino'),
        (STATUS_IN_PROGRESS,  'En ejecucion'),
        (STATUS_COMPLETED,    'Completado'),
        (STATUS_CANCELLED,    'Cancelado'),
    ]

    PRIORITY_HIGH = 'HIGH'
    PRIORITY_LOW  = 'LOW'
    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, 'Alta'),
        (PRIORITY_LOW,  'Baja'),
    ]

    ticket_number  = models.CharField(max_length=30, unique=True, db_index=True)
    operation_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    status         = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_CREATED, db_index=True
    )
    priority       = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES,
        default=PRIORITY_LOW, db_index=True
    )
    customer       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='operation_tickets',
    )

    # Exactamente uno debe ser no nulo (validado por CheckConstraint)
    source_order = models.ForeignKey(
        'orders.Order',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='operation_tickets',
    )
    source_rental_request = models.OneToOneField(
        'renting.RentalRequest',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='operation_ticket',
    )

    # [2026-07-12] Enlace de trazabilidad hacia el registro de ejecucion especifico de cada
    # dominio (CORE v4, Fase 5, Opcion B -- Paso 1). Nullable y sin efecto en el status propio
    # de este ticket todavia -- solo permite saber, por primera vez, que ServiceOperation/
    # RentalOperation/Shipment corresponde a cada ticket. Exactamente uno se puebla segun
    # operation_type (SERVICE/RENTAL/SHOP_DELIVERY respectivamente), via el comando de backfill
    # `operations/management/commands/backfill_operation_satellite_links.py`. Ver
    # Documentacion/Arquitectura_general/MIGRACION_CORE_V4_DOMINIOS_FASE5_PROPUESTA_OPERACIONES.md.
    service_operation = models.OneToOneField(
        'technical_services.ServiceOperation',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='operation_ticket',
    )
    rental_operation = models.OneToOneField(
        'renting.RentalOperation',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='operation_ticket',
    )
    shipment = models.OneToOneField(
        'orders.Shipment',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='operation_ticket',
    )

    # Programacion del hito "Fecha y hora programada"
    scheduled_date       = models.DateField(null=True, blank=True, db_index=True)
    scheduled_time_start = models.TimeField(null=True, blank=True)
    scheduled_time_end   = models.TimeField(null=True, blank=True)

    # Snapshot de ubicacion
    location_address    = models.CharField(max_length=300, blank=True, default='')
    location_city       = models.CharField(max_length=100, blank=True, default='')
    location_department = models.CharField(max_length=100, blank=True, default='')

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name        = 'ticket de operacion'
        verbose_name_plural = 'tickets de operacion'
        ordering            = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(source_order__isnull=False, source_rental_request__isnull=True) |
                    Q(source_order__isnull=True,  source_rental_request__isnull=False)
                ),
                name='operationticket_single_source',
            ),
            models.UniqueConstraint(
                fields=['source_order', 'operation_type'],
                condition=Q(source_order__isnull=False, is_deleted=False),
                name='operationticket_unique_order_type',
            ),
        ]

    def __str__(self):
        return f"{self.ticket_number} [{self.status}]"

    @property
    def source(self):
        return self.source_order or self.source_rental_request

    # [2026-07-12] CORE v4, Fase 5, Opcion B, Paso 2. `status` (arriba) SIGUE siendo un campo
    # real de BD -- no se convierte en property porque OperationTicketSelector ya lo usa en
    # `.filter(status=...)` y romperia esa query. En vez de eso, `get_effective_status()` es un
    # metodo ADITIVO de solo lectura que deriva el estado del satelite especifico
    # (ServiceOperation/RentalOperation/Shipment) cuando existe, usando los mapas de traduccion
    # de abajo -- best-effort, no 1:1 exacto (cada satelite tiene su propia secuencia y
    # granularidad, ver MIGRACION_CORE_V4_DOMINIOS_FASE5_PROPUESTA_OPERACIONES.md). Si el
    # satelite todavia no existe (ticket en etapa temprana, DOCS_PENDING/READY_TO_ASSIGN) cae al
    # campo `status` propio, que en ese caso SI es la unica fuente de verdad real.
    _SERVICE_OPERATION_STATUS_MAP = {
        'READY_FOR_PLANNING':  STATUS_READY,
        'PLANNED':             STATUS_SCHEDULED,
        'TECHNICIAN_ASSIGNED': STATUS_ASSIGNED,
        'CUSTOMER_NOTIFIED':   STATUS_ASSIGNED,
        'READY_TO_VISIT':      STATUS_ASSIGNED,
        'ON_THE_WAY':          STATUS_EN_ROUTE,
        'ARRIVED':             STATUS_IN_PROGRESS,
        'IN_PROGRESS':         STATUS_IN_PROGRESS,
        'COMPLETED':           STATUS_COMPLETED,
        'CLOSED':              STATUS_COMPLETED,
        'CANCELLED':           STATUS_CANCELLED,
    }
    _RENTAL_OPERATION_STATUS_MAP = {
        'READY_FOR_SCHEDULING': STATUS_READY,
        'SCHEDULED':            STATUS_SCHEDULED,
        'TRANSPORT_ASSIGNED':   STATUS_ASSIGNED,
        'READY_FOR_DELIVERY':   STATUS_ASSIGNED,
        'DELIVERED':            STATUS_IN_PROGRESS,
        'IN_OPERATION':         STATUS_IN_PROGRESS,
        'READY_FOR_PICKUP':     STATUS_IN_PROGRESS,
        'PICKED_UP':            STATUS_IN_PROGRESS,
        'RETURN_INSPECTION':    STATUS_IN_PROGRESS,
        'COMPLETED':            STATUS_COMPLETED,
    }
    _SHIPMENT_STATUS_MAP = {
        'PREPARING':          STATUS_READY,
        'READY_FOR_DISPATCH': STATUS_READY,
        'ASSIGNED':           STATUS_ASSIGNED,
        'PICKED_UP':          STATUS_EN_ROUTE,
        'IN_TRANSIT':         STATUS_EN_ROUTE,
        'OUT_FOR_DELIVERY':   STATUS_EN_ROUTE,
        'delivered':          STATUS_COMPLETED,
        'COMPLETED':          STATUS_COMPLETED,
        'FAILED_DELIVERY':    STATUS_IN_PROGRESS,
        'LOST':               STATUS_CANCELLED,
    }

    def get_effective_status(self):
        """
        Estado a MOSTRAR en el tablero unificado de Operaciones. Deriva del satelite
        especifico cuando existe; si no, usa el campo `status` propio (fuente de verdad
        real para tickets en etapa temprana, antes de que exista el satelite).

        [2026-07-12] Los estados terminales propios (CANCELLED/COMPLETED) tienen prioridad
        sobre el satelite -- encontrado con datos reales durante esta migracion: existe al
        menos un ticket real con status=CANCELLED cuyo ServiceOperation vinculado sigue en
        READY_FOR_PLANNING (nunca se sincronizo). Confiar ciegamente en el satelite en ese
        caso mostraria "listo para asignar" para un trabajo que en realidad esta cancelado --
        peor que el comportamiento actual. Un estado terminal explicito en el ticket es una
        decision que no deberia quedar oculta por un satelite desactualizado.
        """
        if self.status in (self.STATUS_CANCELLED, self.STATUS_COMPLETED):
            return self.status
        if self.operation_type == self.SERVICE and self.service_operation_id:
            return self._SERVICE_OPERATION_STATUS_MAP.get(self.service_operation.status, self.status)
        if self.operation_type == self.RENTAL and self.rental_operation_id:
            return self._RENTAL_OPERATION_STATUS_MAP.get(self.rental_operation.status, self.status)
        if self.operation_type == self.SHOP_DELIVERY and self.shipment_id:
            return self._SHIPMENT_STATUS_MAP.get(self.shipment.status, self.status)
        return self.status


class OperationAssignment(SintelBaseModel):
    ROLE_TECHNICIAN = 'TECHNICIAN'
    ROLE_DISPATCHER = 'DISPATCHER'
    ROLE_TRANSPORTER = 'TRANSPORTER'
    ROLE_CONTRACTOR = 'CONTRACTOR'
    ROLE_CHOICES    = [
        (ROLE_TECHNICIAN, 'Tecnico'),
        (ROLE_DISPATCHER, 'Despachador'),
        (ROLE_TRANSPORTER, 'Transportista'),
        (ROLE_CONTRACTOR, 'Contratista'),
    ]
    STATUS_ACTIVE   = 'ACTIVE'
    STATUS_RELEASED = 'RELEASED'

    ticket    = models.ForeignKey(
        OperationTicket,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    assignee  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='operation_assignments',
    )
    role      = models.CharField(max_length=15, choices=ROLE_CHOICES)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='operation_assignments_made',
    )
    availability_slot = models.ForeignKey(
        'accounts.ProfessionalAvailability',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='operation_assignments',
    )
    status = models.CharField(
        max_length=10,
        choices=[(STATUS_ACTIVE, 'Activa'), (STATUS_RELEASED, 'Liberada')],
        default=STATUS_ACTIVE,
        db_index=True,
    )

    class Meta:
        verbose_name        = 'asignacion de operacion'
        verbose_name_plural = 'asignaciones de operacion'

    def __str__(self):
        return f"{self.ticket.ticket_number} -> {self.assignee.email} ({self.role})"


class TrackingEvent(SintelBaseModel):
    MILESTONE_CREATED      = 'CREATED'
    MILESTONE_DOCS_APPROVED = 'DOCS_APPROVED'
    MILESTONE_ASSIGNED     = 'ASSIGNED'
    MILESTONE_SCHEDULED    = 'SCHEDULED'
    MILESTONE_EN_ROUTE     = 'EN_ROUTE'
    MILESTONE_IN_PROGRESS  = 'IN_PROGRESS'
    MILESTONE_COMPLETED    = 'COMPLETED'
    MILESTONE_CANCELLED    = 'CANCELLED'
    MILESTONE_NOTE         = 'NOTE'
    MILESTONE_CHOICES = [
        (MILESTONE_CREATED,       'Solicitud creada'),
        (MILESTONE_DOCS_APPROVED, 'Documentos aprobados'),
        (MILESTONE_ASSIGNED,      'Recurso asignado'),
        (MILESTONE_SCHEDULED,     'Fecha y hora programada'),
        (MILESTONE_EN_ROUTE,      'En camino'),
        (MILESTONE_IN_PROGRESS,   'En ejecucion'),
        (MILESTONE_COMPLETED,     'Completado'),
        (MILESTONE_CANCELLED,     'Cancelado'),
        (MILESTONE_NOTE,          'Nota'),
    ]

    ticket              = models.ForeignKey(
        OperationTicket,
        on_delete=models.CASCADE,
        related_name='tracking_events',
    )
    milestone           = models.CharField(max_length=20, choices=MILESTONE_CHOICES, db_index=True)
    description         = models.TextField(blank=True, default='')
    created_by          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    is_customer_visible = models.BooleanField(default=True)
    metadata            = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name        = 'evento de tracking'
        verbose_name_plural = 'eventos de tracking'
        ordering            = ['created_at']

    def __str__(self):
        return f"{self.ticket.ticket_number} | {self.milestone}"


class OperationDocument(SintelBaseModel):
    DOC_ID_CARD          = 'ID_CARD'
    DOC_RENTAL_CONTRACT  = 'RENTAL_CONTRACT'
    DOC_SERVICE_CONTRACT = 'SERVICE_CONTRACT'
    DOC_INVOICE          = 'INVOICE'
    DOC_OTHER            = 'OTHER'
    DOC_TYPE_CHOICES = [
        (DOC_ID_CARD,          'Cedula de identidad'),
        (DOC_RENTAL_CONTRACT,  'Contrato de alquiler'),
        (DOC_SERVICE_CONTRACT, 'Contrato de servicios'),
        (DOC_INVOICE,          'Factura de compra'),
        (DOC_OTHER,            'Otro'),
    ]

    STATUS_PENDING  = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pendiente'),
        (STATUS_APPROVED, 'Aprobado'),
        (STATUS_REJECTED, 'Rechazado'),
    ]

    ticket           = models.ForeignKey(
        OperationTicket,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    doc_type         = models.CharField(max_length=25, choices=DOC_TYPE_CHOICES, db_index=True)
    file             = models.FileField(
        upload_to='operations/documents/%Y/%m/',
        blank=True, null=True,
    )
    status           = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default=STATUS_PENDING, db_index=True
    )
    uploaded_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_operation_docs',
    )
    reviewed_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_operation_docs',
    )
    rejection_reason = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        verbose_name        = 'documento de operacion'
        verbose_name_plural = 'documentos de operacion'

    def __str__(self):
        return f"{self.ticket.ticket_number} | {self.doc_type} [{self.status}]"


class OperationReview(SintelBaseModel):
    ticket   = models.OneToOneField(
        OperationTicket,
        on_delete=models.CASCADE,
        related_name='review',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='operation_reviews',
    )
    rating             = models.PositiveSmallIntegerField(default=5)
    quality_rating     = models.PositiveSmallIntegerField(default=5)
    punctuality_rating = models.PositiveSmallIntegerField(default=5)
    condition_rating   = models.PositiveSmallIntegerField(default=5)
    comment            = models.TextField(blank=True, default='')

    class Meta:
        verbose_name        = 'resena de operacion'
        verbose_name_plural = 'resenas de operacion'

    def __str__(self):
        return f"Resena de {self.reviewer.email} para {self.ticket.ticket_number}"
