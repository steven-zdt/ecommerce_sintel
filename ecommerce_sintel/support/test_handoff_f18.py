"""
HARDENING F18 (2026-09-24) -- safe handoff: toma de control humana, reactivacion explicita y aviso de turnos degradados.
ESCRITO PERO NO EJECUTADO (regla vigente: el usuario ejecuta los tests a mano).
"""
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from support.models import ChatMessage, ChatRoom
from support.services.ai_bridge import is_ai_mode_active
from support.services.commands import ChatCommands
from users.models import User


def _user(email, staff=False):
    u = User.objects.create_user(email=email, password='x-test-pass-123')
    if staff:
        u.is_staff = True
        u.save(update_fields=['is_staff'])
    return u


@override_settings(AI_SUPPORT_CHAT_ENABLED=True)
class HumanTakeoverTests(TestCase):
    def setUp(self):
        self.client_user = _user('cliente@example.com')
        self.room = ChatCommands.get_or_create_room(self.client_user)

    def test_una_sala_nueva_esta_atendida_por_la_ia(self):
        self.assertTrue(is_ai_mode_active(self.room))

    def test_la_respuesta_de_un_humano_pausa_la_ia_y_es_idempotente(self):
        self.assertTrue(ChatCommands.pause_ai_for_human_takeover(self.room))
        self.assertFalse(ChatCommands.pause_ai_for_human_takeover(self.room))  # ya estaba pausada
        self.room.refresh_from_db()
        self.assertTrue(self.room.ai_paused)
        self.assertFalse(is_ai_mode_active(self.room))

    def test_la_pausa_no_depende_de_una_instancia_vieja(self):
        stale = ChatRoom.objects.get(pk=self.room.pk)
        ChatRoom.objects.filter(pk=self.room.pk).update(ai_paused=True)
        self.assertFalse(ChatCommands.pause_ai_for_human_takeover(stale))  # el UPDATE condicional ve el estado real


@override_settings(AI_SUPPORT_CHAT_ENABLED=True)
class ResumeAiTests(TestCase):
    def setUp(self):
        self.admin = _user('admin@example.com', staff=True)
        self.client_user = _user('cliente@example.com')
        self.room = ChatCommands.get_or_create_room(self.client_user)
        ChatRoom.objects.filter(pk=self.room.pk).update(ai_paused=True, assigned_admin=self.admin)
        self.room.refresh_from_db()
        self.api = APIClient()
        self.url = f'/api/v1/support/chats/{self.room.uuid}/resume-ai/'

    def test_solo_un_admin_puede_reactivar(self):
        self.api.force_authenticate(self.client_user)
        self.assertEqual(self.api.post(self.url).status_code, 403)
        self.room.refresh_from_db()
        self.assertTrue(self.room.ai_paused)
        self.assertEqual(APIClient().post(self.url).status_code, 401)

    def test_el_admin_reactiva_libera_la_asignacion_y_deja_un_mensaje_del_asistente(self):
        self.api.force_authenticate(self.admin)
        response = self.api.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.room.refresh_from_db()
        self.assertFalse(self.room.ai_paused)
        self.assertIsNone(self.room.assigned_admin_id)
        self.assertTrue(is_ai_mode_active(self.room))
        self.assertTrue(ChatMessage.objects.filter(room=self.room, message__contains='volvio a atender').exists())

    def test_no_se_reactiva_en_una_sala_cerrada(self):
        ChatRoom.objects.filter(pk=self.room.pk).update(status=ChatRoom.STATUS_CLOSED)
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post(self.url).status_code, 400)

    def test_sala_inexistente_da_404(self):
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post('/api/v1/support/chats/00000000-0000-0000-0000-000000000000/resume-ai/').status_code, 404)


class DegradedAlertTests(TestCase):
    def setUp(self):
        cache.clear()
        self.room = ChatCommands.get_or_create_room(_user('cliente@example.com'))

    @patch('support.api.internal_ai._notify_support_admins')
    def test_avisa_a_los_admins_una_sola_vez_por_ventana(self, notify):
        self.assertTrue(ChatCommands.alert_admins_ai_degraded(self.room, 'no_response'))
        self.assertFalse(ChatCommands.alert_admins_ai_degraded(self.room, 'no_response'))
        self.assertEqual(notify.call_count, 1)
        self.assertEqual(notify.call_args.kwargs['label'], '[Asistente no disponible]')

    @override_settings(AI_DEGRADED_ADMIN_ALERT=False)
    @patch('support.api.internal_ai._notify_support_admins')
    def test_se_puede_apagar(self, notify):
        self.assertFalse(ChatCommands.alert_admins_ai_degraded(self.room))
        notify.assert_not_called()

    @patch('support.api.internal_ai._notify_support_admins', side_effect=RuntimeError('canal caido'))
    def test_un_aviso_fallido_nunca_rompe_el_turno(self, _notify):
        self.assertFalse(ChatCommands.alert_admins_ai_degraded(self.room))

    def test_el_consumer_conecta_pausa_y_aviso_en_los_puntos_correctos(self):
        import inspect

        from support import consumers

        src = inspect.getsource(consumers.SupportChatConsumer)
        self.assertIn('await self._pause_ai_on_human_reply(room)', src)
        self.assertIn("alert_admins_ai_degraded(room, 'no_response')", src)
        self.assertIn("alert_admins_ai_degraded(room, 'engine_unavailable')", src)


class AiInactiveReasonTests(TestCase):
    """INCIDENTE 2026-09-25: el motivo por el que la IA no atiende una sala queda identificable (y se registra). Escritos, no ejecutados."""

    def _room(self, **kw):
        from types import SimpleNamespace
        base = dict(status='OPEN', STATUS_OPEN='OPEN', ai_paused=False, assigned_admin_id=None)
        base.update(kw)
        return SimpleNamespace(**base)

    @override_settings(AI_SUPPORT_CHAT_ENABLED=True)
    def test_motivos(self):
        from support.services.ai_bridge import ai_inactive_reason, is_ai_mode_active
        self.assertIsNone(ai_inactive_reason(self._room()))
        self.assertEqual(ai_inactive_reason(self._room(ai_paused=True)), 'paused')
        self.assertEqual(ai_inactive_reason(self._room(assigned_admin_id=3)), 'assigned')
        self.assertEqual(ai_inactive_reason(self._room(status='CLOSED')), 'closed')
        self.assertTrue(is_ai_mode_active(self._room()))
        self.assertFalse(is_ai_mode_active(self._room(ai_paused=True)))

    @override_settings(AI_SUPPORT_CHAT_ENABLED=False)
    def test_flag_apagado(self):
        from support.services.ai_bridge import ai_inactive_reason
        self.assertEqual(ai_inactive_reason(self._room()), 'flag_off')

    @override_settings(AI_SUPPORT_CHAT_ENABLED=True, AI_GLOBAL_ENABLED=False)
    def test_kill_switch_global(self):
        from support.services.ai_bridge import ai_inactive_reason
        self.assertEqual(ai_inactive_reason(self._room()), 'flag_off')
