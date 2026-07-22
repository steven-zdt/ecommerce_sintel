"""
specialized_retrieval.py - Specialized Index Architecture (Phases 5 & 6)

Implements multiple specialized indices that COMPLEMENT LangGraph/ChromaDB:
  - ModelIndex       : Django model definitions, FK relations, SintelBaseModel subclasses
  - SerializerIndex  : DRF serializers, fields, Meta classes
  - ViewSetIndex     : ViewSets, APIViews, @action methods, permission classes
  - CommandIndex     : Commands with @transaction.atomic, service layer
  - SelectorIndex    : Selectors, read-only static methods, queryset patterns
  - ServiceIndex     : Business logic services, pricing calculators
  - FrontendIndex    : Vue components, composables, Pinia stores
  - DocumentationIndex: Architecture docs, .AGENT/docs/ Markdowns
  - BusinessRulesIndex: CLAUDE.md rules, guardrail definitions
  - DependencyIndex  : Cross-app dependency facts from DEPENDENCY_GRAPH.json

Each index is a ChromaDB collection + BM25 retriever pair.
RouterRetriever selects the best index(es) for a given query.
SubQuestionEngine decomposes multi-part questions into per-index sub-queries.
"""
import logging
import re
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

logger = logging.getLogger(__name__)

AI_ENGINE_DIR = Path(__file__).resolve().parent
MAP_PATH      = AI_ENGINE_DIR / "PROJECT_MAP.json"
DG_PATH       = AI_ENGINE_DIR / "DEPENDENCY_GRAPH.json"
KG_PATH       = AI_ENGINE_DIR / "KNOWLEDGE_GRAPH.json"


# ---------------------------------------------------------------------------
# Index identifiers and routing rules
# ---------------------------------------------------------------------------

INDEX_NAMES = [
    "ModelIndex", "SerializerIndex", "ViewSetIndex", "CommandIndex",
    "SelectorIndex", "ServiceIndex", "FrontendIndex", "DocumentationIndex",
    "BusinessRulesIndex", "DependencyIndex",
]

INDEX_KEYWORDS: dict[str, list[str]] = {
    "ModelIndex": [
        "model", "modelo", "field", "campo", "foreignkey", "fk", "m2m",
        "sintelbasemodel", "tabla", "table", "schema", "bd", "database",
        "migration", "migracion", "uuid", "soft-delete", "is_deleted",
    ],
    "SerializerIndex": [
        "serializer", "serializa", "field", "validate", "valida",
        "to_representation", "create", "update", "meta", "read_only",
        "write_only", "nested", "anidado",
    ],
    "ViewSetIndex": [
        "viewset", "view", "endpoint", "apiview", "action", "@action",
        "get_queryset", "permission", "permission_classes", "authentication",
        "http", "rest", "api", "router",
    ],
    "CommandIndex": [
        "command", "comando", "transaction.atomic", "atomic", "mutacion",
        "mutation", "create_", "update_", "delete_", "perform",
        "on_commit", "service layer",
    ],
    "SelectorIndex": [
        "selector", "query", "get_by", "filter", "select_related",
        "prefetch_related", "read-only", "lectura", "fetch",
        "get_or_404", "staticmethod",
    ],
    "ServiceIndex": [
        "service", "servicio", "pricing", "precio", "calculator",
        "business logic", "logica de negocio", "process", "flow",
    ],
    "FrontendIndex": [
        "vue", "component", "componente", "composable", "pinia", "store",
        "template", "v-model", "v-for", "script setup", "ref(", "reactive(",
        "onmounted", "defineprops", "defineemits", "router", "ruta",
        "frontend", "vite", "bootstrap",
    ],
    "DocumentationIndex": [
        "arquitectura", "architecture", "doc", "documentation", "como",
        "how", "por que", "why", "patron", "pattern", "flujo", "flow",
        "diagrama", "diagram", "spec", "especificacion",
    ],
    "BusinessRulesIndex": [
        "regla", "rule", "restriccion", "constraint", "prohibido",
        "forbidden", "siempre", "always", "nunca", "never", "critico",
        "critical", "guardrail", "validacion", "decimal", "float",
    ],
    "DependencyIndex": [
        "depende", "depends", "usa", "uses", "impacto", "impact",
        "rompe", "breaks", "frontend usa", "consumer", "relacion",
        "relation", "dependencia", "blast radius",
    ],
}


def route_to_indices(query: str) -> list[str]:
    """Return the most relevant index names for a query."""
    q_lower = query.lower()
    scores: dict[str, int] = {}
    for idx_name, keywords in INDEX_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scores[idx_name] = score
    if not scores:
        return ["DocumentationIndex", "ViewSetIndex", "ModelIndex"]
    return sorted(scores, key=lambda k: scores[k], reverse=True)[:3]


# ---------------------------------------------------------------------------
# Document builders per index type
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    import json
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def build_model_docs() -> list[Document]:
    """Builds Documents for ModelIndex from PROJECT_MAP models."""
    pmap = _load_json(MAP_PATH)
    docs = []
    for app_name, app_data in pmap.get("apps", {}).items():
        for m in app_data.get("models", []):
            fields_txt = "\n".join(
                f"  {f['name']}: {f['field_type']}"
                + (f" -> {f['related_model']}" if f.get("related_model") else "")
                for f in m.get("fields", [])
            )
            content = (
                f"Model: {m['name']} (app={app_name})\n"
                f"File: {m.get('file', '')}\n"
                f"Bases: {', '.join(m.get('bases', []))}\n"
                f"Fields:\n{fields_txt}\n"
                f"Methods: {', '.join(m.get('methods', [])[:10])}"
            )
            docs.append(Document(
                page_content=content,
                metadata={"index": "ModelIndex", "app_name": app_name,
                          "entity": m["name"], "type": "model",
                          "file": m.get("file", "")}
            ))
    return docs


def build_serializer_docs() -> list[Document]:
    pmap = _load_json(MAP_PATH)
    docs = []
    for app_name, app_data in pmap.get("apps", {}).items():
        for s in app_data.get("serializers", []):
            content = (
                f"Serializer: {s['name']} (app={app_name})\n"
                f"File: {s.get('file', '')}\n"
                f"Bases: {', '.join(s.get('bases', []))}\n"
                f"Fields: {', '.join(s.get('fields', []))}"
            )
            docs.append(Document(
                page_content=content,
                metadata={"index": "SerializerIndex", "app_name": app_name,
                          "entity": s["name"], "type": "serializer"}
            ))
    return docs


def build_viewset_docs() -> list[Document]:
    pmap = _load_json(MAP_PATH)
    docs = []
    for app_name, app_data in pmap.get("apps", {}).items():
        prefix = app_data.get("api_prefix", f"api/v1/{app_name}")
        for vs in app_data.get("viewsets", []):
            actions = vs.get("actions", [])
            content = (
                f"ViewSet: {vs['name']} (app={app_name})\n"
                f"File: {vs.get('file', '')}\n"
                f"Bases: {', '.join(vs.get('bases', []))}\n"
                f"Actions: {', '.join(actions)}\n"
                f"API prefix: {prefix}"
            )
            docs.append(Document(
                page_content=content,
                metadata={"index": "ViewSetIndex", "app_name": app_name,
                          "entity": vs["name"], "type": "viewset"}
            ))
    return docs


def build_command_selector_service_docs() -> list[Document]:
    pmap = _load_json(MAP_PATH)
    docs = []
    for app_name, app_data in pmap.get("apps", {}).items():
        for svc in app_data.get("services", []):
            role = svc.get("role", "service")
            idx = "CommandIndex" if "command" in role.lower() else \
                  "SelectorIndex" if "selector" in role.lower() else "ServiceIndex"
            content = (
                f"{role.capitalize()}: {svc['name']} (app={app_name})\n"
                f"File: {svc.get('file', '')}\n"
                f"Methods: {', '.join(svc.get('methods', [])[:8])}"
            )
            docs.append(Document(
                page_content=content,
                metadata={"index": idx, "app_name": app_name,
                          "entity": svc["name"], "type": role}
            ))
    return docs


def build_frontend_docs() -> list[Document]:
    pmap = _load_json(MAP_PATH)
    fe = pmap.get("frontend", {})
    docs = []
    for group in ("views", "components", "composables", "stores"):
        for entry in fe.get(group, []):
            path = entry.get("path", "")
            api_calls = entry.get("api_calls", [])
            calls_txt = ", ".join(
                f"{c['method']} {c['url']}" for c in api_calls[:4]
            )
            store_info = entry.get("store_info", {})
            content = (
                f"Frontend {group[:-1].capitalize()}: {path}\n"
                f"API calls: {calls_txt}\n"
                f"Store imports: {', '.join(entry.get('store_imports', []))}\n"
                f"Component imports: {', '.join(entry.get('component_imports', [])[:5])}\n"
            )
            if store_info:
                content += (
                    f"Store ID: {store_info.get('store_id', '')}\n"
                    f"State keys: {', '.join(store_info.get('state_keys', []))}\n"
                    f"Actions: {', '.join(store_info.get('actions', [])[:6])}\n"
                )
            docs.append(Document(
                page_content=content,
                metadata={"index": "FrontendIndex", "type": group,
                          "layer": "frontend", "file": path}
            ))
    return docs


def build_dependency_docs() -> list[Document]:
    dg = _load_json(DG_PATH)
    docs = []
    # change_impact
    for entity, blast in dg.get("change_impact", {}).items():
        affected_txt = "; ".join(
            f"{t}: {', '.join(items[:3])}" for t, items in blast.items()
        )
        content = (
            f"Change impact for {entity}:\n"
            f"Affects: {affected_txt}"
        )
        docs.append(Document(
            page_content=content,
            metadata={"index": "DependencyIndex", "entity": entity, "type": "impact"}
        ))
    # endpoint_consumers
    for ep, consumers in dg.get("endpoint_consumers", {}).items():
        if consumers:
            clist = ", ".join(c.get("name", c.get("file", "?")) for c in consumers[:5])
            content = f"Endpoint {ep} is consumed by: {clist}"
            docs.append(Document(
                page_content=content,
                metadata={"index": "DependencyIndex", "entity": ep, "type": "consumer"}
            ))
    return docs


def build_business_rules_docs() -> list[Document]:
    """Builds BusinessRulesIndex from GLOBAL_MEMORY.json critical_rules."""
    import json
    gm_path = AI_ENGINE_DIR / "GLOBAL_MEMORY.json"
    if not gm_path.exists():
        return []
    gm = json.loads(gm_path.read_text(encoding="utf-8"))
    docs = []
    for rule in gm.get("critical_rules", []):
        content = (
            f"Business Rule [{rule['id']}]:\n"
            f"Rule: {rule['rule']}\n"
            f"Why: {rule.get('why', '')}"
        )
        docs.append(Document(
            page_content=content,
            metadata={"index": "BusinessRulesIndex", "rule_id": rule["id"], "type": "rule"}
        ))
    for decision in gm.get("architectural_decisions", []):
        content = (
            f"Architectural Decision [{decision['id']}]:\n"
            f"Decision: {decision['decision']}"
        )
        docs.append(Document(
            page_content=content,
            metadata={"index": "BusinessRulesIndex", "rule_id": decision["id"], "type": "decision"}
        ))
    return docs


# ---------------------------------------------------------------------------
# Index registry
# ---------------------------------------------------------------------------

class SpecializedIndexRegistry:
    """
    Registry of all specialized indices.
    Each index is a BM25Retriever built from its specialized document set.
    ChromaDB integration is optional (used when vectorstore is available).
    """

    def __init__(self):
        self._indices: dict[str, list[Document]] = {}
        self._bm25: dict[str, BM25Retriever]    = {}
        self._built = False

    def build(self):
        """Build all specialized indices from PROJECT_MAP and supporting JSON."""
        logger.info("[specialized] Building specialized indices...")
        builders = {
            "ModelIndex":        build_model_docs,
            "SerializerIndex":   build_serializer_docs,
            "ViewSetIndex":      build_viewset_docs,
            "FrontendIndex":     build_frontend_docs,
            "DependencyIndex":   build_dependency_docs,
            "BusinessRulesIndex":build_business_rules_docs,
        }
        # Command/Selector/Service share a builder
        css_docs = build_command_selector_service_docs()
        self._indices["CommandIndex"]  = [d for d in css_docs if d.metadata.get("index") == "CommandIndex"]
        self._indices["SelectorIndex"] = [d for d in css_docs if d.metadata.get("index") == "SelectorIndex"]
        self._indices["ServiceIndex"]  = [d for d in css_docs if d.metadata.get("index") == "ServiceIndex"]

        for name, builder in builders.items():
            docs = builder()
            self._indices[name] = docs
            logger.info("[specialized] %s: %d docs", name, len(docs))

        # Build BM25 retrievers
        for name, docs in self._indices.items():
            if docs:
                self._bm25[name] = BM25Retriever.from_documents(docs, k=5)

        self._built = True
        logger.info("[specialized] All indices built. Total docs: %d",
                    sum(len(d) for d in self._indices.values()))

    def retrieve(self, query: str, index_names: list[str] | None = None) -> list[Document]:
        if not self._built:
            self.build()
        if index_names is None:
            index_names = route_to_indices(query)

        collected: list[Document] = []
        for name in index_names:
            retriever = self._bm25.get(name)
            if retriever:
                docs = retriever.invoke(query)
                collected.extend(docs)

        # Dedup
        seen: set[str] = set()
        unique: list[Document] = []
        for d in collected:
            key = d.page_content[:100]
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique[:20]

    def stats(self) -> dict:
        return {name: len(docs) for name, docs in self._indices.items()}

    def get_docs(self, index_name: str) -> list[Document]:
        return self._indices.get(index_name, [])


# ---------------------------------------------------------------------------
# Sub-Question Engine
# ---------------------------------------------------------------------------

def decompose_query(query: str) -> list[str]:
    """
    Decomposes a multi-part query into sub-questions per index type.
    Returns a list of sub-queries, one per relevant index.
    Simplified version of LlamaIndex's SubQuestionQueryEngine.
    """
    target_indices = route_to_indices(query)
    sub_questions = []

    sub_templates = {
        "ModelIndex":        f"What models are involved in: {query}",
        "SerializerIndex":   f"What serializers handle: {query}",
        "ViewSetIndex":      f"What ViewSets or endpoints implement: {query}",
        "CommandIndex":      f"What Commands (transaction.atomic) are needed for: {query}",
        "SelectorIndex":     f"What Selectors query the data for: {query}",
        "ServiceIndex":      f"What services or pricing logic applies to: {query}",
        "FrontendIndex":     f"What Vue components/stores consume: {query}",
        "DocumentationIndex":f"What architecture documentation explains: {query}",
        "BusinessRulesIndex":f"What business rules or guardrails apply to: {query}",
        "DependencyIndex":   f"What is the change impact/blast radius for: {query}",
    }

    for idx in target_indices:
        sub_questions.append(sub_templates.get(idx, query))
    return sub_questions


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_registry: SpecializedIndexRegistry | None = None


def get_registry(force_rebuild: bool = False) -> SpecializedIndexRegistry:
    global _registry
    if _registry is None or force_rebuild:
        _registry = SpecializedIndexRegistry()
        _registry.build()
    return _registry


def retrieve_specialized(query: str, index_names: list[str] | None = None) -> list[Document]:
    """
    Main entry point for specialized retrieval.
    Routes to the best indices and returns deduplicated documents.
    """
    registry = get_registry()
    return registry.retrieve(query, index_names)


def retrieve_with_routing(query: str) -> dict:
    """
    Returns both the routing decision and the retrieved documents.
    Used by the AI Engine for transparent retrieval.
    """
    indices = route_to_indices(query)
    docs = retrieve_specialized(query, indices)
    return {
        "routed_to": indices,
        "sub_questions": decompose_query(query),
        "docs": [{"content": d.page_content[:200], "meta": d.metadata} for d in docs],
        "total": len(docs),
    }
