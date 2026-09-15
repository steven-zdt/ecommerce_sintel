"""
whatsapp/domain/customer_resolver.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 13
(2026-09-16). La identidad del cliente se resuelve en la capa de negocio
-- identica para CUALQUIER adapter (REST hoy, QR el dia que exista). Un
adapter nunca decide quien es el usuario SINTEL, solo entrega un telefono
normalizado.

Misma logica real que ya vivia inline en
notifications/tasks.py::process_whatsapp_inbound_task -- extraida tal
cual, no reinventada (ultimos 10 digitos contra UserProfile.phone_number).
"""
from accounts.models import UserProfile


class WhatsAppCustomerResolver:
    @staticmethod
    def resolve_user(sender_phone: str):
        """Devuelve el User real de SINTEL asociado a este telefono, o
        None si no hay match (mismo criterio real de siempre: no se
        responde a numeros desconocidos)."""
        digits = "".join(c for c in sender_phone if c.isdigit())[-10:]
        if not digits:
            return None
        profile = (
            UserProfile.objects
            .filter(phone_number__isnull=False, user__is_active=True)
            .filter(phone_number__endswith=digits)
            .select_related("user")
            .first()
        )
        return profile.user if profile else None
