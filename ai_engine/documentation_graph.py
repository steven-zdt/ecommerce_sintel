"""
documentation_graph.py - Fase 2 de AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md

Agrega nodos `Documentation` al Knowledge Graph existente (knowledge_graph.py) y
la arista `DOCUMENTED_BY` (App -> Documentation) para las apps que ya tienen
una convencion de nombre de archivo clara ("<app>/.AGENT/docs/*.md").

No reemplaza ni duplica el RAG vectorial (ChromaDB, ver retrievers.py) -- ese
sigue siendo la fuente de contexto narrativo. Este modulo solo estructura
metadata (ruta, fecha declarada, app) como nodos de grafo consultables, algo
que antes no existia (ver AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md §2.4).

Fuentes de documentos indexadas (deliberadamente explicito, no "todo .md del
repo" -- indexar ruido como wizard/fase docs historicos degradaria la senal):
  1. <app>/.AGENT/docs/*.md               -> app = <app>, scope = "nivel2"
  2. frontend/.AGENT/doc/*.md              -> app = "frontend", scope = "nivel2"
  3. ai_engine/.AGENT/*.md                 -> app = "ai_engine", scope = "nivel2"
  4. Documentacion/Arquitectura_general/*.md (+ GOBERNANZA_DOCUMENTAL/)
                                            -> app = None, scope = "arquitectura"
  5. AUDITORIA/*.md                        -> app = None, scope = "auditoria"
  6. docs/.AGENT/*.md                      -> app = None, scope = "auditoria"
"""
import os
import re
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_ecommerce_dir() -> Path:
    """Ver auditor.py::_resolve_base_dir() -- mismo fix. Corrige la deteccion de docs de
    Nivel 2 (viven dentro de ecommerce_sintel/) cuando este modulo corre dentro del
    contenedor sintel_ai (mount real: /workspace, no /ecommerce_sintel). Las fuentes
    cross-app (AUDITORIA/, Documentacion/, docs/.AGENT/, ai_engine/.AGENT/) siguen sin
    estar disponibles en el contenedor -- no hay volumen que las monte, esto NO lo
    arregla (requeriria agregar mounts nuevos a docker-compose.yml, fuera de alcance sin
    aprobacion explicita) -- collect_doc_sources() ya las salta con seguridad via
    `if dir.exists()`, asi que el resultado en-contenedor es parcial pero no incorrecto."""
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    return REPO_ROOT / "ecommerce_sintel"


ECOMMERCE_DIR = _resolve_ecommerce_dir()

# Mismos 21 nombres de app que auditor.py::DJANGO_APPS (mantener sincronizado
# a mano -- import directo crearia un ciclo, ambos archivos son hojas)
KNOWN_APPS = {
    "accounts", "cart", "core", "dashboard", "ecommerce", "inventory", "kyc",
    "marketing", "notifications", "operations", "organization", "orders",
    "payment", "quotes", "renting", "security", "shared", "shop", "support",
    "technical_services", "users",
}

DATE_PATTERNS = [
    re.compile(r"Ultima revision:\s*(\d{4}-\d{2}-\d{2})"),
    re.compile(r"\*\*Fecha:\*\*\s*(\d{4}-\d{2}-\d{2})"),
    re.compile(r"^Fecha:\*?\*?\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE),
    re.compile(r"Actualizado\s+(\d{4}-\d{2}-\d{2})"),
    re.compile(r"Sincronizado\s+(\d{4}-\d{2}-\d{2})"),
]

HEADER_SCAN_CHARS = 4000  # la fecha vive en el encabezado, no en el changelog

# Fase 4 -- "conteos contradictorios" (§7 de la auditoria): unidades cuyo
# numero declarado en prosa se puede comparar 1:1 contra un conteo real del
# grafo (nodos de tipo Model/ViewSet/Endpoint por app). Deliberadamente NO
# se incluyen unidades ambiguas ("componentes", "archivos") -- alto riesgo de
# falso positivo por variar segun que se cuente exactamente.
COUNT_CLAIM_RE = re.compile(r"(\d+)\s+(modelos?|viewsets?|endpoints?)\b", re.IGNORECASE)


def extract_declared_date(text: str) -> Optional[str]:
    """Primer patron de fecha reconocido dentro del encabezado del documento."""
    header = text[:HEADER_SCAN_CHARS]
    for pat in DATE_PATTERNS:
        m = pat.search(header)
        if m:
            return m.group(1)
    return None


# Palabras que, si aparecen justo antes del numero, casi siempre indican que
# la frase describe un SUBCONJUNTO ("7 ViewSets de CV", "2 modelos sin
# signal") y no el total real de la app -- filtro conservador, no perfecto
# (ver AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md §15 "materializacion total",
# donde se documenta con evidencia real por que este filtro se agrego: sin
# el, la primera corrida de esta validacion tuvo un falso positivo verificado
# en la primerisima linea de salida).
SUBSET_CUE_BEFORE_RE = re.compile(
    r"\b(de|sin|solo|s[oó]lo|nuevo[s]?|adicional(?:es)?|extra|mas|m[aá]s)\s*$",
    re.IGNORECASE,
)
# Los calificadores de subconjunto suelen ir DESPUES del numero tambien
# ("7 ViewSets de CV", "6 modelos con signal") -- se descubrio con evidencia
# real (ver AUDITORIA/14 §15): filtrar solo "antes" dejaba pasar la mayoria.
SUBSET_CUE_AFTER_RE = re.compile(
    r"^\s*(de|con|sin|del|nuevos?|adicionales?|migrados?|faltantes?|"
    r"existentes?|relacionad\w+)\b",
    re.IGNORECASE,
)


def extract_count_claims(text: str) -> list[dict]:
    """Todas las afirmaciones tipo 'N modelos'/'N endpoints'/'N viewsets' en
    el cuerpo del doc, con una ventana de contexto corta para que el reporte
    de validacion sea legible sin tener que abrir el archivo. Filtra (no
    elimina del todo el riesgo, ver SUBSET_CUE_RE arriba) las que claramente
    describen un subconjunto, no el total de la app."""
    claims = []
    for m in COUNT_CLAIM_RE.finditer(text):
        unit = m.group(2).lower()
        unit = unit[:-1] if unit.endswith("s") and unit not in ("endpoints",) else unit
        unit = unit if unit in ("modelo", "viewset", "endpoint") else unit

        pre_context = text[max(0, m.start() - 20):m.start()]
        post_context = text[m.end():m.end() + 15]
        if SUBSET_CUE_BEFORE_RE.search(pre_context) or SUBSET_CUE_AFTER_RE.search(post_context):
            continue  # "7 ViewSets de CV" / "solo 7 viewsets" -- no es el total, se descarta

        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 10)
        claims.append({
            "count": int(m.group(1)),
            "unit": unit,
            "context": text[start:end].replace("\n", " ").strip(),
        })
    return claims


def collect_doc_sources() -> list[dict]:
    """Devuelve [{path: Path, app: str|None, scope: str}, ...] sin leer contenido aun."""
    sources: list[dict] = []

    # 1. Docs de Nivel 2 por app
    if ECOMMERCE_DIR.exists():
        for app_dir in sorted(ECOMMERCE_DIR.iterdir()):
            if not app_dir.is_dir() or app_dir.name not in KNOWN_APPS:
                continue
            docs_dir = app_dir / ".AGENT" / "docs"
            if docs_dir.exists():
                for md in sorted(docs_dir.glob("*.md")):
                    sources.append({"path": md, "app": app_dir.name, "scope": "nivel2"})

    # 2. Frontend (carpeta singular "doc", no "docs" -- convencion real del repo)
    fe_doc_dir = ECOMMERCE_DIR / "frontend" / ".AGENT" / "doc"
    if fe_doc_dir.exists():
        for md in sorted(fe_doc_dir.glob("*.md")):
            sources.append({"path": md, "app": "frontend", "scope": "nivel2"})

    # 3. AI Engine
    ai_doc_dir = REPO_ROOT / "ai_engine" / ".AGENT"
    if ai_doc_dir.exists():
        for md in sorted(ai_doc_dir.glob("*.md")):
            sources.append({"path": md, "app": "ai_engine", "scope": "nivel2"})

    # 4. Arquitectura general (IMPLEMENTATION_SUMMARY.md + gobernanza documental)
    arq_dir = REPO_ROOT / "Documentacion" / "Arquitectura_general"
    if arq_dir.exists():
        for md in sorted(arq_dir.glob("*.md")):
            sources.append({"path": md, "app": None, "scope": "arquitectura"})
        gob_dir = arq_dir / "GOBERNANZA_DOCUMENTAL"
        if gob_dir.exists():
            for md in sorted(gob_dir.glob("*.md")):
                sources.append({"path": md, "app": None, "scope": "arquitectura"})

    # 5. AUDITORIA/ (raiz del repo)
    aud_dir = REPO_ROOT / "AUDITORIA"
    if aud_dir.exists():
        for md in sorted(aud_dir.glob("*.md")):
            sources.append({"path": md, "app": None, "scope": "auditoria"})

    # 6. docs/.AGENT/
    docs_agent_dir = REPO_ROOT / "docs" / ".AGENT"
    if docs_agent_dir.exists():
        for md in sorted(docs_agent_dir.glob("*.md")):
            sources.append({"path": md, "app": None, "scope": "auditoria"})

    return sources


def build_documentation_index() -> list[dict]:
    """Lee cada fuente y arma la lista de entradas listas para convertirse en nodos."""
    entries = []
    for src in collect_doc_sources():
        path: Path = src["path"]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        entries.append({
            "path": rel,
            "name": path.stem,
            "app": src["app"],
            "scope": src["scope"],
            "declared_date": extract_declared_date(text),
            "size_bytes": len(text.encode("utf-8")),
            "count_claims": extract_count_claims(text) if src["scope"] == "nivel2" else [],
        })
    return entries


def enrich_with_documentation(kg) -> dict:
    """
    Muta el KnowledgeGraph ya construido: agrega un nodo `Documentation` por
    cada doc indexado y, cuando el doc pertenece a una app real que ya tiene
    nodo `App` en el grafo, la arista App -[DOCUMENTED_BY]-> Documentation.

    No requiere que knowledge_graph.py importe este modulo al reves -- se
    invoca desde build_and_save_knowledge_graph() como paso de enriquecimiento,
    igual que _infer_frontend_edges() es un paso posterior a _add_apps().
    """
    from knowledge_graph import Node  # import local: evita ciclo en import-time

    entries = build_documentation_index()
    linked = 0
    for entry in entries:
        nid = f"doc:{entry['path']}"
        kg.add_node(Node(
            nid, "Documentation", entry["name"],
            app=entry["app"] or "",
            file=entry["path"],
            meta={
                "scope": entry["scope"],
                "declared_date": entry["declared_date"],
                "size_bytes": entry["size_bytes"],
                "count_claims": entry["count_claims"],
            },
        ))
        if entry["app"]:
            app_nid = f"app:{entry['app']}"
            if app_nid in kg.nodes:
                kg.add_edge(app_nid, nid, "DOCUMENTED_BY")
                linked += 1

    return {"documentation_nodes": len(entries), "documented_by_edges": linked}


if __name__ == "__main__":
    # Uso standalone (sin knowledge_graph.py) para inspeccionar el indice solo:
    #   python ai_engine/documentation_graph.py
    idx = build_documentation_index()
    by_scope: dict[str, int] = {}
    undated = 0
    for e in idx:
        by_scope[e["scope"]] = by_scope.get(e["scope"], 0) + 1
        if not e["declared_date"]:
            undated += 1
    print(f"Documentos indexados: {len(idx)}")
    for scope, count in sorted(by_scope.items()):
        print(f"  {scope}: {count}")
    print(f"Sin fecha detectable en encabezado: {undated}")
