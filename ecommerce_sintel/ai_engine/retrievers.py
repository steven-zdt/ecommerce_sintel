"""
retrievers.py

FASE 3 (mision de simplificacion arquitectonica, 2026-09-14, ver
AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md): retrieve_knowledge_for_chat
ya NO habla con ChromaDB directo -- delega en el endpoint interno de Django
`ai_knowledge` (RetrievalService sobre PostgreSQL + pgvector, FASE 1/2, ya
construido y validado). Mismo motivo que el resto de /internal/ai/* (ver
tools/http_bridge.py): AI Engine corre como proceso separado y no debe
importar Postgres directo.

Filtro de gobernanza (visibility=="public", nunca contenido interno de
ingenieria a un cliente -- ver AI_SUPPORT_SCOPE.md seccion 6) ahora vive
server-side en ai_knowledge.services.selectors.RetrievalService, no aqui --
este archivo confia en la respuesta de Django, no la re-filtra.
"""
import logging

import httpx

from config import DJANGO_INTERNAL_API_URL, internal_django_headers

logger = logging.getLogger(__name__)

_KNOWLEDGE_RETRIEVE_URL = f"{DJANGO_INTERNAL_API_URL}/internal/ai/knowledge/retrieve/"
_TIMEOUT_SECONDS = 8

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


async def retrieve_knowledge_for_chat(query: str, apps: list[str] | None = None, k: int = 8) -> list[dict]:
    """
    Retrieval para /chat (Support Agent) -- SOLO documentacion PUBLICA. La
    gobernanza (nunca devolver contenido interno de ingenieria/codigo fuente
    a un cliente, ver AI_SUPPORT_SCOPE.md seccion 6) la aplica Django
    (ai_knowledge.services.selectors.RetrievalService), no este archivo.

    Retorna [] (nunca lanza) si Django no responde o no hay conocimiento
    relevante -- mismo criterio de degradacion con gracia que ya tenia esta
    funcion con vectorstore=None sobre ChromaDB.

    Cada elemento: {"content", "source", "app_name", "title", "updated_at"}
    -- ya NO son langchain Document (sin .page_content); ver
    action_graph.py::node_retrieve_knowledge para el consumidor real.
    """
    if not apps:
        apps = detect_apps_from_text(query)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                _KNOWLEDGE_RETRIEVE_URL,
                json={"query": query, "app_names": apps, "k": k},
                headers=internal_django_headers(),
            )
        if resp.status_code != 200:
            logger.warning("[retrievers] ai_knowledge/retrieve respondio %d, sin conocimiento para este turno", resp.status_code)
            return []
        chunks = resp.json().get("chunks", [])
    except httpx.HTTPError as exc:
        logger.warning("[retrievers] ai_knowledge inalcanzable (%s), sin conocimiento para este turno", exc)
        return []

    logger.info("[retrievers] chat-knowledge query='%s...' apps=%s -> %d chunks", query[:60], apps, len(chunks))
    return chunks
