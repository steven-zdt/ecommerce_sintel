"""
memory_builder.py - Sintel Memory System (Phases 9 & 10)

Builds:
  - APP_MEMORY/{app_name}.json   (per-app architecture knowledge)
  - GLOBAL_MEMORY.json           (cross-app architectural decisions)

Memory is KNOWLEDGE, not just code. It captures:
  - Architecture patterns per app
  - Known constraints and rules
  - Data flow contracts
  - Known issues / HOT_FIX notes
  - Business rules
  - Cross-app dependencies
  - Service contracts
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

AI_ENGINE_DIR   = Path(__file__).resolve().parent
MAP_PATH        = AI_ENGINE_DIR / "PROJECT_MAP.json"
APP_MEMORY_DIR  = AI_ENGINE_DIR / "APP_MEMORY"
GLOBAL_MEMORY   = AI_ENGINE_DIR / "GLOBAL_MEMORY.json"

# ---------------------------------------------------------------------------
# Static knowledge extracted from CLAUDE.md, .AGENT.md, and architecture docs
# ---------------------------------------------------------------------------

# Global architectural rules — distilled from CLAUDE.md + .AGENT.md
GLOBAL_RULES: dict = {
    "generated_at": "",
    "project": "Sintel E-Commerce REST v5",
    "stack": {
        "backend": "Django 5 + DRF + PostgreSQL + Redis + Celery + Channels",
        "frontend": "Vue 3 + Vite + Pinia + Vue Router + Axios",
        "auth": "JWT (simplejwt), email as USERNAME_FIELD",
        "payments": "Wompi Colombia (sandbox + production)",
        "realtime": "Django Channels + WebSocket",
        "async": "Celery + Redis",
    },
    "critical_rules": [
        {
            "id": "DECIMAL_MONEY",
            "rule": "All monetary values must be Decimal('X.XX'). Never float.",
            "why": "Float arithmetic causes rounding errors in financial calculations.",
        },
        {
            "id": "SOFT_DELETE",
            "rule": "Never call .delete() on business entities. Use is_active=False + is_deleted=True.",
            "why": "Maintains audit trail. Exception: CartItem and management commands.",
        },
        {
            "id": "NO_EMOJI_IN_PY",
            "rule": "No emoji or multibyte Unicode in .py files. Plain ASCII only.",
            "why": "Causes SyntaxError in Python which generates 500 in production.",
        },
        {
            "id": "SERVICE_LAYER",
            "rule": "ViewSets orchestrate HTTP only. All mutations in Commands with @transaction.atomic.",
            "why": "Separation of concerns; testability; atomic consistency.",
        },
        {
            "id": "SELECTOR_READ_ONLY",
            "rule": "Selectors are static, read-only. No .save(), .create(), .delete().",
            "why": "Ensures predictable side-effect-free queries.",
        },
        {
            "id": "NOTIFICATIONS_ON_COMMIT",
            "rule": "dispatch_notification and ws_notify ONLY inside transaction.on_commit(lambda: ...).",
            "why": "Prevents notifications firing on rolled-back transactions.",
        },
        {
            "id": "ADMIN_PERMISSION",
            "rule": "Always 'from users.api.permissions import IsAdminUser' (checks is_staff AND is_superuser).",
            "why": "rest_framework.permissions.IsAdminUser only checks is_staff, not is_superuser.",
        },
        {
            "id": "WOMPI_WEBHOOK_VERIFY",
            "rule": "All Wompi webhook views must call _verify_wompi_event_signature() before DB mutation.",
            "why": "Prevents replay attacks on payment webhooks.",
        },
        {
            "id": "NO_ROLE_FIELD",
            "rule": "No 'role' field on User. Profile is in accounts.UserProfile.user_type (CUSTOMER|TECHNICIAN|PROFESSIONAL|SPECIALIST).",
            "why": "DDD separation: auth in users/, profiles in accounts/.",
        },
        {
            "id": "UUID_IN_URLS",
            "rule": "Use UUID in public URLs, never integer PK. SintelBaseModel provides uuid.",
            "why": "Security: prevents enumeration attacks on resource IDs.",
        },
        {
            "id": "INVENTORY_LOCK",
            "rule": "Use stock_record.stock (select_for_update) for inventory writes, never InventorySelector.get_current_stock().",
            "why": "Selector may return stale cached value under concurrent load.",
        },
        {
            "id": "CONFIRM_PAYMENT",
            "rule": "Always call confirm_order_payment() from payment/shared/commands.py. Never duplicate inventory/notification logic.",
            "why": "confirm_order_payment is idempotent and handles all post-payment side effects.",
        },
        {
            "id": "COUPON_FILTER",
            "rule": "Filter coupons by active=True + valid_from__lte=now + valid_to__gte=now. Cap discount with min(discount, total_items_price).",
            "why": "Prevents expired/inactive coupons from being applied.",
        },
        {
            "id": "BASE_MODEL",
            "rule": "All business models must inherit from SintelBaseModel (provides uuid, created_at, updated_at, is_deleted).",
            "why": "Ensures consistent soft-delete, UUID URLs, and audit timestamps.",
        },
    ],
    "architectural_decisions": [
        {
            "id": "DDD_USERS_ACCOUNTS",
            "decision": "users/ handles auth only. accounts/ handles profiles (UserProfile, TechnicianProfile).",
            "date": "2025",
        },
        {
            "id": "PAYMENT_SSoT",
            "decision": "payment/shared/commands.py:confirm_order_payment() is the Single Source of Truth for post-payment logic.",
            "date": "2025",
        },
        {
            "id": "NOTIFICATIONS_CENTRALIZED",
            "decision": "dispatch_notification() replaces ws_notify in all 8 callers. Supports WS/Email/WhatsApp channels.",
            "date": "2025",
        },
        {
            "id": "COST_DECENTRALIZATION",
            "decision": "quotes.AdditionalCost removed. Each app has its own CostRule model + PricingCalculator.",
            "date": "2025",
        },
        {
            "id": "GRANULAR_PERMISSIONS",
            "decision": "IsBuyerOrAdmin for cart/orders/renting. IsServiceProviderUser for CV/skills/agenda.",
            "date": "2025",
        },
    ],
    "api_prefix_map": {
        "accounts":           "api/v1/auth",
        "users":              "api/v1/users",
        "dashboard":          "api/v1/dashboard",
        "shop":               "api/v1/shop",
        "cart":               "api/v1/cart",
        "orders":             "api/v1/orders",
        "payment":            "api/v1/payment",
        "inventory":          "api/v1/inventory",
        "technical_services": "api/v1/services",
        "quotes":             "api/v1/quotes",
        "marketing":          "api/v1/marketing",
        "renting":            "api/v1/renting",
        "core":               "api/v1/core",
        "notifications":      "api/v1/notifications",
        "operations":         "api/v1/operations",
        "support":            "api/v1/support",
        "shipping":           "api/v1/shipping",
    },
    "base_model": {
        "name": "SintelBaseModel",
        "file": "ecommerce/base_models.py",
        "fields": ["uuid (UUIDField, primary_key=False)", "created_at", "updated_at", "is_deleted (bool, default=False)"],
    },
    "patterns": {
        "command": "NombreCommands with @staticmethod @transaction.atomic methods",
        "selector": "NombreSelector with @staticmethod read-only methods returning QuerySet or Model",
        "viewset": "Inherits ReadOnlyModelViewSet/GenericViewSet/CreateModelMixin, never writes directly to DB",
        "model": "Always inherits SintelBaseModel, soft-delete via is_deleted",
        "notification": "transaction.on_commit(lambda: NotificationCommands.dispatch_notification(...))",
    },
}


# Per-app static knowledge: architecture, known constraints, services, events
APP_STATIC_KNOWLEDGE: dict[str, dict] = {
    "shop": {
        "purpose": "Product catalog management: products, variants, categories, brands, taxes, pricing rules",
        "key_models": ["Product", "ProductVariant", "Category", "Brand", "Tax", "ProductCostRule"],
        "constraints": [
            "vendor FK NOT NULL — always pass User.objects.filter(is_superuser=True).first() when creating Products via shell",
            "ProductVariant requires sku + pricing_strategy; FIXED strategy requires fixed_price",
        ],
        "services": ["ProductPricingService", "ProductCostRuleSelector"],
        "events": [],
        "known_issues": [],
    },
    "orders": {
        "purpose": "Purchase order lifecycle: creation from cart, status tracking, shipping addresses",
        "key_models": ["Order", "OrderItem", "ShippingAddress"],
        "constraints": [
            "create_from_cart() is the only valid way to create an Order — never create directly",
            "Coupon: filter by active=True + valid_from__lte=now + valid_to__gte=now",
            "Discount capped: min(coupon_discount, total_items_price)",
        ],
        "services": ["OrderCommands", "OrderSelector"],
        "events": ["order_created", "order_paid", "order_cod_confirmed"],
        "known_issues": [],
    },
    "cart": {
        "purpose": "Shopping cart: add/remove items, quantity updates, cart summary",
        "key_models": ["Cart", "CartItem"],
        "constraints": [
            "CartItem is one of 2 exceptions to soft-delete — cart.items.all().delete() is allowed",
        ],
        "services": ["CartCommands", "CartSelector"],
        "events": [],
        "known_issues": [],
    },
    "payment": {
        "purpose": "Multi-method payment: Wompi online, Nequi, COD (cash-on-delivery)",
        "key_models": ["TokenizedCard", "CodTransaction", "NequiTransaction"],
        "constraints": [
            "confirm_order_payment() is idempotent SSoT for post-payment (inventory, notifications)",
            "Wompi webhooks MUST call _verify_wompi_event_signature() before any DB mutation",
            "COD does NOT use confirm_order_payment() — handled by CodCommands separately",
        ],
        "services": ["WompiCommands", "NequiCommands", "CodCommands", "confirm_order_payment"],
        "events": ["payment_confirmed", "payment_failed"],
        "known_issues": [
            "Wompi sandbox webhooks cannot reach localhost — /orden-confirmada shows PENDING status in dev",
        ],
    },
    "inventory": {
        "purpose": "Stock management: entries, exits, kardex, select_for_update on stock writes",
        "key_models": ["InventoryRecord", "StockRecord"],
        "constraints": [
            "Use stock_record.stock (select_for_update) for writes — never InventorySelector.get_current_stock() which may be stale",
            "register_entry / register_exit must be atomic",
        ],
        "services": ["InventoryCommands", "InventorySelector"],
        "events": ["stock_updated", "stock_low"],
        "known_issues": [],
    },
    "notifications": {
        "purpose": "Centralized notification dispatch: WebSocket, Email, WhatsApp channels",
        "key_models": ["Notification", "NotificationTemplate", "NotificationChannel"],
        "constraints": [
            "Always use dispatch_notification() — never direct ws_notify() anymore",
            "dispatch_notification MUST be called inside transaction.on_commit(lambda: ...)",
            "8 NotificationTemplate seeds in BD (order_created, order_paid, etc.)",
        ],
        "services": ["NotificationCommands", "dispatch_notification"],
        "events": ["order_created", "order_paid", "order_cod_confirmed"],
        "known_issues": [],
    },
    "accounts": {
        "purpose": "User profiles: UserProfile (user_type), TechnicianProfile, customer dashboard",
        "key_models": ["UserProfile", "TechnicianProfile"],
        "constraints": [
            "No 'role' field on User — use accounts.UserProfile.user_type",
            "user_type choices: CUSTOMER | TECHNICIAN | PROFESSIONAL | SPECIALIST",
            "Admins identified by is_staff=True AND is_superuser=True",
            "TechnicianProfile.specialties related_name='technician_profiles'",
        ],
        "services": ["ProfileCommands", "ProfileSelector"],
        "events": [],
        "known_issues": [],
    },
    "users": {
        "purpose": "Authentication only: JWT login, registration, password reset. No profile data.",
        "key_models": [],
        "constraints": [
            "users/ handles auth only — profile data is in accounts/",
            "IsCustomerUser is alias for IsAuthenticatedActiveUser",
            "Always 'from users.api.permissions import IsAdminUser' (not rest_framework.permissions)",
        ],
        "services": ["AdminLoginView"],
        "events": [],
        "known_issues": [],
    },
    "renting": {
        "purpose": "Equipment rental: wizard flow, rental requests, rental periods, pricing",
        "key_models": ["RentalRequest", "RentalPeriod", "Equipment"],
        "constraints": [
            "RentalRequest created via 8-step wizard at /alquiler/equipo/:uuid/solicitar",
            "Migration 0003 applied — RentalRequest model active",
        ],
        "services": ["RentalCommands", "RentalPricingCalculator"],
        "events": ["rental_request_created"],
        "known_issues": [],
    },
    "technical_services": {
        "purpose": "Technician services: catalog, booking, service variants, cost rules",
        "key_models": ["TechnicalService", "ServiceVariant", "ServiceBooking", "ServiceCostRule"],
        "constraints": [
            "vendor/category/level are null=True (optional)",
            "ServiceVariant requires sku + pricing_strategy; FIXED requires fixed_price",
            "API prefix is 'services/' not 'technical_services/'",
        ],
        "services": ["ServiceCommands", "ServiceSelector", "ServicePricingCalculator"],
        "events": ["service_booked"],
        "known_issues": [],
    },
    "support": {
        "purpose": "Real-time support chat: ChatRoom, ChatMessage, SupportChatConsumer WebSocket",
        "key_models": ["ChatRoom", "ChatMessage"],
        "constraints": [
            "JWTAuthMiddleware uses deferred imports to avoid circular imports",
            "SupportChatConsumer handles WS connections",
        ],
        "services": ["SupportChatConsumer"],
        "events": ["chat_message_received"],
        "known_issues": [],
    },
    "core": {
        "purpose": "Public home feed, featured products/services, Home Config (banners/modules/cards/CTA/brand slider) and footer/navbar site customization",
        "key_models": ["HomeBanner", "HomeModuleConfig", "HomeCard", "HomeCardGroup", "FooterCTAConfig", "FooterGroup", "FooterLink", "NavbarLink", "BrandSliderItem", "BrandSliderConfig"],
        "constraints": [
            "GET /api/v1/core/home-feed/ is public (no auth), cached 5 min (sintel_home_feed_v1); incluye 'brand_slider': {config, items}",
            "GET /api/v1/core/footer/ es publico, cache separado (sintel_footer_v1); 'groups' (FooterGroup+FooterLink por FK) reemplazo a 'nav_groups' (texto libre) el 2026-07-15",
            "FooterLink.group_name (CharField) fue eliminado -- ahora FooterLink.group es FK a FooterGroup (migraciones core 0023-0025)",
            "SiteBrandConfig y CompanyContactInfo fueron eliminados de core el 2026-07-12 (migrados a organization.Company/Branding/ContactInfo)",
            "IconRenderer.vue (frontend/src/components/ui/IconRenderer.vue) es el unico componente de render de iconos Bootstrap Icons, con fallback y normalizacion de atajos (core/api/serializers.py::normalize_icon_class)",
        ],
        "services": ["HomeFeedSelector", "HomeConfigSelector/Commands", "HomeCardSelector/Commands", "HomeCardGroupSelector/Commands", "FooterSelector/Commands", "FooterGroupSelector/Commands", "BrandSliderSelector/Commands", "NavbarLinkSelector/Commands", "FooterCTASelector/Commands"],
        "events": [],
        "known_issues": [],
    },
    "quotes": {
        "purpose": "Quotation requests for custom orders and services",
        "key_models": ["Quote", "QuoteItem"],
        "constraints": [
            "quotes.AdditionalCost was eliminated — cost rules are now per-app",
        ],
        "services": ["QuoteCommands", "QuoteSelector"],
        "events": ["quote_created"],
        "known_issues": [],
    },
    "marketing": {
        "purpose": "Campaigns, flash offers, promotional pricing",
        "key_models": ["MarketingCampaign", "FlashOffer"],
        "constraints": [],
        "services": ["MarketingCommands"],
        "events": [],
        "known_issues": [],
    },
    "dashboard": {
        "purpose": "BFF (Backend for Frontend) — orchestrates data for admin panel. No business logic.",
        "key_models": [],
        "constraints": [
            "Dashboard ViewSets are read-only aggregators — no writes",
            "All writes must go through the domain app's endpoints",
        ],
        "services": [],
        "events": [],
        "known_issues": [],
    },
    "operations": {
        "purpose": "Operational scheduling, field operations tracking",
        "key_models": [],
        "constraints": [],
        "services": [],
        "events": [],
        "known_issues": [],
    },
    "shipping": {
        "purpose": "Shipping address management and delivery calculations",
        "key_models": [],
        "constraints": [],
        "services": [],
        "events": [],
        "known_issues": [],
    },
    "kyc": {
        "purpose": "Identity verification (KYC) — required only for CUSTOMER-to-professional upgrade, not for base registration",
        "key_models": ["UserVerification", "VerificationDocument", "VerificationEvent", "ConsentRecord"],
        "constraints": [
            "SSoT identidad CUSTOMER-first: el registro SIEMPRE crea un CUSTOMER instantaneo — KYC ya no es un gate universal de registro",
            "El upgrade a profesional (request_upgrade) reabre la MISMA UserVerification en vez de crear una nueva",
            "first_approved_at (no reviewed_at) es la senal correcta de 'aprobado alguna vez' — reviewed_at cambia en cada revision",
            "force_approve permite aprobacion manual desde /panel/usuarios sin pasar por el flujo de documentos",
            "REQUIRED_DOC_TYPES_BY_TYPE define los documentos requeridos segun el tipo de perfil solicitado",
            "kyc.api.urls esta montado en api/v1/auth/ — comparte namespace con accounts, no tiene prefijo propio",
        ],
        "services": ["KycCommands", "KycSelector"],
        "events": ["kyc_submitted_for_review", "kyc_approved", "kyc_rejected", "kyc_info_requested", "kyc_blocked"],
        "known_issues": [],
    },
    "security": {
        "purpose": "Security event logging/audit trail across the platform (SecurityEvent) — not authentication itself",
        "key_models": ["SecurityEvent"],
        "constraints": [
            "log_event() NUNCA debe llamarse dentro de un bloque @transaction.atomic que pueda hacer rollback — el evento se perdia silenciosamente (bug real corregido)",
            "log_event() NO pasa por dispatch_notification — escribe directo el modelo SecurityEvent, no dispara notificaciones WS/Email/WhatsApp",
            "Sanitizacion XSS con strip_tags aplicada en 7 serializers de core tras la certificacion 'CON OBSERVACIONES'",
            "Mapeado en api/v1/security/health/ (montado en api/v1/, no en un prefijo api/v1/security propio a nivel de include)",
        ],
        "services": ["SecurityCommands", "SecuritySelector"],
        "events": [],
        "known_issues": [],
    },
    "organization": {
        "purpose": "Institutional company data: branding, contact info, social links, SEO and domain/email settings — SSoT since the 2026-07-12 migration out of core",
        "key_models": ["Company", "Branding", "ContactInfo", "SocialLink", "EmailSettings", "DomainSettings", "SeoSettings", "LegalEntityInfo"],
        "constraints": [
            "Creada 2026-07-12: SiteBrandConfig/CompanyContactInfo/FooterLink(category='social') migrados desde core a Company/Branding/ContactInfo/SocialLink",
            "No usa signals para invalidar cache -- la invalidacion de site-config/footer cache es explicita en dashboard/api/views.py tras cada OrganizationCommands.upsert_*",
            "Montada en api/v1/organization/ (ecommerce/urls.py)",
            "Panel admin: /panel/organizacion (frontend/src/modules/organization/OrganizationView.vue)",
        ],
        "services": ["OrganizationSelector", "OrganizationCommands"],
        "events": [],
        "known_issues": [],
    },
}


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------

def build_app_memory(app_name: str, app_data: dict) -> dict:
    """Build per-app memory combining static knowledge + dynamic data from PROJECT_MAP."""
    static = APP_STATIC_KNOWLEDGE.get(app_name, {})

    dynamic_models    = [m["name"] for m in app_data.get("models", [])]
    dynamic_viewsets  = [v["name"] for v in app_data.get("viewsets", [])]
    dynamic_endpoints = [p.get("prefix", "") for p in app_data.get("url_patterns", [])]
    dynamic_mgmt_cmds = [c["name"] for c in app_data.get("management_commands", [])]
    dynamic_tasks     = [t["name"] for t in app_data.get("tasks", [])]
    dynamic_consumers = [c["name"] for c in app_data.get("consumers", [])]

    return {
        "app": app_name,
        "api_prefix": app_data.get("api_prefix", f"api/v1/{app_name}"),
        "purpose": static.get("purpose", ""),
        "architecture": {
            "models": dynamic_models,
            "viewsets": dynamic_viewsets,
            "serializers": [s["name"] for s in app_data.get("serializers", [])],
            "url_patterns": dynamic_endpoints,
            "management_commands": dynamic_mgmt_cmds,
            "celery_tasks": dynamic_tasks,
            "consumers": dynamic_consumers,
            "migrations": len(app_data.get("migrations", [])),
        },
        "key_models": static.get("key_models", dynamic_models[:5]),
        "services": static.get("services", [s["name"] for s in app_data.get("services", [])[:5]]),
        "constraints": static.get("constraints", []),
        "events": static.get("events", []),
        "patterns": {
            "command_class": f"{app_name.capitalize()}Commands",
            "selector_class": f"{app_name.capitalize()}Selector",
            "service_layer": True,
            "soft_delete": True,
        },
        "known_issues": static.get("known_issues", []),
        "TODO": [],
        "BUG": [],
        "HOT_FIX": [],
        "decisions": [],
    }


def build_all_memories() -> dict[str, dict]:
    """Build per-app memories and global memory. Returns {app_name: memory_dict}."""
    import datetime

    if not MAP_PATH.exists():
        logger.error("[memory_builder] PROJECT_MAP.json not found")
        return {}

    pmap = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    APP_MEMORY_DIR.mkdir(exist_ok=True)

    now = datetime.datetime.now(datetime.UTC).isoformat()
    memories: dict[str, dict] = {}

    # Per-app memories
    for app_name, app_data in pmap.get("apps", {}).items():
        mem = build_app_memory(app_name, app_data)
        mem["generated_at"] = now
        memories[app_name] = mem
        out_path = APP_MEMORY_DIR / f"{app_name}.json"
        out_path.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[memory_builder] Written %s", out_path.name)

    # Global memory
    global_mem = dict(GLOBAL_RULES)
    global_mem["generated_at"] = now
    global_mem["app_count"] = len(memories)
    global_mem["apps"] = list(memories.keys())
    GLOBAL_MEMORY.write_text(json.dumps(global_mem, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[memory_builder] Written GLOBAL_MEMORY.json")

    return memories


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

_app_memories: dict[str, dict] = {}
_global_memory: dict = {}


def get_app_memory(app_name: str) -> dict:
    global _app_memories
    if app_name not in _app_memories:
        path = APP_MEMORY_DIR / f"{app_name}.json"
        if path.exists():
            _app_memories[app_name] = json.loads(path.read_text(encoding="utf-8"))
        else:
            _app_memories[app_name] = {}
    return _app_memories[app_name]


def get_global_memory() -> dict:
    global _global_memory
    if not _global_memory:
        if GLOBAL_MEMORY.exists():
            _global_memory = json.loads(GLOBAL_MEMORY.read_text(encoding="utf-8"))
    return _global_memory


def get_memory_context(apps: list[str]) -> str:
    """Returns a compact memory context string for LLM prompt injection."""
    lines = []
    gm = get_global_memory()

    # Inject critical rules relevant to the task
    lines.append("=== REGLAS GLOBALES CRITICAS ===")
    for rule in gm.get("critical_rules", [])[:6]:
        lines.append(f"  [{rule['id']}] {rule['rule']}")
    lines.append("")

    # Per-app knowledge
    for app in apps:
        mem = get_app_memory(app)
        if not mem:
            continue
        lines.append(f"=== CONOCIMIENTO APP [{app}] ===")
        if mem.get("purpose"):
            lines.append(f"  Proposito: {mem['purpose']}")
        if mem.get("constraints"):
            lines.append("  Restricciones:")
            for c in mem["constraints"][:3]:
                lines.append(f"    - {c}")
        if mem.get("events"):
            lines.append(f"  Eventos: {', '.join(mem['events'])}")
        if mem.get("known_issues"):
            lines.append("  Issues conocidos:")
            for ki in mem["known_issues"][:2]:
                lines.append(f"    - {ki}")
        lines.append("")

    return "\n".join(lines)
