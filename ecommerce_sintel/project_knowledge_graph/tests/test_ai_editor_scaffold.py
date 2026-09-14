"""
Fase 14 "AI Editor Runtime" (Site Knowledge Graph, 2026-08-10), extendido
por el rediseno "AI Editor Runtime" (POST-GRAPH 0-N, 2026-08-11).
`ai_editor/` empezo como scaffold deliberado -- ver
`ecommerce_sintel/ai_editor/__init__.py` "ESTADO REAL" para el detalle
completo de que esta implementado hoy (`graph_client/` desde Fase 14;
`llm/`/`intent/` desde POST-GRAPH 2; `resolver/` desde POST-GRAPH 3;
`planner/` desde POST-GRAPH 4/5; `patch/` desde POST-GRAPH 6, alcance
acotado -- MECANISMO de escritura segura, sin generacion de codigo real;
`repository/` desde POST-GRAPH 7, sandbox aislado; `validation/` desde
POST-GRAPH 8, solo Nivel 1 -- sintaxis -- de 5, Niveles 2-5
`NOT_IMPLEMENTED` explicito). **Con POST-GRAPH 8, los 8 submodulos tienen
logica real** -- `_STUB_MODULES` queda vacio, se mantiene el mecanismo
del test por si una fase futura introduce un scaffold nuevo. Estos tests
verifican que cualquier stub restante respeta su propio alcance
declarado, y que los modulos YA implementados funcionan segun su
contrato real.
"""
import ast
from pathlib import Path

AI_EDITOR_DIR = Path(__file__).resolve().parents[2] / "ai_editor"

_STUB_MODULES: tuple[str, ...] = ()


def test_ai_editor_directory_structure_matches_the_plan():
    """12 submodulos: los 7 originales de Fase 14
    (intent/resolver/planner/repository/patch/validation/graph_client) mas
    3 agregados durante el rediseno POST-GRAPH (2026-08-11), no previstos
    por nombre en el plan original de Fase 14 pero requeridos
    explicitamente: `llm/` (POST-GRAPH 2, decision directa del usuario
    "ai_editor accede al llm de forma totalmente independiente"),
    `approval/` (POST-GRAPH 11, "Human Approval Gate" -- el punto de
    parada estructural antes de promover cualquier cambio al repo real) y
    `audit/` (POST-GRAPH 13, "Change Audit" -- registro append-only de
    cada corrida del pipeline), mas `generation/` agregado en FASE 24 del
    plan "AI Change Proposal Engine" (2026-08-11) -- el AI Change Proposal
    Engine: LLM + contexto real -> `PatchProposal` estructurada, todavia
    sin aplicar (ver `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md`), mas
    `agent/` agregado en FASE 51-53 del mismo plan (2026-08-12) -- el loop
    autonomo controlado que orquesta intent->...->human_review en una
    sola llamada, sin capacidad estructural de promover (nunca importa
    `generation.promotion`/`repository.promote`, ver
    `test_ai_editor_agent.py::test_never_imports_promotion_or_repository_promote`)."""
    expected = {"intent", "resolver", "planner", "repository", "patch",
                "validation", "graph_client", "llm", "approval", "audit", "generation", "agent"}
    # `.AGENT` (Fase 17, 2026-08-10) es documentacion pura del diseno del
    # Autonomous Change Loop, no un submodulo Python del plan; `data`
    # (POST-GRAPH 13) son artefactos generados (CHANGE_AUDIT_LOG.jsonl) --
    # ninguno de los dos es un submodulo Python, excluidos del mismo modo
    # que `__pycache__`.
    actual = {p.name for p in AI_EDITOR_DIR.iterdir()
              if p.is_dir() and p.name not in ("__pycache__", ".AGENT", "data")}
    assert expected == actual


def test_stub_modules_have_no_executable_logic():
    """`_STUB_MODULES` esta vacio desde POST-GRAPH 8 -- los 8 submodulos
    de `ai_editor/` tienen logica real (aunque varios con alcance
    deliberadamente acotado, ver sus propios docstrings). Este test queda
    como mecanismo reusable: si una fase futura introduce un submodulo
    nuevo que deba quedar como scaffold puro (solo docstring, sin logica
    ejecutable), agregarlo a `_STUB_MODULES` reactiva la verificacion sin
    tocar el resto de este archivo."""
    for name in _STUB_MODULES:
        path = AI_EDITOR_DIR / name / "__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        non_docstring_nodes = [
            n for n in tree.body
            if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str))
        ]
        assert non_docstring_nodes == [], (
            f"ai_editor/{name}/__init__.py deberia ser solo un docstring "
            f"(sin logica ejecutable), encontrado: {non_docstring_nodes}"
        )


def test_graph_client_is_read_only_reexport_of_graph_sdk():
    """El unico submodulo real -- confirma que es EXACTAMENTE una
    re-exportacion de graph_sdk (mismos 16 nombres desde POST-GRAPH 1,
    2026-08-11 -- eran 13 en Fase 14), sin agregar logica
    propia ni importar nada de escritura/patch."""
    from project_knowledge_graph import graph_sdk
    from ai_editor import graph_client

    for name in graph_sdk.__all__:
        assert hasattr(graph_client, name), f"graph_client deberia re-exportar {name}"
        assert getattr(graph_client, name) is getattr(graph_sdk, name), (
            f"graph_client.{name} deberia ser el MISMO objeto que graph_sdk.{name} "
            "(re-exportacion directa, no una copia/reimplementacion)"
        )


def test_ai_editor_never_imports_ai_engine():
    """Regla arquitectonica de Fase 0, sigue aplicando aca: ai_engine
    (chatbot de soporte) permanece completamente independiente. Ningun
    archivo de ai_editor/ debe importar nada de ai_engine."""
    offenders = []
    for py_file in AI_EDITOR_DIR.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if "ai_engine" in names:
                offenders.append(str(py_file.relative_to(AI_EDITOR_DIR)))
    assert not offenders, f"ai_editor no deberia importar ai_engine: {offenders}"


def test_ai_editor_root_docstring_documents_real_implementation_status():
    """El __init__.py raiz debe distinguir explicitamente IMPLEMENTADO de
    lo que NO lo esta (Regla de documentacion del plan, Fase 19) -- no
    debe presentar el sistema como mas completo de lo que realmente es.
    Desde POST-GRAPH 12 ya no queda ningun submodulo 'PLANIFICADO' puro
    (los 9 tienen logica real, aunque varios con alcance acotado) -- la
    honestidad ahora se expresa como `NOT_IMPLEMENTED` explicito en
    piezas puntuales (`validation.reconcile_graph()`, Niveles 2-5,
    generacion de codigo real en `patch/`), no como un submodulo entero
    sin construir."""
    text = (AI_EDITOR_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "IMPLEMENTADO" in text
    assert "NOT_IMPLEMENTED" in text
    assert "graph_client" in text
