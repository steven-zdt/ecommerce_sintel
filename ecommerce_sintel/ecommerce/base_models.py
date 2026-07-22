import uuid
from django.db import models

class SintelBaseModel(models.Model):
    """
    Modelo base abstracto que inyecta UUID, timestamps de auditoria y soft-delete.
    Usado por todos los modelos de negocio.
    """
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True
