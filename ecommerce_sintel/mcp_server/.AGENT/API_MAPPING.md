# API_MAPPING - recursos MCP -> endpoints de Django

Todas las rutas cuelgan de `/api/v1/dashboard/` y se verifican contra `/api/schema/` (OpenAPI). Lookup por `uuid`. Los ViewSets del panel no tipan su cuerpo en OpenAPI (p. ej. categorias/marcas), por eso **Django valida los datos al ejecutar** (400 con errores por campo) y el preview no puede validar el esquema.

| Recurso | Dominio | Ruta | Operaciones | Filtros REALES | Notas |
|---|---|---|---|---|---|
| `products` | shop | `products/` | list, get, create, update, delete | `search`, `is_active`, `is_featured` | sin `updated_at` en el serializador => version = hash |
| `categories` | shop | `categories/` | list, get, create, update, delete | ninguno | lista sin paginar (el MCP pagina) |
| `brands` | shop | `brands/` | list, get, create, update, delete | ninguno | idem |
| `taxes` | shop | `taxes/` | list, get | ninguno | solo lectura (afecta precios/facturacion) |
| `services` | services | `services/` | list, get | ninguno | solo lectura |
| `service-categories` | services | `service-categories/` | list, get | ninguno | solo lectura |
| `equipment` | renting | `equipment/` | list, get | `search`, `category__slug`, `brand__slug` | solo lectura |
| `renting-categories`, `renting-brands` | renting | `renting-categories/`, `renting-brands/` | list, get | ninguno | solo lectura |
| `orders` | orders | `orders/` | list, get | ninguno | solo lectura, PII enmascarada; transiciones = logica de Django |
| `quotations` | quotes | `quotations/` | list, get | ninguno | solo lectura, PII enmascarada |
| `payment-transactions` | payment | `payment-transactions/` | list, get | `status` | solo lectura, datos financieros |

Un filtro que Django ignoraria en silencio se **rechaza** (`INVALID_ARGUMENT`) para no dar resultados engañosos.
Delete: `DELETE <recurso>/<uuid>/` = borrado logico (204); el registro desaparece del listado. Al leerlo por uuid sigue siendo accesible.

## Dominios bloqueados (con motivo, ver `registry.BLOCKED_DOMAINS`)
marketing (envios = efectos externos: requieren workflows), support (datos personales de clientes), inventory (vive en `/api/v1/inventory/stock-records/`, no en `/dashboard/`),
users (SECURITY_SENSITIVE), notifications (EXTERNAL_SIDE_EFFECT). No se reintroducen rutas historicas eliminadas.

## Endpoint propio de Django para el MCP
`GET /api/v1/dashboard/mcp/whoami/` (`dashboard/api/mcp_views.py`): solo lectura, `IsAdminUser`; devuelve `{uuid, email, is_admin, is_staff, is_superuser}`. Existe porque `/auth/profile/` no expone `is_superuser`.
