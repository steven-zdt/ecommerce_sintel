"""
Unit tests puros (sin I/O, fuente sintetica via ast.parse) para scanner/.
Fase 15, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08.
"""
import ast

from project_knowledge_graph.scanner.django_scanner import (
    detect_python_role,
    extract_api_test_calls,
    extract_direct_symbol_calls,
    extract_model_fields,
    extract_model_manager_usages,
    extract_signal_registrations,
    extract_task_queue_calls,
    extract_websocket_patterns,
    is_model_class,
    is_permission_class,
    is_serializer_class,
    is_task_function,
    is_test_class,
    is_viewset_class,
)
from project_knowledge_graph.scanner.frontend_scanner import (
    extract_frontend_symbols,
    extract_pinia_store,
    extract_use_hook_calls,
    extract_vue_api_calls,
    isolate_vue_script,
)
from project_knowledge_graph.scanner.python_scanner import (
    extract_classes,
    extract_env_var_calls,
    extract_imports,
    extract_symbols,
    file_stats,
    get_base_names,
)


def _parse(src: str) -> ast.Module:
    return ast.parse(src)


def test_extract_classes_captures_bases_methods_and_public_fields():
    tree = _parse(
        "class Product(models.Model):\n"
        "    name = models.CharField(max_length=100)\n"
        "    _internal = 1\n"
        "    def save(self):\n"
        "        pass\n"
    )
    classes = extract_classes(tree)
    assert len(classes) == 1
    cls = classes[0]
    assert cls["name"] == "Product"
    assert cls["bases"] == ["models.Model"]
    assert cls["methods"] == ["save"]
    assert cls["fields"] == ["name"]  # _internal se descarta por empezar con "_"


def test_extract_imports_covers_both_import_forms():
    tree = _parse("import os\nfrom shop.models import Product\n")
    imports = extract_imports(tree)
    assert "os" in imports
    assert "shop.models.Product" in imports


def test_get_base_names_handles_name_and_attribute_bases():
    tree = _parse("class X(Model, serializers.ModelSerializer):\n    pass\n")
    cls_node = tree.body[0]
    assert get_base_names(cls_node) == ["Model", "serializers.ModelSerializer"]


def test_detect_python_role_matches_known_filename_patterns():
    assert detect_python_role("shop/models.py") == "model"
    assert detect_python_role("shop/views.py") == "viewset"
    assert detect_python_role("shop/serializers.py") == "serializer"
    assert detect_python_role("shop/migrations/0001_initial.py") == "migration"
    assert detect_python_role("shop/random_helper.py") == "misc"


def test_is_model_class_recognizes_sintel_base_and_suffix():
    assert is_model_class(["SintelBaseModel"]) is True
    assert is_model_class(["models.Model"]) is True  # termina en "Model" (endswith, no match exacto)
    assert is_model_class(["CustomBaseModel"]) is True  # tambien termina en "Model"
    assert is_model_class(["Serializer"]) is False


def test_is_viewset_class_matches_drf_bases():
    assert is_viewset_class(["viewsets.ModelViewSet"]) is True
    assert is_viewset_class(["APIView"]) is True
    assert is_viewset_class(["object"]) is False


def test_is_serializer_and_permission_class():
    assert is_serializer_class(["serializers.ModelSerializer"]) is True
    assert is_serializer_class(["Model"]) is False
    assert is_permission_class(["BasePermission"]) is True
    assert is_permission_class(["IsAuthenticated"]) is False  # no contiene "Permission"


def test_extract_model_fields_detects_foreign_key_related_model():
    tree = _parse(
        "class OrderLine(models.Model):\n"
        "    order = models.ForeignKey(Order, on_delete=models.CASCADE)\n"
        "    quantity = models.IntegerField()\n"
    )
    cls_node = tree.body[0]
    fields = extract_model_fields(cls_node)
    by_name = {f["name"]: f for f in fields}
    assert by_name["order"]["field_type"] == "ForeignKey"
    assert by_name["order"]["related_model"] == "Order"
    assert by_name["quantity"]["field_type"] == "IntegerField"
    assert by_name["quantity"]["related_model"] is None


def test_extract_signal_registrations_finds_receiver_decorator_and_connect_call():
    tree = _parse(
        "@receiver(post_save, sender=Order)\n"
        "def on_order_saved(sender, instance, **kwargs):\n"
        "    pass\n"
        "\n"
        "post_save.connect(on_order_saved)\n"
    )
    signals = extract_signal_registrations(tree)
    triggers = {s["trigger"] for s in signals}
    assert "receiver_decorator" in triggers
    assert "connect_call" in triggers


def test_is_task_function_detects_shared_task_decorator():
    tree = _parse("@shared_task\ndef send_email():\n    pass\n")
    fn = tree.body[0]
    assert is_task_function(fn.name, fn.decorator_list) is True

    tree2 = _parse("def regular_function():\n    pass\n")
    fn2 = tree2.body[0]
    assert is_task_function(fn2.name, fn2.decorator_list) is False


def test_is_task_function_detects_shared_task_called_with_kwargs():
    """[CORREGIDO Fase 6, 2026-08-10] Bug real: `@shared_task(bind=True,
    max_retries=3)` (llamada directa a un Name, no un Attribute) devolvia
    False -- verificado que notifications/tasks.py usa EXCLUSIVAMENTE esta
    forma en las 8 tasks reales del archivo, todas invisibles antes de este
    fix (0 nodos Task para toda la app notifications)."""
    tree = _parse(
        "@shared_task(bind=True, max_retries=3)\n"
        "def send_ws_notification_task(self, user_id):\n"
        "    pass\n"
    )
    fn = tree.body[0]
    assert is_task_function(fn.name, fn.decorator_list) is True


# ---------------------------------------------------------------------------
# extract_symbols / file_stats -- Fase 1, Site Knowledge Graph, 2026-08-10
# ---------------------------------------------------------------------------

def test_extract_symbols_captures_methods_with_qualified_name_and_line_range():
    tree = _parse(
        "class AvailabilityEngine:\n"
        "    def calculate_availability(self, equipment):\n"
        "        x = 1\n"
        "        return x\n"
        "\n"
        "    async def refresh_cache(self):\n"
        "        pass\n"
    )
    symbols = extract_symbols(tree)
    by_name = {s["qualified_name"]: s for s in symbols}

    assert "AvailabilityEngine.calculate_availability" in by_name
    sym = by_name["AvailabilityEngine.calculate_availability"]
    assert sym["kind"] == "method"
    assert sym["class_name"] == "AvailabilityEngine"
    assert sym["name"] == "calculate_availability"
    assert sym["start_line"] == 2
    assert sym["end_line"] == 4
    assert sym["is_async"] is False

    assert by_name["AvailabilityEngine.refresh_cache"]["is_async"] is True


def test_extract_symbols_captures_module_level_functions_separately_from_methods():
    tree = _parse(
        "def module_level():\n"
        "    pass\n"
        "\n"
        "class Foo:\n"
        "    def method_level(self):\n"
        "        pass\n"
    )
    symbols = extract_symbols(tree)
    by_name = {s["qualified_name"]: s for s in symbols}

    assert by_name["module_level"]["kind"] == "function"
    assert by_name["module_level"]["class_name"] is None
    assert by_name["Foo.method_level"]["kind"] == "method"


def test_extract_symbols_ignores_nested_functions_inside_functions():
    """Funciones anidadas dentro de otra funcion no son una unidad de cambio
    util (no se puede "ir a" ese segmento independientemente) -- deliberadamente
    fuera de alcance."""
    tree = _parse(
        "def outer():\n"
        "    def inner():\n"
        "        pass\n"
        "    return inner\n"
    )
    symbols = extract_symbols(tree)
    names = [s["qualified_name"] for s in symbols]
    assert names == ["outer"]


def test_extract_classes_now_includes_end_line():
    tree = _parse(
        "class Foo:\n"
        "    def bar(self):\n"
        "        pass\n"
    )
    classes = extract_classes(tree)
    assert classes[0]["line"] == 1
    assert classes[0]["end_line"] == 3


def test_file_stats_computes_line_count_and_stable_hash():
    source = "line one\nline two\nline three"
    stats = file_stats(source)
    assert stats["lines"] == 3
    assert len(stats["hash"]) == 32  # md5 hex digest

    # Determinista: el mismo contenido siempre produce el mismo hash.
    assert file_stats(source)["hash"] == stats["hash"]
    # Contenido distinto -> hash distinto (no una constante disfrazada).
    assert file_stats(source + "\nline four")["hash"] != stats["hash"]


def test_file_stats_empty_source():
    assert file_stats("") == {"lines": 0, "hash": file_stats("")["hash"]}


# ---------------------------------------------------------------------------
# extract_env_var_calls / extract_websocket_patterns -- Fase 2 "Contract
# Graph", Site Knowledge Graph, 2026-08-10
# ---------------------------------------------------------------------------

def test_extract_env_var_calls_finds_config_calls_deduplicated_in_order():
    tree = _parse(
        "SECRET_KEY = config('SECRET_KEY')\n"
        "DEBUG = config('DEBUG', default=False, cast=bool)\n"
        "SECRET_KEY_AGAIN = config('SECRET_KEY')\n"
    )
    names = extract_env_var_calls(tree)
    assert names == ["SECRET_KEY", "DEBUG"]  # deduplicado, orden de aparicion


def test_extract_env_var_calls_supports_env_alias_too():
    tree = _parse("REDIS_URL = env('REDIS_URL', default='redis://localhost')\n")
    assert extract_env_var_calls(tree) == ["REDIS_URL"]


def test_extract_env_var_calls_ignores_unrelated_calls():
    tree = _parse("x = some_other_function('NOT_AN_ENV_VAR')\n")
    assert extract_env_var_calls(tree) == []


def test_extract_websocket_patterns_matches_path_with_as_asgi():
    tree = _parse(
        "support_websocket_patterns = [\n"
        "    path('ws/support/chat/', SupportChatConsumer.as_asgi()),\n"
        "]\n"
    )
    patterns = extract_websocket_patterns(tree)
    assert patterns == [{"route": "ws/support/chat/", "consumer": "SupportChatConsumer"}]


def test_extract_websocket_patterns_matches_re_path_too():
    """Bug real encontrado corriendo contra el repo: operations/routing.py
    usa re_path(), no path() -- la primera version de esta funcion solo
    reconocia path() y perdia esta ruta en silencio."""
    tree = _parse(
        "operations_websocket_patterns = [\n"
        "    re_path(\n"
        "        r'^ws/operations/(?P<ticket_uuid>[0-9a-f-]+)/$',\n"
        "        OperationTrackingConsumer.as_asgi(),\n"
        "    ),\n"
        "]\n"
    )
    patterns = extract_websocket_patterns(tree)
    assert len(patterns) == 1
    assert patterns[0]["consumer"] == "OperationTrackingConsumer"
    assert "ws/operations" in patterns[0]["route"]


def test_extract_websocket_patterns_ignores_plain_django_urls():
    """path() sin .as_asgi() es una URL HTTP normal, no una ruta WebSocket --
    no debe aparecer aca (eso ya lo cubre extract_url_patterns())."""
    tree = _parse("urlpatterns = [path('api/v1/shop/', include('shop.urls'))]\n")
    assert extract_websocket_patterns(tree) == []


# ---------------------------------------------------------------------------
# extract_frontend_symbols / isolate_vue_script -- Fase 3 "Frontend Symbol
# Intelligence", Site Knowledge Graph, 2026-08-10. Sintetico pero modelado
# sobre patrones reales del repo (ver frontend/src/composables/
# useOperationTracking.js y frontend/src/store/renting/availabilityStore.js
# -- la prueba contra el repo real vive en test_pipeline_equivalence.py).
# ---------------------------------------------------------------------------

def test_extract_frontend_symbols_captures_named_function_declarations():
    content = (
        "export function useThing() {\n"
        "  async function fetchTicket() {\n"
        "    await api.get('operations/x/');\n"
        "  }\n"
        "  return { fetchTicket };\n"
        "}\n"
    )
    symbols = extract_frontend_symbols(content, container_name="useThing")
    by_name = {s["qualified_name"]: s for s in symbols}

    assert by_name["useThing"]["kind"] == "function"
    assert by_name["useThing"]["class_name"] is None
    assert by_name["useThing"]["start_line"] == 1
    assert by_name["useThing"]["end_line"] == 6

    fetch = by_name["useThing.fetchTicket"]
    assert fetch["kind"] == "method"
    assert fetch["class_name"] == "useThing"
    assert fetch["symbol_type"] == "function"
    assert fetch["is_async"] is True
    assert fetch["start_line"] == 2
    assert fetch["end_line"] == 4
    assert fetch["role"] == "api_call"  # llama api.get(...)


def test_extract_frontend_symbols_classifies_role_emit_and_event_handler():
    content = (
        "function handleSelect(payload) {\n"
        "  emit('select', payload);\n"
        "}\n"
    )
    symbols = extract_frontend_symbols(content, container_name="AvailabilityCard")
    sym = symbols[0]
    assert sym["name"] == "handleSelect"
    # emit() tiene prioridad sobre el nombre de tipo "handle*" en _classify_role
    assert sym["role"] == "emit"


def test_extract_frontend_symbols_arrow_const_and_computed():
    content = (
        "const formattedDate = computed(() => {\n"
        "  return props.date;\n"
        "});\n"
        "\n"
        "const shortDate = (value) => {\n"
        "  return value.slice(0, 4);\n"
        "};\n"
    )
    symbols = extract_frontend_symbols(content, container_name="AvailabilityCard")
    by_name = {s["name"]: s for s in symbols}

    assert by_name["formattedDate"]["symbol_type"] == "computed"
    assert by_name["formattedDate"]["qualified_name"] == "AvailabilityCard.formattedDate"
    assert by_name["shortDate"]["symbol_type"] == "function"


def test_extract_frontend_symbols_bare_lifecycle_hooks_get_unique_names():
    content = (
        "onMounted(async () => {\n"
        "  await fetchTicket();\n"
        "});\n"
        "onUnmounted(() => {\n"
        "  ws?.close();\n"
        "});\n"
    )
    symbols = extract_frontend_symbols(content, container_name="useOperationTracking")
    names = sorted(s["name"] for s in symbols)
    assert names == ["onMounted", "onUnmounted"]
    assert all(s["symbol_type"] == "lifecycle" for s in symbols)


def test_extract_frontend_symbols_bare_watch_disambiguates_duplicates():
    content = (
        "watch(a, () => { doA(); });\n"
        "watch(b, () => { doB(); });\n"
    )
    symbols = extract_frontend_symbols(content, container_name="Foo")
    names = sorted(s["name"] for s in symbols)
    assert names == ["watch", "watch_2"]


def test_extract_frontend_symbols_store_actions_only_when_is_store_true():
    content = (
        "export const useAvailabilityStore = defineStore('rentalAvailability', {\n"
        "  state: () => ({ checking: false }),\n"
        "  actions: {\n"
        "    async check(uuid, params) {\n"
        "      try { this.result = await availabilityService.check(uuid, params); }\n"
        "      catch (error) { this.error = error; }\n"
        "      finally { this.checking = false; }\n"
        "    },\n"
        "    async fetchAvailability(uuid, params) {\n"
        "      return await availabilityService.get(uuid, params);\n"
        "    },\n"
        "  },\n"
        "});\n"
    )
    without_store_flag = extract_frontend_symbols(content, container_name="rentalAvailability")
    assert without_store_flag == []

    symbols = extract_frontend_symbols(content, container_name="rentalAvailability", is_store=True)
    by_name = {s["name"]: s for s in symbols}
    assert set(by_name) == {"check", "fetchAvailability"}
    assert by_name["check"]["symbol_type"] == "method"
    assert by_name["check"]["qualified_name"] == "rentalAvailability.check"
    assert by_name["check"]["is_async"] is True
    # catch/finally anidados dentro de check() no deben aparecer como
    # simbolos propios -- confirma que el overlap-skip funciona.
    assert "catch" not in by_name and "finally" not in by_name


def test_extract_frontend_symbols_store_getters_use_computed_symbol_type():
    content = (
        "export const useCartStore = defineStore('cart', {\n"
        "  getters: {\n"
        "    itemCount(state) {\n"
        "      return state.items.length;\n"
        "    },\n"
        "  },\n"
        "  actions: {},\n"
        "});\n"
    )
    symbols = extract_frontend_symbols(content, container_name="cart", is_store=True)
    assert len(symbols) == 1
    assert symbols[0]["name"] == "itemCount"
    assert symbols[0]["symbol_type"] == "computed"


def test_extract_frontend_symbols_hash_is_stable_and_content_sensitive():
    a = extract_frontend_symbols("function foo() { return 1; }\n", container_name="X")[0]
    b = extract_frontend_symbols("function foo() { return 1; }\n", container_name="X")[0]
    c = extract_frontend_symbols("function foo() { return 2; }\n", container_name="X")[0]
    assert a["hash"] == b["hash"]
    assert a["hash"] != c["hash"]


def test_isolate_vue_script_blanks_template_and_style_but_keeps_line_numbers():
    content = (
        "<template>\n"
        "  <div>{{ x }}</div>\n"
        "</template>\n"
        "\n"
        "<script setup>\n"
        "function realFn() {\n"
        "  return 1;\n"
        "}\n"
        "</script>\n"
        "\n"
        "<style>\n"
        ".x { color: red; }\n"
        "</style>\n"
    )
    isolated = isolate_vue_script(content)
    assert isolated.count("\n") == content.count("\n")
    assert "<div>" not in isolated
    assert ".x { color: red; }" not in isolated
    assert "function realFn()" in isolated

    symbols = extract_frontend_symbols(isolated, container_name="Whatever")
    assert symbols[0]["start_line"] == content.splitlines().index("function realFn() {") + 1


def test_isolate_vue_script_is_noop_for_plain_js_content():
    content = "function foo() {\n  return 1;\n}\n"
    assert isolate_vue_script(content) == content


# ---------------------------------------------------------------------------
# Fase 4 "Contract Graph Frontend<->Backend", Site Knowledge Graph,
# 2026-08-10. Modelado sobre patrones reales: services/renting/
# availabilityService.js (llamada encadenada useApi().get(...)) y
# store/renting/availabilityStore.js (hook_name real de defineStore).
# ---------------------------------------------------------------------------

def test_extract_vue_api_calls_matches_chained_use_api_call():
    """Bug real corregido en Fase 4: los 10 archivos de services/**/*.js
    (la capa real de 'custom API wrapper') usan SIEMPRE el patron encadenado
    `useApi().get(url)`, nunca `const api = useApi(); api.get(url)` -- antes
    de este fix, extract_vue_api_calls no reconocia ninguna de las 69
    llamadas reales de esa capa."""
    content = "check(uuid, params) { return useApi().get(`renting/equipment/${uuid}/check-availability/`, { params }).then(r => r.data); }"
    calls = extract_vue_api_calls(content)
    assert calls == [{"method": "GET", "url": "renting/equipment/${uuid}/check-availability/"}]


def test_extract_use_hook_calls_captures_full_hook_name_deduplicated():
    content = (
        "const store = useAvailabilityStore();\n"
        "const toast = useToast();\n"
        "const store2 = useAvailabilityStore();\n"
    )
    assert extract_use_hook_calls(content) == ["useAvailabilityStore", "useToast"]


def test_extract_use_hook_calls_ignores_non_hook_calls():
    content = "const x = useApi().get('x');\nconsole.log('use this carefully');\n"
    names = extract_use_hook_calls(content)
    assert "useApi" in names
    assert "console" not in names


def test_extract_pinia_store_captures_real_hook_name():
    """hook_name (Fase 4) es lo que permite matchear EXACTO contra el
    nombre real que aparece en el sitio de uso (`useAvailabilityStore()`)
    -- a diferencia de store_id (`rentalAvailability`), que es un slug de
    negocio sin relacion textual garantizada con el nombre del hook."""
    content = (
        "export const useAvailabilityStore = defineStore('rentalAvailability', {\n"
        "  state: () => ({ checking: false }),\n"
        "  actions: {},\n"
        "});\n"
    )
    info = extract_pinia_store(content)
    assert info["store_id"] == "rentalAvailability"
    assert info["hook_name"] == "useAvailabilityStore"


def test_extract_pinia_store_hook_name_is_none_when_not_a_plain_export_const():
    content = "const x = defineStore('foo', {});\n"
    info = extract_pinia_store(content)
    assert info["hook_name"] is None


def test_extract_frontend_symbols_flat_exported_object_captures_service_methods():
    """Patron real de frontend/src/services/**/*.js -- objeto exportado
    plano (no un Pinia store) con metodos que llaman a la API."""
    content = (
        "import useApi from '@/composables/useApi';\n"
        "\n"
        "export const availabilityService = {\n"
        "  check(equipmentUuid, params) {\n"
        "    return useApi().get(`renting/equipment/${equipmentUuid}/check-availability/`, { params }).then(r => r.data);\n"
        "  },\n"
        "  get(equipmentUuid, params) {\n"
        "    return useApi().get(`renting/equipment/${equipmentUuid}/availability/`, { params }).then(r => r.data);\n"
        "  },\n"
        "};\n"
    )
    symbols = extract_frontend_symbols(content, container_name="availabilityService")
    by_name = {s["name"]: s for s in symbols}
    assert set(by_name) == {"check", "get"}
    assert by_name["check"]["qualified_name"] == "availabilityService.check"
    assert by_name["check"]["api_calls"] == [
        {"method": "GET", "url": "renting/equipment/${equipmentUuid}/check-availability/"}
    ]
    assert by_name["check"]["hook_calls"] == ["useApi"]


def test_extract_frontend_symbols_flat_object_extraction_does_not_fire_on_pinia_store():
    """`export const useXStore = defineStore('id', { actions: {...} })` NO
    debe matchear el extractor de objeto plano (el `=` va seguido de
    `defineStore(`, no de `{` directo) -- evita doble-conteo con
    _extract_store_block_methods() cuando is_store=True."""
    content = (
        "export const useAvailabilityStore = defineStore('rentalAvailability', {\n"
        "  actions: {\n"
        "    async check(uuid) { return await x(uuid); },\n"
        "  },\n"
        "});\n"
    )
    without_store_flag = extract_frontend_symbols(content, container_name="rentalAvailability", is_store=False)
    assert without_store_flag == []  # ni store ni objeto plano: is_store=False no extrae actions:

    with_store_flag = extract_frontend_symbols(content, container_name="rentalAvailability", is_store=True)
    assert len(with_store_flag) == 1  # solo la logica de store, sin duplicado del objeto plano
    assert with_store_flag[0]["name"] == "check"


def test_make_frontend_symbol_carries_api_calls_and_hook_calls_from_body():
    content = "function fetchThing() {\n  return useApi().get('shop/products/');\n}\n"
    symbols = extract_frontend_symbols(content, container_name="useThing")
    sym = symbols[0]
    assert sym["api_calls"] == [{"method": "GET", "url": "shop/products/"}]
    assert sym["hook_calls"] == ["useApi"]


# ---------------------------------------------------------------------------
# extract_model_manager_usages -- Fase 5 "Data Flow Graph", Site Knowledge
# Graph, 2026-08-10. Modelado sobre shop/services/selectors.py real
# (ProductSelector.list_active/TaxSelector.list_active homonimos) y
# shop/services/commands.py (StockRecord.objects.get_or_create).
# ---------------------------------------------------------------------------

def test_extract_model_manager_usages_classifies_read_and_write_verbs():
    tree = _parse(
        "class ProductSelector:\n"
        "    @staticmethod\n"
        "    def list_active():\n"
        "        return Product.objects.filter(is_active=True)\n"
        "\n"
        "class ProductCommands:\n"
        "    @staticmethod\n"
        "    def create(data):\n"
        "        return Product.objects.create(**data)\n"
    )
    usages = extract_model_manager_usages(tree)
    by_qname = {u["qualified_name"]: u for u in usages}
    assert by_qname["ProductSelector.list_active"]["kind"] == "read"
    assert by_qname["ProductSelector.list_active"]["model"] == "Product"
    assert by_qname["ProductCommands.create"]["kind"] == "write"


def test_extract_model_manager_usages_does_not_confuse_homonymous_methods_in_different_classes():
    """Bug real encontrado y corregido contra el repo: shop/services/
    selectors.py tiene tanto ProductSelector.list_active() como
    TaxSelector.list_active() -- atribuir por nombre crudo de funcion
    mezclaba los modelos de ambos. qualified_name (Clase.metodo) los separa."""
    tree = _parse(
        "class ProductSelector:\n"
        "    @staticmethod\n"
        "    def list_active():\n"
        "        return Product.objects.filter(is_active=True)\n"
        "\n"
        "class TaxSelector:\n"
        "    @staticmethod\n"
        "    def list_active():\n"
        "        return Tax.objects.filter(is_active=True)\n"
    )
    usages = extract_model_manager_usages(tree)
    by_qname = {u["qualified_name"]: u["model"] for u in usages}
    assert by_qname["ProductSelector.list_active"] == "Product"
    assert by_qname["TaxSelector.list_active"] == "Tax"


def test_extract_model_manager_usages_ignores_unrelated_calls():
    tree = _parse(
        "def helper():\n"
        "    x = some_dict.filter(y=1)\n"  # no es Model.objects
        "    return x\n"
    )
    assert extract_model_manager_usages(tree) == []


def test_extract_model_manager_usages_attributes_module_level_functions_without_class():
    tree = _parse(
        "def _generate_sku():\n"
        "    return ProductVariant.objects.filter(sku='X').exists()\n"
    )
    usages = extract_model_manager_usages(tree)
    assert usages[0]["qualified_name"] == "_generate_sku"
    assert usages[0]["model"] == "ProductVariant"
    assert usages[0]["kind"] == "read"  # exists() es de lectura


# ---------------------------------------------------------------------------
# extract_signal_registrations (sender/signal_name) / extract_task_queue_calls
# -- Fase 6 "Execution Graph", Site Knowledge Graph, 2026-08-10. Modelado
# sobre accounts/models.py (@receiver(post_save, sender=UserProfile)) y
# notifications/services/commands.py (5 tasks reales encoladas via .delay()).
# ---------------------------------------------------------------------------

def test_extract_signal_registrations_captures_sender_and_signal_name():
    tree = _parse(
        "@receiver(post_save, sender=UserProfile)\n"
        "def create_technician_profile(sender, instance, created, **kwargs):\n"
        "    pass\n"
    )
    signals = extract_signal_registrations(tree)
    assert signals[0]["sender"] == "UserProfile"
    assert signals[0]["signal_name"] == "post_save"


def test_extract_signal_registrations_sender_is_none_without_kwarg():
    tree = _parse(
        "post_save.connect(on_order_saved)\n"
    )
    signals = extract_signal_registrations(tree)
    assert signals[0]["sender"] is None
    assert signals[0]["signal_name"] == "post_save"


def test_extract_task_queue_calls_captures_real_dispatch_pattern():
    tree = _parse(
        "class NotificationCommands:\n"
        "    @staticmethod\n"
        "    def dispatch_notification(user, template_slug, context):\n"
        "        send_ws_notification_task.delay(user_id=user.pk)\n"
        "        send_email_notification_task.delay(user_id=user.pk)\n"
    )
    usages = extract_task_queue_calls(tree)
    tasks = {u["task"] for u in usages}
    assert tasks == {"send_ws_notification_task", "send_email_notification_task"}
    assert all(u["qualified_name"] == "NotificationCommands.dispatch_notification" for u in usages)


def test_extract_task_queue_calls_recognizes_apply_async_too():
    tree = _parse(
        "def enqueue():\n"
        "    my_task.apply_async(args=[1], countdown=10)\n"
    )
    usages = extract_task_queue_calls(tree)
    assert usages == [{"qualified_name": "enqueue", "task": "my_task"}]


def test_extract_task_queue_calls_ignores_unrelated_delay_attribute():
    tree = _parse(
        "def helper():\n"
        "    x = queryset.delay(5)\n"  # no relacionado a una task real, igual se captura
        "    return x\n"
    )
    # No hay forma de distinguir esto de una task real via AST solo -- se
    # documenta como limitacion (ver ARQUITECTURA_COMPLETA_GRAFO.md): el
    # filtro real ocurre en builder.py al matchear contra nodos Task
    # existentes, no aca.
    usages = extract_task_queue_calls(tree)
    assert usages == [{"qualified_name": "helper", "task": "queryset"}]


# ---------------------------------------------------------------------------
# is_test_class / extract_api_test_calls / extract_direct_symbol_calls --
# Fase 7 "Test Graph", Site Knowledge Graph, 2026-08-10. Modelado sobre
# shop/tests.py (APITestCase real, self.client.post con f-string) y
# renting/tests_endpoints.py (RentalRequestCommands.create_request(...)
# llamado directo desde un test real).
# ---------------------------------------------------------------------------

def test_is_test_class_recognizes_api_test_case_and_variants():
    assert is_test_class(["APITestCase"]) is True
    assert is_test_class(["TestCase"]) is True
    assert is_test_class(["SomeCustomTestCase"]) is True  # termina en "TestCase"
    assert is_test_class(["ModelViewSet"]) is False


def test_extract_api_test_calls_captures_fstring_url_real_pattern():
    tree = _parse(
        "class ProductReviewDuplicatePreventionTestCase(APITestCase):\n"
        "    def test_second_review_blocked_by_serializer_validation(self):\n"
        "        self.client.force_authenticate(user=self.user)\n"
        "        response = self.client.post(\n"
        "            f'/api/v1/shop/products/{self.product.uuid}/review/',\n"
        "            {'rating': 5},\n"
        "        )\n"
    )
    calls = extract_api_test_calls(tree)
    assert len(calls) == 1
    call = calls[0]
    assert call["qualified_name"] == (
        "ProductReviewDuplicatePreventionTestCase."
        "test_second_review_blocked_by_serializer_validation"
    )
    assert call["method"] == "POST"
    assert call["url"].startswith("/api/v1/shop/products/")


def test_extract_api_test_calls_ignores_non_client_attribute():
    tree = _parse(
        "def helper():\n"
        "    api.post('/api/v1/shop/products/')\n"  # no es self.client
        "    return 1\n"
    )
    assert extract_api_test_calls(tree) == []


def test_extract_direct_symbol_calls_matches_real_command_pattern():
    tree = _parse(
        "class RentalRequestAdminActionsTestCase(APITestCase):\n"
        "    def setUp(self):\n"
        "        self.rental_request = RentalRequestCommands.create_request(self.customer, {})\n"
        "        RentalRequestCommands.process_payment_selection(self.rental_request, 'COD')\n"
    )
    calls = extract_direct_symbol_calls(tree)
    targets = {c["target_qualified_name"] for c in calls}
    assert targets == {
        "RentalRequestCommands.create_request",
        "RentalRequestCommands.process_payment_selection",
    }
    assert all(c["qualified_name"] == "RentalRequestAdminActionsTestCase.setUp" for c in calls)


def test_extract_direct_symbol_calls_ignores_lowercase_instance_calls():
    tree = _parse(
        "def helper():\n"
        "    self.assertEqual(1, 1)\n"  # 'self' empieza en minuscula, no una Clase
        "    response.json()\n"  # idem
        "    return 1\n"
    )
    assert extract_direct_symbol_calls(tree) == []
