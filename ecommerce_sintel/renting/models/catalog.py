# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.db import models
from ecommerce.base_models import SintelBaseModel

from .equipment import Equipment

class RentalIncludedItem(SintelBaseModel):
    """Que incluye el alquiler -- fila administrable (reemplaza el TextField libre)."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='included_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item incluido en el alquiler'
        verbose_name_plural = 'items incluidos en el alquiler'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} incluye: {self.title}"

class RentalExcludedItem(SintelBaseModel):
    """Que NO incluye el alquiler -- fila administrable."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='excluded_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item no incluido en el alquiler'
        verbose_name_plural = 'items no incluidos en el alquiler'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} no incluye: {self.title}"

class RentalFeature(SintelBaseModel):
    """Caracteristica destacada del equipo (titulo + valor), ej. 'Potencia: 20T'."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='features')
    title = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'caracteristica de equipo'
        verbose_name_plural = 'caracteristicas de equipo'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- {self.title}: {self.value}"

class RentalSpecificationGroup(SintelBaseModel):
    """Agrupador de especificaciones tecnicas (ej. 'Motor', 'Dimensiones')."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='specification_groups')
    name = models.CharField(max_length=150)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'grupo de especificaciones'
        verbose_name_plural = 'grupos de especificaciones'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- grupo {self.name}"

class RentalSpecification(SintelBaseModel):
    """
    Fila de ficha tecnica. equipment se mantiene denormalizado ademas de group
    (tal como lo pide el modelo) para poder listar/optimizar todas las specs de
    un equipo sin pasar por el join de group -- igual que el patron ya usado
    en RentalSpecificationGroup.equipment.
    """
    group = models.ForeignKey(RentalSpecificationGroup, on_delete=models.CASCADE, related_name='specifications')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=150)
    value = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'especificacion tecnica'
        verbose_name_plural = 'especificaciones tecnicas'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- {self.name}: {self.value}"

class RentalRequirement(SintelBaseModel):
    """Requisito para poder rentar el equipo (ej. acceso vehicular, punto electrico)."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='requirements')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'requisito de alquiler'
        verbose_name_plural = 'requisitos de alquiler'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- requiere: {self.title}"

class RentalServiceIncluded(SintelBaseModel):
    """Servicio que ya viene incluido en el precio del alquiler (ej. entrega basica)."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='services_included')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'servicio incluido'
        verbose_name_plural = 'servicios incluidos'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- servicio incluido: {self.title}"

class RentalOptionalService(SintelBaseModel):
    """
    Servicio adicional que el cliente puede contratar por un costo extra
    (catalogo informativo del producto -- distinto de RentalLabor, que es
    mano de obra generica reutilizable entre equipos).
    """
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='optional_services')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'servicio opcional'
        verbose_name_plural = 'servicios opcionales'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- servicio opcional: {self.title}"

class RentalFAQ(SintelBaseModel):
    """Pregunta frecuente del equipo, mostrada en el detalle publico."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- FAQ: {self.question[:50]}"

class RentalVideo(SintelBaseModel):
    """
    Video del equipo. source_type distingue el origen porque cada uno se
    resuelve distinto en el frontend: YOUTUBE/VIMEO usan video_url (embed),
    MP4 usa video_file (subido, servido directo).
    """
    SOURCE_YOUTUBE = 'YOUTUBE'
    SOURCE_VIMEO = 'VIMEO'
    SOURCE_MP4 = 'MP4'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_YOUTUBE, 'YouTube'),
        (SOURCE_VIMEO, 'Vimeo'),
        (SOURCE_MP4, 'Archivo MP4'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255, blank=True, default='')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default=SOURCE_YOUTUBE)
    video_url = models.URLField(blank=True, default='')
    video_file = models.FileField(upload_to='renting/videos/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='renting/videos/thumbs/', blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'video de equipo'
        verbose_name_plural = 'videos de equipo'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- video: {self.title or self.source_type}"

class RentalDocument(SintelBaseModel):
    """
    Documento descargable del equipo: manual, ficha tecnica, guia, certificado,
    plano, catalogo, firmware o driver. is_public controla visibilidad en el
    detalle del cliente (documentos internos pueden quedar is_public=False).
    """
    TYPE_MANUAL = 'MANUAL'
    TYPE_FICHA_TECNICA = 'FICHA_TECNICA'
    TYPE_GUIA = 'GUIA'
    TYPE_CERTIFICADO = 'CERTIFICADO'
    TYPE_PLANO = 'PLANO'
    TYPE_CATALOGO = 'CATALOGO'
    TYPE_FIRMWARE = 'FIRMWARE'
    TYPE_DRIVER = 'DRIVER'
    TYPE_OTRO = 'OTRO'
    DOCUMENT_TYPE_CHOICES = [
        (TYPE_MANUAL, 'Manual'),
        (TYPE_FICHA_TECNICA, 'Ficha tecnica'),
        (TYPE_GUIA, 'Guia'),
        (TYPE_CERTIFICADO, 'Certificado'),
        (TYPE_PLANO, 'Plano'),
        (TYPE_CATALOGO, 'Catalogo'),
        (TYPE_FIRMWARE, 'Firmware'),
        (TYPE_DRIVER, 'Driver'),
        (TYPE_OTRO, 'Otro'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default=TYPE_OTRO, db_index=True)
    version = models.CharField(max_length=50, blank=True, default='')
    language = models.CharField(max_length=10, blank=True, default='es')
    file = models.FileField(upload_to='renting/documents/')
    cover_image = models.ImageField(upload_to='renting/documents/covers/', blank=True, null=True)
    downloads = models.PositiveIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'documento de equipo'
        verbose_name_plural = 'documentos de equipo'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- {self.get_document_type_display()}: {self.title}"

