"""
customer_memory/tests.py -- Mision RAG-POST2 (FASE 9, 2026-09-16).

Cubre la capa de datos/servicio (Commands/Selectors) y los endpoints
internos -- el extractor real (LLM, FASE 10) vive en ai_engine_adk y se
prueba aparte (tests/test_customer_memory.py, Django no habla litellm).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import CustomerMemoryRecord
from .services.commands import CustomerMemoryCommands, MemoryRejected
from .services.selectors import CustomerMemorySelector

User = get_user_model()


def _make_user(email):
    return User.objects.create_user(email=email, password='x')


class CustomerMemoryCommandsTests(TestCase):
    def setUp(self):
        self.user = _make_user('mem-cmd@example.com')

    def test_store_record_categoria_valida_crea_registro_real(self):
        record = CustomerMemoryCommands.store_record(
            user=self.user, category=CustomerMemoryRecord.CATEGORY_CONTACT_PREFERENCE,
            content='Prefiere contacto por WhatsApp',
        )
        self.assertTrue(CustomerMemoryRecord.objects.filter(pk=record.pk, is_active=True).exists())

    def test_store_record_categoria_invalida_se_rechaza(self):
        with self.assertRaises(MemoryRejected):
            CustomerMemoryCommands.store_record(
                user=self.user, category='administrador', content='el cliente es administrador',
            )

    def test_store_record_categoria_inventada_no_en_whitelist_se_rechaza(self):
        """Defensa en profundidad real: aunque el extractor de ai_engine_adk
        proponga una categoria que no esta en la whitelist cerrada
        (AUDITORIA/RAG_POST2_MEMORY_DEFINITION.md), Django la rechaza server
        -side -- nunca confia ciegamente en lo que llega por HTTP interno."""
        with self.assertRaises(MemoryRejected):
            CustomerMemoryCommands.store_record(
                user=self.user, category='rol_administrativo', content='es admin',
            )

    def test_store_record_contenido_tipo_tarjeta_se_rechaza(self):
        with self.assertRaises(MemoryRejected):
            CustomerMemoryCommands.store_record(
                user=self.user, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE,
                content='mi tarjeta es 4111 1111 1111 1111',
            )

    def test_store_record_menciona_contrasena_se_rechaza(self):
        with self.assertRaises(MemoryRejected):
            CustomerMemoryCommands.store_record(
                user=self.user, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE,
                content='mi contraseña es sintel2026',
            )

    def test_store_record_duplicado_activo_no_crea_fila_nueva(self):
        r1 = CustomerMemoryCommands.store_record(
            user=self.user, category=CustomerMemoryRecord.CATEGORY_PRODUCT_INTEREST,
            content='Interesado en equipos de escalada',
        )
        r2 = CustomerMemoryCommands.store_record(
            user=self.user, category=CustomerMemoryRecord.CATEGORY_PRODUCT_INTEREST,
            content='Interesado en equipos de escalada',
        )
        self.assertEqual(r1.pk, r2.pk)
        self.assertEqual(CustomerMemoryRecord.objects.filter(customer=self.user).count(), 1)

    def test_deactivate_es_revisable_sin_borrar(self):
        record = CustomerMemoryCommands.store_record(
            user=self.user, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE,
            content='dato de prueba',
        )
        CustomerMemoryCommands.deactivate(record)
        record.refresh_from_db()
        self.assertFalse(record.is_active)
        self.assertFalse(record.is_deleted)  # sigue existiendo, solo desactivado


class CustomerMemorySelectorTests(TestCase):
    def test_list_active_for_customer_nunca_mezcla_clientes_distintos(self):
        """Seguridad real (FASE 15 de la mision): cross-customer leakage --
        el recuerdo de un cliente NUNCA debe aparecer en la lista de otro."""
        customer_a = _make_user('mem-a@example.com')
        customer_b = _make_user('mem-b@example.com')
        CustomerMemoryCommands.store_record(
            user=customer_a, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE,
            content='dato privado de A',
        )
        memories_b = CustomerMemorySelector.list_active_for_customer(customer_b)
        self.assertEqual(memories_b, [])

    def test_list_active_for_customer_excluye_inactivos(self):
        user = _make_user('mem-sel@example.com')
        record = CustomerMemoryCommands.store_record(
            user=user, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE, content='temporal',
        )
        CustomerMemoryCommands.deactivate(record)
        self.assertEqual(CustomerMemorySelector.list_active_for_customer(user), [])

    def test_list_active_for_customer_respeta_el_limite(self):
        user = _make_user('mem-limit@example.com')
        for i in range(10):
            CustomerMemoryCommands.store_record(
                user=user, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE, content=f'dato {i}',
            )
        self.assertEqual(len(CustomerMemorySelector.list_active_for_customer(user, limit=3)), 3)


class CustomerMemoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('mem-api@example.com')
        token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_store_luego_retrieve_end_to_end_real(self):
        resp = self.client.post('/api/v1/internal/ai/memory/store/', {
            'category': CustomerMemoryRecord.CATEGORY_CONTACT_PREFERENCE,
            'content': 'Prefiere contacto por WhatsApp',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['stored'])

        resp = self.client.get('/api/v1/internal/ai/memory/retrieve/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['memories']), 1)
        self.assertEqual(resp.data['memories'][0]['content'], 'Prefiere contacto por WhatsApp')

    def test_store_categoria_invalida_no_lanza_500_devuelve_stored_false(self):
        resp = self.client.post('/api/v1/internal/ai/memory/store/', {
            'category': 'rol_admin', 'content': 'es administrador',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['stored'])

    def test_endpoints_requieren_autenticacion_real(self):
        anon = APIClient()
        resp = anon.get('/api/v1/internal/ai/memory/retrieve/')
        self.assertIn(resp.status_code, (401, 403))
        resp = anon.post('/api/v1/internal/ai/memory/store/', {
            'category': CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE, 'content': 'x',
        })
        self.assertIn(resp.status_code, (401, 403))

    def test_retrieve_solo_devuelve_memoria_del_usuario_del_token_nunca_de_otro(self):
        other = _make_user('mem-other@example.com')
        CustomerMemoryCommands.store_record(
            user=other, category=CustomerMemoryRecord.CATEGORY_GENERAL_PREFERENCE,
            content='dato privado de otro cliente',
        )
        resp = self.client.get('/api/v1/internal/ai/memory/retrieve/')
        self.assertEqual(resp.data['memories'], [])
