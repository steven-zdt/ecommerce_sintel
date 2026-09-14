import os
import logging
from datetime import datetime, timezone
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    UnstructuredMarkdownLoader,
    PythonLoader,
    TextLoader,
)

logger = logging.getLogger(__name__)

# Módulos Vue conocidos — para inferir app_name desde la ruta del componente
FRONTEND_MODULE_NAMES = {
    "shop", "inventory", "orders", "renting", "technical_services",
    "quotes", "users", "marketing", "support", "core", "operations",
    "customer", "auth", "landing", "checkout", "services",
}

# Apps conocidas del proyecto — usadas para inferir app_name desde la ruta
APP_NAMES = {
    "shop", "inventory", "orders", "payment", "wompi",
    "technical_services", "renting", "cart", "notifications",
    "users", "accounts", "dashboard", "quotes", "marketing",
    "support", "core", "ecommerce",
    "kyc", "security", "operations", "shipping", "organization",
}

APP_KEYWORDS = {
    "shop":                ["shop", "product", "variant", "brand", "category", "tax", "pricing"],
    "inventory":           ["inventory", "stock", "kardex", "stockrecord"],
    "orders":              ["order", "orders", "orderitem", "checkout", "coupon", "shippingaddress"],
    "payment":             ["payment", "codcommands", "confirm_order_payment", "codtransaction", "nequi"],
    "wompi":               ["wompi", "webhook", "transaction", "nequitransaction", "tokenizedcard"],
    "technical_services":  ["technical_services", "service", "servicevariant", "servicebooking", "quotation"],
    "renting":             ["renting", "rental", "equipment", "equipmentvariant"],
    "cart":                ["cart", "cartitem"],
    "notifications":       ["notification", "notificationlog", "whatsapp", "dispatch"],
    "users":               ["users", "user", "permission", "isadminuser"],
    "accounts":            ["accounts", "userprofile", "technician"],
    "dashboard":           ["dashboard", "bff", "orchestrator"],
    "quotes":              ["quotes", "quote"],
    "marketing":           ["marketing", "coupon", "campaign"],
    "support":             ["support", "chat", "chatroom", "chatmessage"],
    "core":                ["core", "homefeed", "homeconfig", "footer", "footergroup", "footerlink", "brandslider", "brandslideritem", "brandsliderconfig", "navbarlink", "footercta"],
    "kyc":                 ["kyc", "userverification", "verificationdocument", "verificationevent", "consentrecord", "force_approve", "request_upgrade"],
    "security":            ["security", "securityevent", "log_event", "audit"],
    "operations":          ["operations", "operationticket", "dispatcher", "dispatcherprofile", "trackingevent"],
    "shipping":            ["shipping"],  # app stub: solo apps.py, sin models/views propios
    "organization":        ["organization", "company", "branding", "contactinfo", "sociallink", "emailsettings", "domainsettings", "seosettings", "legalentityinfo"],
}


def _app_from_segments(segments: list[str]) -> str:
    """Devuelve el nombre de la app leyendo los segmentos de la ruta de izquierda a derecha."""
    for seg in segments:
        if seg in APP_NAMES:
            return seg
    # payment es un meta-paquete que contiene online/, cod/, shared/
    if "payment" in segments:
        return "payment"
    return "unknown"


def _infer_metadata(path: str) -> dict:
    normalized = path.replace("\\", "/").lower()
    segments = normalized.split("/")

    # Documentos de arquitectura (.AGENT/docs/)
    if ".agent" in segments and "docs" in segments:
        app_name = _app_from_segments(segments)
        return {
            "app_name": app_name,
            "doc_type": "architecture",
            "layer": "architecture",
            "language": "markdown",
        }

    if path.endswith(".vue"):
        fname = segments[-1].replace(".vue", "")
        # Inferir módulo desde la ruta
        app_name = "frontend"
        for seg in segments:
            if seg in FRONTEND_MODULE_NAMES:
                app_name = f"frontend_{seg}"
                break

        doc_type = "component"
        if "view" in fname.lower() or "page" in fname.lower():
            doc_type = "view"
        elif "list" in fname.lower():
            doc_type = "module_list"
        elif "form" in fname.lower():
            doc_type = "module_form"
        elif "layout" in fname.lower() or "shell" in fname.lower() or "navbar" in fname.lower() or "sidebar" in fname.lower():
            doc_type = "layout"
        elif "composable" in normalized or "use" in fname[:3].lower():
            doc_type = "composable"

        return {
            "app_name": app_name,
            "doc_type": doc_type,
            "layer": "frontend",
            "language": "vue",
        }

    if path.endswith(".js") and "frontend" in normalized:
        fname = segments[-1].replace(".js", "")
        app_name = "frontend"
        for seg in segments:
            if seg in FRONTEND_MODULE_NAMES:
                app_name = f"frontend_{seg}"
                break

        doc_type = "composable" if fname.startswith("use") or "composable" in normalized else "store"
        if "router" in fname:
            doc_type = "router"
        elif "store" in normalized or "pinia" in normalized:
            doc_type = "store"

        return {
            "app_name": app_name,
            "doc_type": doc_type,
            "layer": "frontend",
            "language": "javascript",
        }

    if path.endswith(".py"):
        fname = segments[-1]
        doc_type = "command"
        if "selector" in fname:
            doc_type = "selector"
        elif "permission" in fname:
            doc_type = "permission"
        elif "serializer" in fname:
            doc_type = "serializer"
        elif "model" in fname:
            doc_type = "model"
        elif "webhook" in fname or "view" in fname:
            doc_type = "view"
        elif "kardex" in fname or "calculator" in fname or "pricing" in fname:
            doc_type = "service"

        app_name = _app_from_segments(segments)

        return {
            "app_name": app_name,
            "doc_type": doc_type,
            "layer": "service_layer" if doc_type in ("command", "selector", "service") else "api",
            "language": "python",
        }

    if path.endswith(".md"):
        stem = segments[-1].replace(".md", "")
        # Skills de DRF — tratarlas como specs de backend, no de frontend
        if "ai_skills/drf" in normalized:
            return {
                "app_name": "backend",
                "doc_type": "drf_spec",
                "layer": "service_layer",
                "language": "markdown",
            }
        # Skills de frontend — tratarlos como specs de frontend
        if "frontend" in normalized or "ai_skills" in normalized:
            return {
                "app_name": "frontend",
                "doc_type": "frontend_spec",
                "layer": "frontend",
                "language": "markdown",
            }
        # Specs de docs/specs/ — usar el nombre del stem como app_name
        app_name = stem if stem in APP_KEYWORDS else "global"
        return {
            "app_name": app_name,
            "doc_type": "spec",
            "layer": "architecture",
            "language": "markdown",
        }

    return {"app_name": "unknown", "doc_type": "other", "layer": "unknown", "language": "other"}


# Knowledge Governance (Fase 17, PLAN_MAESTRO_SINTEL_AI_SUPPORT, 2026-08-08):
# ningun doc_type ingestado hoy es contenido curado para clientes -- todo lo que
# existe es documentacion de arquitectura interna (.AGENT/docs), specs de
# ingenieria (docs/specs/*.md, ej. global_rules.md/architecture_contracts.md/
# wompi.md) o skills de codegen (ai_skills/). Verificado en vivo: una pregunta de
# cliente sobre "horario de atencion" recupero un fragmento de
# ARQUITECTURA_COMPLETA_SERVICES.md sobre agendamiento tecnico de servicios (nada
# que ver con horario de tienda) y el LLM fabrico una respuesta de todos modos
# ("lunes a viernes 8am-6pm") -- no existe ese dato en ningun lado del repo.
# visibility="internal" para TODO hasta que exista una fuente de conocimiento
# real para clientes (FAQ/politicas/garantias) marcada explicitamente "public".
# retrieve_knowledge_for_chat (retrievers.py) debe filtrar por esto -- ver ahi.
_PUBLIC_DOC_TYPES: set[str] = set()


def enrich_metadata(docs: list[Document]) -> list[Document]:
    for doc in docs:
        src = doc.metadata.get("source", "")
        inferred = _infer_metadata(src)
        try:
            inferred["updated_at"] = datetime.fromtimestamp(
                os.path.getmtime(src), tz=timezone.utc
            ).isoformat()
        except OSError:
            inferred["updated_at"] = None
        inferred["visibility"] = "public" if inferred["doc_type"] in _PUBLIC_DOC_TYPES else "internal"
        doc.metadata.update(inferred)
    return docs


def load_all_documents(docs_path: str, codebase_path: str) -> list[Document]:
    all_docs: list[Document] = []

    # ── 1. Specs en docs/specs/ ──────────────────────────────────────────────
    if os.path.isdir(docs_path):
        try:
            md_loader = DirectoryLoader(
                docs_path,
                glob="**/*.md",
                loader_cls=UnstructuredMarkdownLoader,
                show_progress=False,
                use_multithreading=True,
            )
            md_docs = md_loader.load()
            logger.info("[loaders] Specs Markdown cargados: %d", len(md_docs))
            all_docs.extend(md_docs)
        except Exception as exc:
            logger.error("[loaders] Error cargando Specs Markdown: %s", exc)

    if os.path.isdir(codebase_path):

        # ── 2. Docs de arquitectura por app (.AGENT/docs/**/*.md) ─────────────
        try:
            agent_md_loader = DirectoryLoader(
                codebase_path,
                glob="**/.AGENT/docs/**/*.md",
                loader_cls=UnstructuredMarkdownLoader,
                show_progress=False,
                use_multithreading=True,
                recursive=True,
                # DirectoryLoader descarta por defecto cualquier ruta con un segmento
                # que empiece con "." (load_hidden=False) -- ".AGENT" siempre cayo en
                # ese filtro y esto cargaba 0 documentos silenciosamente, sin error
                # (bug real, confirmado en vivo 2026-07-31: glob.glob crudo encontraba
                # 38 archivos, pero DirectoryLoader.load() devolvia una lista vacia).
                load_hidden=True,
            )
            agent_docs = agent_md_loader.load()
            logger.info("[loaders] Docs de arquitectura (.AGENT/docs) cargados: %d", len(agent_docs))
            all_docs.extend(agent_docs)
        except Exception as exc:
            logger.error("[loaders] Error cargando .AGENT/docs: %s", exc)

        # ── 3. Codigo Python por capas ────────────────────────────────────────
        py_patterns = [
            # Service layer
            "**/services/commands.py",
            "**/services/selectors.py",
            # Payment subpackages
            "**/shared/commands.py",
            "**/cod/services/commands.py",
            "**/online/services/commands.py",
            # API layer
            "**/api/views.py",
            "**/api/serializers.py",
            "**/api/permissions.py",
            "**/online/api/views.py",
            # Modelos
            "**/models.py",
        ]
        for pattern in py_patterns:
            try:
                py_loader = DirectoryLoader(
                    codebase_path,
                    glob=pattern,
                    loader_cls=PythonLoader,
                    show_progress=False,
                    recursive=True,
                )
                py_docs = py_loader.load()
                logger.info("[loaders] Python (%s): %d", pattern, len(py_docs))
                all_docs.extend(py_docs)
            except Exception as exc:
                logger.error("[loaders] Error cargando %s: %s", pattern, exc)

    if os.path.isdir(codebase_path):

        # ── 4. Componentes Vue del frontend ──────────────────────────────────────
        vue_patterns = [
            # Módulos admin (los más valiosos como ejemplos)
            "frontend/src/modules/**/*.vue",
            # Vistas customer
            "frontend/src/views/**/*.vue",
            # Componentes compartidos clave
            "frontend/src/components/ui/*.vue",
            "frontend/src/components/ui/landing/*.vue",
            "frontend/src/components/ui/home/**/*.vue",
            "frontend/src/components/layout/*.vue",
            "frontend/src/components/customer/*.vue",
            "frontend/src/components/customer/ui/*.vue",
            # Composables (lógica reutilizable)
            "frontend/src/composables/*.js",
            # Stores Pinia
            "frontend/src/store/*.js",
            # Router
            "frontend/src/apps/admin/router.js",
        ]
        for pattern in vue_patterns:
            try:
                vue_loader = DirectoryLoader(
                    codebase_path,
                    glob=pattern,
                    loader_cls=TextLoader,
                    loader_kwargs={"encoding": "utf-8"},
                    show_progress=False,
                    recursive=True,
                    silent_errors=True,
                )
                vue_docs = vue_loader.load()
                logger.info("[loaders] Vue/JS (%s): %d", pattern, len(vue_docs))
                all_docs.extend(vue_docs)
            except Exception as exc:
                logger.error("[loaders] Error cargando %s: %s", pattern, exc)

        # ── 5. Skills de frontend (ai_skills/frontend/*.md) ──────────────────────
        skills_path = os.path.join(codebase_path, "ai_skills", "frontend")
        if os.path.isdir(skills_path):
            try:
                skills_loader = DirectoryLoader(
                    skills_path,
                    glob="**/*.md",
                    loader_cls=UnstructuredMarkdownLoader,
                    show_progress=False,
                )
                skills_docs = skills_loader.load()
                logger.info("[loaders] Frontend skills: %d", len(skills_docs))
                all_docs.extend(skills_docs)
            except Exception as exc:
                logger.error("[loaders] Error cargando frontend skills: %s", exc)

        # ── 5b. Skills de DRF (ai_skills/drf/*.md) ────────────────────────────────
        drf_skills_path = os.path.join(codebase_path, "ai_skills", "drf")
        if os.path.isdir(drf_skills_path):
            try:
                drf_skills_loader = DirectoryLoader(
                    drf_skills_path,
                    glob="**/*.md",
                    loader_cls=UnstructuredMarkdownLoader,
                    show_progress=False,
                )
                drf_skills_docs = drf_skills_loader.load()
                logger.info("[loaders] DRF skills: %d", len(drf_skills_docs))
                all_docs.extend(drf_skills_docs)
            except Exception as exc:
                logger.error("[loaders] Error cargando DRF skills: %s", exc)

        # ── 6. Docs arquitectura frontend (.AGENT/doc/*.md) ──────────────────────
        try:
            fe_agent_loader = DirectoryLoader(
                codebase_path,
                glob="frontend/.AGENT/doc/*.md",
                loader_cls=UnstructuredMarkdownLoader,
                show_progress=False,
                # Mismo bug que el loader de arriba (.AGENT/docs) -- ver ese comentario.
                load_hidden=True,
            )
            fe_agent_docs = fe_agent_loader.load()
            logger.info("[loaders] Frontend .AGENT docs: %d", len(fe_agent_docs))
            all_docs.extend(fe_agent_docs)
        except Exception as exc:
            logger.error("[loaders] Error cargando frontend .AGENT docs: %s", exc)

    # ── 7. Enriquecer metadata y deduplicar por ruta fuente ──────────────────
    enriched = enrich_metadata(all_docs)

    seen_sources: set[str] = set()
    unique: list[Document] = []
    for doc in enriched:
        src = doc.metadata.get("source", "")
        if src not in seen_sources:
            seen_sources.add(src)
            unique.append(doc)

    logger.info(
        "[loaders] Total docs (specs=%d  arch_md=%d  py=variable  dedup_total=%d)",
        len([d for d in unique if d.metadata.get("doc_type") == "spec"]),
        len([d for d in unique if d.metadata.get("doc_type") == "architecture"]),
        len(unique),
    )
    return unique
