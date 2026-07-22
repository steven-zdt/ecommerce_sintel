from django.db import models
from django.conf import settings
from ecommerce.base_models import SintelBaseModel


class UserProfile(SintelBaseModel):
    TECHNICIAN = 'TECHNICIAN'
    PROFESSIONAL = 'PROFESSIONAL'
    SPECIALIST = 'SPECIALIST'
    CUSTOMER = 'CUSTOMER'
    TRANSPORTER = 'TRANSPORTER'
    CONTRACTOR = 'CONTRACTOR'
    ACCOUNTANT = 'ACCOUNTANT'

    USER_TYPE_CHOICES = [
        (TECHNICIAN, 'Tecnico'),
        (PROFESSIONAL, 'Profesional'),
        (SPECIALIST, 'Especialista'),
        (CUSTOMER, 'Comprador'),
        (TRANSPORTER, 'Transportista'),
        (CONTRACTOR, 'Contratista'),
        (ACCOUNTANT, 'Contador'),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ('CC', 'Cedula de Ciudadania'),
        ('CE', 'Cedula de Extranjeria'),
        ('NIT', 'Numero de Identificacion Tributaria'),
        ('PP', 'Pasaporte'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('COP', 'COP'),
        ('MXN', 'MXN'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    first_name = models.CharField(max_length=50, blank=True, default='')
    last_name = models.CharField(max_length=50, blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPE_CHOICES, blank=True, null=True)
    document = models.CharField(max_length=30, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/pictures/', blank=True, null=True)
    company = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)

    # Advanced professional fields
    user_type = models.CharField(
        max_length=20, choices=USER_TYPE_CHOICES, default=TECHNICIAN, db_index=True
    )
    birth_date = models.DateField(blank=True, null=True)
    contractor_type = models.CharField(max_length=50, blank=True, default='')
    bio = models.TextField(blank=True, default='')

    # Financial fields
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    daily_rate = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    project_rate = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='USD')

    @property
    def average_rating(self):
        # Filtra en Python sobre .all() para reusar el cache de prefetch_related cuando el
        # selector que arma la lista ya trajo 'contractor_reviews' -- un .filter() explicito
        # aqui dispararia una consulta nueva por perfil listado.
        reviews = [r for r in self.contractor_reviews.all() if not r.is_deleted]
        if not reviews:
            return 0.0
        total_sum = sum(
            r.quality_rating + r.punctuality_rating + r.professionalism_rating +
            r.communication_rating + r.compliance_rating
            for r in reviews
        )
        return round(total_sum / (len(reviews) * 5), 2)

    @property
    def total_reviews(self):
        return len([r for r in self.contractor_reviews.all() if not r.is_deleted])

    @property
    def total_services_completed(self):
        # ContractorAdminSelector.list_all_for_admin() anota este mismo nombre via
        # .annotate(total_services_completed=Count(...)) para evitar un COUNT() por
        # perfil listado (N+1); el setter de abajo permite que Django escriba ese
        # valor anotado sin chocar con el property. Si no viene anotado (por ejemplo
        # desde ContractorSearchSelector/ContractorRecommendationSelector), se calcula
        # bajo demanda como antes.
        if '_total_services_completed' in self.__dict__:
            return self.__dict__['_total_services_completed']
        from orders.models import Order
        return self.user.assigned_services.filter(order__status=Order.STATUS_COMPLETED).count()

    @total_services_completed.setter
    def total_services_completed(self, value):
        self.__dict__['_total_services_completed'] = value

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.user.email

    def __str__(self):
        return f"Perfil de {self.user.email}"

    class Meta:
        verbose_name = 'perfil de usuario'
        verbose_name_plural = 'perfiles de usuario'
        constraints = [
            models.UniqueConstraint(
                fields=['document_type', 'document'],
                # document es CharField(blank=True, null=True): perfiles sin documento
                # (la mayoria via register_user, que nunca lo setea) quedan con '' (no
                # NULL) por el default de CharField -- excluir tambien '' o la
                # constraint chocaria contra cualquier segundo usuario sin documento.
                condition=models.Q(document__isnull=False) & ~models.Q(document=''),
                name='userprofile_document_unique',
            ),
        ]


class TechnicianProfile(SintelBaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='technician_profile',
    )
    # related_name 'technicians' reservado — se asigna tras eliminar users.TechnicianProfile
    specialties = models.ManyToManyField(
        'technical_services.ServiceCategory',
        related_name='technician_profiles',
        blank=True,
    )
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Tecnico {self.user.email}"

    class Meta:
        verbose_name = 'perfil de tecnico'
        verbose_name_plural = 'perfiles de tecnicos'


class ContractorSpecialty(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='contractor_specialties',
    )
    category = models.ForeignKey(
        'technical_services.ServiceCategory',
        on_delete=models.CASCADE,
        related_name='contractor_specialties',
    )

    class Meta:
        unique_together = ('user_profile', 'category')
        verbose_name = 'especialidad de contratista'
        verbose_name_plural = 'especialidades de contratista'

    def __str__(self):
        return f"{self.user_profile.user.email} - {self.category.name}"


class ContractorSkill(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='contractor_skills',
    )
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        unique_together = ('user_profile', 'name')
        verbose_name = 'habilidad de contratista'
        verbose_name_plural = 'habilidades de contratista'

    def __str__(self):
        return f"{self.name} ({self.level})"


class AcademicTraining(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='academic_trainings',
    )
    institution = models.CharField(max_length=150)
    degree = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150, blank=True, default='')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'educacion academica'
        verbose_name_plural = 'educaciones academicas'

    def __str__(self):
        return f"{self.degree} en {self.institution}"


class ProfessionalCourse(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='professional_courses',
    )
    title = models.CharField(max_length=150)
    institution = models.CharField(max_length=150)
    completion_date = models.DateField()
    hours = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        verbose_name = 'curso profesional'
        verbose_name_plural = 'cursos profesionales'

    def __str__(self):
        return f"{self.title} - {self.institution}"


class ProfessionalCertification(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='professional_certifications',
    )
    name = models.CharField(max_length=150)
    issuing_organization = models.CharField(max_length=150)
    issue_date = models.DateField()
    expiration_date = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=100, blank=True, default='')
    credential_url = models.URLField(blank=True, default='')
    document = models.FileField(upload_to='contractors/certifications/', blank=True, null=True)

    class Meta:
        verbose_name = 'certificacion profesional'
        verbose_name_plural = 'certificaciones profesionales'

    def __str__(self):
        return f"{self.name} - {self.issuing_organization}"


class ProfessionalExperience(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='professional_experiences',
    )
    company = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'experiencia profesional'
        verbose_name_plural = 'experiencias profesionales'

    def __str__(self):
        return f"{self.position} en {self.company}"


class SuccessCase(SintelBaseModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='success_cases',
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    completion_date = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = 'caso de exito'
        verbose_name_plural = 'casos de exito'

    def __str__(self):
        return self.title


class SuccessCaseImage(SintelBaseModel):
    success_case = models.ForeignKey(
        SuccessCase,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='contractors/success_cases/')
    is_before = models.BooleanField(default=False)
    is_after = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'imagen de caso de exito'
        verbose_name_plural = 'imagenes de casos de exito'

    def __str__(self):
        return f"Imagen de {self.success_case.title}"


class ContractorReview(SintelBaseModel):
    contractor = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='contractor_reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_reviews',
    )
    comment = models.TextField(blank=True, default='')

    # 5 rating factors
    quality_rating = models.PositiveSmallIntegerField(default=5)
    punctuality_rating = models.PositiveSmallIntegerField(default=5)
    professionalism_rating = models.PositiveSmallIntegerField(default=5)
    communication_rating = models.PositiveSmallIntegerField(default=5)
    compliance_rating = models.PositiveSmallIntegerField(default=5)

    class Meta:
        verbose_name = 'reseña de contratista'
        verbose_name_plural = 'reseñas de contratista'
        unique_together = ('contractor', 'reviewer')

    def __str__(self):
        return f"Reseña de {self.reviewer.email} para {self.contractor.user.email}"


class ProfessionalAvailability(SintelBaseModel):
    """
    Representa un bloque de tiempo de disponibilidad de un profesional.
    Los bloqueos temporales (PENDING_RESERVATION) expiran en 15 min vía Celery.
    """
    AVAILABLE           = 'AVAILABLE'
    PENDING_RESERVATION = 'PENDING_RESERVATION'
    BOOKED              = 'BOOKED'
    BLOCKED             = 'BLOCKED'
    VACATION            = 'VACATION'
    SICK_LEAVE          = 'SICK_LEAVE'

    STATUS_CHOICES = [
        (AVAILABLE,           'Disponible'),
        (PENDING_RESERVATION, 'Reserva temporal (15 min)'),
        (BOOKED,              'Reservado'),
        (BLOCKED,             'Bloqueado'),
        (VACATION,            'Vacaciones'),
        (SICK_LEAVE,          'Incapacidad'),
    ]

    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='availabilities',
    )
    date       = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time   = models.TimeField()
    status     = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=AVAILABLE,
        db_index=True,
    )
    # Quién realizó la reserva temporal / definitiva
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='slot_bookings',
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name        = 'disponibilidad profesional'
        verbose_name_plural = 'disponibilidades profesionales'
        unique_together     = ('user_profile', 'date', 'start_time')
        ordering            = ['date', 'start_time']

    def __str__(self):
        return (
            f"{self.user_profile} | {self.date} "
            f"{self.start_time:%H:%M}-{self.end_time:%H:%M} [{self.status}]"
        )


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=UserProfile)
def create_technician_profile(sender, instance, created, **kwargs):
    # TechnicianProfile (disponibilidad + especialidades por categoria) es el perfil asignable
    # que usa TechnicianSelector/ServiceAssignmentCommands -- se generaliza a los 4 tipos
    # service-provider (no solo TECHNICIAN) para que Profesionales/Especialistas/Contratistas
    # tambien puedan ser asignados por categoria/disponibilidad. Import diferido para evitar
    # el ciclo profile_registry -> accounts.models.
    from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
    if instance.user_type in SERVICE_PROVIDER_TYPES:
        TechnicianProfile.objects.get_or_create(user=instance.user)
