"""
whatsapp/factory.py

Mision "Migracion Arquitectonica de WhatsApp -- QR Web Session Experimental
+ Meta Cloud API Futura" (2026-09-16). UNICO lugar del repositorio donde
puede existir `if connection_type == ...` para WhatsApp -- capa de
composicion, nunca dominio (Regla 1 de la mision).

Renombrado desde CONNECTION_TYPE_QR/CONNECTION_TYPE_REST (mision anterior)
-- nomenclatura explicita: QR_WEB_SESSION (experimental, tercero) vs
META_CLOUD_API (oficial).

Uso real:
    from whatsapp.factory import WhatsAppConnectionFactory
    connection = WhatsAppConnectionFactory.create()
    service = WhatsAppService(connection)
"""
from django.conf import settings

CONNECTION_TYPE_QR_WEB_SESSION = "QR_WEB_SESSION"
CONNECTION_TYPE_META_CLOUD_API = "META_CLOUD_API"
_VALID_TYPES = {CONNECTION_TYPE_QR_WEB_SESSION, CONNECTION_TYPE_META_CLOUD_API}


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
        if resolved == CONNECTION_TYPE_QR_WEB_SESSION:
            from whatsapp.adapters.qr_web_session_adapter import QRWebSessionAdapter
            return QRWebSessionAdapter()
        from whatsapp.adapters.meta_cloud_api_adapter import MetaCloudAPIAdapter
        return MetaCloudAPIAdapter()
