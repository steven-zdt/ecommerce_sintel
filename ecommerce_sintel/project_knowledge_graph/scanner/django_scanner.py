"""
Scanner especifico de Django -- interpreta lo que python_scanner.py extrajo
(clases/imports/AST) en terminos de roles Django reales (modelo, viewset,
serializer, permission, signal, task). Extraido de ai_engine/auditor.py
(Fase 4, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
"""
import ast

from project_knowledge_graph.config import ROLE_PATTERNS


def detect_python_role(rel_path: str) -> str:
    for role, pattern in ROLE_PATTERNS:
        if pattern.search(rel_path.replace("\\", "/")):
            return role
    return "misc"


def is_model_class(bases: list[str]) -> bool:
    model_bases = {"Model", "SintelBaseModel", "AbstractBaseUser",
                   "AbstractUser", "PolymorphicModel"}
    return any(b in model_bases or b.endswith("Model") for b in bases)


def is_viewset_class(bases: list[str]) -> bool:
    viewset_bases = {"ViewSet", "ModelViewSet", "ReadOnlyModelViewSet",
                     "GenericViewSet", "CreateModelMixin", "APIView",
                     "ListAPIView", "RetrieveAPIView", "CreateAPIView",
                     "UpdateAPIView", "DestroyAPIView", "ListCreateAPIView",
                     "RetrieveUpdateDestroyAPIView", "RetrieveUpdateAPIView"}
    return any(b in viewset_bases or "ViewSet" in b or "APIView" in b
               for b in bases)


def is_serializer_class(bases: list[str]) -> bool:
    return any("Serializer" in b for b in bases)


def is_permission_class(bases: list[str]) -> bool:
    return any("Permission" in b or "BasePermission" in b for b in bases)


def is_test_class(bases: list[str]) -> bool:
    """Fase 7 "Test Graph" (Site Knowledge Graph, 2026-08-10): patron real
    verificado en shop/tests.py/renting/tests_endpoints.py -- `class
    XTestCase(APITestCase):`. Cubre unittest/Django/DRF (`TestCase`,
    `APITestCase`, `TransactionTestCase`, `SimpleTestCase`,
    `LiveServerTestCase`, o cualquier base que termine en "TestCase")."""
    test_bases = {"TestCase", "APITestCase", "TransactionTestCase",
                  "SimpleTestCase", "LiveServerTestCase"}
    return any(b in test_bases or b.endswith("TestCase") for b in bases)


def extract_url_patterns(tree: ast.Module) -> list[dict]:
    """Extract router.register() and path() calls from urls.py files."""
    from project_knowledge_graph.scanner.python_scanner import extract_string_value

    patterns = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # router.register(r'prefix', ViewSet, basename='x')
        if (isinstance(func, ast.Attribute) and func.attr == "register"):
            args = node.args
            if len(args) >= 2:
                prefix = extract_string_value(args[0])
                viewset = args[1].id if isinstance(args[1], ast.Name) else str(args[1])
                basename = None
                for kw in node.keywords:
                    if kw.arg == "basename":
                        basename = extract_string_value(kw.value)
                if prefix:
                    patterns.append({"type": "router", "prefix": prefix.strip("^$"),
                                     "viewset": viewset, "basename": basename})
        # path('prefix/', include('app.urls'))
        elif (isinstance(func, ast.Name) and func.id == "path") or \
             (isinstance(func, ast.Attribute) and func.attr == "path"):
            args = node.args
            if len(args) >= 2:
                route = extract_string_value(args[0])
                if route:
                    patterns.append({"type": "path", "route": route})
    return patterns


def extract_websocket_patterns(tree: ast.Module) -> list[dict]:
    """WebSocket Contract (Fase 2, Site Knowledge Graph, 2026-08-10): extrae
    `path(route, XConsumer.as_asgi())` **y** `re_path(regex, XConsumer.as_asgi())`
    de un archivo routing.py de Django Channels -- misma forma que
    extract_url_patterns() para urls.py, pero reconociendo `.as_asgi()` en vez
    de una vista/ViewSet. [CORREGIDO en la primera corrida real, 2026-08-10]
    La version inicial solo reconocia `path()` -- `operations/routing.py`
    (el unico consumer real de operations, `OperationTrackingConsumer`) usa
    `re_path()` con una ruta con parametro (`ticket_uuid`), y quedaba fuera
    del grafo en silencio hasta que se verifico contra el repo real."""
    from project_knowledge_graph.scanner.python_scanner import extract_string_value

    patterns = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.id if isinstance(func, ast.Name) else \
            func.attr if isinstance(func, ast.Attribute) else None
        if func_name not in ("path", "re_path"):
            continue
        args = node.args
        if len(args) < 2:
            continue
        route = extract_string_value(args[0])
        if not route:
            continue
        # Solo es una ruta WebSocket si el segundo argumento es literalmente
        # `Algo.as_asgi()` -- un path()/re_path() de Django "normal" (vista,
        # ViewSet, include(...)) no matchea esto y se descarta aca (ya lo
        # cubre extract_url_patterns() para urls.py).
        consumer_expr = args[1]
        if not (isinstance(consumer_expr, ast.Call)
                and isinstance(consumer_expr.func, ast.Attribute)
                and consumer_expr.func.attr == "as_asgi"):
            continue
        target = consumer_expr.func.value
        consumer_name = None
        if isinstance(target, ast.Name):
            consumer_name = target.id
        elif isinstance(target, ast.Attribute):
            consumer_name = target.attr
        patterns.append({"route": route, "consumer": consumer_name})
    return patterns


def extract_model_fields(cls_node: ast.ClassDef) -> list[dict]:
    """Extract Django model field definitions with FK relations."""
    result = []
    for item in cls_node.body:
        if not isinstance(item, ast.Assign):
            continue
        for target in item.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            value = item.value
            if not isinstance(value, ast.Call):
                continue
            func = value.func
            field_type = ""
            if isinstance(func, ast.Attribute):
                field_type = func.attr
            elif isinstance(func, ast.Name):
                field_type = func.id
            # Capture FK/M2M related model
            related_model = None
            if field_type in ("ForeignKey", "OneToOneField", "ManyToManyField",
                              "GenericRelatedObjectManager"):
                if value.args:
                    first = value.args[0]
                    if isinstance(first, ast.Constant):
                        related_model = first.value
                    elif isinstance(first, ast.Name):
                        related_model = first.id
                    elif isinstance(first, ast.Attribute):
                        related_model = f"{first.value.id}.{first.attr}" if isinstance(first.value, ast.Name) else first.attr
            if not name.startswith("_"):
                result.append({
                    "name": name,
                    "field_type": field_type,
                    "related_model": related_model,
                })
    return result


def _extract_sender_name(keywords) -> str | None:
    for kw in keywords:
        if kw.arg == "sender" and isinstance(kw.value, ast.Name):
            return kw.value.id
    return None


def extract_signal_registrations(tree: ast.Module) -> list[dict]:
    """Deteccion real de signals -- NO depende de que el archivo se llame
    signals.py (ej. el signal de TechnicianProfile vive inline en
    accounts/models.py). Detecta:
      1. @receiver(...) sobre una funcion, en cualquier archivo.
      2. alguna_senal.connect(handler, ...) como llamada, en cualquier archivo.

    [EXTENDIDO Fase 6 "Execution Graph", 2026-08-10] `sender`/`signal_name`
    agregados -- verificado contra `@receiver(post_save, sender=UserProfile)`
    real en accounts/models.py (dispara create_technician_profile). Habilita
    la arista `Model -TRIGGERS-> Signal` en builder.py. Cambio aditivo puro:
    los 2 campos originales (`name`/`trigger`) no cambian de forma, `sender`/
    `signal_name` son `None` cuando no se puede resolver (ej. `.connect()`
    sin kwarg `sender=`), no se rompe ningun consumidor existente."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                dec_func = dec.func if isinstance(dec, ast.Call) else dec
                fname = None
                if isinstance(dec_func, ast.Name):
                    fname = dec_func.id
                elif isinstance(dec_func, ast.Attribute):
                    fname = dec_func.attr
                if fname != "receiver":
                    continue
                sender = signal_name = None
                if isinstance(dec, ast.Call):
                    sender = _extract_sender_name(dec.keywords)
                    if dec.args and isinstance(dec.args[0], ast.Name):
                        signal_name = dec.args[0].id
                found.append({"name": node.name, "trigger": "receiver_decorator",
                              "sender": sender, "signal_name": signal_name})
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "connect" and node.args:
                first = node.args[0]
                handler_name = (first.id if isinstance(first, ast.Name) else
                                 first.attr if isinstance(first, ast.Attribute) else
                                 "connect_call")
                signal_name = func.value.id if isinstance(func.value, ast.Name) else None
                found.append({"name": handler_name, "trigger": "connect_call",
                              "sender": _extract_sender_name(node.keywords),
                              "signal_name": signal_name})
    return found


_TASK_QUEUE_METHODS = {"delay", "apply_async"}


def extract_task_queue_calls(tree: ast.Module) -> list[dict]:
    """Fase 6 "Execution Graph" (Site Knowledge Graph, 2026-08-10): cada uso
    real de `nombre_de_task.delay(...)`/`.apply_async(...)`, atribuido por
    `qualified_name` (mismo esquema que extract_model_manager_usages() de
    Fase 5, mismo motivo: evitar mezclar metodos homonimos de clases
    distintas en el mismo archivo). Verificado contra el patron real de
    `notifications/services/commands.py` (`send_ws_notification_task.
    delay(...)`, `send_email_notification_task.delay(...)`, etc. -- 5 tasks
    reales encoladas desde `dispatch_notification`). Solo reconoce el
    nombre LITERAL de la task (`Name(id=X).delay(...)`) -- no resuelve
    alias de import ni tasks obtenidas dinamicamente (`get_task(x).delay()`
    o similar), consistente con el mismo criterio de Fase 5 (evidencia AST
    directa, no inferencia)."""
    usages: list[dict] = []

    def _scan_func(func, qualified_name: str):
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            call_func = node.func
            if not (isinstance(call_func, ast.Attribute) and call_func.attr in _TASK_QUEUE_METHODS):
                continue
            if not isinstance(call_func.value, ast.Name):
                continue
            usages.append({"qualified_name": qualified_name, "task": call_func.value.id})

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_func(item, f"{node.name}.{item.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_func(node, node.name)

    return usages


# ---- Data Flow Graph (Fase 5, Site Knowledge Graph, 2026-08-10) -----------
#
# Evidencia real (AST) de que una funcion/metodo lee o escribe un Model
# especifico -- el patron `Model.objects.verbo(...)` verificado contra
# shop/services/selectors.py (ProductSelector.list_active: `Product.objects
# .filter(is_active=True)...`) y shop/services/commands.py
# (`StockRecord.objects.get_or_create(...)`, `ProductVariant.objects.
# filter(...).exists()`). Alcance deliberado, documentado (Regla 3: no
# agregar relaciones que no puedan demostrarse):
#   - SI: `Model.objects.verbo(...)` -- el primer accesor inmediato despues
#     de `.objects`, clasificado READ o WRITE segun el verbo.
#   - NO: cadenas donde el verbo de escritura llega DESPUES de un verbo de
#     lectura en la misma expresion (`Product.objects.filter(x=1)
#     .update(y=2)` -- el AST ve el "value" de `.update` como el resultado
#     de `.filter(...)`, no directamente `Product.objects`; requeriria
#     seguir la cadena de llamadas completa, no solo el accesor inmediato).
#   - NO: `instancia.save()`/`.delete()` sobre una variable ya tipada (ej.
#     `variant.stock = x; variant.save()`) -- requeriria inferencia de
#     tipos (que variable es de que Model), fuera de alcance de un scanner
#     AST de una sola pasada sin resolver anotaciones de tipo real.
# Estas 2 omisiones significan que READS_FROM/WRITES_TO es un PISO real
# (subconjunto verificado), no el 100% de los accesos reales -- documentado
# en ARQUITECTURA_COMPLETA_GRAFO.md, no asumido como completo.

_READ_MANAGER_VERBS = {
    "filter", "get", "all", "exclude", "annotate", "aggregate", "exists",
    "count", "first", "last", "values", "values_list", "none", "order_by",
    "select_related", "prefetch_related", "distinct", "only", "defer",
    "iterator", "in_bulk", "latest", "earliest",
}
_WRITE_MANAGER_VERBS = {
    "create", "bulk_create", "bulk_update", "update", "delete",
    "get_or_create", "update_or_create",
}


def extract_model_manager_usages(tree: ast.Module) -> list[dict]:
    """Cada uso real de `Model.objects.verbo(...)` dentro de una funcion o
    metodo, atribuido por `qualified_name` -- MISMO esquema exacto que
    python_scanner.extract_symbols() (`Clase.metodo` / `funcion` de
    modulo), a proposito: [BUG REAL encontrado y corregido, no una
    reescritura preventiva] la primera version atribuia por nombre CRUDO
    de funcion (`func.name` sin clase), lo que mezclaba usos de metodos con
    el MISMO nombre en clases distintas del mismo archivo -- verificado
    contra el repo real: `shop/services/selectors.py` tiene tanto
    `ProductSelector.list_active()` como `TaxSelector.list_active()`, y la
    version con nombre crudo le atribuia acceso a `Tax` tambien a
    `ProductSelector.list_active()` (que nunca menciona `Tax`). Usar
    `qualified_name` para matchear 1:1 contra el Symbol real (ver
    builder.py::_link_model_usages) elimina esa colision por construccion."""
    usages: list[dict] = []

    def _scan_func(func, qualified_name: str):
        for node in ast.walk(func):
            if not isinstance(node, ast.Attribute):
                continue
            verb = node.attr
            if verb not in _READ_MANAGER_VERBS and verb not in _WRITE_MANAGER_VERBS:
                continue
            value = node.value
            if not (isinstance(value, ast.Attribute) and value.attr == "objects"
                    and isinstance(value.value, ast.Name)):
                continue
            usages.append({
                "qualified_name": qualified_name,
                "model": value.value.id,
                "verb": verb,
                "kind": "write" if verb in _WRITE_MANAGER_VERBS else "read",
            })

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_func(item, f"{node.name}.{item.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_func(node, node.name)

    return usages


# ---- Test Graph (Fase 7, Site Knowledge Graph, 2026-08-10) ----------------
#
# Sin node types nuevos (Test/TestSuite/E2ETest/...) -- mismo criterio que
# Fase 3 (Symbol reusado para frontend en vez de un FrontendSymbol aparte):
# un metodo de test YA es un Symbol real (extract_symbols() ya lo captura,
# sea metodo de clase o funcion pytest de modulo) -- lo unico que faltaba
# era MARCARLO como test (meta.is_test, via is_test_class() de arriba +
# convencion de nombre `test_*`) y conectar 2 relaciones reales:
# VALIDATES (Test->Endpoint, via self.client.verbo(url)) y TESTS
# (Test->Symbol, via llamada directa a Clase.metodo dentro del test).

def _extract_url_literal(node) -> str | None:
    """Extrae el string real de una URL, incluyendo f-strings (patron real
    verificado: `f'/api/v1/shop/products/{self.product.uuid}/review/'`) --
    las partes interpoladas (uuid, pk, etc.) se reemplazan por vacio, no se
    intenta resolverlas; el matching posterior contra Endpoint es por
    PREFIJO (ver builder.py::_match_endpoints_for_url, Fase 4), asi que
    conservar solo el prefijo estatico inicial ya es suficiente."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else ""
            for v in node.values
        )
    return None


_TEST_CLIENT_METHODS = {"get", "post", "put", "patch", "delete"}


def extract_api_test_calls(tree: ast.Module) -> list[dict]:
    """VALIDATES: `self.client.verbo(url, ...)` real dentro de un metodo de
    test -- patron DRF `APITestCase`/`Client`, verificado en shop/tests.py.
    Solo reconoce el atributo LITERAL `.client` (el nombre real que usa
    Django/DRF para el test client en `self.client`), no cualquier objeto
    con un metodo `.get()`/`.post()`."""
    calls: list[dict] = []

    def _scan_func(func, qualified_name: str):
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            call_func = node.func
            if not (isinstance(call_func, ast.Attribute) and call_func.attr in _TEST_CLIENT_METHODS):
                continue
            obj = call_func.value
            if not (isinstance(obj, ast.Attribute) and obj.attr == "client"):
                continue
            if not node.args:
                continue
            url = _extract_url_literal(node.args[0])
            if url is None:
                continue
            calls.append({"qualified_name": qualified_name, "method": call_func.attr.upper(), "url": url})

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_func(item, f"{node.name}.{item.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_func(node, node.name)

    return calls


def extract_direct_symbol_calls(tree: ast.Module) -> list[dict]:
    """TESTS: llamadas DIRECTAS `ClaseX.metodo(...)` dentro de un test --
    evidencia real de que ese test ejercita el Symbol directamente (capa
    de Service/Selector/Command), no solo via HTTP. Solo `Name.attr(...)`
    donde `Name` empieza con mayuscula (heuristica: "parece una referencia
    de clase", no una variable de instancia como `self`/`response`) --
    verificado en renting/tests_endpoints.py:
    `RentalRequestCommands.create_request(...)`. No se limita a archivos de
    test (se corre parejo al resto de scanners de esta fase) -- el filtro
    real de "esto es un test" ocurre en builder.py via `meta.is_test`."""
    calls: list[dict] = []

    def _scan_func(func, qualified_name: str):
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            call_func = node.func
            if not isinstance(call_func, ast.Attribute):
                continue
            obj = call_func.value
            if not (isinstance(obj, ast.Name) and obj.id[:1].isupper()):
                continue
            calls.append({
                "qualified_name": qualified_name,
                "target_qualified_name": f"{obj.id}.{call_func.attr}",
            })

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_func(item, f"{node.name}.{item.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_func(node, node.name)

    return calls


def is_task_function(name: str, decorators) -> bool:
    """[CORREGIDO Fase 6 "Execution Graph", 2026-08-10 -- bug real
    encontrado, no una reescritura preventiva] La rama `ast.Call` solo
    reconocia `@algo.shared_task(...)` (decorador via atributo) -- el
    patron REAL y dominante de este proyecto es `@shared_task(bind=True,
    ...)` (llamada directa a un Name, no un Attribute), verificado en
    notifications/tasks.py: 8 funciones decoradas asi, TODAS devolvian
    `False` antes de este fix. Consecuencia real: 0 nodos Task para
    `notifications/tasks.py` en todo el grafo pese a que `role=='task'` ya
    detectaba el archivo correctamente -- la app con mas tasks reales del
    proyecto (notificaciones multi-canal) estaba invisible."""
    for d in decorators:
        if isinstance(d, ast.Name) and d.id in ("shared_task", "task"):
            return True
        if isinstance(d, ast.Attribute) and d.attr in ("task", "shared_task"):
            return True
        if isinstance(d, ast.Call):
            func = d.func
            if isinstance(func, ast.Name) and func.id in ("shared_task", "task"):
                return True
            if isinstance(func, ast.Attribute) and func.attr in ("task", "shared_task"):
                return True
    return False
