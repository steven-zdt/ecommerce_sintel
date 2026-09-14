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

def detect_apps_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    detected = []
    for app, keywords in APP_KEYWORDS_MAP.items():
        if any(kw.lower() in text_lower for kw in keywords):
            detected.append(app)
    return detected or ["shop"]


SAFE_KNOWLEDGE_LANGUAGE = "markdown"
# Knowledge Governance (Fase 17, 2026-08-08): "markdown" solo evita codigo fuente --
# no evita documentacion INTERNA de arquitectura/ingenieria (.AGENT/docs, docs/specs,
# ai_skills) que tambien es markdown pero jamas deberia llegar a un cliente. Un
# hallazgo real en vivo: una pregunta sobre "horario de atencion" recupero un
# fragmento de arquitectura de agendamiento tecnico y el LLM fabrico una respuesta a
# partir de eso. visibility=="public" es el filtro real -- ver loaders.py
# (_PUBLIC_DOC_TYPES, hoy vacio: no existe todavia contenido curado para clientes).
SAFE_KNOWLEDGE_VISIBILITY = "public"


def _safe_knowledge_filter(app: str | None) -> dict:
    base = [{"language": {"$eq": SAFE_KNOWLEDGE_LANGUAGE}}, {"visibility": {"$eq": SAFE_KNOWLEDGE_VISIBILITY}}]
    if app:
        base.append({"app_name": {"$eq": app}})
    return {"$and": base}


def retrieve_knowledge_for_chat(
    query: str,
    vectorstore: Chroma,
    all_docs: list[Document],
    apps: list[str] | None = None,
) -> list[Document]:
    """
    Retrieval para /chat (Support Agent) -- SOLO documentacion PUBLICA
    (metadata.language == "markdown" Y metadata.visibility == "public").
    Nunca devuelve codigo fuente Python/Vue/JS ni documentacion interna de
    ingenieria (aunque sea markdown) -- nada de eso es apropiado como
    contexto para responder a un cliente. Ver AI_SUPPORT_SCOPE.md seccion 6
    y AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md hallazgo 1 (2026-08-08).

    Nota: _PUBLIC_DOC_TYPES (loaders.py) esta vacio hoy -- no existe todavia
    contenido curado para clientes en el repo, asi que esta funcion devuelve
    lista vacia hasta que se autoren documentos reales de FAQ/politicas/
    garantias marcados visibility="public". Es el comportamiento correcto:
    preferir "no tengo esa informacion" a inventar una respuesta.

    Fallback de produccion (auditoria de puesta en produccion, 2026-08-17):
    vectorstore puede ser None si ChromaDB no estaba disponible al arrancar
    sintel_ai (ver main.py::lifespan) -- se degrada a "sin conocimiento" en vez
    de un AttributeError. Hoy esto nunca se ejercita en la practica (sin docs
    publicos, `corpus` siempre queda vacio antes de llegar a este punto), pero
    no debe depender de esa coincidencia de datos.
    """
    if vectorstore is None:
        return []
    if not apps:
        apps = detect_apps_from_text(query)

    safe_docs = [
        d for d in all_docs
        if d.metadata.get("language") == SAFE_KNOWLEDGE_LANGUAGE
        and d.metadata.get("visibility") == SAFE_KNOWLEDGE_VISIBILITY
    ]

    collected: list[Document] = []
    for app in apps:
        corpus = [d for d in safe_docs if d.metadata.get("app_name") == app] or safe_docs
        if not corpus:
            continue
        bm25 = BM25Retriever.from_documents(corpus, k=6)
        semantic = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 8, "fetch_k": 25, "lambda_mult": 0.6, "filter": _safe_knowledge_filter(app)},
        )
        retriever = EnsembleRetriever(retrievers=[bm25, semantic], weights=[0.35, 0.65])
        collected.extend(retriever.invoke(query))

    seen: set[int] = set()
    unique: list[Document] = []
    for doc in collected:
        h = hash(doc.page_content[:200])
        if h not in seen:
            seen.add(h)
            unique.append(doc)

    limited = unique[:MAX_RETRIEVER_CHUNKS]
    # Knowledge Governance (Fase 17): loguear la fuente exacta de cada chunk usado --
    # antes era imposible auditar retroactivamente que documento (y que tan
    # actualizado) sustento una respuesta dada.
    sources = [
        {"source": d.metadata.get("source"), "updated_at": d.metadata.get("updated_at")}
        for d in limited
    ]
    logger.info(
        "[retrievers] chat-knowledge query='%s...' apps=%s -> %d chunks (dedup de %d, solo markdown+public) sources=%s",
        query[:60], apps, len(limited), len(collected), sources,
    )
    return limited
