"""
support/test_tickets.py -- CreateSupportTicketView (2026-09-16).

Archivo SEPARADO de support/tests.py a proposito: ese archivo importa
`pytest` a nivel de modulo (para los tests de Channels/WebSocket, que
necesitan pytest-asyncio) y `pytest` no esta instalado en el contenedor de
dev -- `manage.py test support` falla en el import ANTES de correr nada
(confirmado real, no asumido). CreateSupportTicketView es una vista DRF
sincrona normal, sin necesidad de pytest-asyncio -- un TestCase clasico
(ejecutable ahora mismo con manage.py test) es la herramienta correcta,
y este archivo evita heredar el problema de import del otro.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from support.models import ChatRoom, ChatMessage, SupportTicket

User = get_user_model()


def _make_user(email):
    return User.objects.create_user(email=email, password='TestPass123!')


class CreateSupportTicketViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('ticket-cliente@example.com')
        token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_crea_ticket_real_con_sala_mensaje_y_ai_paused(self):
        resp = self.client.post('/api/v1/support/tickets/create/', {
            'subject': 'Producto llego danado',
            'description': 'El equipo llego con la carcasa rota, necesito cambio.',
            'category': SupportTicket.CATEGORY_ORDER,
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(resp.data['ticket']['ticket_number'].startswith('SUP-'))
        self.assertEqual(resp.data['ticket']['subject'], 'Producto llego danado')
        self.assertEqual(resp.data['ticket']['category'], SupportTicket.CATEGORY_ORDER)
        self.assertEqual(resp.data['ticket']['status'], SupportTicket.STATUS_NEW)

        room = ChatRoom.objects.get(uuid=resp.data['room_uuid'])
        self.assertEqual(room.user_id, self.user.id)
        self.assertTrue(room.ai_paused, "un ticket manual tambien debe pausar la IA (Human Handoff)")
        self.assertTrue(
            ChatMessage.objects.filter(room=room, sender=self.user, message__icontains='carcasa rota').exists(),
            "la descripcion debe quedar como el primer mensaje real de la sala",
        )

    def test_falta_subject_o_description_da_400(self):
        resp = self.client.post('/api/v1/support/tickets/create/', {'description': 'solo descripcion'})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post('/api/v1/support/tickets/create/', {'subject': 'solo asunto'})
        self.assertEqual(resp.status_code, 400)

    def test_categoria_invalida_da_400(self):
        resp = self.client.post('/api/v1/support/tickets/create/', {
            'subject': 'x', 'description': 'y', 'category': 'NO_EXISTE',
        })
        self.assertEqual(resp.status_code, 400)

    def test_categoria_es_opcional(self):
        resp = self.client.post('/api/v1/support/tickets/create/', {
            'subject': 'Consulta general', 'description': 'Solo una pregunta.',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['ticket']['category'], '')

    def test_requiere_autenticacion_real(self):
        anon = APIClient()
        resp = anon.post('/api/v1/support/tickets/create/', {'subject': 'x', 'description': 'y'})
        self.assertIn(resp.status_code, (401, 403))

    def test_segunda_llamada_reusa_la_misma_sala_abierta_no_duplica(self):
        self.client.post('/api/v1/support/tickets/create/', {'subject': 'Caso 1', 'description': 'Primer mensaje.'})
        self.assertEqual(ChatRoom.objects.filter(user=self.user, status=ChatRoom.STATUS_OPEN).count(), 1)

        resp = self.client.post('/api/v1/support/tickets/create/', {'subject': 'Caso 2', 'description': 'Segundo mensaje.'})
        self.assertEqual(resp.status_code, 201)
        # Mismo criterio real que ChatCommands.get_or_create_room: una sala
        # OPEN se reutiliza -- no se crea una segunda sala solo por abrir
        # otro ticket mientras la primera sigue abierta.
        self.assertEqual(ChatRoom.objects.filter(user=self.user, status=ChatRoom.STATUS_OPEN).count(), 1)
        # SupportTicket es OneToOne con ChatRoom -- el ticket existente
        # (subject/summary ya no vacios) no se pisa con los datos del
        # segundo llamado, mismo comportamiento ya probado de
        # SupportTicketCommands.create_ticket.
        room = ChatRoom.objects.filter(user=self.user, status=ChatRoom.STATUS_OPEN).first()
        self.assertEqual(room.ticket.subject, 'Caso 1')

    def test_ticket_de_otro_cliente_no_es_visible_via_esta_sala(self):
        """Aislamiento real -- cada cliente autenticado solo puede crear/ver
        su PROPIA sala via get_or_create_room (scoped por request.user),
        nunca la de otro."""
        other = _make_user('otro-cliente@example.com')
        other_room = ChatRoom.objects.create(user=other)

        resp = self.client.post('/api/v1/support/tickets/create/', {'subject': 'x', 'description': 'y'})
        self.assertNotEqual(resp.data['room_uuid'], str(other_room.uuid))
