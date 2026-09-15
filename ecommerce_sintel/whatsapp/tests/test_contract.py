"""
whatsapp/tests/test_contract.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 20
(2026-09-16). Prueba que QRConnectionAdapter y RestConnectionAdapter
cumplen el MISMO contrato real (`WhatsAppConnectionPort`) -- parametrizado,
corre identico contra ambos. Esto es lo que demuestra que el dominio
podria recibir cualquiera de los dos sin distinguirlos.
"""
from django.test import TestCase

from whatsapp.adapters.qr_adapter import QRConnectionAdapter
from whatsapp.adapters.rest_adapter import RestConnectionAdapter
from whatsapp.domain.contracts import MessageType, WhatsAppOutboundMessage
from whatsapp.ports.connection import ConnectionCapabilities, ConnectionStatus, WhatsAppConnectionPort


def _adapters():
    return [RestConnectionAdapter(), QRConnectionAdapter()]


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

    def test_ambos_generate_pairing_qr_no_lanza_para_rest_lanza_para_qr_sin_gateway(self):
        """No es el mismo COMPORTAMIENTO (Regla FASE 4: capacidades
        distintas son legitimas) -- pero SI es el mismo CONTRATO: ambos
        exponen el metodo, ninguno falla de forma inesperada/silenciosa."""
        rest = RestConnectionAdapter()
        self.assertIsNone(rest.generate_pairing_qr())  # no aplica, documentado, no es un error

        qr = QRConnectionAdapter()
        from whatsapp.adapters.qr_adapter import WhatsAppQRNotImplementedError
        with self.assertRaises(WhatsAppQRNotImplementedError):
            qr.generate_pairing_qr()

    def test_ambos_disconnect_no_lanza(self):
        for adapter in _adapters():
            adapter.disconnect()  # no debe lanzar, sin importar el estado previo

    def test_send_message_respeta_capabilities_declaradas(self):
        """Si un adapter declara send_text=False (o no tiene gateway real,
        como QR), pedirle un send_text real debe fallar EXPLICITO, nunca
        en silencio (Regla FASE 4)."""
        message = WhatsAppOutboundMessage(
            external_conversation_id="573000000000",
            recipient="573000000000",
            text="prueba de contrato",
            message_type=MessageType.TEXT,
        )
        qr = QRConnectionAdapter()
        from whatsapp.adapters.qr_adapter import WhatsAppQRNotImplementedError
        with self.assertRaises(WhatsAppQRNotImplementedError):
            qr.send_message(message)
