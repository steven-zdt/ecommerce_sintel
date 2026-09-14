# Extracted from the former renting.models module. Public imports remain in __init__.py.

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from ecommerce.base_models import SintelBaseModel

from .common import RentalLabor
from .equipment import EquipmentVariant

class RentalRequest(SintelBaseModel):
    """Solicitud de alquiler generada por el wizard de 8 pasos."""

    STATUS_DRAFT = 'draft'
    STATUS_PENDING_VALIDATION = 'pending_validation'
    STATUS_PENDING_PAYMENT = 'pending_payment'
    STATUS_PAID = 'paid'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_OPERATION = 'in_operation'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAYMENT_CONFLICT = 'payment_conflict'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Borrador'),
        (STATUS_PENDING_VALIDATION, 'Pendiente de validacion'),
        (STATUS_PENDING_PAYMENT, 'Pendiente de pago'),
        (STATUS_PAID, 'Pagado'),
        (STATUS_CONFIRMED, 'Confirmado'),
        (STATUS_IN_OPERATION, 'En operacion'),
        (STATUS_FINISHED, 'Finalizado'),
        (STATUS_CANCELLED, 'Cancelado'),
        (STATUS_PAYMENT_CONFLICT, 'Conflicto de pago'),
    ]

    RENTAL_MODE_DAYS = 'days'
    RENTAL_MODE_HOURS = 'hours'
    RENTAL_MODE_CHOICES = [
        (RENTAL_MODE_DAYS, 'Por dias'),
        (RENTAL_MODE_HOURS, 'Por horas'),
    ]

    # Modalidad comercial (2026-07-22) -- distinto de rental_mode (dias/horas,
    # un eje de pricing). commercial_type es "que tipo de contrato es esto":
    # RENTAL paga de inmediato (Wompi/Nequi/COD), COMODATO nunca cobra y pasa
    # directo a pending_validation (ver RentalRequestCommands.create_request()).
    # Default RENTAL preserva el comportamiento de toda fila/codigo existente.
    COMMERCIAL_RENTAL = 'RENTAL'
    COMMERCIAL_COMODATO = 'COMODATO'
    COMMERCIAL_TYPE_CHOICES = [
        (COMMERCIAL_RENTAL, 'Renting'),
        (COMMERCIAL_COMODATO, 'Comodato'),
    ]

    PRIORITY_LOW  = 'LOW'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW,  'Baja'),
        (PRIORITY_HIGH, 'Alta'),
    ]
    PRIORITY_MIN_DAYS = {
        PRIORITY_LOW:  7,
        PRIORITY_HIGH: 3,
    }

    DOC_CC = 'CC'
    DOC_NIT = 'NIT'
    DOC_CE = 'CE'
    DOC_PP = 'PP'
    DOC_TYPE_CHOICES = [
        (DOC_CC, 'Cedula de ciudadania'),
        (DOC_NIT, 'NIT'),
        (DOC_CE, 'Cedula de extranjeria'),
        (DOC_PP, 'Pasaporte'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rental_requests'
    )
    equipment_variant = models.ForeignKey(
        EquipmentVariant,
        on_delete=models.PROTECT,
        related_name='rental_requests'
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default=STATUS_DRAFT, db_index=True
    )
    commercial_type = models.CharField(
        max_length=10, choices=COMMERCIAL_TYPE_CHOICES,
        default=COMMERCIAL_RENTAL, db_index=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_LOW,
        db_index=True,
    )

    # Paso 2 -- Lugar de operacion  -> RentalRequestLocation ('location_info')
    # Paso 3 -- Responsable         -> RentalRequestContact  ('contact_info')
    # Las columnas se movieron en la migracion 0036 (auditoria DB-H1). Los
    # atributos siguen disponibles aqui via @property (bloque de delegacion al
    # final de la clase).

    # Paso 4 — Configuracion de renta
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    estimated_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    rental_mode = models.CharField(
        max_length=10, choices=RENTAL_MODE_CHOICES, default=RENTAL_MODE_DAYS
    )
    delivery_time = models.TimeField(null=True, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)
    operational_notes = models.TextField(blank=True, default='')

    # Paso 5 — Contrato y terminos
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # Paso 6 -- Transporte y puesta en marcha + totales calculados
    # -> RentalRequestCosts ('costs_info'), migracion 0036. labor_items se
    # queda aqui porque es ManyToMany (no se movio a proposito).
    labor_items = models.ManyToManyField(
        RentalLabor, blank=True, related_name='rental_requests'
    )

    PAYMENT_WOMPI    = 'WOMPI'
    PAYMENT_NEQUI    = 'NEQUI'
    PAYMENT_COD      = 'COD'
    # Comodato nunca cobra -- se salta process_payment_selection() por
    # completo (create_request() la fija directo, ver services/commands.py),
    # asi que sin esta constante el campo se quedaba en el default del modelo
    # ('WOMPI') para una solicitud que jamas se cobro (bug real, hallado en
    # smoke test 2026-07-22: el Order resultante quedaba marcado
    # payment_method='WOMPI' pese a no haber pasarela involucrada).
    PAYMENT_COMODATO = 'COMODATO'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_WOMPI, 'Wompi'),
        (PAYMENT_NEQUI, 'Nequi'),
        (PAYMENT_COD,   'Contra entrega'),
        (PAYMENT_COMODATO, 'Comodato (sin costo)'),
    ]

    # Paso 8 -- metodo de pago y rastro de la pasarela
    # -> RentalRequestPaymentInfo ('payment_info'), migracion 0036.

    # Conflicto de disponibilidad al confirmar pago o aprobar COD
    refund_required = models.BooleanField(default=False, db_index=True)
    admin_notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'solicitud de alquiler'
        verbose_name_plural = 'solicitudes de alquiler'
        ordering = ['-created_at']

    def __str__(self):
        return f"Renta {self.uuid} - {self.equipment_variant.equipment.name}"

    # -----------------------------------------------------------------------
    # Delegacion hacia los sub-modelos (auditoria DB-H1, migracion 0036)
    #
    # Los 35 campos de abajo ya no son columnas de esta tabla, pero siguen
    # siendo atributos normales de Python: se leen y se escriben igual que
    # antes (request.grand_total, request.contact_email = x, ...) y tambien
    # se aceptan como kwargs de RentalRequest(...) / .objects.create(...).
    #
    # LIMITE IMPORTANTE: una property NO es un campo. No sirven en filter(),
    # exclude(), order_by(), values(), annotate(), only(), filterset_fields ni
    # en save(update_fields=[...]) directo. Para el ORM hay que usar la
    # relacion: costs_info__grand_total, payment_info__payment_method, etc.
    # (save(update_fields=[...]) si esta cubierto: el override de save() de
    # abajo filtra los nombres movidos, porque el setter ya los persistio.)
    # -----------------------------------------------------------------------

    LOCATION_FIELD_NAMES = (
        'location_address', 'location_city', 'location_department',
        'location_coordinates', 'project_type', 'access_conditions',
        'location_notes',
    )
    CONTACT_FIELD_NAMES = (
        'contact_full_name', 'contact_doc_type', 'contact_doc_number',
        'contact_email', 'contact_phone', 'contact_company',
        'contact_position',
    )
    COSTS_FIELD_NAMES = (
        'delivery_cost', 'pickup_cost', 'distance_km', 'installation_cost',
        'calibration_cost', 'training_cost', 'startup_cost',
        'total_rental_days', 'base_cost', 'price_per_day_snapshot',
        'price_per_hour_snapshot', 'labor_total', 'transport_total',
        'setup_total', 'tax_amount', 'grand_total',
    )
    PAYMENT_FIELD_NAMES = (
        'payment_method', 'wompi_reference', 'wompi_transaction_id',
        'payment_status', 'paid_at',
    )

    SUBMODEL_RELATIONS = (
        ('location_info', LOCATION_FIELD_NAMES),
        ('contact_info', CONTACT_FIELD_NAMES),
        ('costs_info', COSTS_FIELD_NAMES),
        ('payment_info', PAYMENT_FIELD_NAMES),
    )

    MOVED_FIELD_NAMES = frozenset(
        LOCATION_FIELD_NAMES + CONTACT_FIELD_NAMES
        + COSTS_FIELD_NAMES + PAYMENT_FIELD_NAMES
    )

    def __init__(self, *args, **kwargs):
        """
        Saca de kwargs los campos que ahora viven en los sub-modelos antes de
        llamar a Model.__init__, que reventaria con TypeError por kwarg
        desconocido. Quedan guardados y se materializan en el primer save().
        """
        pending = {}
        for name in RentalRequest.MOVED_FIELD_NAMES:
            if name in kwargs:
                pending[name] = kwargs.pop(name)
        self._pending_submodel_values = pending
        super().__init__(*args, **kwargs)

    @staticmethod
    def _submodel_class(related_name):
        if related_name == 'location_info':
            return RentalRequestLocation
        if related_name == 'contact_info':
            return RentalRequestContact
        if related_name == 'costs_info':
            return RentalRequestCosts
        if related_name == 'payment_info':
            return RentalRequestPaymentInfo
        raise ValueError(f"Relacion de sub-modelo desconocida: {related_name}")

    def _submodel_instance(self, related_name):
        """Devuelve la fila hija o None si la solicitud aun no se ha guardado."""
        if self.pk is None:
            return None
        try:
            return getattr(self, related_name)
        except ObjectDoesNotExist:
            return None

    def _submodel_get(self, related_name, field_name, default=None):
        related = self._submodel_instance(related_name)
        if related is not None:
            return getattr(related, field_name)
        # Todavia sin guardar (o fila hija ausente): responde con lo que se
        # paso al constructor, si es que se paso algo.
        pending = getattr(self, '_pending_submodel_values', None) or {}
        if field_name in pending:
            return pending[field_name]
        return default

    def _submodel_set(self, related_name, field_name, value):
        related = self._submodel_instance(related_name)
        if related is None:
            if self.pk is None:
                # Sin PK no se puede crear la fila hija todavia: queda
                # pendiente para el primer save().
                if getattr(self, '_pending_submodel_values', None) is None:
                    self._pending_submodel_values = {}
                self._pending_submodel_values[field_name] = value
                return
            # Defensivo: la solicitud existe pero le falta la fila hija
            # (fila legacy, o borrado manual). Se crea al vuelo.
            self._submodel_class(related_name).objects.create(
                rental_request=self, **{field_name: value}
            )
            return
        setattr(related, field_name, value)
        related.save(update_fields=[field_name, 'updated_at'])

    def _materialize_submodels(self):
        """Crea las cuatro filas hijas tras el INSERT de la solicitud."""
        pending = getattr(self, '_pending_submodel_values', None) or {}
        for related_name, field_names in RentalRequest.SUBMODEL_RELATIONS:
            if self._submodel_instance(related_name) is not None:
                continue
            values = {
                name: pending[name] for name in field_names if name in pending
            }
            self._submodel_class(related_name).objects.create(
                rental_request=self, **values
            )
        self._pending_submodel_values = {}

    def save(self, *args, **kwargs):
        """
        Dos responsabilidades extra sobre el save() normal:

        1. update_fields: los nombres movidos ya no son campos de esta tabla,
           asi que Django lanzaria ValueError. Se filtran -- el valor ya quedo
           persistido por el setter correspondiente en el momento de la
           asignacion, asi que no se pierde nada.
        2. Primer INSERT: despues de que la solicitud tiene PK, se crean las
           cuatro filas hijas con lo que se haya pasado al constructor.
        """
        is_new = self.pk is None

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = list(update_fields)
            remaining = [
                name for name in update_fields
                if name not in RentalRequest.MOVED_FIELD_NAMES
            ]
            if len(remaining) != len(update_fields):
                # update_fields vacio hace que Django no guarde nada; se deja
                # updated_at para conservar el efecto de "esto se toco".
                kwargs['update_fields'] = remaining or ['updated_at']

        super().save(*args, **kwargs)

        if is_new:
            self._materialize_submodels()

    # -- Metodos get_FOO_display() que Django generaba por los campos con
    # -- choices y que desaparecieron junto con las columnas.

    def get_contact_doc_type_display(self):
        related = self._submodel_instance('contact_info')
        if related is None:
            return ''
        return related.get_contact_doc_type_display()

    def get_payment_method_display(self):
        related = self._submodel_instance('payment_info')
        if related is None:
            return ''
        return related.get_payment_method_display()

    # -- Paso 2: lugar de operacion (RentalRequestLocation) ------------------

    @property
    def location_address(self):
        return self._submodel_get('location_info', 'location_address', '')

    @location_address.setter
    def location_address(self, value):
        self._submodel_set('location_info', 'location_address', value)

    @property
    def location_city(self):
        return self._submodel_get('location_info', 'location_city', '')

    @location_city.setter
    def location_city(self, value):
        self._submodel_set('location_info', 'location_city', value)

    @property
    def location_department(self):
        return self._submodel_get('location_info', 'location_department', '')

    @location_department.setter
    def location_department(self, value):
        self._submodel_set('location_info', 'location_department', value)

    @property
    def location_coordinates(self):
        return self._submodel_get('location_info', 'location_coordinates', '')

    @location_coordinates.setter
    def location_coordinates(self, value):
        self._submodel_set('location_info', 'location_coordinates', value)

    @property
    def project_type(self):
        return self._submodel_get('location_info', 'project_type', '')

    @project_type.setter
    def project_type(self, value):
        self._submodel_set('location_info', 'project_type', value)

    @property
    def access_conditions(self):
        return self._submodel_get('location_info', 'access_conditions', '')

    @access_conditions.setter
    def access_conditions(self, value):
        self._submodel_set('location_info', 'access_conditions', value)

    @property
    def location_notes(self):
        return self._submodel_get('location_info', 'location_notes', '')

    @location_notes.setter
    def location_notes(self, value):
        self._submodel_set('location_info', 'location_notes', value)

    # -- Paso 3: responsable (RentalRequestContact) --------------------------

    @property
    def contact_full_name(self):
        return self._submodel_get('contact_info', 'contact_full_name', '')

    @contact_full_name.setter
    def contact_full_name(self, value):
        self._submodel_set('contact_info', 'contact_full_name', value)

    @property
    def contact_doc_type(self):
        return self._submodel_get('contact_info', 'contact_doc_type', RentalRequest.DOC_CC)

    @contact_doc_type.setter
    def contact_doc_type(self, value):
        self._submodel_set('contact_info', 'contact_doc_type', value)

    @property
    def contact_doc_number(self):
        return self._submodel_get('contact_info', 'contact_doc_number', '')

    @contact_doc_number.setter
    def contact_doc_number(self, value):
        self._submodel_set('contact_info', 'contact_doc_number', value)

    @property
    def contact_email(self):
        return self._submodel_get('contact_info', 'contact_email', '')

    @contact_email.setter
    def contact_email(self, value):
        self._submodel_set('contact_info', 'contact_email', value)

    @property
    def contact_phone(self):
        return self._submodel_get('contact_info', 'contact_phone', '')

    @contact_phone.setter
    def contact_phone(self, value):
        self._submodel_set('contact_info', 'contact_phone', value)

    @property
    def contact_company(self):
        return self._submodel_get('contact_info', 'contact_company', '')

    @contact_company.setter
    def contact_company(self, value):
        self._submodel_set('contact_info', 'contact_company', value)

    @property
    def contact_position(self):
        return self._submodel_get('contact_info', 'contact_position', '')

    @contact_position.setter
    def contact_position(self, value):
        self._submodel_set('contact_info', 'contact_position', value)

    # -- Paso 6 + totales (RentalRequestCosts) -------------------------------

    @property
    def delivery_cost(self):
        return self._submodel_get('costs_info', 'delivery_cost', Decimal('0'))

    @delivery_cost.setter
    def delivery_cost(self, value):
        self._submodel_set('costs_info', 'delivery_cost', value)

    @property
    def pickup_cost(self):
        return self._submodel_get('costs_info', 'pickup_cost', Decimal('0'))

    @pickup_cost.setter
    def pickup_cost(self, value):
        self._submodel_set('costs_info', 'pickup_cost', value)

    @property
    def distance_km(self):
        return self._submodel_get('costs_info', 'distance_km', None)

    @distance_km.setter
    def distance_km(self, value):
        self._submodel_set('costs_info', 'distance_km', value)

    @property
    def installation_cost(self):
        return self._submodel_get('costs_info', 'installation_cost', Decimal('0'))

    @installation_cost.setter
    def installation_cost(self, value):
        self._submodel_set('costs_info', 'installation_cost', value)

    @property
    def calibration_cost(self):
        return self._submodel_get('costs_info', 'calibration_cost', Decimal('0'))

    @calibration_cost.setter
    def calibration_cost(self, value):
        self._submodel_set('costs_info', 'calibration_cost', value)

    @property
    def training_cost(self):
        return self._submodel_get('costs_info', 'training_cost', Decimal('0'))

    @training_cost.setter
    def training_cost(self, value):
        self._submodel_set('costs_info', 'training_cost', value)

    @property
    def startup_cost(self):
        return self._submodel_get('costs_info', 'startup_cost', Decimal('0'))

    @startup_cost.setter
    def startup_cost(self, value):
        self._submodel_set('costs_info', 'startup_cost', value)

    @property
    def total_rental_days(self):
        return self._submodel_get('costs_info', 'total_rental_days', None)

    @total_rental_days.setter
    def total_rental_days(self, value):
        self._submodel_set('costs_info', 'total_rental_days', value)

    @property
    def base_cost(self):
        return self._submodel_get('costs_info', 'base_cost', None)

    @base_cost.setter
    def base_cost(self, value):
        self._submodel_set('costs_info', 'base_cost', value)

    @property
    def price_per_day_snapshot(self):
        return self._submodel_get('costs_info', 'price_per_day_snapshot', None)

    @price_per_day_snapshot.setter
    def price_per_day_snapshot(self, value):
        self._submodel_set('costs_info', 'price_per_day_snapshot', value)

    @property
    def price_per_hour_snapshot(self):
        return self._submodel_get('costs_info', 'price_per_hour_snapshot', None)

    @price_per_hour_snapshot.setter
    def price_per_hour_snapshot(self, value):
        self._submodel_set('costs_info', 'price_per_hour_snapshot', value)

    @property
    def labor_total(self):
        return self._submodel_get('costs_info', 'labor_total', Decimal('0'))

    @labor_total.setter
    def labor_total(self, value):
        self._submodel_set('costs_info', 'labor_total', value)

    @property
    def transport_total(self):
        return self._submodel_get('costs_info', 'transport_total', Decimal('0'))

    @transport_total.setter
    def transport_total(self, value):
        self._submodel_set('costs_info', 'transport_total', value)

    @property
    def setup_total(self):
        return self._submodel_get('costs_info', 'setup_total', Decimal('0'))

    @setup_total.setter
    def setup_total(self, value):
        self._submodel_set('costs_info', 'setup_total', value)

    @property
    def tax_amount(self):
        return self._submodel_get('costs_info', 'tax_amount', Decimal('0'))

    @tax_amount.setter
    def tax_amount(self, value):
        self._submodel_set('costs_info', 'tax_amount', value)

    @property
    def grand_total(self):
        return self._submodel_get('costs_info', 'grand_total', None)

    @grand_total.setter
    def grand_total(self, value):
        self._submodel_set('costs_info', 'grand_total', value)

    # -- Paso 8: pago (RentalRequestPaymentInfo) -----------------------------

    @property
    def payment_method(self):
        return self._submodel_get('payment_info', 'payment_method', RentalRequest.PAYMENT_WOMPI)

    @payment_method.setter
    def payment_method(self, value):
        self._submodel_set('payment_info', 'payment_method', value)

    @property
    def wompi_reference(self):
        return self._submodel_get('payment_info', 'wompi_reference', '')

    @wompi_reference.setter
    def wompi_reference(self, value):
        self._submodel_set('payment_info', 'wompi_reference', value)

    @property
    def wompi_transaction_id(self):
        return self._submodel_get('payment_info', 'wompi_transaction_id', '')

    @wompi_transaction_id.setter
    def wompi_transaction_id(self, value):
        self._submodel_set('payment_info', 'wompi_transaction_id', value)

    @property
    def payment_status(self):
        return self._submodel_get('payment_info', 'payment_status', '')

    @payment_status.setter
    def payment_status(self, value):
        self._submodel_set('payment_info', 'payment_status', value)

    @property
    def paid_at(self):
        return self._submodel_get('payment_info', 'paid_at', None)

    @paid_at.setter
    def paid_at(self, value):
        self._submodel_set('payment_info', 'paid_at', value)


# ---------------------------------------------------------------------------
# Sub-modelos de RentalRequest (hallazgo de auditoria DB-H1, 2026-07-27)
#
# RentalRequest habia crecido a ~50 columnas mezclando identidad/ciclo de vida
# con cuatro bloques de datos que en realidad son pasos del wizard. Cada bloque
# se movio a un OneToOneField propio. RentalRequest conserva su API de atributos
# en Python al 100% via @property/.setter (ver bloque "Delegacion" mas abajo),
# asi que serializers, selectors, commands y payloads del frontend siguen
# leyendo/escribiendo request.location_address, request.grand_total, etc.
#
# Regla: NO consultar estos campos por ORM sobre RentalRequest directamente
# (las properties no son campos, no funcionan en filter()/order_by()/values()).
# Para eso usar el lookup por relacion: location_info__location_city,
# contact_info__contact_doc_number, costs_info__grand_total,
# payment_info__payment_method.
# ---------------------------------------------------------------------------

class RentalRequestLocation(SintelBaseModel):
    """Paso 2 del wizard -- Lugar de operacion."""

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='location_info',
    )
    location_address = models.CharField(max_length=500, blank=True, default='')
    location_city = models.CharField(max_length=100, blank=True, default='')
    location_department = models.CharField(max_length=100, blank=True, default='')
    location_coordinates = models.CharField(max_length=100, blank=True, default='')
    project_type = models.CharField(max_length=255, blank=True, default='')
    access_conditions = models.TextField(blank=True, default='')
    location_notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'lugar de operacion de solicitud'
        verbose_name_plural = 'lugares de operacion de solicitudes'

    def __str__(self):
        return f"Lugar de {self.rental_request_id}: {self.location_city}"

class RentalRequestContact(SintelBaseModel):
    """Paso 3 del wizard -- Responsable de la operacion."""

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='contact_info',
    )
    contact_full_name = models.CharField(max_length=255, blank=True, default='')
    contact_doc_type = models.CharField(
        max_length=10, choices=RentalRequest.DOC_TYPE_CHOICES,
        default=RentalRequest.DOC_CC,
    )
    contact_doc_number = models.CharField(max_length=50, blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=30, blank=True, default='')
    contact_company = models.CharField(max_length=255, blank=True, default='')
    contact_position = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'responsable de solicitud'
        verbose_name_plural = 'responsables de solicitudes'

    def __str__(self):
        return f"Responsable de {self.rental_request_id}: {self.contact_full_name}"

class RentalRequestCosts(SintelBaseModel):
    """Paso 6 del wizard (transporte y puesta en marcha) + totales calculados."""

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='costs_info',
    )
    # Paso 6 -- Transporte y puesta en marcha
    delivery_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pickup_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    installation_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calibration_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    training_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    startup_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Totales calculados al confirmar
    total_rental_days = models.PositiveIntegerField(null=True, blank=True)
    base_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # R-07 (auditoria enterprise): snapshot inmutable del precio unitario del
    # EquipmentVariant vigente al momento de la reserva -- antes solo se
    # guardaban los totales derivados (base_cost/grand_total), no la tarifa
    # unitaria en si. Si el admin cambia rental_price_per_day/hour despues,
    # el historico de "cuanto costaba en ese momento" quedaba sin proteger,
    # a diferencia del mismo patron ya usado en Quotes/Orders/technical_services.
    # Nullable: filas ya existentes quedan None (no hay forma de reconstruir
    # el precio historico retroactivamente), solo las nuevas lo llenan.
    price_per_day_snapshot = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Snapshot de EquipmentVariant.rental_price_per_day al crear la solicitud.',
    )
    price_per_hour_snapshot = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Snapshot de EquipmentVariant.rental_price_per_hour al crear la solicitud.',
    )
    labor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transport_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    setup_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = 'costos de solicitud'
        verbose_name_plural = 'costos de solicitudes'

    def __str__(self):
        return f"Costos de {self.rental_request_id}: {self.grand_total}"

class RentalRequestPaymentInfo(SintelBaseModel):
    """
    Paso 8 del wizard -- metodo de pago y rastro de la pasarela.

    Se llama PaymentInfo y no Payment a proposito: la app `payment` tiene su
    propio modelo Payment/Transaction, y este solo guarda el eco de la pasarela
    dentro de la solicitud de alquiler.
    """

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='payment_info',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=RentalRequest.PAYMENT_METHOD_CHOICES,
        default=RentalRequest.PAYMENT_WOMPI,
    )
    wompi_reference = models.CharField(max_length=255, blank=True, default='')
    wompi_transaction_id = models.CharField(max_length=255, blank=True, default='')
    payment_status = models.CharField(max_length=50, blank=True, default='', db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'pago de solicitud'
        verbose_name_plural = 'pagos de solicitudes'

    def __str__(self):
        return f"Pago de {self.rental_request_id}: {self.payment_method}"

class RentalProjectAttachment(SintelBaseModel):
    """Fotografía o documento de reconocimiento aportado por el cliente."""
    rental_request = models.ForeignKey(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='project_attachments',
    )
    file = models.FileField(upload_to='renting/project_attachments/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True, default='')
    content_type = models.CharField(max_length=100, blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rental_project_attachments',
    )

    class Meta:
        ordering = ['created_at']

