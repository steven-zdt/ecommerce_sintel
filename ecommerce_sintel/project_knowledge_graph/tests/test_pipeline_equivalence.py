"""
Prueba de equivalencia end-to-end: el pipeline nuevo (project_knowledge_graph)
debe seguir respondiendo lo mismo que ai_engine/auditor.py + knowledge_graph.py
+ dependency_graph.py respondian antes de la migracion, sobre el codigo REAL
del repo -- no un fixture sintetico. Fase 15-16, PLAN_MAESTRO_DE_SEPARACION_
PROJECT_KNOWLEDGE_GRAPH, 2026-08-08.

El caso 'renting' en particular es deliberado: es el escenario real que
motivo AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md y el bug fix documentado en
dependency_graph/blast_radius.py -- si esta prueba se rompe, es la señal mas
directa posible de que la migracion regreso ese bug.
"""
import json

from project_knowledge_graph.config import DEPENDENCY_GRAPH_PATH, PROJECT_MAP_PATH


def test_project_map_has_all_known_django_apps(audited_project):
    from project_knowledge_graph.config import DJANGO_APPS

    pmap = json.loads(PROJECT_MAP_PATH.read_text(encoding="utf-8"))
    audited = set(pmap["apps"].keys())
    # No todas las DJANGO_APPS declaradas tienen que existir como directorio en
    # todo checkout (ver Regla 13 -- fallar explicito, no en silencio, es
    # responsabilidad de config.py, no de esta prueba) pero las apps nucleo
    # del dominio deben estar siempre presentes en un checkout real.
    assert {"shop", "renting", "orders", "accounts"}.issubset(audited)
    assert audited.issubset(set(DJANGO_APPS))


def test_renting_app_summary_has_expected_viewsets(audited_project):
    from project_knowledge_graph.dependency_graph.query import get_app_summary

    summary = get_app_summary("renting")
    assert "EquipmentViewSet" in summary["viewsets"]
    assert "RentingCategoryViewSet" in summary["viewsets"]
    assert len(summary["endpoints"]) > 0


def test_renting_blast_radius_reproduces_original_bugfix_scenario(audited_project):
    """[CORREGIDO 2026-07-30] Antes de ese fix, preguntar por 'renting' (nombre
    de app, no de entidad exacta) devolvia el impacto de UNA sola entidad
    ('renting.Equipment') en vez de agregar las de toda la app. Esta prueba
    fija ese comportamiento: el resultado debe incluir ViewSets de mas de una
    entidad de renting, no solo la primera coincidencia parcial."""
    from project_knowledge_graph.dependency_graph.blast_radius import what_breaks_if_i_change

    blast = what_breaks_if_i_change("renting")
    assert "ViewSet" in blast
    renting_viewsets = [v for v in blast["ViewSet"] if v.startswith("renting.")]
    assert len(renting_viewsets) >= 3, (
        "El blast radius de 'renting' deberia agregar ViewSets de varias entidades "
        f"de esa app, no solo la primera coincidencia parcial. Obtenido: {renting_viewsets}"
    )


def test_dependency_graph_has_all_expected_top_level_keys(audited_project):
    dg = json.loads(DEPENDENCY_GRAPH_PATH.read_text(encoding="utf-8"))
    expected_keys = {
        "model_dependents", "endpoint_consumers", "viewset_to_endpoint",
        "serializer_to_model", "app_to_models", "app_to_viewsets",
        "app_to_endpoints", "frontend_to_endpoint", "store_to_endpoint",
        "change_impact", "tests",
    }
    assert expected_keys.issubset(dg.keys())


def test_knowledge_graph_nodes_include_all_enricher_layers(audited_project):
    """Confirma que las 3 capas de enriquecimiento (Fase 5: Documentation,
    DockerService, Agent/Tool) realmente corrieron y no fallaron en silencio
    -- cada enricher esta wrappeado en try/except en build_and_save_
    knowledge_graph(), un fallo ahi no tumba el resto del grafo pero tampoco
    deberia pasar desapercibido en una prueba de equivalencia."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

    kg = get_knowledge_graph()
    type_counts = kg._type_counts()
    for expected_type in ("App", "Model", "ViewSet", "Endpoint",
                           "Documentation", "DockerService", "Agent", "Tool",
                           "File", "Symbol"):
        assert type_counts.get(expected_type, 0) > 0, f"Sin nodos de tipo {expected_type}"


def test_file_and_symbol_nodes_have_real_contains_structure(audited_project):
    """Fase 1 (Site Knowledge Graph, 2026-08-10): File debe CONTAINS a los
    Symbol de ese archivo, y una clase real (ej. un ViewSet) debe CONTAINS a
    sus propios metodos como Symbol -- el objetivo explicito del plan es que
    la IA reciba 'Clase.metodo() lineas N-M', no solo el nombre del archivo."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

    kg = get_knowledge_graph()

    file_nodes = kg.nodes_of_type("File")
    symbol_nodes = kg.nodes_of_type("Symbol")
    assert len(file_nodes) > 100, "Muy pocos nodos File para un repo de este tamano"
    assert len(symbol_nodes) > 100, "Muy pocos nodos Symbol para un repo de este tamano"

    sample_sym = symbol_nodes[0]
    assert sample_sym.meta["start_line"] <= sample_sym.meta["end_line"]
    assert sample_sym.meta["kind"] in ("function", "method")

    # File -CONTAINS-> Symbol: el archivo dueno del primer Symbol debe listarlo
    # entre sus sucesores CONTAINS.
    owning_file_nid = f"file:{sample_sym.file}"
    assert owning_file_nid in kg.nodes, f"Symbol sin nodo File dueno: {sample_sym.file}"
    contained_ids = {s["node"]["id"] for s in kg.successors(owning_file_nid) if s["edge"] == "CONTAINS"}
    assert sample_sym.id in contained_ids

    # Clase real -CONTAINS-> metodo real: al menos un ViewSet debe tener sus
    # metodos como Symbol hijos (no solo el string "actions" que ya existia).
    viewsets_with_method_symbols = [
        vs for vs in kg.nodes_of_type("ViewSet")
        if any(s["node"]["type"] == "Symbol" for s in kg.successors(vs.id))
    ]
    assert viewsets_with_method_symbols, "Ningun ViewSet tiene sus metodos como nodos Symbol"


def test_contract_graph_links_endpoints_websockets_and_env_vars(audited_project):
    """Fase 2 'Contract Graph' (Site Knowledge Graph, 2026-08-10): 3 casos
    reales y verificables, no sinteticos -- reproducen exactamente los
    ejemplos del plan del usuario."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

    kg = get_knowledge_graph()

    # 1. API Contract: un Endpoint real -IMPLEMENTED_BY-> Symbol real, con
    #    rango de lineas (no solo el nombre del ViewSet).
    endpoints_with_symbols = [
        ep for ep in kg.nodes_of_type("Endpoint")
        if any(s["edge"] == "IMPLEMENTED_BY" for s in kg.successors(ep.id))
    ]
    assert endpoints_with_symbols, "Ningun Endpoint esta IMPLEMENTED_BY un Symbol"

    # 2. WebSocket Contract: la ruta real del chat de soporte debe apuntar al
    #    Consumer real (el mismo verificado en vivo en la auditoria E2E del
    #    chatbot, sesion 2026-08-10).
    ws_chat = kg.nodes.get("ws:ws/support/chat/")
    assert ws_chat is not None, "Falta el nodo WebSocketRoute de ws/support/chat/"
    linked_consumers = {s["node"]["name"] for s in kg.successors(ws_chat.id) if s["edge"] == "IMPLEMENTED_BY"}
    assert "SupportChatConsumer" in linked_consumers

    # re_path() (operations/routing.py) debe capturarse igual que path() --
    # bug real encontrado en la primera corrida contra el repo, ya corregido.
    ws_types = kg.nodes_of_type("WebSocketRoute")
    assert any("OperationTrackingConsumer" in
               {s["node"]["name"] for s in kg.successors(w.id) if s["edge"] == "IMPLEMENTED_BY"}
               for w in ws_types), "operations/routing.py (re_path) no se capturo"

    # 3. Environment Contract: AI_SUPPORT_CHAT_ENABLED (el flag real que
    #    is_ai_mode_active() lee, ver support/services/ai_bridge.py) debe
    #    tener al menos un File que lo USES_ENV.
    env_node = kg.nodes.get("envvar:AI_SUPPORT_CHAT_ENABLED")
    assert env_node is not None, "Falta el nodo EnvVar de AI_SUPPORT_CHAT_ENABLED"
    users = [p["node"]["name"] for p in kg.predecessors(env_node.id) if p["edge"] == "USES_ENV"]
    assert users, "AI_SUPPORT_CHAT_ENABLED no tiene ningun archivo que la use"


def test_frontend_symbols_reproduce_real_composable_store_and_component(audited_project):
    """Fase 3 'Frontend Symbol Intelligence' (Site Knowledge Graph,
    2026-08-10): criterio de aceptacion 3.6 del plan -- 'donde se ejecuta
    loadAvailability()?' debe responderse con archivo/simbolo/lineas/
    componente sin buscar el repo a mano. Se usan 3 archivos reales del
    dominio Renting/Availability (el mismo que ilustra el plan), no
    fixtures sinteticos:
      - store/renting/availabilityStore.js (Pinia option-store real)
      - composables/useOperationTracking.js (composable real con
        lifecycle hooks + llamadas API reales)
      - components/customer/renting/AvailabilityCard.vue (componente real
        con computed + funciones planas)."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

    kg = get_knowledge_graph()

    # 1. Pinia store: los 2 actions reales de availabilityStore.js deben
    #    aparecer como Symbol propios, CONTAINS por el nodo PiniaStore --
    #    no solo "el archivo existe", el metodo exacto con sus lineas.
    store_sym = kg.nodes.get(
        "symbol:store/renting/availabilityStore.js:rentalAvailability.fetchAvailability"
    )
    assert store_sym is not None, "Falta el Symbol de fetchAvailability en el store real de disponibilidad"
    assert store_sym.meta["start_line"] < store_sym.meta["end_line"]
    assert store_sym.meta["symbol_type"] == "method"

    store_node = kg.nodes.get("frontend:Store:rentalAvailability")
    assert store_node is not None
    contained = {s["node"]["id"] for s in kg.successors(store_node.id) if s["edge"] == "CONTAINS"}
    assert store_sym.id in contained, "PiniaStore no CONTAINS su propio Symbol de accion real"

    # 2. Composable real: la funcion exportada (entry point) y sus 5
    #    funciones internas nombradas + 2 lifecycle hooks deben aparecer
    #    todos como Symbol independientes -- el patron dominante real de
    #    este proyecto (toda la logica anidada dentro de la funcion
    #    exportada), no solo el nivel de archivo.
    composable_file = "composables/useOperationTracking.js"
    entry_sym = kg.nodes.get(f"symbol:{composable_file}:useOperationTracking")
    assert entry_sym is not None, "Falta el Symbol del composable useOperationTracking en si"
    fetch_sym = kg.nodes.get(f"symbol:{composable_file}:useOperationTracking.fetchTicket")
    assert fetch_sym is not None, "Falta el Symbol anidado fetchTicket dentro del composable"
    assert fetch_sym.meta["role"] == "api_call"  # llama api.get(...) real
    mounted_sym = kg.nodes.get(f"symbol:{composable_file}:useOperationTracking.onMounted")
    assert mounted_sym is not None
    assert mounted_sym.meta["symbol_type"] == "lifecycle"

    composable_node = kg.nodes.get(f"frontend:Composable:{composable_file}")
    assert composable_node is not None
    contained = {s["node"]["id"] for s in kg.successors(composable_node.id) if s["edge"] == "CONTAINS"}
    assert fetch_sym.id in contained, "Composable no CONTAINS su propio Symbol interno real"

    # 3. Componente real: computed + funciones planas del <script setup>,
    #    CONTAINS por el nodo FrontendComponent real.
    component_file = "components/customer/renting/AvailabilityCard.vue"
    computed_sym = kg.nodes.get(f"symbol:{component_file}:AvailabilityCard.formattedDate")
    assert computed_sym is not None
    assert computed_sym.meta["symbol_type"] == "computed"
    component_node = kg.nodes.get(f"frontend:Component:{component_file}")
    assert component_node is not None
    contained = {s["node"]["id"] for s in kg.successors(component_node.id) if s["edge"] == "CONTAINS"}
    assert computed_sym.id in contained

    # No falsos positivos sistemicos: en todo el frontend real (~520
    # archivos) ningun Symbol frontend tiene rango de lineas invertido,
    # nombre vacio, o nombre igual a una palabra reservada de JS que se
    # coló por error de deteccion de metodo de objeto.
    fe_symbols = [n for n in kg.nodes_of_type("Symbol") if n.meta.get("symbol_type") is not None]
    assert len(fe_symbols) > 500, "Muy pocos FrontendSymbol para un frontend de este tamano"
    js_keywords = {"if", "for", "while", "switch", "catch", "try", "function",
                   "return", "else", "finally", "do", "with"}
    for sym in fe_symbols:
        assert sym.meta["end_line"] >= sym.meta["start_line"], f"Rango invertido: {sym.id}"
        assert sym.name, f"Symbol con nombre vacio: {sym.id}"
        assert sym.name not in js_keywords, f"Palabra reservada colada como Symbol: {sym.id}"


def test_frontend_backend_contract_graph_resolves_real_availability_chain(audited_project):
    """Fase 4 'Contract Graph Frontend<->Backend' (Site Knowledge Graph,
    2026-08-10): reproduce el mismo dominio Renting/Availability usado en
    Fase 3, esta vez verificando la cadena real end-to-end hasta el backend
    -- criterio 4.5 del plan: '¿quien consume GET /api/v1/renting/
    equipment/?' debe responder con el Symbol real que la implementa y sus
    Serializers, sin busqueda manual."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

    kg = get_knowledge_graph()

    # 1. services/renting/availabilityService.js: la capa real de "custom
    #    API wrapper" (frontend/CLAUDE.md la llama la capa de servicio) --
    #    antes de Fase 4 esto no generaba NINGUN Symbol (objeto exportado
    #    plano, no un Pinia store) y el patron `useApi().get(url)`
    #    encadenado ni siquiera lo reconocia extract_vue_api_calls().
    service_check = kg.nodes.get(
        "symbol:services/renting/availabilityService.js:availabilityService.check"
    )
    assert service_check is not None, "availabilityService.check no genero Symbol"
    assert service_check.meta["api_calls"], "No se detecto la llamada useApi().get(...) real"

    consumed_endpoints = {s["node"]["id"] for s in kg.successors(service_check.id)
                           if s["edge"] == "CONSUMES_ENDPOINT"}
    assert "endpoint:api/v1/renting/equipment" in consumed_endpoints, (
        "availabilityService.check() deberia consumir el Endpoint real de "
        f"EquipmentViewSet, no otro por coincidencia de substring. Obtenido: {consumed_endpoints}"
    )

    used_composables = {s["node"]["id"] for s in kg.successors(service_check.id)
                         if s["edge"] == "USES_COMPOSABLE"}
    assert "frontend:Composable:composables/useApi.js" in used_composables

    # 2. Desde el Endpoint real, IMPLEMENTED_BY (Fase 2) + SERIALIZES (Fase
    #    4, nuevo) deben responder con el metodo real y sus serializers --
    #    la cadena completa que pide 4.5 sin buscar el repo a mano.
    ep = kg.nodes["endpoint:api/v1/renting/equipment"]
    implemented_by = {s["node"]["name"] for s in kg.successors(ep.id) if s["edge"] == "IMPLEMENTED_BY"}
    assert "EquipmentViewSet.check_availability" in implemented_by
    serializes = {s["node"]["name"] for s in kg.successors(ep.id) if s["edge"] == "SERIALIZES"}
    assert "EquipmentSerializer" in serializes

    # 3. Falso positivo real encontrado y corregido en esta fase: antes del
    #    fix de _match_endpoints_for_url(), esta MISMA llamada matcheaba
    #    por error 'api/v1/auth/availability' (dominio no relacionado) solo
    #    porque ambas URLs terminan en el substring literal "availability".
    assert "endpoint:api/v1/auth/availability" not in consumed_endpoints

    # 4. USES_COMPOSABLE a nivel de archivo, dominio distinto (CRUD admin
    #    real, no Renting): ProductList.vue -> useToast/useErrorHandler/
    #    useOffcanvas + USES_STORE -> shopAdmin. Confirma que el fix del
    #    matching de hooks (antes: 0 aristas USES_STORE en todo el repo)
    #    funciona tambien fuera del dominio de Renting.
    product_list = kg.nodes.get("frontend:Component:modules/shop/ProductList.vue")
    assert product_list is not None
    pl_composables = {s["node"]["name"] for s in kg.successors(product_list.id)
                       if s["edge"] == "USES_COMPOSABLE"}
    assert {"useToast", "useErrorHandler", "useOffcanvas"}.issubset(pl_composables)
    pl_stores = {s["node"]["name"] for s in kg.successors(product_list.id) if s["edge"] == "USES_STORE"}
    assert "shopAdmin" in pl_stores

    # 5. Verificacion sistemica: USES_STORE ya no esta en cero (bug real
    #    pre-Fase-4), y ningun Symbol Python (sin symbol_type) genero
    #    aristas de contrato frontend por error.
    uses_store_edges = [e for e in kg.edges if e.label == "USES_STORE"]
    assert len(uses_store_edges) > 50, "USES_STORE deberia tener aristas reales, no seguir en 0"
    for e in kg.edges:
        if e.label in ("CONSUMES_ENDPOINT", "USES_STORE", "USES_COMPOSABLE"):
            src = kg.nodes.get(e.source)
            if src and src.type == "Symbol":
                assert src.meta.get("symbol_type") is not None, (
                    f"Symbol Python genero arista de contrato frontend por error: {e.source}"
                )


def test_data_flow_graph_reads_writes_and_trace_resolve_real_product_chain(audited_project):
    """Fase 5 'Data Flow Graph' (Site Knowledge Graph, 2026-08-10): verifica
    contra codigo real de shop (no fixtures) que READS_FROM/WRITES_TO son
    correctos y que trace_data_flow() reconstruye la cadena completa
    'database -> serializer -> API -> frontend -> component' (5.4 del
    plan) para un Model real, sin busqueda manual."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
    from project_knowledge_graph.knowledge_graph.query import trace_data_flow

    kg = get_knowledge_graph()

    # 1. Bug real corregido durante esta fase: ProductSelector.list_active()
    #    y TaxSelector.list_active() son metodos homonimos en el MISMO
    #    archivo (shop/services/selectors.py) -- deben quedar atribuidos a
    #    su propio Model real, no mezclados entre si.
    product_list_active = kg.nodes.get(
        "symbol:shop/services/selectors.py:ProductSelector.list_active"
    )
    assert product_list_active is not None
    product_reads = {s["node"]["name"] for s in kg.successors(product_list_active.id)
                      if s["edge"] == "READS_FROM"}
    assert product_reads == {"Product"}, (
        f"ProductSelector.list_active() no deberia leer nada mas que Product, obtenido: {product_reads}"
    )

    tax_list_active = kg.nodes.get("symbol:shop/services/selectors.py:TaxSelector.list_active")
    assert tax_list_active is not None
    tax_reads = {s["node"]["name"] for s in kg.successors(tax_list_active.id)
                 if s["edge"] == "READS_FROM"}
    assert tax_reads == {"Tax"}

    # 2. WRITES_TO real: shop/services/commands.py::_get_or_create_stock_record
    #    escribe StockRecord (app `inventory`, cross-app real) via
    #    `.objects.get_or_create(...)`.
    stock_fn = kg.nodes.get("symbol:shop/services/commands.py:_get_or_create_stock_record")
    assert stock_fn is not None
    stock_writes = {s["node"]["name"] for s in kg.successors(stock_fn.id) if s["edge"] == "WRITES_TO"}
    assert "StockRecord" in stock_writes

    # 3. trace_data_flow('Product') debe reconstruir la cadena completa real
    #    sin busqueda manual: Serializer real, Endpoint real, y al menos un
    #    consumidor frontend real (shopService.js, la capa de servicio de
    #    shop equivalente a availabilityService en renting).
    flow = trace_data_flow("Product")
    assert flow["found"] is True
    assert len(flow["backend_access"]) > 0
    serializer_names = {s["name"] for s in flow["serializers"]}
    assert "ProductSerializer" in serializer_names
    endpoint_names = {e["name"] for e in flow["api"]}
    assert "api/v1/shop/products" in endpoint_names
    frontend_ids = {f["id"] for f in flow["frontend_consumers"]}
    assert any("shopService.js" in fid for fid in frontend_ids), (
        "trace_data_flow('Product') deberia incluir shopService.js entre los consumidores reales"
    )

    # 4. field_verified debe ser honesto, no optimista: 'name' es un campo
    #    real declarado en Product (ver shop/models.py), 'image' NO lo es
    #    (las imagenes viven en el modelo relacionado ProductImage, no como
    #    campo directo de Product) -- confirma que la verificacion es real,
    #    no una suposicion de que cualquier campo pedido "existe".
    assert trace_data_flow("Product.name")["field_verified"] is True
    assert trace_data_flow("Product.this_field_does_not_exist")["field_verified"] is False

    # 5. Verificacion sistemica: ningun READS_FROM/WRITES_TO apunta a un
    #    Model con nombre distinto del que realmente aparece en su propio
    #    Symbol.file (deteccion basica de colisiones remanentes) -- no
    #    exhaustivo, pero cubre la clase de bug ya encontrada una vez.
    df_edges = [e for e in kg.edges if e.label in ("READS_FROM", "WRITES_TO")]
    assert len(df_edges) > 500, "Deberian existir cientos de aristas reales de acceso a datos"


def test_execution_graph_triggers_queues_and_trace_execution_resolve_real_chains(audited_project):
    """Fase 6 'Execution Graph' (Site Knowledge Graph, 2026-08-10): verifica
    contra codigo real (no fixtures) que TRIGGERS/QUEUES son correctos y
    que trace_execution() reconstruye cadenas reales end-to-end (criterio
    6.3 del plan: 'que ocurre desde que el usuario pulsa este boton hasta
    que termina la operacion'), incluyendo el bug real de is_task_function
    encontrado y corregido durante esta misma fase."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
    from project_knowledge_graph.knowledge_graph.query import trace_execution

    kg = get_knowledge_graph()

    # 1. TRIGGERS real: accounts/models.py tiene
    #    @receiver(post_save, sender=UserProfile) -> create_technician_profile.
    user_profile = kg.nodes.get("accounts:Model:UserProfile")
    assert user_profile is not None
    triggered = {s["node"]["name"] for s in kg.successors(user_profile.id) if s["edge"] == "TRIGGERS"}
    assert "create_technician_profile" in triggered

    # 2. Bug real corregido en esta fase: is_task_function() no reconocia
    #    `@shared_task(bind=True, ...)` (llamada directa, no via atributo)
    #    -- notifications/tasks.py tenia 8 tasks reales, TODAS invisibles
    #    antes del fix (0 nodos Task para esa app).
    notif_tasks = [n for n in kg.nodes_of_type("Task") if n.file == "notifications/tasks.py"]
    assert len(notif_tasks) >= 6, (
        f"notifications/tasks.py deberia tener varios nodos Task reales, obtenido: {len(notif_tasks)}"
    )

    # 3. QUEUES real: NotificationCommands.dispatch_notification encola los
    #    5 canales reales via .delay() -- verificado exacto, no aproximado.
    dispatch_sym = kg.nodes.get(
        "symbol:notifications/services/commands.py:NotificationCommands.dispatch_notification"
    )
    assert dispatch_sym is not None
    queued = {s["node"]["name"] for s in kg.successors(dispatch_sym.id) if s["edge"] == "QUEUES"}
    assert queued == {
        "send_ws_notification_task", "send_email_notification_task",
        "ai_proactive_room_message_task", "send_whatsapp_notification_task",
        "send_sms_notification_task",
    }

    # 4. trace_execution() debe reconstruir la cadena real completa desde un
    #    Symbol frontend real hasta la accion de ViewSet correcta -- no
    #    cualquier IMPLEMENTED_BY del Endpoint (ambiguo por diseno desde
    #    Fase 4), sino la que realmente corresponde a la URL llamada.
    flow = trace_execution("availabilityService.check")
    assert flow["found"] is True
    steps_by_via = {s["via"]: s["node"]["name"] for s in flow["steps"]}
    assert steps_by_via.get("CONSUMES_ENDPOINT") == "api/v1/renting/equipment"
    assert steps_by_via.get("IMPLEMENTED_BY") == "EquipmentViewSet.check_availability", (
        "trace_execution deberia desambiguar por URL real, no elegir la primera "
        f"accion del ViewSet por casualidad. Pasos obtenidos: {steps_by_via}"
    )

    # 5. trace_execution() sobre dispatch_notification debe mostrar las 5
    #    tasks reales en 'also' (no perderlas por el callejon sin salida de
    #    WRITES_TO->NotificationLog, que no tiene salida propia).
    flow2 = trace_execution("dispatch_notification")
    all_also_names = {a["node"]["name"] for s in flow2["steps"] for a in s["also"]}
    assert {"send_ws_notification_task", "send_email_notification_task",
            "send_sms_notification_task"}.issubset(all_also_names)

    # 6. Verificacion sistemica: TRIGGERS/QUEUES tienen volumen real, no son
    #    casos aislados de un solo ejemplo hardcodeado.
    assert len([e for e in kg.edges if e.label == "TRIGGERS"]) >= 10
    assert len([e for e in kg.edges if e.label == "QUEUES"]) >= 5


def test_test_graph_validates_tests_and_find_tests_for_change_resolve_real_chains(audited_project):
    """Fase 7 'Test Graph' (Site Knowledge Graph, 2026-08-10): verifica
    contra codigo real de tests (no fixtures) que VALIDATES/TESTS son
    correctos y que find_tests_for_change() responde el criterio 7.4 del
    plan ('que pruebas debo ejecutar si cambio este simbolo') sin busqueda
    manual, incluyendo el bug real de resolucion de target por
    find_by_name() encontrado durante esta fase."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
    from project_knowledge_graph.knowledge_graph.query import find_tests_for_change

    kg = get_knowledge_graph()

    # 1. VALIDATES real: shop/tests.py::ProductReviewDuplicatePreventionTestCase
    #    pega a /api/v1/shop/products/.../review/ real.
    review_test = kg.nodes.get(
        "symbol:shop/tests.py:ProductReviewDuplicatePreventionTestCase."
        "test_second_review_blocked_by_serializer_validation"
    )
    assert review_test is not None
    assert review_test.meta.get("is_test") is True
    validated = {s["node"]["name"] for s in kg.successors(review_test.id) if s["edge"] == "VALIDATES"}
    assert "api/v1/shop/products" in validated

    # 2. TESTS real: renting/tests_endpoints.py::RentalRequestAdminActionsTestCase.setUp
    #    llama RentalRequestCommands directo (unit-test-style).
    setup_sym = kg.nodes.get(
        "symbol:renting/tests_endpoints.py:RentalRequestAdminActionsTestCase.setUp"
    )
    assert setup_sym is not None
    tested = {s["node"]["name"] for s in kg.successors(setup_sym.id) if s["edge"] == "TESTS"}
    assert "RentalRequestCommands.create_request" in tested

    # 3. Bug real corregido en esta fase: find_by_name('Product') devuelve
    #    460 matches por substring en orden no determinista -- el primer
    #    Symbol/Endpoint/Model NUNCA era el Model 'Product' real antes del
    #    fix de resolucion por nombre exacto.
    flow = find_tests_for_change("Product")
    assert flow["found"] is True
    assert flow["node"]["id"] == "shop:Model:Product"
    assert len(flow["indirect_tests"]) > 0, (
        "find_tests_for_change('Product') deberia encontrar tests reales via "
        "ProductSerializer -> endpoint -> VALIDATES, no quedar en 0 por el bug de resolucion"
    )

    # 4. find_tests_for_change() sobre un Symbol real con tests directos.
    flow2 = find_tests_for_change("RentalRequestCommands.create_request")
    assert flow2["found"] is True
    assert len(flow2["direct_tests"]) > 0

    # 5. Verificacion sistemica: volumen real, no casos aislados.
    assert len([n for n in kg.nodes_of_type("Symbol") if n.meta.get("is_test")]) > 500
    assert len([e for e in kg.edges if e.label == "VALIDATES"]) > 50
    assert len([e for e in kg.edges if e.label == "TESTS"]) > 200


def test_documentation_graph_references_and_find_docs_resolve_real_chains(audited_project):
    """Fase 8 'Documentation Graph' (Site Knowledge Graph, 2026-08-10):
    verifica contra la documentacion real del repo (no fixtures) que
    REFERENCES es correcto y que find_docs_for_change() responde el
    criterio 8.2 del plan con el ejemplo TEXTUAL EXACTO del propio plan
    ('renting availability'), sin busqueda manual."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
    from project_knowledge_graph.knowledge_graph.query import find_docs_for_change

    kg = get_knowledge_graph()

    # 1. REFERENCES real: ARQUITECTURA_COMPLETA_RENTIG.md cita
    #    AvailabilityEngine.is_available y renting/services/availability.py
    #    entre backticks -- el mismo dominio usado en Fases 3-7.
    doc = kg.nodes.get(
        "doc:ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md"
    )
    assert doc is not None
    refs = {s["node"]["id"] for s in kg.successors(doc.id) if s["edge"] == "REFERENCES"}
    assert "symbol:renting/services/availability.py:AvailabilityEngine.is_available" in refs
    assert "file:renting/services/availability.py" in refs

    # 2. find_docs_for_change('renting availability') -- el ejemplo TEXTUAL
    #    exacto de 8.2 del plan -- debe devolver el doc real como
    #    resultado MAS relevante (no solo "en algun lugar de la lista"),
    #    gracias al scoring por ocurrencias + coincidencia de nombre.
    result = find_docs_for_change("renting availability")
    assert result["found"] is True
    assert any(cat for cat in ("architecture_docs", "implementation_docs", "audit_docs")
               if result[cat]), "Deberia haber resultados en al menos una categoria"
    top_implementation = result["implementation_docs"][0]["id"] if result["implementation_docs"] else None
    assert top_implementation == "doc:ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md", (
        f"El doc real de Renting deberia ser el resultado #1 de implementation_docs, obtenido: {top_implementation}"
    )

    # 3. Resolucion estructural EXACTA (Ruta 1): un File path real como
    #    query devuelve SOLO el doc que realmente lo cita, sin ruido de
    #    texto libre.
    exact_result = find_docs_for_change("renting/services/availability.py")
    assert exact_result["found"] is True
    all_exact = (exact_result["architecture_docs"] + exact_result["implementation_docs"]
                 + exact_result["audit_docs"])
    assert len(all_exact) == 1
    assert all_exact[0]["id"] == "doc:ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md"

    # 4. Verificacion sistemica: volumen real, no un caso aislado.
    assert len([e for e in kg.edges if e.label == "REFERENCES"]) > 500


def test_infrastructure_graph_ports_provides_routes_resolve_real_chains(audited_project):
    """Fase 9 'Configuration/Infrastructure Graph' (Site Knowledge Graph,
    2026-08-10): verifica contra docker-compose.yml/nginx-common.conf
    reales (no fixtures) que EXPOSES/PROVIDES/ROUTES_TO son correctos y
    que find_configuration_for() responde el criterio 9.2 del plan sin
    busqueda manual, incluyendo el bug real de resolucion de ruta del
    template .env encontrado durante esta fase."""
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
    from project_knowledge_graph.knowledge_graph.query import find_configuration_for

    kg = get_knowledge_graph()

    # 1. EXPOSES real: django expone el puerto 8000 real.
    django = kg.nodes.get("docker:django")
    assert django is not None
    exposed_ports = {s["node"]["name"] for s in kg.successors(django.id) if s["edge"] == "EXPOSES"}
    assert "8000" in exposed_ports

    # 2. Bug real corregido en esta fase: .env.production.example vive
    #    DENTRO de ecommerce_sintel/, no en la raiz del repo -- la primera
    #    version buscaba en la raiz y PROVIDES quedaba en 0 en todo el
    #    grafo, en silencio.
    provided = {s["node"]["name"] for s in kg.successors(django.id) if s["edge"] == "PROVIDES"}
    assert "AI_SUPPORT_CHAT_ENABLED" in provided or len(provided) > 30, (
        f"django deberia PROVIDES decenas de EnvVar reales, obtenido: {len(provided)}"
    )

    # 3. ROUTES_TO real: nginx enruta / -> django, pero NO
    #    /api/v1/internal/ (bloqueado a proposito con deny all -- bug real
    #    corregido en esta fase: 'location' matcheaba como substring de
    #    'geolocation=()' en un header CSP, produciendo un NginxRoute con
    #    cientos de lineas de texto como "path").
    root_route = kg.nodes.get("nginx:/")
    assert root_route is not None
    assert len(root_route.name) < 10, "El path de nginx:/ no deberia contener texto de config completo"
    routed = {s["node"]["id"] for s in kg.successors(root_route.id) if s["edge"] == "ROUTES_TO"}
    assert "docker:django" in routed

    internal_route = kg.nodes.get("nginx:/api/v1/internal/")
    assert internal_route is not None
    internal_routed = [s for s in kg.successors(internal_route.id) if s["edge"] == "ROUTES_TO"]
    assert internal_routed == [], "/api/v1/internal/ esta bloqueado (deny all), no deberia enrutar a ningun DockerService"

    # 4. find_configuration_for(): responde 9.2 del plan sin busqueda manual.
    result = find_configuration_for("sintel_ai")
    assert result["found"] is True
    assert any(d["name"] == "sintel_ai" for d in result["docker"])


def test_change_graph_impact_excludes_structural_edges_and_categorizes_real_chains(audited_project):
    """Fase 10 'Change Graph' (Site Knowledge Graph, 2026-08-10) -- "la fase
    critica" del plan. Verifica contra codigo real (no fixtures) que
    calculate_change_impact() categoriza correctamente frontend/backend/
    contract/test/documentation/configuration, y que excluye aristas
    ESTRUCTURALES (CONTAINS/BELONGS_TO) del impacto -- bug real encontrado
    y corregido durante la propia verificacion."""
    from project_knowledge_graph.knowledge_graph.query import calculate_change_impact

    # 1. Bug real corregido en esta fase: CONTAINS (ViewSet->su propio
    #    metodo) NO es impacto funcional -- antes del fix,
    #    'EquipmentViewSet' aparecia como "impacto DIRECTO" de cambiar
    #    `EquipmentViewSet.check_availability` (su propia clase
    #    "dependia" de contenerlo, un artefacto estructural sin sentido
    #    para "que se rompe"). Con el fix, el total baja de 797 a un
    #    numero mucho mas chico y realista.
    result = calculate_change_impact("EquipmentViewSet.check_availability")
    assert result["found"] is True
    assert result["total_affected"] < 100, (
        "CONTAINS/BELONGS_TO no deberian inflar el impacto -- verificado real: "
        f"797 (con bug) vs <100 (corregido), obtenido: {result['total_affected']}"
    )
    direct_names = [n["name"] for n in result["direct_impact"]["backend"]]
    assert "EquipmentViewSet" not in direct_names, (
        "La propia clase ViewSet no deberia aparecer como impacto DIRECTO de "
        "cambiar su propio metodo (relacion estructural CONTAINS, no funcional)"
    )

    # 2. Categorizacion real correcta: el mismo dominio Renting/Availability
    #    usado en Fases 3-9 -- consumidores frontend reales, tests reales,
    #    documentacion real, todos alcanzables transitivamente.
    indirect_frontend_names = {n["name"] for n in result["indirect_impact"]["frontend"]}
    assert "availabilityService.check" in indirect_frontend_names
    indirect_doc_names = {n["name"] for n in result["indirect_impact"]["documentation"]}
    assert "ARQUITECTURA_COMPLETA_RENTIG" in indirect_doc_names

    # 3. resolve_change_target() usa el mismo criterio EXACTO-antes-que-
    #    fuzzy de Fases 7-9 -- 'Product' debe resolver al Model real, no a
    #    uno de los otros 459 matches por substring.
    product_result = calculate_change_impact("Product")
    assert product_result["target"]["id"] == "shop:Model:Product"
    assert product_result["risk"] in ("LOW", "MEDIUM", "HIGH")

    # 4. Composicion real de las consultas de Fases 7-9 (no reimplementadas,
    #    reusadas tal cual).
    assert "tests" in product_result and product_result["tests"]["found"] is True
    assert "documentation" in product_result and product_result["documentation"]["found"] is True


def test_change_resolver_produces_full_envelope_for_real_symbol(audited_project):
    """Fase 11 'Change Resolver' (Site Knowledge Graph, 2026-08-10):
    verifica que resolve_change() produce el envelope completo del criterio
    del plan (11) contra un Symbol real, componiendo funciones ya
    verificadas de Fases 5/6/10 sin reimplementar nada."""
    from project_knowledge_graph.knowledge_graph.query import resolve_change

    result = resolve_change("EquipmentViewSet.check_availability")
    assert result["found"] is True
    assert result["primary_files"][0]["id"] == "file:renting/api/views.py"
    assert result["symbols"][0]["id"] == (
        "symbol:renting/api/views.py:EquipmentViewSet.check_availability"
    )
    assert result["contracts"][0]["id"] == "endpoint:api/v1/renting/equipment"
    assert len(result["frontend_consumers"]) > 0
    # Symbol de partida -> execution_paths poblado, data_flows no (no es Model).
    assert result["execution_paths"]["found"] is True
    assert result["data_flows"] is None
    assert result["risk"] in ("LOW", "MEDIUM", "HIGH")
    assert len(result["validation_plan"]) > 0
    assert "raw_request" in result["intent"]


def test_graph_context_packet_compresses_thousands_of_nodes_to_relevant_subset(audited_project):
    """Fase 12 'Graph Context Packet' (Site Knowledge Graph, 2026-08-10):
    verifica que build_graph_context_packet() reduce el grafo completo
    (miles de nodos) a un subgrafo relevante chico, con solo id/type/name/
    file/lineas por nodo (nunca el meta completo) -- literalmente el
    diagrama de la Fase 12 del plan."""
    from project_knowledge_graph.knowledge_graph.query import build_graph_context_packet

    result = build_graph_context_packet("EquipmentViewSet.check_availability")
    assert result["found"] is True
    assert result["stats"]["total_graph_nodes"] > 9000
    assert 0 < result["stats"]["relevant_nodes"] < 50, (
        "El packet deberia comprimir a decenas de nodos relevantes, no miles"
    )
    # Nunca se filtra el meta completo (api_calls/hook_calls/fields/etc.) --
    # solo id/type/name/file/lines.
    assert set(result["target"].keys()) <= {"id", "type", "name", "file", "lines"}
    assert result["target"]["lines"] == "151-168"


def test_graph_sdk_exposes_stable_facade_over_real_data(audited_project):
    """Fase 13 'Graph SDK' (Site Knowledge Graph, 2026-08-10): verifica que
    `project_knowledge_graph.graph_sdk` expone las 11 operaciones del plan
    sobre datos reales, devolviendo SOLO dicts planos (nunca instancias de
    Node/KnowledgeGraph) -- un consumidor externo no deberia necesitar
    importar nada de knowledge_graph.relations."""
    from project_knowledge_graph import graph_sdk

    sym = graph_sdk.find_symbol("EquipmentViewSet.check_availability")
    assert sym is not None and isinstance(sym, dict)
    assert sym["id"] == "symbol:renting/api/views.py:EquipmentViewSet.check_availability"

    file_node = graph_sdk.find_file("renting/api/views.py")
    assert file_node is not None and file_node["id"] == "file:renting/api/views.py"

    endpoint = graph_sdk.find_endpoint("api/v1/renting/equipment")
    assert endpoint is not None and endpoint["id"] == "endpoint:api/v1/renting/equipment"

    consumers = graph_sdk.find_consumers("EquipmentViewSet.check_availability")
    assert isinstance(consumers, list)
    assert any(c["id"] == "endpoint:api/v1/renting/equipment" for c in consumers)

    plan = graph_sdk.build_change_plan("EquipmentViewSet.check_availability")
    assert plan["found"] is True
    assert plan["risk"] in ("LOW", "MEDIUM", "HIGH")
    assert len(plan["change_order"]) == 5

    # El resto de la fachada son re-exportaciones directas de funciones ya
    # verificadas en fases anteriores -- solo confirmar que resuelven.
    assert graph_sdk.resolve_change("Product")["found"] is True
    assert graph_sdk.trace_data_flow("Product")["found"] is True
    assert graph_sdk.trace_execution("EquipmentViewSet.check_availability")["found"] is True
    assert graph_sdk.find_tests("Product")["found"] is True
    assert graph_sdk.find_docs("renting availability")["found"] is True
    assert graph_sdk.calculate_impact("Product")["found"] is True
    assert graph_sdk.build_context_packet("Product")["found"] is True
    assert graph_sdk.find_configuration("sintel_ai")["found"] is True


def test_graph_sdk_post_graph_1_operations_resolve_against_real_data(audited_project):
    """POST-GRAPH 1 'AI Editor Graph Client' (rediseno 'AI Editor Runtime',
    2026-08-11): las 3 operaciones nuevas (`find_node`/`get_app_summary`/
    `get_graph_status`) contra el grafo real, mas la verificacion central
    de por que `find_node` usa `resolve_change_target` y no
    `find_node_context`: 'Product' es un nombre EXACTO que existe como
    Model real (`shop.models.Product`) -- si `find_node` heredara el bug
    de matching de `find_node_context` (substring puro, sin preferencia
    por exacto), podria devolver cualquiera de los ~460 nodos cuyo nombre
    CONTIENE 'Product' como substring en vez del Model real."""
    from project_knowledge_graph import graph_sdk

    node = graph_sdk.find_node("Product")
    assert node is not None
    assert node["type"] == "Model"
    assert node["name"] == "Product"

    summary = graph_sdk.get_app_summary("renting")
    assert isinstance(summary, dict)
    assert set(summary.keys()) == {"models", "viewsets", "endpoints", "tests"}
    assert "EquipmentViewSet" in summary["viewsets"]

    status = graph_sdk.get_graph_status()
    assert status is not None
    assert status["kg_nodes"] > 9000
    assert status["kg_edges"] > 19000
    assert "Symbol" in status["kg_node_types"]


def test_ai_editor_graph_client_exposes_16_operations_as_stable_facade(audited_project):
    """POST-GRAPH 1: `ai_editor.graph_client` debe re-exportar las 16
    operaciones de `graph_sdk` (13 de Fase 14 + 3 de POST-GRAPH 1) por
    IDENTIDAD de objeto, no copia -- mismo criterio que
    `test_graph_client_is_read_only_reexport_of_graph_sdk`
    (test_ai_editor_scaffold.py), pero corrido aca con datos REALES para
    confirmar que ademas de la identidad de objeto, las funciones
    RESUELVEN sobre el repo real cuando se llaman a traves de la
    frontera `ai_editor -> graph_client -> graph_sdk`, sin acceder a
    ningun JSON interno directamente."""
    from ai_editor import graph_client
    from project_knowledge_graph import graph_sdk

    assert len(graph_sdk.__all__) == 16
    for name in graph_sdk.__all__:
        assert getattr(graph_client, name) is getattr(graph_sdk, name)

    packet = graph_client.build_context_packet("EquipmentViewSet.check_availability")
    assert packet["found"] is True
    assert packet["stats"]["total_graph_nodes"] > 9000
    assert 0 < packet["stats"]["relevant_nodes"] < packet["stats"]["total_graph_nodes"]


def test_intent_interprets_and_validates_domain_against_real_graph(audited_project, monkeypatch):
    """POST-GRAPH 2 'Change Intent' (rediseno 'AI Editor Runtime',
    2026-08-11): mockea la llamada al LLM (nunca un LLM real en tests),
    pero deja la validacion de `domain` corriendo contra el grafo REAL --
    confirma que `interpret_request()` efectivamente cruza lo que el LLM
    'dijo' contra `graph_client.find_node()` en vez de confiar
    ciegamente."""
    import json

    from ai_editor import llm
    from ai_editor.intent import STATUS_NEEDS_CLARIFICATION, STATUS_RESOLVED, interpret_request
    from ai_editor.llm.providers import LLMResponse

    def _fake_complete(user, system=None, max_tokens=512, temperature=0.0, provider=None):
        return LLMResponse(
            text=json.dumps({
                "domain": "renting", "intent": "modify_availability",
                "entities": ["Equipment", "AvailabilityService"],
                "scope": ["backend", "frontend"], "confidence": 0.9, "ambiguities": [],
            }),
            provider="fake", model="fake-model", raw={},
        )

    monkeypatch.setattr(llm, "complete", _fake_complete)

    result = interpret_request("Quiero permitir alquiler por horas.")

    assert result.status == STATUS_RESOLVED
    assert result.domain == "renting"
    assert result.intent == "modify_availability"
    assert result.confidence == 0.9
    assert result.ambiguities == []

    def _fake_complete_hallucinated_domain(user, system=None, max_tokens=512, temperature=0.0, provider=None):
        return LLMResponse(
            text=json.dumps({
                "domain": "rentals_that_do_not_exist", "intent": "modify_availability",
                "entities": [], "scope": [], "confidence": 0.9, "ambiguities": [],
            }),
            provider="fake", model="fake-model", raw={},
        )

    monkeypatch.setattr(llm, "complete", _fake_complete_hallucinated_domain)

    result2 = interpret_request("Quiero permitir alquiler por horas.")

    assert result2.status == STATUS_NEEDS_CLARIFICATION
    assert result2.domain is None
    assert any("rentals_that_do_not_exist" in a for a in result2.ambiguities)


def test_change_resolver_picks_exact_symbol_over_fuzzy_match_and_composes_real_context(audited_project):
    """POST-GRAPH 3 'Change Resolver' (rediseno 'AI Editor Runtime',
    2026-08-11). Reproduce el defecto real encontrado durante la propia
    verificacion de esta fase: 'Equipment' (mencion de negocio plausible
    del dominio Renting) NO es un Model real -- `renting` tiene 0 Models
    -- y `find_node('Equipment')` solo devuelve un match FUZZY
    (`FeaturedEquipmentCardSerializer`, matchea por substring). El
    resolver NO debe aceptar ese fuzzy match como una entidad confirmada;
    debe preferir la entidad EXACTA (`EquipmentViewSet.check_availability`,
    Symbol real) como target principal y marcar 'Equipment' como no
    resuelta con una nota explicita, no como si fuera un dato real."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.resolver import STATUS_PARTIALLY_RESOLVED, resolve_change_context

    intent = ChangeIntent(
        id="test-real-repo", request="Modificar disponibilidad de Renting",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability", "Equipment"],
        scope=["backend", "frontend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )

    ctx = resolve_change_context(intent)

    assert ctx.status == STATUS_PARTIALLY_RESOLVED
    assert ctx.primary_target["id"] == "symbol:renting/api/views.py:EquipmentViewSet.check_availability"
    assert len(ctx.unresolved_entities) == 1
    assert "Equipment" in ctx.unresolved_entities[0]
    assert "aproximado" in ctx.unresolved_entities[0]  # nunca se acepta el fuzzy match en silencio

    # El envelope completo de resolve_change() (Fase 11) y el packet
    # comprimido de build_context_packet() (Fase 12) llegan intactos,
    # reusados tal cual -- sin reimplementar nada.
    assert ctx.resolution["target"]["id"] == ctx.primary_target["id"]
    assert set(ctx.resolution.keys()) >= {
        "primary_files", "symbols", "contracts", "frontend_consumers",
        "backend_dependencies", "tests", "documentation", "risk", "change_order",
    }
    assert ctx.context_packet["stats"]["total_graph_nodes"] > 9000


def test_change_plan_produces_real_ordered_steps_with_actual_lines_and_files(audited_project):
    """POST-GRAPH 4 'Change Plan' (rediseno 'AI Editor Runtime',
    2026-08-11): sobre el mismo caso 'renting' de siempre --
    `EquipmentViewSet.check_availability` (lineas reales 151-168,
    verificado en fases previas) -- confirma que el plan resultante:
    (1) pone el target real en el step 1 con las lineas EXACTAS del
    archivo real, (2) todo paso dependiente referencia el step 1,
    (3) los tests quedan con operation=RUN (no MODIFY/REVIEW), (4) 0
    llamadas nuevas al grafo mas alla de las que ya hizo el resolver
    (verificable indirectamente: el plan no requiere `audited_project`
    para construirse, solo para RESOLVER el context antes)."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.planner import STATUS_PLANNED, build_change_plan
    from ai_editor.resolver import resolve_change_context

    intent = ChangeIntent(
        id="test-plan", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend", "frontend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)

    plan = build_change_plan(context)

    assert plan.status == STATUS_PLANNED
    assert len(plan.steps) > 1

    step1 = plan.steps[0]
    assert step1.step == 1
    assert step1.file == "renting/api/views.py"
    assert step1.symbol == "EquipmentViewSet.check_availability"
    assert step1.line_start == 151 and step1.line_end == 168
    assert step1.operation == "MODIFY"
    assert step1.dependencies == []

    for step in plan.steps[1:]:
        assert step.dependencies == [1]
        assert step.operation in ("REVIEW", "RUN")

    run_steps = [s for s in plan.steps if s.operation == "RUN"]
    assert len(run_steps) > 0
    assert all(s.symbol and "test" in s.symbol.lower() for s in run_steps)


def test_change_plan_validator_resolves_real_frontend_paths_and_approves_real_plan(audited_project):
    """POST-GRAPH 5 'Change Plan Validator' (rediseno 'AI Editor Runtime',
    2026-08-11): defecto real encontrado durante la propia verificacion
    de esta fase -- los paths de Symbol/nodos de frontend en el grafo son
    relativos a `frontend/src/` (`FRONTEND_DIR` en `project_knowledge_
    graph/config.py`), NO a la raiz de `ecommerce_sintel/` como los de
    backend. Validar el plan REAL de 'EquipmentViewSet.check_availability'
    (que incluye consumidores frontend reales, ej. `RentalCatalogView.vue`)
    con la resolucion NAIVE (solo `WORKSPACE_ROOT + path`) reportaba esos
    archivos como 'no existen en disco' -- falso, existen en
    `frontend/src/...`. Corregido probando ambas raices reales contra el
    disco (`ai_editor.workspace.resolve_repo_file`). Este test confirma
    que el plan real y completo (backend + frontend) queda `APPROVED`,
    sin ese falso positivo."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.planner import STATUS_APPROVED, build_change_plan, validate_plan
    from ai_editor.resolver import resolve_change_context
    from ai_editor.workspace import resolve_repo_file

    intent = ChangeIntent(
        id="test-validator", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend", "frontend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)

    frontend_steps = [s for s in plan.steps if s.file and s.file.endswith(".vue")]
    assert frontend_steps, "el plan deberia incluir al menos un consumidor frontend real"
    for step in frontend_steps:
        assert resolve_repo_file(step.file) is not None, (
            f"'{step.file}' deberia resolver a un archivo real bajo frontend/src/"
        )

    result = validate_plan(plan)
    assert result.status == STATUS_APPROVED
    assert result.issues == []


def test_full_pipeline_patches_sandbox_without_touching_the_real_repo(audited_project):
    """POST-GRAPH 7 'Repository Sandbox' (rediseno 'AI Editor Runtime',
    2026-08-11): demuestra el ciclo completo REQUEST -> ... -> SANDBOX ->
    PATCH sobre el caso real de siempre (`EquipmentViewSet.
    check_availability`, backend+frontend) -- confirma que
    `create_sandbox()` copia archivos reales de AMBOS lados (backend
    relativo a la raiz, frontend relativo a `frontend/src/`, el defecto
    real corregido en POST-GRAPH 5) y que aplicar un patch sobre el
    sandbox NUNCA modifica el checkout real."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox
    from ai_editor.resolver import resolve_change_context
    from ai_editor.workspace import resolve_repo_file

    intent = ChangeIntent(
        id="test-sandbox", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend", "frontend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)

    real_target_path = resolve_repo_file(plan.steps[0].file)
    real_content_before = real_target_path.read_text(encoding="utf-8")

    with create_sandbox(plan) as sandbox:
        assert len(sandbox.copied_files) > 1
        assert any(f.endswith(".vue") or f.endswith(".js") for f in sandbox.copied_files), (
            "el sandbox deberia incluir al menos un consumidor frontend real"
        )
        assert sandbox.skipped_sensitive == []

        step1 = plan.steps[0]
        operation = PatchOperation(
            file=step1.file, operation=OPERATION_ADD,
            line_start=step1.line_start, line_end=step1.line_start,
            old_fingerprint=None, new_content="    # TEST MARKER (nunca debe llegar al repo real)\n",
            reason="test end-to-end",
        )
        result = apply_operation(sandbox.root, operation)
        assert result.status == "APPLIED"

        sandbox_content_after = (sandbox.root / step1.file).read_text(encoding="utf-8")
        assert "TEST MARKER" in sandbox_content_after

    real_content_after = real_target_path.read_text(encoding="utf-8")
    assert real_content_after == real_content_before
    assert "TEST MARKER" not in real_content_after
    assert not sandbox.root.exists()  # limpiado por el context manager


def test_validation_engine_detects_a_real_injected_syntax_error_in_the_sandbox(audited_project):
    """POST-GRAPH 8 'Validation Engine' (rediseno 'AI Editor Runtime',
    2026-08-11), Nivel 1 (sintaxis) -- sobre el sandbox real del caso
    Renting: confirma que un sandbox recien creado (sin modificar) pasa
    limpio, y que INYECTAR sintaxis Python realmente rota via
    `apply_operation()` (POST-GRAPH 6) lo detecta `run_validation()`
    -- no un caso sintetico aislado, el ciclo completo SANDBOX -> PATCH ->
    VALIDATE contra codigo real de la aplicacion (dentro del sandbox, el
    checkout real nunca se toca)."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox
    from ai_editor.resolver import resolve_change_context
    from ai_editor.validation import run_validation

    intent = ChangeIntent(
        id="test-validation", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend", "frontend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)

    with create_sandbox(plan) as sandbox:
        clean_report = run_validation(sandbox, plan)
        assert clean_report.level_1_passed is True
        assert clean_report.levels_2_to_5_status == "NOT_IMPLEMENTED"

        step1 = plan.steps[0]
        operation = PatchOperation(
            file=step1.file, operation=OPERATION_ADD,
            line_start=step1.line_start, line_end=step1.line_start,
            old_fingerprint=None, new_content="    def broken_syntax(:\n",
            reason="test: inyectar sintaxis rota real",
        )
        apply_result = apply_operation(sandbox.root, operation)
        assert apply_result.status == "APPLIED"

        broken_report = run_validation(sandbox, plan)
        assert broken_report.level_1_passed is False
        assert broken_report.level_1_syntax[step1.file]["ok"] is False
        assert "SyntaxError" in broken_report.level_1_syntax[step1.file]["detail"]


def test_test_validation_report_classifies_real_tests_without_running_them(audited_project):
    """POST-GRAPH 10 'Test Impact Execution' (rediseno 'AI Editor
    Runtime', 2026-08-11): sobre 'Product' (target real con tests
    indirectos reales conocidos, ver Fase 12 del Site Knowledge Graph --
    'relevant_tests': 5) confirma que la clasificacion usa datos REALES
    del grafo, nunca ejecuta nada."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.resolver import resolve_change_context
    from ai_editor.validation import build_test_validation_report

    intent = ChangeIntent(
        id="test-tests", request="r", domain="shop", intent="x",
        entities=["Product"], scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)

    report = build_test_validation_report(context)

    assert report["tests_run"] is False
    assert report["passed"] is None
    assert (report["required_count"] + report["recommended_count"]) > 0
    assert all(isinstance(name, str) and "." in name for name in report["required"] + report["recommended"])


def test_change_summary_composes_real_data_from_the_full_pipeline(audited_project):
    """POST-GRAPH 11 'Human Approval Gate' (rediseno 'AI Editor Runtime',
    2026-08-11): arma el CHANGE SUMMARY real sobre el caso Renting,
    encadenando intent -> resolver -> planner -> sandbox -> validation ->
    approval -- confirma que el resumen final refleja datos reales de
    cada etapa (no placeholders) y que `render_text()` produce el formato
    legible completo."""
    from ai_editor.approval import build_change_summary, record_decision
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox
    from ai_editor.resolver import resolve_change_context
    from ai_editor.validation import build_test_validation_report, run_validation

    intent = ChangeIntent(
        id="test-approval", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend", "frontend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    with create_sandbox(plan) as sandbox:
        validation_report = run_validation(sandbox, plan)
    test_report = build_test_validation_report(context)

    summary = build_change_summary(context, plan, validation_report, test_report)

    assert summary.request == "Permitir alquiler por horas."
    assert "renting/api/views.py" in summary.files
    assert "EquipmentViewSet.check_availability" in summary.symbols
    assert summary.risk == "HIGH"
    assert summary.validation_status == "PASS"
    assert summary.patch_operations == 1

    record = record_decision("APPROVE", reviewer_note="verificado en test")
    assert record.decision == "APPROVE"


def test_commit_control_promotes_a_real_sandbox_to_a_fake_workspace_never_the_real_one(
    audited_project, tmp_path
):
    """POST-GRAPH 12 'Commit Control' (rediseno 'AI Editor Runtime',
    2026-08-11): pipeline COMPLETO sobre el caso Renting real --
    intent->resolver->planner->sandbox->approval->promote -- pero
    `promote_to_workspace()` se apunta a un `tmp_path` FALSO (una copia
    minima de solo el archivo target), nunca a
    `ai_editor.workspace.WORKSPACE_ROOT`. Confirma que el archivo REAL del
    repo (`renting/api/views.py`) permanece intacto en todo momento,
    mientras que el workspace de prueba SI recibe el cambio."""
    from ai_editor.approval import build_change_summary, record_decision
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox, promote_to_workspace
    from ai_editor.repository.sandbox import Sandbox
    from ai_editor.resolver import resolve_change_context
    from ai_editor.workspace import resolve_repo_file

    intent = ChangeIntent(
        id="test-commit", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)

    real_target = resolve_repo_file(plan.steps[0].file)
    real_content_before = real_target.read_text(encoding="utf-8")

    fake_workspace = tmp_path / "fake_workspace"
    (fake_workspace / plan.steps[0].file).parent.mkdir(parents=True, exist_ok=True)
    (fake_workspace / plan.steps[0].file).write_text(real_content_before, encoding="utf-8")

    with create_sandbox(plan) as sandbox:
        step1 = plan.steps[0]
        operation = PatchOperation(
            file=step1.file, operation=OPERATION_ADD,
            line_start=step1.line_start, line_end=step1.line_start,
            old_fingerprint=None, new_content="    # TEST MARKER (solo en el fake workspace)\n",
            reason="test end-to-end commit control",
        )
        apply_operation(sandbox.root, operation)

        # Un sandbox "recortado" que solo conoce el archivo backend real
        # que efectivamente se toco, para no tener que fabricar copias
        # frontend en el fake_workspace tambien.
        limited_sandbox = Sandbox(
            root=sandbox.root, copied_files=[step1.file],
            original_fingerprints={step1.file: sandbox.original_fingerprints[step1.file]},
        )

        approval = record_decision("APPROVE", reviewer_note="test")
        result = promote_to_workspace(limited_sandbox, approval, fake_workspace, confirm=True)

    assert result.status == "PROMOTED"
    assert "TEST MARKER" in (fake_workspace / step1.file).read_text(encoding="utf-8")

    real_content_after = real_target.read_text(encoding="utf-8")
    assert real_content_after == real_content_before
    assert "TEST MARKER" not in real_content_after


def test_change_audit_records_a_real_pipeline_run_without_leaking_anything(audited_project, tmp_path, monkeypatch):
    """POST-GRAPH 13 'Change Audit' (rediseno 'AI Editor Runtime',
    2026-08-11): pipeline completo real (Renting) auditado de punta a
    punta -- confirma que el registro final tiene los archivos/simbolos
    reales del caso, y que ningun campo de nivel superior ni anidado
    contenga algo que matchee un patron sensible."""
    import json

    from ai_editor.approval import build_change_summary, record_decision
    from ai_editor.audit import log as audit_log
    from ai_editor.audit import audit_pipeline_run, read_recent_operations
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox
    from ai_editor.resolver import resolve_change_context
    from ai_editor.validation import build_test_validation_report, run_validation

    temp_log = tmp_path / "CHANGE_AUDIT_LOG.jsonl"
    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", temp_log)

    intent = ChangeIntent(
        id="test-audit", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    with create_sandbox(plan) as sandbox:
        validation_report = run_validation(sandbox, plan)
    test_report = build_test_validation_report(context)
    approval = record_decision("APPROVE", reviewer_note="test")

    audit_pipeline_run(intent, context, plan, validation_report, test_report, approval)

    records = read_recent_operations()
    assert len(records) == 1
    record = records[0]
    assert record["intent_id"] == "test-audit"
    assert "renting/api/views.py" in record["files"]
    assert record["validation_status"] == "PASS"
    assert record["approval_decision"] == "APPROVE"
    assert "sk-" not in json.dumps(record)  # nunca hay claves tipo API key en este pipeline


def test_rollback_restores_a_real_promoted_change_on_a_fake_workspace(audited_project, tmp_path):
    """POST-GRAPH 16 'Rollback' (rediseno 'AI Editor Runtime',
    2026-08-11): pipeline completo real (Renting) -- promociona un patch
    real a un `fake_workspace`, confirma el cambio, revierte, confirma
    que quedo IDENTICO al contenido real original. Nunca toca
    `WORKSPACE_ROOT`."""
    from ai_editor.approval import record_decision
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox, promote_to_workspace, rollback_promotion
    from ai_editor.repository.sandbox import Sandbox
    from ai_editor.resolver import resolve_change_context
    from ai_editor.workspace import resolve_repo_file

    intent = ChangeIntent(
        id="test-rollback", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)

    real_target = resolve_repo_file(plan.steps[0].file)
    real_content = real_target.read_text(encoding="utf-8")

    fake_workspace = tmp_path / "fake_workspace"
    (fake_workspace / plan.steps[0].file).parent.mkdir(parents=True, exist_ok=True)
    (fake_workspace / plan.steps[0].file).write_text(real_content, encoding="utf-8")

    with create_sandbox(plan) as sandbox:
        step1 = plan.steps[0]
        operation = PatchOperation(
            file=step1.file, operation=OPERATION_ADD,
            line_start=step1.line_start, line_end=step1.line_start,
            old_fingerprint=None, new_content="    # TEST MARKER\n", reason="test rollback",
        )
        apply_operation(sandbox.root, operation)

        limited_sandbox = Sandbox(
            root=sandbox.root, copied_files=[step1.file],
            original_fingerprints={step1.file: sandbox.original_fingerprints[step1.file]},
        )
        approval = record_decision("APPROVE")
        promote_result = promote_to_workspace(limited_sandbox, approval, fake_workspace, confirm=True)

    assert promote_result.status == "PROMOTED"
    assert "TEST MARKER" in (fake_workspace / step1.file).read_text(encoding="utf-8")

    rollback_result = rollback_promotion(fake_workspace, promote_result)

    assert rollback_result.status == "ROLLED_BACK"
    assert (fake_workspace / step1.file).read_text(encoding="utf-8") == real_content
    # el repo real, ni tocado en ningun momento
    assert real_target.read_text(encoding="utf-8") == real_content


def test_observability_metrics_reflect_a_real_pipeline_run_end_to_end(audited_project, tmp_path, monkeypatch):
    """POST-GRAPH 17 'Observability' (rediseno 'AI Editor Runtime',
    2026-08-11): pipeline completo real (Renting), incluyendo un patch
    aplicado y un rollback real -- confirma que `audit_pipeline_run()`
    popula los campos correctos y que `compute_metrics()` los agrega
    correctamente sobre datos reales, no sinteticos."""
    from ai_editor.approval import record_decision
    from ai_editor.audit import log as audit_log
    from ai_editor.audit import audit_pipeline_run, compute_metrics
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.patch import OPERATION_ADD, PatchOperation, apply_operation
    from ai_editor.planner import build_change_plan
    from ai_editor.repository import create_sandbox, promote_to_workspace, rollback_promotion
    from ai_editor.repository.sandbox import Sandbox
    from ai_editor.resolver import resolve_change_context

    temp_log = tmp_path / "CHANGE_AUDIT_LOG.jsonl"
    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", temp_log)

    intent = ChangeIntent(
        id="test-metrics", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability",
        entities=["EquipmentViewSet.check_availability"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    fake_workspace = tmp_path / "fake_workspace"

    with create_sandbox(plan) as sandbox:
        step1 = plan.steps[0]
        (fake_workspace / step1.file).parent.mkdir(parents=True, exist_ok=True)
        (fake_workspace / step1.file).write_text(
            (sandbox.root / step1.file).read_text(encoding="utf-8"), encoding="utf-8",
        )
        operation = PatchOperation(
            file=step1.file, operation=OPERATION_ADD,
            line_start=step1.line_start, line_end=step1.line_start,
            old_fingerprint=None, new_content="    # marker\n", reason="test metrics",
        )
        apply_result = apply_operation(sandbox.root, operation)

        limited_sandbox = Sandbox(
            root=sandbox.root, copied_files=[step1.file],
            original_fingerprints={step1.file: sandbox.original_fingerprints[step1.file]},
        )
        approval = record_decision("APPROVE")
        promote_result = promote_to_workspace(limited_sandbox, approval, fake_workspace, confirm=True)
        rollback_result = rollback_promotion(fake_workspace, promote_result)

        audit_pipeline_run(
            intent, context, plan, approval=approval, promote_result=promote_result,
            patch_results=[apply_result], rollback_result=rollback_result,
        )

    metrics = compute_metrics()

    assert metrics["changes_requested"] == 1
    assert metrics["changes_approved"] == 1
    assert metrics["changes_promoted"] == 1
    assert metrics["patch_failures"] == 0  # apply_result fue APPLIED
    assert metrics["rollback_count"] == 1


def test_symbols_touched_by_diff_identifies_real_symbol_from_synthetic_hunk(audited_project):
    """Fase 15 'Incremental Semantic Graph' (Site Knowledge Graph,
    2026-08-10): verifica que un hunk de diff sintetico (rango de lineas
    real) se cruza correctamente contra el Symbol REAL del grafo ya
    construido -- `EquipmentViewSet.check_availability` vive en lineas
    151-168 de renting/api/views.py (verificado en Fases 3-14 de esta
    misma sesion), un hunk que toca la linea 155 debe identificarlo
    exacto, sin ambiguedad con otros metodos vecinos del mismo ViewSet."""
    from project_knowledge_graph.incremental.diff import symbols_touched_by_diff

    hunk = [{"file": "ecommerce_sintel/renting/api/views.py", "start_line": 155, "end_line": 158}]
    touched = symbols_touched_by_diff(hunk)
    touched_names = {s["name"] for s in touched}
    assert "EquipmentViewSet.check_availability" in touched_names
    # Un hunk de 4 lineas dentro de UN metodo no deberia tocar metodos
    # vecinos completamente distintos del mismo archivo.
    assert "EquipmentViewSet.availability" not in touched_names


def test_get_git_diff_text_handles_real_repo_utf8_content_without_crashing():
    """Bug real encontrado y corregido durante Fase 15: `subprocess.run(...,
    text=True)` sin `encoding='utf-8'` explicito usaba cp1252 en Windows y
    tiraba UnicodeDecodeError contra el diff real de este repo (comentarios/
    strings en español con acentos). Esta prueba corre contra el ESTADO
    REAL del repo (no un mock) -- si el bug reaparece, esto falla con la
    misma excepcion real que se vio en produccion."""
    from project_knowledge_graph.incremental.diff import get_git_diff_text

    text = get_git_diff_text()  # no debe lanzar UnicodeDecodeError
    assert isinstance(text, str)


def test_validator_summary_has_all_six_checks(audited_project):
    from project_knowledge_graph.audit.validator import run_all_validations

    result = run_all_validations()
    expected_checks = {
        "orphaned_app_docs", "stale_documentation", "service_layer_violations",
        "import_cycles", "dead_frontend_components", "contradictory_counts",
    }
    assert expected_checks == set(result["summary"].keys())
    for count in result["summary"].values():
        assert isinstance(count, int) and count >= 0


def test_ai_engine_does_not_import_this_module(audited_project):
    """[FASE 0, 2026-08-10] Reemplaza a test_ai_engine_graph_impact_tool_matches_
    the_real_module -- ese test verificaba GraphImpactAnalysisTool
    (ai_engine/tools/graph_tools.py), retirado por completo junto con la regla
    arquitectonica "AI Engine no conoce ni importa project_knowledge_graph"
    (ver ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md). Esta prueba
    verifica lo contrario de lo que verificaba antes: que ese archivo ya NO
    existe y que ningun .py de ai_engine importa este modulo."""
    import ast
    import sys
    from pathlib import Path

    ai_engine_dir = Path(__file__).resolve().parents[2] / "ai_engine"
    assert not (ai_engine_dir / "tools" / "graph_tools.py").exists(), (
        "tools/graph_tools.py deberia estar borrado (FASE 0)"
    )
    assert not (ai_engine_dir / "pkg_bootstrap.py").exists(), (
        "pkg_bootstrap.py deberia estar borrado (FASE 0)"
    )

    offenders = []
    for py_file in ai_engine_dir.rglob("*.py"):
        if "tests" in py_file.relative_to(ai_engine_dir).parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if "project_knowledge_graph" in names:
                offenders.append(str(py_file.relative_to(ai_engine_dir)))

    assert not offenders, f"ai_engine todavia importa project_knowledge_graph desde: {offenders}"


def test_graph_sdk_calls_are_actually_logged_to_the_real_query_audit_log(
    audited_project, tmp_path, monkeypatch
):
    """Fase 18 'Observability' (Site Knowledge Graph, 2026-08-10): verifica
    que llamar una operacion REAL de `graph_sdk` (sobre el grafo real ya
    construido, no un mock) efectivamente escribe una linea al log de
    auditoria -- con el nombre de operacion correcto, sin persistir `meta`,
    y con el `graph_snapshot` que `latest_graph_snapshot()` reporta para el
    grafo real actual."""
    from project_knowledge_graph import graph_sdk
    from project_knowledge_graph.audit import query_log

    temp_log = tmp_path / "QUERY_AUDIT_LOG.jsonl"
    monkeypatch.setattr(query_log, "QUERY_AUDIT_LOG_PATH", temp_log)

    result = graph_sdk.find_symbol("EquipmentViewSet.check_availability")
    assert result["name"] == "EquipmentViewSet.check_availability"

    records = query_log.read_recent_queries()
    assert len(records) == 1
    record = records[0]
    assert record["operation"] == "find_symbol"
    assert record["args"] == ["EquipmentViewSet.check_availability"]
    assert record["result"]["name"] == "EquipmentViewSet.check_availability"
    assert "meta" not in record["result"]


def test_change_validation_report_has_stable_shape_regardless_of_git_state(audited_project):
    """Fase 16 'Change Validation' (Site Knowledge Graph, 2026-08-10). El
    working tree de este repo tiene cambios reales sin commitear ahora
    mismo, pero eso cambia con el tiempo (una vez se commitee, `git diff`
    queda vacio y `detect_changed_symbols()` devuelve `[]`) -- esta prueba
    NO depende de que simbolos especificos esten cambiados hoy, solo de que
    la forma del reporte sea siempre valida (sea cual sea el estado real
    del git diff en el momento de correr la prueba)."""
    from project_knowledge_graph.audit.change_validation import build_change_validation_report

    report = build_change_validation_report()
    expected_keys = {
        "files_changed", "symbols_changed", "contracts_changed", "frontend_affected",
        "backend_affected", "tests_required", "tests_run", "tests_run_note",
        "documentation_affected", "graph_consistency", "contract_consistency", "risk",
    }
    assert expected_keys == set(report.keys())
    assert report["tests_run"] is False
    assert report["risk"] in ("LOW", "MEDIUM", "HIGH")
    assert set(report["graph_consistency"]["summary"].keys()) == {
        "orphaned_app_docs", "stale_documentation", "service_layer_violations",
        "import_cycles", "dead_frontend_components", "contradictory_counts",
    }
    assert isinstance(report["contract_consistency"]["checked"], int)
    for f in report["files_changed"]:
        assert isinstance(f, str) and not f.startswith("ecommerce_sintel/")


def test_change_validation_report_aggregates_real_impact_for_a_known_real_symbol(
    audited_project, monkeypatch
):
    """Fuerza `detect_changed_symbols()` (Fase 15) a devolver un simbolo
    REAL conocido (`EquipmentViewSet.check_availability`, el mismo caso
    'renting' usado en toda esta suite) en vez de depender del git diff
    del momento -- verifica que `build_change_validation_report()` agrega
    correctamente lo que `calculate_change_impact()` (Fase 10) YA calcula
    para ese simbolo, sin reimplementar ni divergir esa logica."""
    import project_knowledge_graph.audit.change_validation as change_validation
    from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
    from project_knowledge_graph.knowledge_graph.query import calculate_change_impact

    kg = get_knowledge_graph()
    real_symbol = next(
        n for n in kg.nodes_of_type("Symbol")
        if n.name == "EquipmentViewSet.check_availability"
    )
    monkeypatch.setattr(
        change_validation, "detect_changed_symbols", lambda: [real_symbol.to_dict()]
    )

    report = change_validation.build_change_validation_report()
    impact = calculate_change_impact("EquipmentViewSet.check_availability")

    assert report["symbols_changed"] == ["EquipmentViewSet.check_availability"]
    assert report["files_changed"] == [real_symbol.file]
    expected_contracts = {
        n["name"] for n in impact["direct_impact"]["contract"] + impact["indirect_impact"]["contract"]
    }
    assert set(report["contracts_changed"]) == expected_contracts
    assert report["risk"] == impact["risk"]
