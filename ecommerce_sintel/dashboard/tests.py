import uuid
from decimal import Decimal
from django.test import TransactionTestCase
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from shop.models import ProductVariant, Product, Category
from renting.models import Equipment, EquipmentVariant, RentingCategory, RentingBrand, RentalLabor, RentalCostAssignment
from renting.services.pricing import RentalCostRuleCommands
from technical_services.models import TechnicalService, ServiceVariant, ServiceCategory, ServiceLevel, ServiceCostRule

User = get_user_model()

# NOTA (2026-07-03): DashboardInventoryAPITestCase se elimino porque probaba rutas
# /api/v1/dashboard/inventory/... que ya no existen -- la administracion de inventario
# se consolido en /api/v1/inventory/stock-records/... (ver inventory/api/views.py y
# InventoryAPITestCase en el tests.py raiz). InventoryAdminOrchestrator fue removido
# de dashboard/services/admin_orchestrators.py sin dejar ninguna referencia colgante.


class DashboardRentingAPITestCase(TransactionTestCase):
    """Suite de integracion para el BFF administrativo de Renting."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.admin_user = User.objects.create_superuser(
            email="renting_admin@example.com",
            password="adminpassword"
        )
        self.client.force_authenticate(user=self.admin_user)

        # Datos base: categoria, marca, equipo, variante
        self.category = RentingCategory.objects.create(
            name="Compresores",
            slug="compresores"
        )
        self.brand = RentingBrand.objects.create(
            name="AtlasCopco",
            slug="atlascopco"
        )
        self.equipment = Equipment.objects.create(
            vendor=self.admin_user,
            category=self.category,
            brand=self.brand,
            name="Compresor GA110",
            slug="compresor-ga110"
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment,
            sku="GA110-STD",
            rental_price_per_day="150.00",
            stock=5
        )
        self.labor = RentalLabor.objects.create(
            name="Tecnico Operador",
            price_per_hour="25.00"
        )

    # ---- Equipment CRUD -------------------------------------------------------

    def test_list_equipment(self):
        url = "/api/v1/dashboard/equipment/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)
        uuids = [item["uuid"] for item in response.data]
        self.assertIn(str(self.equipment.uuid), uuids)

    def test_create_equipment(self):
        url = "/api/v1/dashboard/equipment/"
        data = {
            "name": "Generador 100KVA",
            "description": "Generador diesel",
            "is_active": True,
            "is_featured": False,
            "category": str(self.category.uuid),
            "brand": str(self.brand.uuid),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Generador 100KVA")
        self.assertIn("uuid", response.data)

    def test_retrieve_equipment(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["uuid"], str(self.equipment.uuid))
        self.assertEqual(response.data["name"], "Compresor GA110")

    def test_partial_update_equipment(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/"
        data = {"name": "Compresor GA110 VSD", "is_featured": True}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Compresor GA110 VSD")
        self.assertTrue(response.data["is_featured"])

    def test_destroy_equipment(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.equipment.refresh_from_db()
        self.assertTrue(self.equipment.is_deleted)

    def test_list_equipment_with_search_filter(self):
        url = "/api/v1/dashboard/equipment/?search=Compresor"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)

    # ---- Equipment Variants ---------------------------------------------------

    def test_list_equipment_variants(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/variants/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]["sku"], "GA110-STD")

    def test_create_equipment_variant(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/variants/create/"
        data = {
            "equipment": str(self.equipment.uuid),
            "sku": "GA110-PRO",
            "rental_price_per_day": "200.00",
            "stock": 2,
            "is_active": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["sku"], "GA110-PRO")

    def test_update_equipment_variant(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/variants/{self.variant.uuid}/"
        data = {"rental_price_per_day": "175.00", "stock": 8}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["rental_price_per_day"]), "175.00")

    def test_delete_equipment_variant(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/variants/{self.variant.uuid}/delete/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.variant.refresh_from_db()
        self.assertTrue(self.variant.is_deleted)

    # ---- Logistics Config -----------------------------------------------------

    def test_upsert_logistics_config(self):
        url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/logistics/"
        data = {
            "delivery_cost": "50000.00",
            "pickup_cost": "40000.00",
            "installation_cost": "30000.00",
            "notes": "Requiere grua para instalacion",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["delivery_cost"]), "50000.00")

    def test_get_logistics_config(self):
        # Primero crear la config
        put_url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/logistics/"
        self.client.put(put_url, {"delivery_cost": "60000.00"}, format="json")
        # Luego consultarla
        response = self.client.get(put_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["delivery_cost"]), "60000.00")

    def test_delete_logistics_config(self):
        # Primero crear la config
        put_url = f"/api/v1/dashboard/equipment/{self.equipment.uuid}/logistics/"
        self.client.put(put_url, {"delivery_cost": "60000.00"}, format="json")
        # Luego eliminarla
        response = self.client.delete(put_url)
        self.assertEqual(response.status_code, 204)
        # Bug regresion (2026-07-17): borrar la config de logistica NO debe
        # borrar el Equipment completo (copy-paste erroneo ya corregido).
        self.equipment.refresh_from_db()
        self.assertFalse(self.equipment.is_deleted)
        get_response = self.client.get(f"/api/v1/dashboard/equipment/{self.equipment.uuid}/")
        self.assertEqual(get_response.status_code, 200)

    # ---- Renting Categories ---------------------------------------------------

    def test_list_renting_categories(self):
        url = "/api/v1/dashboard/renting-categories/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)

    def test_create_renting_category(self):
        url = "/api/v1/dashboard/renting-categories/"
        data = {"name": "Montacargas", "description": "Equipos de elevacion", "is_active": True}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Montacargas")

    # ---- Renting Brands -------------------------------------------------------

    def test_list_renting_brands(self):
        url = "/api/v1/dashboard/renting-brands/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)

    def test_create_renting_brand(self):
        url = "/api/v1/dashboard/renting-brands/"
        data = {"name": "Caterpillar"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Caterpillar")

    # ---- Rental Labor ---------------------------------------------------------

    def test_list_rental_labor(self):
        url = "/api/v1/dashboard/rental-labor/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]["name"], "Tecnico Operador")

    def test_create_rental_labor(self):
        url = "/api/v1/dashboard/rental-labor/"
        data = {
            "name": "Supervisor de Obra",
            "price_per_hour": "35.00",
            "description": "Supervision en campo",
            "is_active": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Supervisor de Obra")

    # ---- Rental Cost Rules ----------------------------------------------------

    def test_create_rental_cost_rule(self):
        # Regla arquitectonica: no existen reglas globales -- toda regla nace
        # atada a un equipment y se asigna automaticamente a su variante principal.
        url = "/api/v1/dashboard/rental-cost-rules/"
        data = {
            "equipment": str(self.equipment.uuid),
            "name": "IVA 19%",
            "cost_type": "PERCENTAGE",
            "context": "TAX",
            "value": "19.0000",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "IVA 19%")
        self.assertNotIn("applies_globally", response.data)
        # La regla queda asignada de inmediato a la variante principal de ESTE equipo.
        rule_uuid = response.data["uuid"]
        assignment_exists = RentalCostAssignment.objects.filter(
            rule__uuid=rule_uuid, variant=self.variant, is_deleted=False
        ).exists()
        self.assertTrue(assignment_exists)

    def test_rental_cost_rule_list_is_scoped_to_equipment(self):
        # Otro equipo con su propia variante y su propia regla -- no debe
        # aparecer jamas en el listado del primer equipment.
        other_equipment = Equipment.objects.create(
            vendor=self.admin_user, category=self.category, name="Otro Equipo Independiente",
        )
        other_variant = EquipmentVariant.objects.create(
            equipment=other_equipment, sku="OTRO-SKU-001",
            rental_price_per_day="10.00", stock=1,
        )
        RentalCostRuleCommands.create_rule_for_equipment(
            equipment=other_equipment, name="Regla de otro equipo",
            cost_type="FIXED", context="SURCHARGE", value="500",
        )
        url = f"/api/v1/dashboard/rental-cost-rules/?equipment={self.equipment.uuid}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        names = [r["name"] for r in response.data]
        self.assertNotIn("Regla de otro equipo", names)

    def test_assign_rental_cost_rule_to_variant(self):
        # Primero crear la regla (nace atada a self.equipment)
        create_url = "/api/v1/dashboard/rental-cost-rules/"
        rule_response = self.client.post(create_url, {
            "equipment": str(self.equipment.uuid),
            "name": "Descuento Fidelidad",
            "cost_type": "PERCENTAGE",
            "context": "DISCOUNT",
            "value": "5.0000",
        }, format="json")
        self.assertEqual(rule_response.status_code, 201)
        rule_uuid = rule_response.data["uuid"]
        # Reasignarla explicitamente (idempotente, ya estaba asignada por la creacion)
        assign_url = f"/api/v1/dashboard/rental-cost-rules/{rule_uuid}/assign/"
        assign_response = self.client.post(assign_url, {
            "variant_uuid": str(self.variant.uuid)
        }, format="json")
        self.assertEqual(assign_response.status_code, 201)
        self.assertIn("assignment_uuid", assign_response.data)

    def test_unauthenticated_request_is_denied(self):
        self.client.force_authenticate(user=None)
        url = "/api/v1/dashboard/equipment/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


class DashboardTechnicalServicesAPITestCase(TransactionTestCase):
    """Suite de integracion para el BFF administrativo de Technical Services."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Crear usuarios
        self.admin_user = User.objects.create_superuser(
            email="admin_ts@sintel.com",
            password="adminpassword"
        )
        self.normal_user = User.objects.create_user(
            email="user_ts@sintel.com",
            password="userpassword"
        )

        from technical_services.models import ServiceConfiguration
        # Configuración de servicio activa
        self.config = ServiceConfiguration.objects.create(
            name="Config Test",
            smlv=1300000.00,
            transport_subsidy=162000.00,
            benefit_rate=53.10,
            indirect_costs_rate=15.00,
            iva_rate=19.00,
            is_active=True
        )

        # Categoría y Nivel
        self.category = ServiceCategory.objects.create(
            name="Instalaciones Eléctricas",
            description="Servicios de electricidad"
        )
        self.level = ServiceLevel.objects.create(
            name="Técnico Senior"
        )

        # Servicio Técnico
        self.service = TechnicalService.objects.create(
            name="Instalación Tablero Eléctrico",
            description="Instalación completa de tableros",
            category=self.category,
            level=self.level,
            vendor=self.admin_user,
            is_active=True,
            is_featured=False,
            is_purchasable=True
        )

        # Variante
        self.variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-ELEC-TAB-SR",
            pricing_strategy="HOURLY",
            estimated_hours=4.00,
            complexity_factor=1.20,
            is_default=True
        )

        # Regla de costo
        self.cost_rule = ServiceCostRule.objects.create(
            name="Impuesto Local",
            cost_type="PERCENTAGE",
            context="TAX",
            value=2.5000,
            applies_globally=False,
            is_active=True
        )

        # Autenticar como admin
        self.client.force_authenticate(user=self.admin_user)

    # ── TESTS SERVICIOS ───────────────────────────────────────────────────────

    def test_list_services(self):
        url = "/api/v1/dashboard/services/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_service(self):
        url = "/api/v1/dashboard/services/"
        data = {
            "name": "Mantenimiento Transformador",
            "description": "Mantenimiento preventivo",
            "category": str(self.category.uuid),
            "level": str(self.level.uuid),
            "is_active": True,
            "is_featured": True,
            "is_purchasable": True
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Mantenimiento Transformador")
        self.assertTrue(response.data["is_featured"])

    def test_create_service_with_default_variant(self):
        url = "/api/v1/dashboard/services/"
        data = {
            "name": "Instalación Cámara IP",
            "description": "Instalación con cableado básico",
            "category": str(self.category.uuid),
            "level": str(self.level.uuid),
            "is_active": True,
            "is_featured": False,
            "is_purchasable": True,
            "initial_variant": {
                "pricing_strategy": "FIXED",
                "fixed_price": "250000.00",
                "estimated_hours": "1.00",
                "complexity_factor": "1.00"
            }
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        service = TechnicalService.objects.get(uuid=response.data["uuid"])
        variant = service.variants.get(is_default=True, is_deleted=False)
        self.assertTrue(variant.sku)
        self.assertEqual(variant.pricing_strategy, "FIXED")
        self.assertEqual(variant.fixed_price, Decimal("250000.00"))

    def test_retrieve_service(self):
        url = f"/api/v1/dashboard/services/{self.service.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.service.name)

    def test_partial_update_service(self):
        url = f"/api/v1/dashboard/services/{self.service.uuid}/"
        data = {"name": "Instalación Tablero Modificado"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Instalación Tablero Modificado")

    def test_delete_service(self):
        url = f"/api/v1/dashboard/services/{self.service.uuid}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(TechnicalService.objects.filter(uuid=self.service.uuid, is_deleted=False).exists())

    def test_list_service_levels(self):
        url = "/api/v1/dashboard/service-levels/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    # ── TESTS CATEGORIAS ───────────────────────────────────────────────────────

    def test_list_categories(self):
        url = "/api/v1/dashboard/service-categories/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_category(self):
        url = "/api/v1/dashboard/service-categories/"
        data = {
            "name": "Redes de Datos",
            "description": "Cableado estructurado",
            "is_active": True
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Redes de Datos")

    def test_retrieve_category(self):
        url = f"/api/v1/dashboard/service-categories/{self.category.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.category.name)

    def test_partial_update_category(self):
        url = f"/api/v1/dashboard/service-categories/{self.category.uuid}/"
        data = {"description": "Nueva descripción de cat"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["description"], "Nueva descripción de cat")

    def test_delete_category(self):
        url = f"/api/v1/dashboard/service-categories/{self.category.uuid}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ServiceCategory.objects.filter(uuid=self.category.uuid, is_deleted=False).exists())

    # ── TESTS VARIANTES ────────────────────────────────────────────────────────

    def test_list_variants(self):
        url = f"/api/v1/dashboard/service-variants/?service={self.service.uuid}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_create_variant(self):
        url = "/api/v1/dashboard/service-variants/"
        data = {
            "service": str(self.service.uuid),
            "sku": "SERV-ELEC-NEW-SKU",
            "pricing_strategy": "FIXED",
            "fixed_price": "250000.00",
            "is_default": False
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["sku"], "SERV-ELEC-NEW-SKU")
        self.assertEqual(float(response.data["calculated_price"]), 297500.0) # 250000 * 1.19 (IVA)

    def test_retrieve_variant(self):
        url = f"/api/v1/dashboard/service-variants/{self.variant.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sku"], self.variant.sku)

    def test_partial_update_variant(self):
        url = f"/api/v1/dashboard/service-variants/{self.variant.uuid}/"
        data = {"estimated_hours": "5.00"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["estimated_hours"]), 5.0)

    def test_delete_variant(self):
        url = f"/api/v1/dashboard/service-variants/{self.variant.uuid}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ServiceVariant.objects.filter(uuid=self.variant.uuid, is_deleted=False).exists())

    # ── TESTS COST RULES ───────────────────────────────────────────────────────

    def test_list_cost_rules(self):
        url = "/api/v1/dashboard/service-cost-rules/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_cost_rule(self):
        url = "/api/v1/dashboard/service-cost-rules/"
        data = {
            "name": "Descuento Especial",
            "cost_type": "PERCENTAGE",
            "context": "DISCOUNT",
            "value": "10.0000",
            "applies_globally": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Descuento Especial")
        self.assertTrue(response.data["applies_globally"])

    def test_retrieve_cost_rule(self):
        url = f"/api/v1/dashboard/service-cost-rules/{self.cost_rule.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.cost_rule.name)

    def test_partial_update_cost_rule(self):
        url = f"/api/v1/dashboard/service-cost-rules/{self.cost_rule.uuid}/update/"
        data = {"name": "Impuesto Local Modificado"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Impuesto Local Modificado")

    def test_deactivate_cost_rule(self):
        url = f"/api/v1/dashboard/service-cost-rules/{self.cost_rule.uuid}/deactivate/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 204)
        self.cost_rule.refresh_from_db()
        self.assertFalse(self.cost_rule.is_active)

    def test_assign_cost_rule_to_variant(self):
        url = f"/api/v1/dashboard/service-cost-rules/{self.cost_rule.uuid}/assign/"
        data = {"variant_uuid": str(self.variant.uuid)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("assignment_uuid", response.data)

    def test_unauthenticated_request_is_denied(self):
        self.client.force_authenticate(user=None)
        url = "/api/v1/dashboard/services/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


class DashboardQuotationListQueryCountTestCase(TransactionTestCase):
    """
    Cubre un N+1 real detectado el 2026-07-03 (Fase 6, auditoria de BD): QuotationListSerializer
    (usado por AdminQuotationViewSet.list()) accede a `template.name`, pero
    QuotationSelector.list_all_for_admin() no incluye `template_id` en su .only() ni hace
    select_related('template') -- cada cotizacion en la lista disparaba 2 queries extra
    (recarga de campo diferido + fetch del template).
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email="quotes_admin@example.com", password="adminpassword",
        )
        self.client.force_authenticate(user=self.admin_user)

        from quotes.models import Quotation, QuoteTemplate
        from django.utils import timezone

        self.template = QuoteTemplate.objects.create(name="Instalacion CCTV")
        for i in range(2):
            Quotation.objects.create(
                client_name=f"Cliente {i}",
                client_email=f"cliente{i}@example.com",
                valid_until=timezone.now().date(),
                template=self.template,
            )

    def test_list_quotations_has_no_n_plus_1(self):
        with self.assertNumQueries(1):
            response = self.client.get('/api/v1/dashboard/quotations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['template_name'], 'Instalacion CCTV')


class DashboardServiceListQueryCountRegressionTestCase(TransactionTestCase):
    """
    Cubre un N+1 de 3 capas en /api/v1/dashboard/services/ detectado el 2026-07-03 (Fase 6):
    (1) TechnicalServiceSerializer.get_variants() hacia obj.variants.filter(...), que ignora
    cualquier prefetch_related declarado (Django solo cachea .all()) -- corregido filtrando en
    Python; (2) faltaba variants__materials__product_variant__product en el prefetch de
    ServiceSelector.list_all_for_admin() -- agregado; (3) LaborCostCalculator.get_active_config()
    se consultaba una vez POR VARIANTE pese a ser un valor global -- corregido con cache de 5 min
    invalidado por signal. Medido: 31 -> 23 queries para 2 servicios con 1 variante+1 material c/u.

    NO llega a un numero constante: ServiceVariantSerializer.get_calculated_price() y
    get_price_info() llaman cada uno por separado a ServiceSelector.get_variant_quotation(obj),
    duplicando el calculo de precio por variante -- ese problema quedo identificado pero sin
    corregir (fuera del alcance aprobado en esta sesion). Este test solo evita que el numero
    empeore de nuevo por encima del limite ya medido.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email="services_admin_perf@example.com", password="adminpassword",
        )
        self.client.force_authenticate(user=self.admin_user)

        from technical_services.models import ServiceVariant, ServiceMaterial

        for i in range(2):
            service = TechnicalService.objects.create(
                name=f"Servicio {i}", slug=f"servicio-{i}",
            )
            variant = ServiceVariant.objects.create(
                service=service, sku=f"SVC-VAR-{i}",
                pricing_strategy=ServiceVariant.FIXED, fixed_price=Decimal('100000.00'),
            )
            product = Product.objects.create(
                vendor=self.admin_user,
                category=Category.objects.create(name=f"Cat {i}", slug=f"cat-{i}"),
                name=f"Material {i}", slug=f"material-{i}",
            )
            product_variant = ProductVariant.objects.create(
                product=product, sku=f"MAT-{i}", price=Decimal('5000.00'),
            )
            ServiceMaterial.objects.create(variant=variant, product_variant=product_variant, quantity=2)

    def test_list_services_query_count_does_not_regress(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/v1/dashboard/services/')
        self.assertEqual(response.status_code, 200)
        # 23 medido despues del fix parcial; margen pequeno para no ser fragil, pero
        # bien por debajo de las 31 originales -- si esto falla, revisar antes de subir
        # el limite (podria ser una regresion real, no solo variacion de datos de prueba).
        self.assertLessEqual(len(ctx.captured_queries), 25)


class DashboardMarketplaceMetricsTestCase(TransactionTestCase):
    """
    AdminMetricsOrchestrator._get_marketplace_metrics() -- tarjetas KPI nuevas del dashboard
    global para el marketplace de contratistas + asignacion de tecnicos (Fase 9).
    """

    def setUp(self):
        from accounts.models import UserProfile
        from accounts.services.commands import AccountCommands

        self.contractor = AccountCommands.register_user({
            "email": "kpi_contractor@example.com", "password": "Pass@1234!",
            "user_type": UserProfile.CONTRACTOR, "first_name": "K", "last_name": "P",
        })
        self.technician = AccountCommands.register_user({
            "email": "kpi_tech@example.com", "password": "Pass@1234!",
            "user_type": UserProfile.TECHNICIAN, "first_name": "K", "last_name": "T",
        })

    def test_get_metrics_includes_marketplace_key(self):
        from dashboard.services.admin_orchestrators import AdminMetricsOrchestrator
        metrics = AdminMetricsOrchestrator.get_metrics()
        self.assertIn('marketplace', metrics)
        mp = metrics['marketplace']
        self.assertGreaterEqual(mp['professionals_count'], 2)
        self.assertIn('service_status_counts', mp)
        self.assertIn('top_categories', mp)
        self.assertIn('top_professionals', mp)

    def test_dashboard_endpoint_returns_marketplace_metrics(self):
        self.client = APIClient()
        admin_user = User.objects.create_superuser(
            email="kpi_admin@example.com", password="adminpassword",
        )
        self.client.force_authenticate(user=admin_user)
        response = self.client.get('/api/v1/dashboard/metrics/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('marketplace', response.data)

