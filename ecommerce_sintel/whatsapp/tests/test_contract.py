"""
whatsapp/tests/test_contract.py

Mision "Migracion Arquitectonica de WhatsApp" (2026-09-16, FASE 23 --
renombrado desde FASE 20 de la mision anterior). Prueba que
QRWebSessionAdapter y MetaCloudAPIAdapter cumplen el MISMO contrato real
(`WhatsAppConnectionPort`) -- parametrizado, corre identico contra ambos.
Esto es lo que demuestra que el dominio podria recibir cualquiera de los
dos sin distinguirlos.
"""
from django.test import TestCase

from whatsapp.adapters.qr_web_session_adapter import QRWebSessionAdapter
from whatsapp.adapters.meta_cloud_api_adapter import MetaCloudAPIAdapter
from whatsapp.domain.contracts import MessageType, WhatsAppOutboundMessage
from whatsapp.ports.connection import ConnectionCapabilities, ConnectionStatus, WhatsAppConnectionPort


def _adapters():
    return [MetaCloudAPIAdapter(), QRWebSessionAdapter()]


class ConnectionContractTests(TestCase):
    """TestCase de Django (no pytest puro) a proposito -- este modulo no
    depende de pytest-asyncio (el Port es sincrono, ver ports/connection.py),
    y manage.py test SI puede correr esto real, sin el problema de
    support/tests.py (pytest no instalado, ver AUDITORIA/
    RAG_POST2_FINAL_CERTIFICATION.md seccion 11)."""

    def test_ambos_adapters_son_instancias_del_port_real(self):
        for adapter in _adapters():
            self.assertIsInstance(adapter, WhatsAppConnectionPort)

    def test_ambos_declaran_capabilities_tipadas(self):
        for adapter in _adapters():
            self.assertIsInstance(adapter.capabilities, ConnectionCapabilities)

    def test_ambos_get_status_devuelve_un_connection_status_real(self):
        for adapter in _adapters():
            status = adapter.get_status()
            self.assertIsInstance(status, ConnectionStatus)

    def test_ambos_health_check_devuelve_bool(self):
        for adapter in _adapters():
            self.assertIsInstance(adapter.health_check(), bool)

    def test_ambos_generate_pairing_qr_no_lanza_para_meta_lanza_para_qr_sin_gateway(self):
        """No es el mismo COMPORTAMIENTO (Regla FASE 3: capacidades
        distintas son legitimas) -- pero SI es el mismo CONTRATO: ambos
        exponen el metodo, ninguno falla de forma inesperada/silenciosa."""
        meta = MetaCloudAPIAdapter()
        self.assertIsNone(meta.generate_pairing_qr())  # no aplica, documentado, no es un error

        qr = QRWebSessionAdapter()
        from whatsapp.adapters.qr_web_session_adapter import WhatsAppQRNotImplementedError
        with self.assertRaises(WhatsAppQRNotImplementedError):
            qr.generate_pairing_qr()

    def test_ambos_disconnect_no_lanza(self):
        for adapter in _adapters():
            adapter.disconnect()  # no debe lanzar, sin importar el estado previo

    def test_ambos_reconnect_devuelve_un_connection_status_real(self):
        """FASE 2 de la mision: reconnect() es una capacidad minima del
        Port (default real = disconnect()+connect() en la clase base,
        QRWebSessionAdapter hereda ese default -- no tiene logica de
        reconexion propia sin un gateway real que reconectar)."""
        for adapter in _adapters():
            self.assertIsInstance(adapter.reconnect(), ConnectionStatus)

    def test_send_message_respeta_capabilities_declaradas(self):
        """Si un adapter declara send_text=False (o no tiene gateway real,
        como QR), pedirle un send_text real debe fallar EXPLICITO, nunca
        en silencio (Regla FASE 3)."""
        message = WhatsAppOutboundMessage(
            external_conversation_id="573000000000",
            recipient="573000000000",
            text="prueba de contrato",
            message_type=MessageType.TEXT,
        )
        qr = QRWebSessionAdapter()
        from whatsapp.adapters.qr_web_session_adapter import WhatsAppQRNotImplementedError
        with self.assertRaises(WhatsAppQRNotImplementedError):
            qr.send_message(message)

    def test_meta_status_distingue_not_configured_de_connected(self):
        """FASE 10/21 de la mision: NOT_CONFIGURED nunca debe confundirse
        con DISCONNECTED/ERROR. Verificado real contra la configuracion de
        settings del entorno de test (sin credenciales reales de Meta)."""
        from django.test import override_settings

        with override_settings(META_ACCESS_TOKEN='', WHATSAPP_PHONE_NUMBER_ID=''):
            meta = MetaCloudAPIAdapter()
            self.assertEqual(meta.get_status(), ConnectionStatus.NOT_CONFIGURED)
