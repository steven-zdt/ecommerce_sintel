"""
whatsapp/domain/idempotency.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 14
(2026-09-16). Deduplicacion real en la capa de dominio -- por
`(channel, external_message_id)`, NUNCA depende exclusivamente de lo que
el gateway/proveedor garantice (un gateway QR real podria reintentar
distinto a como reintenta Meta, o no reintentar nunca -- el dominio no
puede asumir ninguno de los dos comportamientos).

Generaliza el mecanismo real que antes vivia solo en
notifications/api/whatsapp_webhook.py (cache.add por message_id, TTL 24h)
-- MISMO mecanismo (Django cache, atomico), namespace ahora incluye
`channel` para que REST y un futuro QR nunca puedan colisionar aunque un
proveedor reuse IDs de mensaje que otro tambien use.
"""
from django.core.cache import cache

_DEDUPE_TIMEOUT_SECONDS = 60 * 60 * 24  # 24h -- mismo TTL real que ya usaba el webhook


class WhatsAppIdempotencyGuard:
    @staticmethod
    def is_duplicate(channel: str, external_message_id: str) -> bool:
        """True si este (channel, external_message_id) ya se proceso
        antes. cache.add() es atomico -- si la clave ya existe, devuelve
        False sin sobreescribir, evitando la ventana de carrera de un
        get()+set() separado ante 2 entregas casi simultaneas (mismo
        razonamiento real que ya aplicaba el codigo original)."""
        if not external_message_id:
            # Mismo criterio real de antes: sin id no se puede deduplicar,
            # se procesa igual (mejor un posible duplicado raro que perder
            # el mensaje).
            return False
        key = f"whatsapp_inbound:{channel}:{external_message_id}"
        is_new = cache.add(key, True, timeout=_DEDUPE_TIMEOUT_SECONDS)
        return not is_new
