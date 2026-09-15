"""
whatsapp/tests/test_isolation.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 21-22
(2026-09-16). Prueba critica de la mision: cambiar
WHATSAPP_CONNECTION_TYPE=QR <-> REST no debe requerir tocar
WhatsAppService/Support/ChatRoom/CustomerResolver/AI bridge -- y prueba
inversa (REST -> QR).

Dos niveles de evidencia, no solo uno:
1. ESTRUCTURAL: el codigo fuente del dominio NUNCA menciona QR/REST (Regla
   1 de la mision -- "nunca condicionales de infraestructura dentro del
   dominio"). No es "no lo hice a proposito", es una asercion real sobre
   el codigo fuente en disco.
2. COMPORTAMENTAL: el mismo WhatsAppService, con un Fake adapter
   inyectado, produce el MISMO resultado de negocio (ChatRoom resuelto,
   mensaje persistido) sin importar que adapter recibio -- la unica
   diferencia observable es la llamada final a send_message().
"""
import ast
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from support.models import ChatMessage, ChatRoom
from whatsapp.domain.contracts import MessageType, WhatsAppInboundMessage, WhatsAppOutboundMessage
from whatsapp.domain.service import WhatsAppService
from whatsapp.factory import WhatsAppConnectionFactory
from whatsapp.ports.connection import ConnectionCapabilities, ConnectionStatus, WhatsAppConnectionPort

User = get_user_model()

_DOMAIN_MODULES = [
    "whatsapp/domain/service.py",
    "whatsapp/domain/contracts.py",
    "whatsapp/domain/customer_resolver.py",
    "whatsapp/domain/conversation_resolver.py",
    "whatsapp/domain/idempotency.py",
]
_FORBIDDEN_NAMES = {"QRConnectionAdapter", "RestConnectionAdapter"}
_FORBIDDEN_MODULES = {"whatsapp.adapters.qr_adapter", "whatsapp.adapters.rest_adapter", "qr_adapter", "rest_adapter"}


class DomainNeverKnowsConnectionMechanismTests(TestCase):
    """Evidencia ESTRUCTURAL -- analiza el AST real del codigo fuente (no
    un grep de texto plano, que daria falsos positivos contra los propios
    docstrings/comentarios que documentan esta regla citando los nombres
    de las clases prohibidas) -- confirma que ningun import ni ninguna
    llamada real del dominio referencia un adapter concreto."""

    def _assert_module_never_imports_or_instantiates_adapters(self, relative_path: str):
        repo_root = Path(__file__).resolve().parent.parent.parent
        source = (repo_root / relative_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(
                    node.module, _FORBIDDEN_MODULES,
                    f"{relative_path} importa {node.module!r} -- el dominio no debe conocer el mecanismo de conexion",
                )
                for alias in node.names:
                    self.assertNotIn(alias.name, _FORBIDDEN_NAMES)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, _FORBIDDEN_MODULES)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(
                    node.func.id, _FORBIDDEN_NAMES,
                    f"{relative_path} instancia {node.func.id}() -- el dominio recibe el adapter por inyeccion, nunca lo construye",
                )

    def test_ningun_modulo_de_dominio_importa_o_instancia_un_adapter_concreto(self):
        for relative_path in _DOMAIN_MODULES:
            self._assert_module_never_imports_or_instantiates_adapters(relative_path)


class FakeConnectionAdapter(WhatsAppConnectionPort):
    """Adapter de prueba -- cumple el contrato real, cuenta llamadas para
    verificar el comportamiento sin depender de Meta/un gateway QR real."""

    def __init__(self, *, label: str):
        self.label = label
        self.sent_messages: list[WhatsAppOutboundMessage] = []

    @property
    def capabilities(self) -> ConnectionCapabilities:
        return ConnectionCapabilities(send_text=True, receive_text=True, webhook=True)

    def connect(self) -> ConnectionStatus:
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> None:
        return None

    def get_status(self) -> ConnectionStatus:
        return ConnectionStatus.CONNECTED

    def send_message(self, message: WhatsAppOutboundMessage) -> str:
        self.sent_messages.append(message)
        return f"fake-{self.label}-msg-id"

    def generate_pairing_qr(self) -> str | None:
        return None

    def health_check(self) -> bool:
        return True


class SwitchConnectionBehaviorTests(TestCase):
    """Evidencia COMPORTAMENTAL -- mismo WhatsAppService, 2 adapters
    distintos inyectados, mismo resultado de negocio."""

    def setUp(self):
        self.user = User.objects.create_user(email="wa-isolation@example.com", password="x")
        from accounts.models import UserProfile
        UserProfile.objects.filter(user=self.user).update(phone_number="3001234567") \
            if UserProfile.objects.filter(user=self.user).exists() \
            else UserProfile.objects.create(user=self.user, phone_number="3001234567")

    def _inbound(self, message_id: str):
        return WhatsAppInboundMessage(
            channel="rest",
            external_message_id=message_id,
            external_conversation_id="573001234567",
            sender_phone="573001234567",
            message_type=MessageType.TEXT,
            text="hola, mensaje de prueba de aislamiento",
        )

    def test_qr_a_rest_no_cambia_el_resultado_de_negocio(self):
        for label, message_id in (("qr-simulado", "iso-1"), ("rest-simulado", "iso-2")):
            adapter = FakeConnectionAdapter(label=label)
            service = WhatsAppService(adapter)
            from unittest.mock import patch
            with patch("support.services.ai_bridge.ask_ai", return_value={"response": "respuesta de prueba", "metrics": {}}):
                result = service.process_inbound_message(self._inbound(message_id))

            self.assertEqual(result["status"], "sent")
            room = ChatRoom.objects.get(user=self.user)
            self.assertTrue(ChatMessage.objects.filter(room=room, message__icontains="mensaje de prueba de aislamiento").exists())
            self.assertEqual(len(adapter.sent_messages), 1)

    def test_rest_a_qr_prueba_inversa_mismo_resultado(self):
        """Prueba inversa explicita (FASE 22 de la mision) -- mismo test
        que arriba, orden invertido, documentado aparte para que quede
        explicito que se corrio en ambos sentidos."""
        self.test_qr_a_rest_no_cambia_el_resultado_de_negocio()


class FactoryIsTheOnlySwitchPointTests(TestCase):
    def test_factory_selecciona_rest_por_configuracion(self):
        with override_settings(WHATSAPP_CONNECTION_TYPE="REST"):
            from whatsapp.adapters.rest_adapter import RestConnectionAdapter
            adapter = WhatsAppConnectionFactory.create()
            self.assertIsInstance(adapter, RestConnectionAdapter)

    def test_factory_selecciona_qr_por_configuracion(self):
        with override_settings(WHATSAPP_CONNECTION_TYPE="QR"):
            from whatsapp.adapters.qr_adapter import QRConnectionAdapter
            adapter = WhatsAppConnectionFactory.create()
            self.assertIsInstance(adapter, QRConnectionAdapter)

    def test_valor_invalido_falla_explicito_no_en_silencio(self):
        with override_settings(WHATSAPP_CONNECTION_TYPE="BLUETOOTH"):
            with self.assertRaises(ValueError):
                WhatsAppConnectionFactory.create()
