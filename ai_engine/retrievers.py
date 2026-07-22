import logging
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from config import MAX_RETRIEVER_CHUNKS

logger = logging.getLogger(__name__)

APP_KEYWORDS_MAP = {
    "shop":               ["shop", "producto", "product", "variante", "variant", "precio", "price", "brand", "marca"],
    "inventory":          ["inventario", "inventory", "stock", "stockrecord", "kardex", "entrada", "salida", "select_for_update", "register_exit", "register_entry"],
    "orders":             ["orden", "order", "pedido", "checkout", "orderitem", "coupon", "shippingaddress", "create_from_cart", "valid_from", "valid_to"],
    "payment":            ["confirm_order_payment", "codcommands", "codtransaction", "pago_contra_entrega", "cod_confirmed", "deduct_inventory", "_deduct_inventory_for_order"],
    "wompi":              ["wompi", "webhook", "pse", "tarjeta", "transaction", "WOMPI_EVENTS_SECRET", "signature", "sha256", "NequiTransaction", "CodTransaction", "TokenizedCard"],
    "technical_services": ["servicio", "service", "tecnico", "quotation", "cotizacion", "ServiceBooking", "ServiceVariant", "breakdown", "ServiceCostRule"],
    "renting":            ["renta", "alquiler", "equipo", "equipment", "wizard", "RentalRequest", "RentalPeriod"],
    "cart":               ["carrito", "cart", "cartitem"],
    "notifications":      ["notificacion", "notification", "whatsapp", "email", "dispatch_notification", "on_commit", "order_paid", "order_created", "order_cod_confirmed"],
    "users":              ["usuario", "user", "IsAdminUser", "is_staff", "is_superuser", "permiso", "permission", "IsAuthenticatedActiveUser", "IsCustomerUser"],
    "accounts":           ["perfil", "profile", "UserProfile", "technician", "tecnico", "user_type", "CUSTOMER", "TECHNICIAN"],
    "dashboard":          ["dashboard", "bff", "admin", "panel", "orchestrator"],
    "quotes":             ["quotes", "quote"],
    "marketing":          ["marketing", "campaign", "promocion"],
    "support":            ["support", "chat", "ChatRoom", "ChatMessage", "SupportChatConsumer"],
    "core":               ["core", "home", "feed", "HomeConfig", "footer", "FooterGroup", "FooterLink", "BrandSlider", "NavbarLink", "FooterCTA"],
    "kyc":                ["kyc", "verificacion", "verification", "UserVerification", "VerificationDocument", "ConsentRecord", "force_approve", "request_upgrade", "first_approved_at"],
    "security":           ["security", "seguridad", "SecurityEvent", "log_event", "audit", "auditoria"],
    "operations":         ["operations", "operaciones", "OperationTicket", "DispatcherProfile", "TrackingEvent", "despachador"],
    "shipping":           ["shipping", "envio", "envios"],
    "organization":       ["organization", "organizacion", "Company", "Branding", "ContactInfo", "SocialLink", "EmailSettings", "DomainSettings", "SeoSettings", "LegalEntityInfo"],
    # Frontend modules — prefijados con "frontend_" para no colisionar con backend
    "frontend_shop":               ["ProductList", "ProductForm", "CategoryList", "CategoryForm", "BrandList", "BrandForm", "TaxList", "TaxForm"],
    "frontend_renting":            ["RentingList", "RentingForm", "RentingDetail", "RentalCatalog", "RentalRequestWizard", "EquipmentDetail"],
    "frontend_technical_services": ["ServiceList", "ServiceForm", "ServicesCatalog", "ServiceDetail", "ServiceRequest", "ContractorSelection"],
    "frontend_orders":             ["OrderList", "OrderDetail", "CheckoutView", "OrderConfirmed"],
    "frontend_inventory":          ["InventoryList", "StockAdjust", "StockCreate"],
    "frontend_customer":           ["CustomerProfile", "CustomerOrders", "CustomerWishlist", "CustomerCards", "AccountSidebar", "CartOffcanvas", "CustomerFooter", "CustomerNavbar"],
    "frontend_landing":            ["HeroSection", "ModuleGrid", "FeaturedSection", "FlashOffers", "TrustSection", "DividerWave", "GlassCard", "LandingView", "HomeView", "BrandSlider", "FooterCTA", "IconRenderer"],
    "frontend_support":            ["SupportDashboard", "SupportChatWidget"],
    "frontend_core":               ["HomeConfigView", "DashboardView"],
    "frontend_organization":       ["OrganizationView"],
}

# Palabras clave que indican que la tarea es de FRONTEND (Vue)
FRONTEND_TASK_KEYWORDS = [
    "vue", "component", "componente", "composable", "vista", "view", ".vue",
    "script setup", "pinia", "store", "useapi", "usetoast", "useoffcanvas",
    "sinteloffcanvas", "offcanvas", "template", "v-model", "v-for", "v-if",
    "frontend", "vite", "bootstrap icons", "bi-", "ref(", "reactive(",
    "onmounted", "defineprops", "defineemits", "emit", "slot",
    "productlist", "productform", "rentinglist", "servicelist",
    "homeview", "landingview", "customerprofile", "shopcat",
    "heroSection", "modulegrid", "flashoffers",
]

# Palabras clave que indican que la tarea es de BACKEND (Django)
BACKEND_TASK_KEYWORDS = [
    "django", "viewset", "serializer", "command", "selector", "model",
    "celery", "consumer", "drf", "rest_framework", "transaction.atomic",
    "queryset", "filter(", "select_related", "prefetch_related",
    "migration", "signal", "permission_classes", "authentication_classes",
    "BaseCommand", "management command", "task.delay", "chord", "canvas",
]


def detect_task_type(text: str) -> str:
    """Detecta si la tarea es de frontend (Vue) o backend (Django)."""
    lower = text.lower()
    frontend_score = sum(1 for kw in FRONTEND_TASK_KEYWORDS if kw.lower() in lower)
    backend_score = sum(1 for kw in BACKEND_TASK_KEYWORDS if kw.lower() in lower)
    task_type = "frontend" if frontend_score > backend_score else "backend"
    logger.info(
        "[retrievers] detect_task_type: frontend=%d backend=%d → %s",
        frontend_score, backend_score, task_type,
    )
    return task_type


def detect_apps_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    detected = []
    for app, keywords in APP_KEYWORDS_MAP.items():
        if any(kw.lower() in text_lower for kw in keywords):
            detected.append(app)
    return detected or ["shop"]


def build_ensemble_retriever(
    vectorstore: Chroma,
    all_docs: list[Document],
    app_filter: str | None = None,
    k_bm25: int = 6,
    k_semantic: int = 8,
) -> EnsembleRetriever:
    corpus = all_docs
    chroma_filter: dict | None = None

    if app_filter:
        corpus = [d for d in all_docs if d.metadata.get("app_name") == app_filter]
        chroma_filter = {"app_name": {"$eq": app_filter}}
        if not corpus:
            logger.warning("[retrievers] Sin corpus BM25 para app_filter=%s, usando global", app_filter)
            corpus = all_docs

    bm25 = BM25Retriever.from_documents(corpus, k=k_bm25)

    search_kwargs: dict = {
        "k": k_semantic,
        "fetch_k": 25,
        "lambda_mult": 0.6,
    }
    if chroma_filter:
        search_kwargs["filter"] = chroma_filter

    semantic = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )

    return EnsembleRetriever(
        retrievers=[bm25, semantic],
        weights=[0.35, 0.65],
    )


def retrieve_context_for_task(
    query: str,
    vectorstore: Chroma,
    all_docs: list[Document],
    apps: list[str] | None = None,
) -> list[Document]:
    if not apps:
        apps = detect_apps_from_text(query)

    collected: list[Document] = []

    for app in apps:
        retriever = build_ensemble_retriever(vectorstore, all_docs, app_filter=app)
        docs = retriever.invoke(query)
        collected.extend(docs)

    global_docs = vectorstore.similarity_search(
        "reglas globales criticas arquitectura service layer decimal soft-delete transaction.on_commit",
        k=5,
        filter={"app_name": {"$in": ["global_rules", "architecture_contracts"]}},
    )
    collected.extend(global_docs)

    seen: set[int] = set()
    unique: list[Document] = []
    for doc in collected:
        h = hash(doc.page_content[:200])
        if h not in seen:
            seen.add(h)
            unique.append(doc)

    limited = unique[:MAX_RETRIEVER_CHUNKS]
    logger.info(
        "[retrievers] query='%s...' apps=%s -> %d chunks (dedup de %d)",
        query[:60], apps, len(limited), len(collected),
    )
    return limited


def retrieve_context_for_frontend_task(
    query: str,
    vectorstore: Chroma,
    all_docs: list[Document],
    apps: list[str] | None = None,
) -> list[Document]:
    """Retrieval especializado para tareas Vue/frontend."""
    # Docs frontend (vue, javascript, frontend_spec, skill)
    frontend_docs = [
        d for d in all_docs
        if d.metadata.get("language") in ("vue", "javascript")
        or d.metadata.get("doc_type") in ("frontend_spec", "skill")
        or d.metadata.get("layer") == "frontend"
    ]

    if not apps:
        # Detectar módulos frontend desde el texto
        detected = detect_apps_from_text(query)
        # Prefixar con "frontend_" para buscar en corpus frontend
        apps = [f"frontend_{a}" if f"frontend_{a}" in APP_KEYWORDS_MAP else a for a in detected]

    collected: list[Document] = []

    for app in apps:
        corpus = [d for d in frontend_docs if app in d.metadata.get("app_name", "")]
        if not corpus:
            corpus = frontend_docs  # fallback a todo el frontend corpus

        if not corpus:
            logger.warning("[retrievers] Sin corpus frontend para app=%s, usando all_docs", app)
            corpus = all_docs

        retriever = build_ensemble_retriever(vectorstore, corpus, app_filter=None, k_bm25=5, k_semantic=7)
        docs = retriever.invoke(query)
        collected.extend(docs)

    # Siempre agregar el registry de componentes y spec frontend
    global_fe_docs = [
        d for d in frontend_docs
        if d.metadata.get("doc_type") in ("frontend_spec", "skill")
        or "registry" in d.metadata.get("source", "").lower()
    ]
    collected.extend(global_fe_docs[:8])

    seen: set[int] = set()
    unique: list[Document] = []
    for doc in collected:
        h = hash(doc.page_content[:200])
        if h not in seen:
            seen.add(h)
            unique.append(doc)

    limited = unique[:MAX_RETRIEVER_CHUNKS]
    logger.info(
        "[retrievers] frontend query='%s...' apps=%s -> %d chunks",
        query[:60], apps, len(limited),
    )
    return limited
