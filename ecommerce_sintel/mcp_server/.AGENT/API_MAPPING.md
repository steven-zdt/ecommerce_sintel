# API_MAPPING - recursos MCP -> endpoints de Django

Todas las rutas cuelgan de `/api/v1/dashboard/` y se verifican contra `/api/schema/` (OpenAPI). Lookup por `uuid`. Los ViewSets del panel no tipan su cuerpo en OpenAPI (p. ej. categorias/marcas), por eso **Django valida los datos al ejecutar** (400 con errores por campo) y el preview no puede validar el esquema.

| Recurso | Dominio | Ruta | Operaciones | Filtros REALES | Notas |
|---|---|---|---|---|---|
| `products` | shop | `products/` | list, get, create, update, delete | `search`, `is_active`, `is_featured` | sin `updated_at` en el serializador => version = hash |
| `categories` | shop | `categories/` | list, get, create, update, delete | ninguno | lista sin paginar (el MCP pagina) |
| `brands` | shop | `brands/` | list, get, create, update, delete | ninguno | idem |
| `taxes` | shop | `taxes/` | list, get | ninguno | solo lectura (afecta precios/facturacion) |
| `services` | services | `services/` | list, get, create, update, delete | ninguno | lectura y escritura (borrado logico) |
| `service-categories` | services | `service-categories/` | list, get, create, update, delete | ninguno | lectura y escritura |
| `equipment` | renting | `equipment/` | list, get, create, update, delete | `search`, `category__slug`, `brand__slug` | lectura y escritura del equipo; variantes/precios por dia y logistica son sub-endpoints (`equipment/<uuid>/variants/`, `/logistics/`) NO habilitados aun |
| `renting-categories`, `renting-brands` | renting | `renting-categories/`, `renting-brands/` | list, get, create, update, delete | ninguno | lectura y escritura |
| `home-cards`, `home-card-groups`, `feature-banner-sections`, `feature-banner-blocks`, `footer-groups`, `navbar`, `brand-slider`, `about-us` | site | `<recurso>/` | list, get, update | ninguno | sitio web: Django solo expone listado y PATCH (sin GET de detalle: el MCP lo resuelve buscando el uuid en el listado, `detail_via_list`); no crea ni borra. Singletons (`footer`, `site-brand`, `footer-cta`, `home-config`) no incluidos |
| `orders` | orders | `orders/` | list, get | ninguno | solo lectura, PII enmascarada; transiciones = logica de Django |
| `quotations` | quotes | `quotations/` | list, get | ninguno | solo lectura, PII enmascarada |
| `payment-transactions` | payment | `payment-transactions/` | list | `status` | solo listado (Django no expone detalle; hallazgo de business.audit 2026-09-25), datos financieros |

Un filtro que Django ignoraria en silencio se **rechaza** (`INVALID_ARGUMENT`) para no dar resultados engañosos.
Delete: `DELETE <recurso>/<uuid>/` = borrado logico (204); el registro desaparece del listado. Al leerlo por uuid sigue siendo accesible.

## Dominios bloqueados (con motivo, ver `registry.BLOCKED_DOMAINS`)
marketing (envios = efectos externos: requieren workflows), support (datos personales de clientes), inventory (vive en `/api/v1/inventory/stock-records/`, no en `/dashboard/`),
users (SECURITY_SENSITIVE), notifications (EXTERNAL_SIDE_EFFECT). No se reintroducen rutas historicas eliminadas.

## Limites reales al escribir por MCP (verificado en produccion, 2026-09-30)

- **Campos anidados se ignoran sin avisar:** `crud.update` sobre `equipment` acepta `marketing` y `logistics_config` (el preview los muestra y el update responde `ok`), pero Django no los guarda; verificar siempre con `crud.get` tras escribir. Los textos anidados de un equipo se editan desde el panel o con un sub-endpoint aun no habilitado.
- **`services` create acepta `initial_variant`** (`pricing_strategy`, `estimated_hours`, `complexity_factor`, `fixed_price`; incluso `fixed_price = 0.00`) y crea la variante por defecto. **update lo descarta** (`unknown_fields`), y el MCP no expone `service-variants`: no se puede dar precio a un servicio que ya existe sin variante (ej. id 5 "Mantenimiento y Configuracion de Computadores").
- **SKU > 100 caracteres da HTTP 500** (`UPSTREAM_ERROR`): el SKU de la variante se autogenera del nombre. Acortar el nombre.
- Crear servicios nuevos con `is_active: false` y activarlos despues de revisar los textos.
- El preview de `update` con un campo anidado parcial muestra solo lo enviado: si se necesita conservar el resto del objeto, enviar el objeto completo.

## Endpoint propio de Django para el MCP
`GET /api/v1/dashboard/mcp/whoami/` (`dashboard/api/mcp_views.py`): solo lectura, `IsAdminUser`; devuelve `{uuid, email, is_admin, is_staff, is_superuser}`. Existe porque `/auth/profile/` no expone `is_superuser`.
