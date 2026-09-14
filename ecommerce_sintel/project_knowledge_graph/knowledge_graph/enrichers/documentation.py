"""
Enricher: nodos Documentation desde los .md del proyecto (Fase 5, PLAN_MAESTRO_
DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08). Extraido de ai_engine/
documentation_graph.py.

Agrega nodos `Documentation` al Knowledge Graph y la arista `DOCUMENTED_BY`
(App -> Documentation) para las apps que ya tienen una convencion de nombre de
archivo clara ("<app>/.AGENT/docs/*.md").

No reemplaza ni duplica el RAG vectorial (PostgreSQL+pgvector via Django/
ai_knowledge, ver ai_engine/retrievers.py -- ChromaDB retirado en la mision
de simplificacion arquitectonica, 2026-09-14) -- ese sigue siendo la fuente
de contexto narrativo. Este modulo solo estructura metadata (ruta, fecha
declarada, app) como nodos de grafo consultables.

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

from project_knowledge_graph.config import DJANGO_APPS

REPO_ROOT = Path(__file__).resolve().parents[4]
KNOWN_APPS = set(DJANGO_APPS)

DATE_PATTERNS = [
    re.compile(r"Ultima revision:\s*(\d{4}-\d{2}-\d{2})"),
    re.compile(r"\*\*Fecha:\*\*\s*(\d{4}-\d{2}-\d{2})"),
    re.compile(r"^Fecha:\*?\*?\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE),
    re.compile(r"Actualizado\s+(\d{4}-\d{2}-\d{2})"),
    re.compile(r"Sincronizado\s+(\d{4}-\d{2}-\d{2})"),
]

HEADER_SCAN_CHARS = 4000  # la fecha vive en el encabezado, no en el changelog

# unidades cuyo numero declarado en prosa se puede comparar 1:1 contra un
# conteo real del grafo (nodos de tipo Model/ViewSet/Endpoint por app).
# Deliberadamente NO se incluyen unidades ambiguas ("componentes", "archivos")
# -- alto riesgo de falso positivo por variar segun que se cuente exactamente.
COUNT_CLAIM_RE = re.compile(r"(\d+)\s+(modelos?|viewsets?|endpoints?)\b", re.IGNORECASE)


def _resolve_ecommerce_dir() -> Path:
    """Prioriza CODEBASE_PATH (env var, Docker) sobre el calculo relativo por
    __file__ -- mismo criterio que config.py::_resolve_base_dir()."""
    env_path = os.environ.get("CODEBASE_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    return REPO_ROOT / "ecommerce_sintel"


ECOMMERCE_DIR = _resolve_ecommerce_dir()


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
# signal") y no el total real de la app -- filtro conservador, no perfecto.
SUBSET_CUE_BEFORE_RE = re.compile(
    r"\b(de|sin|solo|s[oó]lo|nuevo[s]?|adicional(?:es)?|extra|mas|m[aá]s)\s*$",
    re.IGNORECASE,
)
# Los calificadores de subconjunto suelen ir DESPUES del numero tambien
# ("7 ViewSets de CV", "6 modelos con signal").
SUBSET_CUE_AFTER_RE = re.compile(
    r"^\s*(de|con|sin|del|nuevos?|adicionales?|migrados?|faltantes?|"
    r"existentes?|relacionad\w+)\b",
    re.IGNORECASE,
)


def extract_count_claims(text: str) -> list[dict]:
    """Todas las afirmaciones tipo 'N modelos'/'N endpoints'/'N viewsets' en
    el cuerpo del doc, con una ventana de contexto corta para que el reporte
    de validacion sea legible sin tener que abrir el archivo. Filtra las que
    claramente describen un subconjunto, no el total de la app."""
    claims = []
    for m in COUNT_CLAIM_RE.finditer(text):
        unit = m.group(2).lower()
        unit = unit[:-1] if unit.endswith("s") and unit not in ("endpoints",) else unit

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

    # 3. AI Engine (vive dentro de ecommerce_sintel/ desde 2026-07-31)
    ai_doc_dir = REPO_ROOT / "ecommerce_sintel" / "ai_engine" / ".AGENT"
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


# ---- Documentation Graph (Fase 8, Site Knowledge Graph, 2026-08-10) -------
#
# 8.1 del plan: "no confiar unicamente en nombres. Detectar referencias
# mediante: paths, symbols, endpoints...". Los 3 patrones abajo estan
# verificados contra prosa real de renting/.AGENT/docs/
# ARQUITECTURA_COMPLETA_RENTIG.md: rutas de archivo entre backticks
# (`` `dashboard/api/renting_catalog_views.py` ``), referencias
# `Clase.metodo()` entre backticks (`` `EquipmentReviewCommands.
# create_review()` ``), y URLs de endpoint entre backticks
# (`` `/api/v1/dashboard/equipment/{uuid}/marketing/` ``) -- la convencion
# real de este proyecto es citar entidades de codigo en backticks, no en
# prosa plana, lo que hace la extraccion razonablemente precisa sin falsos
# positivos de palabras comunes.
#
# Limitacion documentada, no omitida en silencio: no resuelve la forma
# abreviada real `` `EquipmentMarketingCommands.upsert()`/`.delete()` ``
# (el segundo metodo reusa implicitamente la clase del primero) -- solo se
# captura la referencia EXPLICITA `Clase.metodo`, requeriria parsing con
# estado (recordar "la ultima clase vista") para el caso abreviado.

_DOC_FILE_PATH_RE = re.compile(r"`([\w./-]+\.(?:py|vue|js|ts))`")
_DOC_SYMBOL_REF_RE = re.compile(r"`([A-Z]\w*\.\w+)(?:\(\))?`")
_DOC_ENDPOINT_RE = re.compile(r"`(/api/v\d+/[\w/{}.-]*)`")


def extract_doc_references(text: str) -> dict:
    """Referencias reales a codigo dentro de un documento -- rutas de
    archivo, `Clase.metodo` y URLs de endpoint, todas citadas entre
    backticks (convencion real de la documentacion de este proyecto)."""
    return {
        "file_paths": sorted(set(_DOC_FILE_PATH_RE.findall(text))),
        "symbol_refs": sorted(set(_DOC_SYMBOL_REF_RE.findall(text))),
        "endpoint_urls": sorted(set(u.rstrip("/") for u in _DOC_ENDPOINT_RE.findall(text))),
    }


def _match_endpoints_for_url(kg, url: str) -> list:
    """Mismo algoritmo EXACTO que builder.py::KnowledgeGraphBuilder.
    _match_endpoints_for_url() (Fase 4) -- matching por PREFIJO real (con o
    sin `api/v1/`), no por ultimo-segmento-coincide. Duplicado aca a
    proposito, documentado (no silencioso): este enricher corre DESPUES de
    builder.build() sobre el `kg` ya terminado, sin acceso a `self` del
    builder -- una funcion standalone evita acoplar este modulo al builder
    solo para reusar 6 lineas."""
    url_norm = url.strip("/")
    matches = []
    for ep_node in kg.nodes_of_type("Endpoint"):
        ep_path = ep_node.name.strip("/")
        ep_no_prefix = re.sub(r"^api/v\d+/", "", ep_path)
        for candidate in (ep_path, ep_no_prefix):
            if url_norm == candidate or url_norm.startswith(candidate + "/"):
                matches.append(ep_node)
                break
    return matches


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
            # references (Fase 8, 2026-08-10): en TODO scope, no solo nivel2
            # -- los docs de auditoria/arquitectura tambien citan codigo
            # real entre backticks (ej. AUDITORIA/*.md referencia archivos
            # y endpoints concretos igual que los docs de app).
            "references": extract_doc_references(text),
        })
    return entries


def enrich_with_documentation(kg) -> dict:
    """
    Muta el KnowledgeGraph ya construido: agrega un nodo `Documentation` por
    cada doc indexado, la arista App -[DOCUMENTED_BY]-> Documentation cuando
    aplica, y -- Fase 8, 2026-08-10 -- `Documentation -[REFERENCES]->
    File|Symbol|Endpoint` para cada referencia real de codigo citada en el
    doc (ver extract_doc_references arriba). Responde 8.1 del plan: "no
    confiar unicamente en nombres" -- el enlace se hace por PATH/nombre
    EXACTO real, no por coincidencia de palabra en el nombre del archivo de
    doc.
    """
    from project_knowledge_graph.knowledge_graph.relations import Node

    entries = build_documentation_index()
    linked = 0
    references_added = 0
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

        refs = entry["references"]
        for file_path in refs["file_paths"]:
            file_nid = f"file:{file_path}"
            if file_nid in kg.nodes:
                kg.add_edge(nid, file_nid, "REFERENCES")
                references_added += 1
        for symbol_ref in refs["symbol_refs"]:
            for cand in kg.find_by_name(symbol_ref):
                if cand.type == "Symbol" and cand.name == symbol_ref:
                    kg.add_edge(nid, cand.id, "REFERENCES")
                    references_added += 1
        for url in refs["endpoint_urls"]:
            for ep_node in _match_endpoints_for_url(kg, url):
                kg.add_edge(nid, ep_node.id, "REFERENCES")
                references_added += 1

    return {"documentation_nodes": len(entries), "documented_by_edges": linked,
            "references_edges": references_added}


if __name__ == "__main__":
    # Uso standalone (sin build_and_save_knowledge_graph) para inspeccionar el
    # indice solo: python -m project_knowledge_graph.knowledge_graph.enrichers.documentation
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
