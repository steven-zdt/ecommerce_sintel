"""
customer_memory/models.py

Mision RAG-POST2 (FASE 9, 2026-09-16). Memoria semantica del cliente --
separada explicitamente de `ai_knowledge` (conocimiento documental publico,
igual para todos) y de `Session.state` de ADK (estado efimero de UNA
conversacion, ver ai_engine_adk/sintel_root_workflow.py FASE 7). Ver
AUDITORIA/RAG_POST2_MEMORY_DEFINITION.md (FASE 8) para la clasificacion
completa que motiva este modelo.

Misma separacion de responsabilidades que ai_knowledge/models.py:
  AI ENGINE ADK = nunca importa este modelo ni Postgres directo, lee/escribe
                  solo via HTTP interno (api/views.py de esta app).
  CUSTOMER MEMORY (esta app) = almacenamiento + gobernanza de la memoria.
"""
from django.conf import settings
from django.db import models

from ecommerce.base_models import SintelBaseModel


class CustomerMemoryRecord(SintelBaseModel):
    """Un hecho/preferencia individual, corto, no sensible, extraido de una
    conversacion real -- NUNCA texto libre sin categoria (whitelist cerrada,
    ver AUDITORIA/RAG_POST2_MEMORY_DEFINITION.md). `is_active` (distinto de
    `is_deleted` heredado) es el toggle real de "revisable" -- un admin
    puede desactivar un recuerdo incorrecto sin borrarlo (auditable)."""

    CATEGORY_CONTACT_PREFERENCE = 'contact_preference'
    CATEGORY_PRODUCT_INTEREST = 'product_interest'
    CATEGORY_COMMUNICATION_STYLE = 'communication_style'
    CATEGORY_GENERAL_PREFERENCE = 'general_preference'
    CATEGORY_CHOICES = [
        (CATEGORY_CONTACT_PREFERENCE, 'Preferencia de contacto'),
        (CATEGORY_PRODUCT_INTEREST, 'Interes de producto/servicio'),
        (CATEGORY_COMMUNICATION_STYLE, 'Estilo de comunicacion'),
        (CATEGORY_GENERAL_PREFERENCE, 'Preferencia general'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memory_records',
    )
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    # Corto a proposito -- un hecho, no un resumen de conversacion. El limite
    # tambien es una barrera contra que el extractor (FASE 10) intente
    # guardar un bloque de texto grande en vez de un hecho puntual.
    content = models.CharField(max_length=280)
    source_conversation_id = models.CharField(max_length=128, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'is_active', 'is_deleted', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_id}:{self.category}:{self.content[:40]}"
