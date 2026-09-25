"""
mcp_server/registry.py -- registro DECLARATIVO de recursos y operaciones permitidas (plan MCP sec. 7-10, 27).

Un `resource` solo existe si esta aqui. No hay "ejecutar URL arbitraria". Cada operacion lleva su riesgo; el borrado respeta la politica del proyecto (soft-delete, `delete_semantics`).
Habilitacion PROGRESIVA por dominio: lo que no esta aqui (marketing, support, inventory, users, notifications...) esta bloqueado a proposito y `api.describe` dice por que.
Las rutas se verifican contra el OpenAPI real de Django (`openapi.py`): una operacion que no existe alli se trata como no disponible (las escrituras fallan cerradas).

IMPORTANTE (plan sec. 9): inventario NO vive bajo /api/v1/dashboard/inventory/ (se consolido en /api/v1/inventory/stock-records/): no se reintroducen rutas historicas.
"""
from dataclasses import dataclass, field

READ_OPS = ("list", "get")
WRITE_OPS = ("create", "update", "delete")
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class Resource:
    name: str
    domain: str
    api_tail: str                      # ruta bajo /api/v1/dashboard/ (con "/" final)
    description: str
    operations: tuple = READ_OPS
    risk: dict = field(default_factory=dict)        # operacion -> low|medium|high (default: list/get low, create/update medium, delete high)
    filters: tuple = ("search", "is_active")
    sensitive: bool = False                          # datos personales o financieros: solo lectura y salida mas acotada
    delete_semantics: str = "soft"                   # soft-delete/is_active=False segun el dominio (regla del proyecto)
    detail_param: str = "uuid"
    detail_via_list: bool = False                    # Django no expone GET de detalle (solo PATCH): la lectura de un registro se resuelve buscando su uuid en el listado

    def allows(self, op: str) -> bool:
        return op in self.operations

    def risk_of(self, op: str) -> str:
        default = {"list": "low", "get": "low", "create": "medium", "update": "medium", "delete": "high"}
        return self.risk.get(op, default[op])

    @property
    def list_path(self) -> str:
        return f"/api/v1/dashboard/{self.api_tail}"

    @property
    def detail_path(self) -> str:
        return f"/api/v1/dashboard/{self.api_tail}{{{self.detail_param}}}/"

    def openapi_operations(self) -> dict:
        """operacion -> (metodo HTTP, plantilla de ruta OpenAPI)."""
        return {"list": ("get", self.list_path), "create": ("post", self.list_path), "get": ("get", self.list_path if self.detail_via_list else self.detail_path),
                "update": ("patch", self.detail_path), "delete": ("delete", self.detail_path)}


# Filtros REALES de cada ViewSet (verificados en dashboard/api/views.py): Django ignora en silencio los query params que no conoce, asi que solo se permiten estos.
_PRODUCT_FILTERS = ("search", "is_active", "is_featured")
_EQUIPMENT_FILTERS = ("search", "category__slug", "brand__slug")
_NO_FILTERS = ()

RESOURCES: tuple = (
    # --- shop (escritura habilitada: catalogo) ---
    Resource("products", "shop", "products/", "Productos del catalogo de tienda.", READ_OPS + WRITE_OPS, filters=_PRODUCT_FILTERS),
    Resource("categories", "shop", "categories/", "Categorias de productos.", READ_OPS + WRITE_OPS, filters=_NO_FILTERS),
    Resource("brands", "shop", "brands/", "Marcas de productos.", READ_OPS + WRITE_OPS, filters=_NO_FILTERS),
    Resource("taxes", "shop", "taxes/", "Impuestos configurados (solo lectura: afectan precios y facturacion).", filters=_NO_FILTERS),
    # --- services / renting / quotes / orders / payment: solo lectura por ahora ---
    Resource("services", "services", "services/", "Servicios tecnicos ofrecidos.", READ_OPS + WRITE_OPS, filters=_NO_FILTERS),
    Resource("service-categories", "services", "service-categories/", "Categorias de servicios tecnicos.", READ_OPS + WRITE_OPS, filters=_NO_FILTERS),
    Resource("equipment", "renting", "equipment/", "Equipos de alquiler (los precios por dia/variantes y la logistica tienen sub-endpoints propios aun no habilitados en el MCP).", READ_OPS + WRITE_OPS, filters=_EQUIPMENT_FILTERS),
    Resource("renting-categories", "renting", "renting-categories/", "Categorias de alquiler.", READ_OPS + WRITE_OPS, filters=_NO_FILTERS),
    Resource("renting-brands", "renting", "renting-brands/", "Marcas de alquiler.", READ_OPS + WRITE_OPS, filters=_NO_FILTERS),
    # --- sitio web (home/navbar/footer/about): Django solo expone listado + PATCH por uuid (no crea ni borra desde el panel) ---
    Resource("home-cards", "site", "home-cards/", "Tarjetas del home del sitio web (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("home-card-groups", "site", "home-card-groups/", "Grupos de tarjetas del home (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("feature-banner-sections", "site", "feature-banner-sections/", "Secciones de banners destacados del home (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("feature-banner-blocks", "site", "feature-banner-blocks/", "Bloques de banners destacados del home (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("footer-groups", "site", "footer-groups/", "Grupos de enlaces del footer (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("navbar", "site", "navbar/", "Elementos de la barra de navegacion (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("brand-slider", "site", "brand-slider/", "Carrusel de marcas del home (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("about-us", "site", "about-us/", "Contenido de la pagina Nosotros (solo editar).", ("list", "get", "update"), filters=_NO_FILTERS, detail_via_list=True),
    Resource("orders", "orders", "orders/", "Pedidos (solo lectura: las transiciones de estado son logica de negocio de Django).",
             filters=_NO_FILTERS, sensitive=True),
    Resource("quotations", "quotes", "quotations/", "Cotizaciones (solo lectura).", filters=_NO_FILTERS, sensitive=True),
    Resource("payment-transactions", "payment", "payment-transactions/", "Transacciones de pago (solo listado: Django no expone detalle; datos financieros).",
             ("list",), filters=("status",), sensitive=True),
)

_BY_NAME = {r.name: r for r in RESOURCES}

# Dominios bloqueados a proposito (con motivo): aparecen en api.describe, no en el CRUD.
BLOCKED_DOMAINS = {
    "marketing": "Los envios (campanas, WhatsApp) tienen efectos externos: requieren workflows dedicados (campaign.prepare/preview/send), no CRUD generico.",
    "support": "Contiene conversaciones y datos personales de clientes: no se habilita hasta definir una politica de minimizacion.",
    "inventory": "La administracion vive en /api/v1/inventory/stock-records/ (no en /dashboard/): pendiente de habilitar con sus propias reglas.",
    "users": "Usuarios y permisos son SECURITY_SENSITIVE: fuera del alcance del MCP en esta fase.",
    "notifications": "Los envios de notificaciones son EXTERNAL_SIDE_EFFECT: requieren workflow y confirmacion propios.",
}


def get_resource(name: str) -> Resource:
    from . import errors
    from .errors import McpToolError

    resource = _BY_NAME.get(str(name))
    if resource is None:
        raise McpToolError(errors.RESOURCE_NOT_ALLOWED, f"El recurso '{str(name)[:40]}' no esta registrado. Usa api.describe para ver los disponibles.")
    return resource


def require_operation(resource: Resource, op: str) -> None:
    from . import errors
    from .errors import McpToolError

    if not resource.allows(op):
        raise McpToolError(errors.OPERATION_NOT_ALLOWED, f"La operacion '{op}' no esta habilitada para '{resource.name}'.", allowed=list(resource.operations))
