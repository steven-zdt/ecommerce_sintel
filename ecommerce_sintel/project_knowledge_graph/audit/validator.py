"""
Validaciones automaticas sobre el Knowledge Graph -- capacidad que "auditor.py"
nunca tuvo pese al nombre (solo extraia estructura, no evaluaba calidad).
Extraido de ai_engine/graph_validator.py (Fase 9, PLAN_MAESTRO_DE_SEPARACION_
PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).

6 validaciones con evidencia real, sin heuristicas de alto riesgo de falso
positivo:
  1. Documentacion huerfana real     -- doc de Nivel 2 (app conocida) sin
                                         nodo App que lo reciba.
  2. Documentacion desactualizada    -- fecha declarada en el encabezado del
                                         doc mas vieja que el ultimo commit
                                         real que toco el codigo de esa app.
  3. Violacion de Service Layer      -- un selectors.py (deberia ser SOLO
                                         lectura) contiene una escritura real.
  4. Ciclos de import entre Apps     -- SCC (Tarjan) sobre el subgrafo App-App
                                         de aristas IMPORTS reales.
  5. Componentes Vue sin consumidor  -- FrontendComponent/FrontendView sin
                                         ninguna arista USES_COMPONENT entrante
                                         ni uso como component: de una Route.
  6. Conteos contradictorios         -- lo que un doc afirma en prosa vs. lo
                                         que el grafo mide realmente.

Uso: python -m project_knowledge_graph.audit.validator (requiere
KNOWLEDGE_GRAPH.json ya generado).
"""
import ast
import json
import subprocess

from project_knowledge_graph.config import BASE_DIR, KNOWLEDGE_GRAPH_PATH, VALIDATION_REPORT_PATH

REPO_ROOT = BASE_DIR.parent
ECOMMERCE_DIR = BASE_DIR

WRITE_CALL_NAMES = {"save", "create", "delete", "update", "bulk_create",
                     "bulk_update", "get_or_create", "update_or_create"}

UNIT_TO_NODE_TYPE = {"modelo": "Model", "viewset": "ViewSet", "endpoint": "Endpoint"}


# ---------------------------------------------------------------------------
# 1. Documentacion huerfana
# ---------------------------------------------------------------------------

def find_orphaned_app_docs(kg: dict) -> list[dict]:
    """Docs de scope=nivel2 con app asignada pero SIN arista DOCUMENTED_BY
    entrante -- o bien el App real no existe (nombre de app obsoleto/renombrado),
    o bien el doc quedo huerfano por otra razon."""
    documented_targets = {e["target"] for e in kg["edges"] if e["label"] == "DOCUMENTED_BY"}
    app_ids = {n["id"] for n in kg["nodes"] if n["type"] == "App"}

    findings = []
    for n in kg["nodes"]:
        if n["type"] != "Documentation":
            continue
        meta = n.get("meta", {})
        if meta.get("scope") != "nivel2" or not n.get("app"):
            continue
        if n["id"] in documented_targets:
            continue
        expected_app_id = f"app:{n['app']}"
        reason = ("app_no_existe_como_nodo_App" if expected_app_id not in app_ids
                  else "razon_desconocida_revisar_manualmente")
        findings.append({"doc": n["file"], "app_declarada": n["app"], "razon": reason})
    return findings


# ---------------------------------------------------------------------------
# 2. Documentacion desactualizada
# ---------------------------------------------------------------------------

def _last_commit_date_for_path(rel_path: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short", "--", rel_path],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=15,
        )
        date = out.stdout.strip()
        return date or None
    except (OSError, subprocess.SubprocessError):
        return None


def find_stale_documentation(kg: dict) -> list[dict]:
    """Compara la fecha declarada en el encabezado del doc contra la fecha del
    ultimo commit real que toco el directorio de esa app (excluyendo el propio
    doc). Solo aplica a docs de Nivel 2 con fecha detectada Y app real."""
    app_dirs = {n["app"] for n in kg["nodes"] if n["type"] == "App"}
    findings = []

    for n in kg["nodes"]:
        if n["type"] != "Documentation":
            continue
        meta = n.get("meta", {})
        declared = meta.get("declared_date")
        app = n.get("app")
        if meta.get("scope") != "nivel2" or not declared or app not in app_dirs:
            continue

        # ultimo commit del codigo de la app, no de la carpeta .AGENT/docs
        code_rel = f"ecommerce_sintel/{app}" if app != "frontend" and app != "ai_engine" \
            else ("ecommerce_sintel/frontend/src" if app == "frontend" else "ecommerce_sintel/ai_engine")
        last_code_commit = _last_commit_date_for_path(code_rel)
        if not last_code_commit:
            continue

        if last_code_commit > declared:
            findings.append({
                "doc": n["file"],
                "fecha_declarada": declared,
                "ultimo_commit_real_del_codigo": last_code_commit,
                "dias_de_atraso_aprox": None,  # str dates, no se calcula delta exacto aqui
            })
    return findings


# ---------------------------------------------------------------------------
# 3. Violaciones de Service Layer (Command dentro de selectors.py)
# ---------------------------------------------------------------------------

def _contains_write_call(node: ast.AST) -> list[str]:
    hits = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in WRITE_CALL_NAMES:
                hits.append(f".{sub.func.attr}(")
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in sub.decorator_list:
                dec_name = dec.attr if isinstance(dec, ast.Attribute) else \
                    (dec.id if isinstance(dec, ast.Name) else None)
                if dec_name == "atomic":
                    hits.append("@transaction.atomic")
    return hits


def find_service_layer_violations() -> list[dict]:
    """AST real (no heuristica de nombre) sobre cada selectors.py del proyecto."""
    findings = []
    if not ECOMMERCE_DIR.exists():
        return findings

    for selectors_file in sorted(ECOMMERCE_DIR.glob("*/services/selectors.py")):
        try:
            tree = ast.parse(selectors_file.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue

        rel = str(selectors_file.relative_to(REPO_ROOT)).replace("\\", "/")
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_"):
                continue
            hits = _contains_write_call(node)
            if hits:
                findings.append({
                    "file": rel,
                    "function_or_method": node.name,
                    "line": node.lineno,
                    "escrituras_detectadas": sorted(set(hits)),
                })
    return findings


# ---------------------------------------------------------------------------
# 4. Ciclos de import entre Apps (arista IMPORTS real)
# ---------------------------------------------------------------------------

def find_import_cycles(kg: dict) -> list[dict]:
    """Tarjan SCC sobre el subgrafo App-App de aristas IMPORTS reales -- un
    grupo de apps es una sola unidad circular si y solo si son mutuamente
    alcanzables."""
    adj: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for e in kg["edges"]:
        if e["label"] == "IMPORTS":
            adj.setdefault(e["source"], []).append(e["target"])
            nodes.add(e["source"])
            nodes.add(e["target"])

    index_counter = [0]
    stack: list[str] = []
    lowlink: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == v:
                    break
            sccs.append(component)

    for n in sorted(nodes):
        if n not in index:
            strongconnect(n)

    findings = []
    for comp in sccs:
        if len(comp) < 2:
            continue
        comp_set = set(comp)
        internal_edges = [f"{e['source']} -> {e['target']}" for e in kg["edges"]
                          if e["label"] == "IMPORTS" and e["source"] in comp_set
                          and e["target"] in comp_set]
        findings.append({
            "apps_mutuamente_acopladas": sorted(a.replace("app:", "") for a in comp),
            "cantidad_apps": len(comp),
            "aristas_internas": sorted(internal_edges),
        })
    return sorted(findings, key=lambda f: -f["cantidad_apps"])


# ---------------------------------------------------------------------------
# 5. Componentes Vue sin ningun consumidor (arista USES_COMPONENT real)
# ---------------------------------------------------------------------------

def find_dead_frontend_components(kg: dict) -> list[dict]:
    """FrontendComponent O FrontendView con 0 aristas USES_COMPONENT entrantes
    Y que no es el component: (resuelto) de ninguna Route."""
    used_targets = {e["target"] for e in kg["edges"] if e["label"] == "USES_COMPONENT"}
    route_components = set()
    for n in kg["nodes"]:
        if n["type"] != "Route":
            continue
        meta = n.get("meta", {})
        resolved = meta.get("component_resolved")
        route_components.add(resolved if resolved else meta.get("component"))
    route_components.discard(None)

    findings = []
    for n in kg["nodes"]:
        if n["type"] not in ("FrontendComponent", "FrontendView"):
            continue
        if n["id"] in used_targets:
            continue
        if n["name"] in route_components:
            continue
        findings.append({"file": n["file"], "name": n["name"], "node_type": n["type"]})
    return findings


# ---------------------------------------------------------------------------
# 6. Conteos contradictorios: lo que el doc dice vs. lo que el grafo mide
# ---------------------------------------------------------------------------

def find_contradictory_counts(kg: dict) -> list[dict]:
    """Compara cada 'N modelos/viewsets/endpoints' declarado en un doc de
    Nivel 2 contra el conteo REAL de nodos de ese tipo para esa app en el
    grafo."""
    real_counts: dict[tuple, int] = {}
    for n in kg["nodes"]:
        if n["type"] in UNIT_TO_NODE_TYPE.values() and n.get("app"):
            key = (n["app"], n["type"])
            real_counts[key] = real_counts.get(key, 0) + 1

    findings = []
    for n in kg["nodes"]:
        if n["type"] != "Documentation" or not n.get("app"):
            continue
        for claim in n.get("meta", {}).get("count_claims", []):
            node_type = UNIT_TO_NODE_TYPE.get(claim["unit"])
            if not node_type:
                continue
            real = real_counts.get((n["app"], node_type))
            if real is None or real == claim["count"]:
                continue
            findings.append({
                "doc": n["file"],
                "app": n["app"],
                "afirma": f"{claim['count']} {claim['unit']}(s)",
                "real_en_el_grafo": real,
                "contexto": claim["context"],
            })
    return findings


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_validations() -> dict:
    if not KNOWLEDGE_GRAPH_PATH.exists():
        raise FileNotFoundError(
            f"{KNOWLEDGE_GRAPH_PATH} no existe -- generar el Knowledge Graph primero "
            "(project_knowledge_graph.knowledge_graph.build_and_save_knowledge_graph)"
        )
    kg = json.loads(KNOWLEDGE_GRAPH_PATH.read_text(encoding="utf-8"))

    report = {
        "orphaned_app_docs": find_orphaned_app_docs(kg),
        "stale_documentation": find_stale_documentation(kg),
        "service_layer_violations": find_service_layer_violations(),
        "import_cycles": find_import_cycles(kg),
        "dead_frontend_components": find_dead_frontend_components(kg),
        "contradictory_counts": find_contradictory_counts(kg),
    }
    report["summary"] = {k: len(v) for k, v in report.items()}
    return report


def _safe(s: str) -> str:
    """La consola de Windows (cp1252) no puede imprimir todo UTF-8. Sanea
    solo para stdout; el JSON del reporte (UTF-8 real) no se toca."""
    return s.encode("ascii", errors="replace").decode("ascii")


if __name__ == "__main__":
    result = run_all_validations()
    VALIDATION_REPORT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Graph Validator ===\n")

    print(f"1. Documentacion huerfana (app declarada sin nodo App real o sin enlazar): "
          f"{len(result['orphaned_app_docs'])}")
    for f in result["orphaned_app_docs"]:
        print(f"   - {f['doc']}  (app='{f['app_declarada']}', {f['razon']})")

    print(f"\n2. Documentacion desactualizada (codigo cambio despues de la fecha declarada): "
          f"{len(result['stale_documentation'])}")
    for f in result["stale_documentation"][:15]:
        print(f"   - {f['doc']}  declarada={f['fecha_declarada']}  "
              f"ultimo_commit_codigo={f['ultimo_commit_real_del_codigo']}")
    if len(result["stale_documentation"]) > 15:
        print(f"   ... y {len(result['stale_documentation']) - 15} mas (ver {VALIDATION_REPORT_PATH.name})")

    print(f"\n3. Violaciones de Service Layer (escritura dentro de selectors.py): "
          f"{len(result['service_layer_violations'])}")
    for f in result["service_layer_violations"]:
        print(f"   - {f['file']}:{f['line']} {f['function_or_method']}() -> "
              f"{', '.join(f['escrituras_detectadas'])}")

    print(f"\n4. Grupos de Apps mutuamente acopladas en circulo (SCC, IMPORTS real): "
          f"{len(result['import_cycles'])}")
    for c in result["import_cycles"]:
        print(f"   - {c['cantidad_apps']} apps: {', '.join(c['apps_mutuamente_acopladas'])}")
        for edge in c["aristas_internas"][:8]:
            print(f"       {_safe(edge)}")

    print(f"\n5. Componentes Vue sin consumidor (arista USES_COMPONENT real): "
          f"{len(result['dead_frontend_components'])}")
    for f in result["dead_frontend_components"][:15]:
        print(f"   - {f['file']}")
    if len(result["dead_frontend_components"]) > 15:
        print(f"   ... y {len(result['dead_frontend_components']) - 15} mas (ver {VALIDATION_REPORT_PATH.name})")

    print(f"\n6. Conteos contradictorios (doc dice X, grafo mide Y) -- LEER CON CAUTELA, "
          f"regex sobre prosa libre, revisar cada uno antes de actuar: "
          f"{len(result['contradictory_counts'])}")
    for f in result["contradictory_counts"]:
        print(f"   - {f['doc']}  afirma '{f['afirma']}'  real={f['real_en_el_grafo']}  "
              f"({_safe(f['contexto'])!r})")

    print(f"\nReporte completo: {VALIDATION_REPORT_PATH}")
