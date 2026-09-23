# Admin AI Assistant -- FASE 0: Matriz real de capacidades de /panel/*

Fecha: 2026-09-16
Alcance: SOLO inventario. Ningun agente/tool nuevo se escribio en esta fase.
Metodo: lectura directa de código (grep/glob de `services/selectors.py`,
`services/commands.py`, `dashboard/api/urls.py`, `dashboard/api/views.py`,
`*/api/views.py`, `users/api/permissions.py`), no se asumio nada del plan
pegado por el usuario.

Patron confirmado en TODA la plataforma: cada app de dominio expone
`services/selectors.py` (lectura) + `services/commands.py` (escritura) y casi
todo el CRUD admin real vive centralizado en `dashboard/api/views.py` (BFF),
como `viewsets.ViewSet` a mano que llaman a esos Selectors/Commands -- NO
`ModelViewSet` genericos. Excepciones: `inventory`, `organization`, `users`,
`security`, `orders` (mutaciones reales) tienen su propio `api/urls.py` fuera
del router de `dashboard`.

## Matriz

| Dominio | App real | Selector(s) real(es) | Command(s) real(es) | Endpoint(s) admin real(es) | CRUD real | Permiso real | Riesgo | Infra IA reutilizable |
|---|---|---|---|---|---|---|---|---|
| Productos | `shop` | `shop/services/selectors.py` | `shop/services/commands.py` | `dashboard/api/views.py:235` `AdminProductViewSet` (+ variantes, imagenes) via router `products` | C/R/U/D completos (sin accion `publish` explicita -- el estado de publicacion es un campo mas de `partial_update`) | `ADMIN_PERMISSIONS = [IsAuthenticated, IsAdminUser]` (`is_staff AND is_superuser`) | Medio | Ninguna (agentes IA actuales no tocan `shop`) |
| Categorias | `shop` | `shop/services/selectors.py` | `shop/services/commands.py` | `AdminCategoryViewSet` (l.358) | C/R/U/D completos | Igual que arriba | Bajo | Ninguna |
| Marcas | `shop` | idem | idem | `AdminBrandViewSet` (l.394) | C/R/U/D completos | Igual | Bajo | Ninguna |
| Impuestos (Taxes) | `shop` | idem | idem | `AdminTaxViewSet` (l.430) | C/R/U/D completos | Igual | Medio (afecta precios/facturacion) | Ninguna |
| Orders | `orders` (BFF de `dashboard` es solo lectura) | `orders/services/selectors.py` | `orders/services/commands.py` | `dashboard` `AdminOrderViewSet` (l.468) = **solo `list`/`retrieve`, sin create/update/destroy**. La mutacion real vive en `orders/api/views.py` `OrderViewSet(ReadOnlyModelViewSet)` con ~15 `@action` de maquina de estados (`prepare`, `pack`, `assign-carrier`, `dispatch`, `deliver`, `complete`, etc.) | R completo via dashboard; mutacion real = maquina de estados de fulfillment, NO edicion libre de campos, NO create (create es `create_from_cart`, no admin), NO delete | `IsBuyerOrAdmin` en `orders/api/views.py` (**distinto** del patron `IsAdminUser` del resto -- compartido con el comprador; la logica de negocio interna filtra que transiciones aplican) | Alto | Ninguna |
| Inventory | `inventory` (fuera del router de `dashboard`, monta en `/api/v1/inventory/`) | `inventory/services/selectors.py` | `inventory/services/commands.py` | `inventory/api/views.py` `StockRecordViewSet` (create + `adjust_stock` + `movements`, sin update/destroy generico) + `InventoryTransactionViewSet(ReadOnlyModelViewSet)` | Create + ajuste manual, R completo (incl. auditoria de movimientos), sin U/D libres | `IsAdminUser` explicito en `InventoryTransactionViewSet` (S-01, antes caia a default) | Alto | Ninguna |
| Equipment (Renting) | `renting` | `renting/services/selectors.py` | `renting/services/commands.py` | `AdminEquipmentViewSet` (l.488, + variantes, `logistics`) | C/R/U/D completos | `IsAdminUser` | Medio | Ninguna |
| Renting Categories / Renting Brands | `renting` | idem | idem | `AdminRentingCategoryViewSet`, `AdminRentingBrandViewSet` | C/R/U/D completos (mismo patron que Categorias/Marcas de shop) | Igual | Bajo | Ninguna |
| Rental Labor | `renting` | idem | idem | `AdminRentalLaborViewSet` | C/R/U/D completos (mismo patron) | Igual | Medio | Ninguna |
| Cotizaciones (Quotations) | `quotes` | `quotes/services/selectors.py` | `quotes/services/commands.py` | `AdminQuotationViewSet` (l.737): `list/create/retrieve/partial_update` + `change-status` + `add-item` + `add-service`; plantillas (`AdminQuoteTemplate*`) con CRUD completo aparte | C/R/U + transicion de estado explicita (`change-status`), sin `destroy` en la cotizacion en si | `IsAdminUser` | Alto (dinero + condiciones comerciales) | Ninguna |
| Servicios (Technical Services) | `technical_services` | `technical_services/services/selectors.py` | `technical_services/services/commands.py` | `AdminTechnicalServiceViewSet` (l.1175, + `duplicate`, imagenes) | C/R/U/D completos | `IsAdminUser` | Medio | Ninguna |
| Service Categories / Service Levels / Service Variants | `technical_services` | idem | idem | `AdminServiceCategoryViewSet`, etc. | C/R/U/D completos | Igual | Bajo-Medio | Ninguna |
| Marketing | `marketing` | `marketing/services/selectors.py` | `marketing/services/commands.py` | `AdminMarketingViewSet` (l.1896) = **solo lectura**: `summary`, `campaigns`, `flash-offers` (sin create/update/destroy) | Solo R (dashboards/analitica) | `IsAdminUser` | Medio (info sensible de negocio, no de escritura) | **Si** -- `ai_engine/agents/profiles/marketing_agent.yaml` + `tools/marketing_tools.py` (MetaCampaignsTool, etc.), pero es del Support/Sales Agent orientado a CLIENTE (`IsAuthenticatedActiveUser`), no admin |
| Home Config | `marketing` (mismo archivo `views.py`, clase separada) | `marketing/services/selectors.py` | `marketing/services/commands.py` | `AdminHomeConfigViewSet` (l.1949): banners, modulos, home-cards, footer, navbar, site-brand, brand-slider, about-us -- CRUD completo por sub-recurso | C/R/U/D completos | `IsAdminUser` | Alto (visible publicamente al instante, cache invalidation explicita: `_invalidate_home_feed_cache`, etc.) | **Si, parcial** -- `ai_engine/agents/profiles/admin_agent.yaml` ya cubre exactamente este subset (Home/Navbar/Footer/BrandSlider) -- ver Hallazgo 1 |
| SEO (meta tags) | `seo` | `seo/services/selectors.py` | `seo/services/commands.py` | `AdminSeoMetaTagViewSet`, `AdminSiteVerificationFileViewSet` | C/R/U/D (no verificado a nivel de metodo, mismo patron ViewSet que el resto -- confianza alta por convencion uniforme, no confirmado linea por linea) | `IsAdminUser` (asumido por patron uniforme, no releido literal) | Medio | Ninguna |
| Operations | `operations` | `operations/services/selectors.py` | `operations/services/commands.py` | `AdminOperationViewSet`, `AdminDispatcherViewSet` (importados directo desde `operations.api.views`, no desde `dashboard.api.views`) | NO VERIFICADO a nivel de metodo (se confirmo el modulo real y el import, no se releyeron los metodos CRUD linea por linea) | `IsAdminUser` (por patron; no releido literal) | Alto (logistica/despacho) | Ninguna |
| Users | `users` | `users/services/selectors.py` | `users/services/commands.py` | `users/api/views.py` `UserViewSet` -- **NO esta en el router de `dashboard`**, vive en `users/urls.py` propio. Acciones reales: `list/create/retrieve/partial_update/destroy` + `erase` (borrado GDPR), `reset-password`, `resend-verification`, `bulk-action`, `groups` (asignar roles), `audit-log`, `timeline` | C/R/U/D completos + purga GDPR + accion masiva + gestion de grupos/roles -- **mucho mas potente que "no publica" asumido en el plan** | `[IsAuthenticated, IsAdminUser]` -- mismo `is_staff AND is_superuser`, no un RBAC distinto | Muy alto (confirmado) | Ninguna |
| Organization | `organization` | `organization/services/selectors.py` | `organization/services/commands.py` | `organization/api/urls.py` propio (fuera de `dashboard`): `CompanyViewSet`, `BrandingViewSet`, `ContactInfoViewSet`, `SocialLinkViewSet`, `EmailSettingsViewSet`, `DomainSettingsViewSet`, `SeoSettingsViewSet`, `LegalEntityInfoViewSet`, `LegalDocumentViewSet` (lectura publica intencional, escritura admin), `CommunicationEventViewSet` (`AllowAny`, es un webhook/log, no admin) | C/R/U variable por sub-recurso (mayoria upsert singleton, no lista); ver docstring propio en `LegalDocumentViewSet` que documenta la excepcion `AllowAny` | `ADMIN_PERMISSIONS` (`IsAdminUser`) en casi todo, salvo `CommunicationEventViewSet` que es publico a proposito | Alto | Ninguna |
| Security | `security` | `security/services/selectors.py` (`SecuritySelector.get_health_snapshot`, `list_events`) | `security/services/commands.py` (`SecurityCommands.log_event`, **nunca expuesto por API**, solo interno) | `security/api/views.py`: `SecurityHealthView` (GET), `SecurityEventViewSet(ReadOnlyModelViewSet)` | Solo R (por diseno: `SecurityEvent` es append-only, documentado explicitamente en el propio codigo) | `IsAdminUser` | Critico (coincide con lo asumido en el plan) | Ninguna |
| Support | `support` | `support/services/selectors.py` | `support/services/commands.py` | `dashboard` `AdminSupportChatViewSet` (l.3073): `list/retrieve` + `close`, `assign`, `ticket-status`, `ticket-priority`, `attach-context`, `customer_360` | R completo + transiciones de estado del ticket/chat, sin create/destroy (los tickets los crea el cliente) | `IsAdminUser` | Alto (datos de clientes) | **Si** -- este es el dominio donde ya vive el `SupportAgent` (`ai_engine_adk`, runtime real de ADK, 9-agentes), pero es agente conversacional de CLIENTE, no un agente que opera este panel de admin |

## Hallazgos (lo que el plan asumio vs. lo que hay realmente)

1. **Ya existe un `AdminAgent` embrionario, pero es codigo legado no conectado.**
   `ai_engine/agents/profiles/admin_agent.yaml` define exactamente el patron
   que el plan propone crear desde cero (Coordinator -> Tool -> Command,
   draft-first, "confirma siempre antes de escribir", regla de escalamiento
   para `eliminar|borrar`), pero **solo cubre Home/Navbar/Footer/BrandSlider**
   (el subset de Home Config) y **no tiene ninguna referencia desde
   `ai_engine_adk`**, que es el runtime real desde 2026-09-14 (ver memoria
   `project_adk_migration_cutover_and_reasoning_fix`). Es decir: todo
   `ai_engine/agents/`, `ai_engine/tools/registry.py` y
   `ai_engine/capabilities/registry.py` son el sistema pre-migracion
   (LangGraph-era) y estan huerfanos. Cualquier `AdminAssistantCoordinator`
   nuevo debe construirse sobre la arquitectura real de `ai_engine_adk`
   (`sintel_root_workflow.py`, `sintel_adapter.py`), no revivir el registry
   viejo. Impacto directo en Fase 3-4 del plan.

2. **Orders NO es "parcial create / editar / publicar limitado" -- es de
   solo-lectura en el BFF de `dashboard`, y la mutacion real vive en otra
   app con otro esquema de permisos.** `orders/api/views.py` usa
   `IsBuyerOrAdmin` (compartido con el comprador) en vez de `IsAdminUser`, y
   la escritura es una maquina de estados de fulfillment (~15 acciones,
   `prepare`->`pack`->`dispatch`->`deliver`->`complete`), no edicion libre de
   campos. Un `CommerceAgent` para Orders necesita modelar transiciones de
   estado, no CRUD generico, y su Tool de autorizacion no puede reusar
   ciegamente `ADMIN_PERMISSIONS`.

3. **"Marketing" y "Home Config" NO son el mismo dominio de escritura.** El
   plan los trata como una sola fila `Marketing` con CRUD completo. En
   realidad `AdminMarketingViewSet` es 100% solo-lectura (metricas/campanas),
   mientras que el CRUD real de contenido publico (banners, navbar, footer,
   home-cards) esta en `AdminHomeConfigViewSet`, un viewset distinto dentro
   del mismo archivo. Esto ya coincide, coincidentemente, con el scope real
   del `AdminAgent` legado del Hallazgo 1.

4. **Users es mucho mas potente y mas peligroso de lo que el plan asumio.**
   El plan marca Users como "Crear/Leer/Editar si, Publicar no" con riesgo
   "Muy alto". La realidad confirma el riesgo pero subestima el alcance:
   incluye borrado GDPR (`erase`), reseteo de contrasena admin-forzado,
   `bulk-action` (accion masiva sobre multiples usuarios de una vez) y
   gestion de grupos/roles -- cada una necesita su propio nivel de Tool y
   HITL en la Fase 2 del plan, no una sola entrada generica "Users".

5. **No todo pasa por el BFF `dashboard`.** `inventory`, `organization`,
   `users`, `security` y la mutacion real de `orders` tienen su propio
   `api/urls.py` fuera del router de `dashboard`. El plan asume
   implicitamente (via el diagrama final "Admin AI Gateway ->
   Selectors/Commands") que `dashboard` es el unico punto de entrada
   administrativo; una Tool para esos 5 dominios debe apuntar a esas otras
   apps directamente, no al BFF.

6. **El patron Selector/Command SI es universal** (confirmado: las 15+ apps
   de dominio revisadas tienen `services/selectors.py` + `services/commands.py`
   sin excepcion) -- este es el unico supuesto del plan que se confirma sin
   matices, y es una base solida para la Fase 1 (catalogo de Tools).

## Cobertura de la verificacion

- **Verificados a nivel de metodo/linea de codigo:** Productos, Categorias,
  Marcas, Impuestos, Orders, Inventory, Equipment, Cotizaciones, Servicios,
  Marketing, Home Config, Users, Organization, Security, Support (15/19
  dominios listados en el plan).
- **Verificados a nivel de modulo/import pero no metodo por metodo:**
  Operations, SEO (2/19) -- se confirmo la app real, el selector/command
  existente y el permiso por convencion, pero no se releyo cada accion del
  ViewSet.
- **No aplicables como fila propia / ya cubiertos dentro de otro dominio:**
  Renting Categories, Renting Brands, Rental Labor (cubiertos dentro de la
  fila `renting`, mismo patron que shop), Service Categories/Levels/Variants
  (cubiertos dentro de `technical_services`).
- **Ningun dominio del plan resulto "no encontrado".** Los 19 nombres del
  plan mapean 1:1 a apps o sub-recursos reales.
