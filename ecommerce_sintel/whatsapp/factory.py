"""
whatsapp/factory.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 8-9
(2026-09-16). UNICO lugar del repositorio donde puede existir
`if connection_type == ...` para WhatsApp -- capa de composicion, nunca
dominio (Regla 1 de la mision).

Uso real:
    from whatsapp.factory import WhatsAppConnectionFactory
    connection = WhatsAppConnectionFactory.create()
    service = WhatsAppService(connection)
"""
from django.conf import settings

CONNECTION_TYPE_QR = "QR"
CONNECTION_TYPE_REST = "REST"
_VALID_TYPES = {CONNECTION_TYPE_QR, CONNECTION_TYPE_REST}


class WhatsAppConnectionFactory:
    @staticmethod
    def create(connection_type: str | None = None):
        """`connection_type=None` lee `settings.WHATSAPP_CONNECTION_TYPE`
        -- el parametro explicito existe para tests (contract tests
        parametrizados, ver whatsapp/tests/test_contract.py) sin tener que
        mutar settings."""
        resolved = (connection_type or settings.WHATSAPP_CONNECTION_TYPE or "").strip().upper()
        if resolved not in _VALID_TYPES:
            raise ValueError(
                f"WHATSAPP_CONNECTION_TYPE invalido: {resolved!r} -- valores validos: {sorted(_VALID_TYPES)}"
            )
        if resolved == CONNECTION_TYPE_QR:
            from whatsapp.adapters.qr_adapter import QRConnectionAdapter
            return QRConnectionAdapter()
        from whatsapp.adapters.rest_adapter import RestConnectionAdapter
        return RestConnectionAdapter()
