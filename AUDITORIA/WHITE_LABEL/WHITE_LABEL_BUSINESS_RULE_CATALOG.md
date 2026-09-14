# WHITE_LABEL_BUSINESS_RULE_CATALOG.md
Fase 8, 17, 18, 19, 20, 21 — Reglas de negocio, AI/RAG, dominio, SEO, legal

Solo lectura.

## 1. Reglas de negocio reales vs. capacidad de plataforma

Búsqueda dirigida por seguridad electrónica/CCTV/supervigilancia/marcas de fabricantes/instalación/monitoreo/renting de equipos/tarifas/documentos legales/workflows específicos. Resultado: **casi ninguna regla de negocio real depende del rubro de seguridad electrónica.** El único hallazgo genuino de lógica de negocio hardcodeada es:

- **`ecommerce_sintel/quotes/services/labor_conditions_evaluator.py` (`LaborConditionsEvaluator`)** — BUSINESS_RULE confirmada: umbrales de riesgo de trabajo en altura y labels en español ("Andamio"/"Escalera") hardcodeados en Python, sin configuración desde admin. Esto asume que el negocio siempre involucra instalación física en altura — no generalizable a "zapatería" u otro vertical sin editar código.

Todo lo demás encontrado bajo esos términos de búsqueda es:
- **PLATFORM CAPABILITY genérica** con ejemplos/placeholders del rubro actual (p. ej. `FeatureBannerSection` documentado como reutilizable "para cualquier proposito comercial (Seguridad Electronica, Marketplace, IA...)"; placeholders de formulario admin como `placeholder="CCTV"`).
- **Contenido de catálogo en DB** (nombres de paquetes como "Mantenimiento CCTV 8 Camaras" en `technical_services`, tarjetas de inicio nombrando Hikvision/Dahua en el seed de `core`) — es BUSINESS_DATA, no código, y por tanto reemplazable sin editar la plataforma, aunque hoy viene precargado.
- **Naming/comentarios** que asumen instalación física (`renting.EquipmentImage.TYPE_INSTALLATION`, campos de costo de mano de obra) — BUSINESS_RULE leve, ver scoring de módulos en [WHITE_LABEL_MODULE_AUDIT.md](WHITE_LABEL_MODULE_AUDIT.md).

## 2. AI / RAG

| Elemento | Contenido | Clasificación |
|---|---|---|
| `ai_engine/action_graph.py:383,680` | `"Eres el asistente de Sintel..."`, `"...atencion al cliente de Sintel (Colombia)..."` — prompt de sistema del **chatbot de soporte al cliente**, concatenado sin lookup a datos de `organization` | **BUSINESS_PROMPT** — defecto real, cara al cliente |
| `ai_engine/chains.py`/`chains_frontend.py` (`SINTEL_SYSTEM_PROMPT`) | "Eres un ingeniero senior del proyecto Sintel..." — Engineering Agent (herramienta interna, no cliente) | BUSINESS_PROMPT, riesgo bajo (dev-tool) |
| `ai_editor/generation/prompts.py`, `ai_editor/intent/prompts.py` | Mismo patrón, herramienta interna | BUSINESS_PROMPT, riesgo bajo |
| `ai_engine/config.py:20,28,31` | Hostnames Docker default (`sintel_ollama`, `sintel_chromadb`, `sintel_kb`), todos sobreescribibles por env | AI_PLATFORM, cosmético |
| Filtro de gobernanza de conocimiento en `ai_engine/retrievers.py` (`visibility="public"`) | Ingesta RAG desde docs `.AGENT` marcados públicos | AI_PLATFORM (mecanismo) / BUSINESS_KNOWLEDGE (contenido) — esperado y correcto |
| Perfiles de agente (`support_agent.yaml`, `sales_agent.yaml`, etc.) | Rol/tono genérico, sin términos de negocio salvo locale ("español neutro colombiano") | AI_PLATFORM |

Confirmado: `ai_engine` con **cero** imports de `project_knowledge_graph` (grep sin resultados) — desacoplamiento previo intacto.

**Veredicto:** el mecanismo RAG/ingesta de documentos es agnóstico de negocio, pero **el prompt de sistema del chatbot de soporte al cliente en producción hardcodea "Sintel"/"Colombia" directamente en código Python**, sin derivar de `organization.Company`/`ContactInfo`. Es el mismo patrón de riesgo que la fabricación de horarios de tienda hallada y corregida en la separación previa Support Agent vs Engineering Agent (ver memoria de sesión `project_support_agent_separation_plan`): un bot que afirma factualmente ser de una empresa que no es la del tenant real.

## 3. Knowledge Graph — cobertura

`project_knowledge_graph/cli/main.py` expone un CLI real (`python -m project_knowledge_graph.cli ...`) con `app-summary <app>`, `data-flow <Model|Model.campo>`, `node`, `impact`, `docs-for`, `config-for`, `change-impact`. Según `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` §5-6, `data-flow` traza `database→serializer→API→frontend→component`, y `app-summary` lista modelos/viewsets/endpoints/tests por app — responde directamente a "qué archivos referencian modelos de `organization`" y "qué archivos frontend consumen un endpoint dado". El propio doc muestra resultados de una corrida previa real (12 docs obsoletos, 25 componentes frontend muertos detectados), confirmando que la herramienta ya se ejecutó con éxito. **No existe hoy un artefacto de grafo fresco** (`KNOWLEDGE_GRAPH.json`/`PROJECT_MAP.json`) en la raíz — regenerarlo requiere correr `audit` (operación de escritura, omitida para mantener esta auditoría de solo lectura).

**`GRAPH_COVERAGE_GAP`**: no es una brecha de diseño, es de vigencia del artefacto — antes de usar el grafo para impact analysis real en la migración (Fase 44), se debe correr `audit` primero.

## 4. Configuración de dominio

Dominios hardcodeados (`sintel.net.co`/`panel.sintel.net.co`/`api.sintel.net.co`) aparecen en: `nginx.prod.conf` (×3 `server_name`, CSP `connect-src`), `nginx-common.conf`, `docker-compose.prod.yml` (healthcheck `Host:`), `.env.production.example` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_BASE_URL`, `DEFAULT_FROM_EMAIL`), y `frontend/.env.production`/`.env.local` (`VITE_API_BASE_URL`) — **6 archivos**.

`organization.DomainSettings` (primary_domain, admin_panel_domain, api_domain) existe pero se usa **únicamente** en su propia API CRUD de `organization` — `grep` de `DomainSettings` fuera de esa app: cero consumidores. Nginx/settings/env no lo leen.

**Veredicto:** no-problema arquitectónico — config de dominio en nginx/env es estática por despliegue por diseño, y `DomainSettings` está correctamente delimitado como registro admin-facing, no fuente de runtime para infra. El costo real es operativo: editar 6 archivos a mano por cada tenant nuevo.

## 5. SEO

App `seo` (`SiteMetaTag`, `SiteVerificationFile`, audit log) + `organization.SeoSettings` (meta_title/meta_description/og_image) cubren SEO dinámico por página vía `frontend/src/composables/useSeo.js`, que setea `document.title` en Home/ProductDetail/RentalDetail/PublicDetail.

**Gap real**: `frontend/index.html` (shell estático de la SPA) sigue hardcodeando `<title>Sintel | E-Commerce Ecosystem</title>` y el spinner de carga ("Sintel"/"Cargando ecosistema inteligente..."). Es lo que ven crawlers y cualquier ruta no cubierta por `useSeo.js` en el primer pintado.

**Veredicto:** SEO dinámico por página bien desacoplado; el shell estático de respaldo sigue hardcodeado a la marca — gap pequeño, fácil de corregir.

## 6. Legal / Contacto

`organization` cubre razón social, NIT, dirección, teléfono, correo, representación legal, dominios (`LegalEntityInfo`, `ContactInfo`, `DomainSettings`, `EmailSettings`) — buena cobertura de **metadata**.

**Gap real y mayor bloqueador de toda la auditoría:** el **contenido** de Términos y Condiciones / Política de Privacidad / autorización de tratamiento de datos **no vive en ningún modelo** — vive 100% como texto hardcodeado en `frontend/src/components/auth/kyc/legalDocs.js` (303 líneas), renderizado por `LegalTextModal.vue`. El archivo abre con un objeto `EMPRESA` literal:

```js
nombre: 'Sintel',
razonSocial: 'Sintel Corp [PENDIENTE: razon social exacta segun Camara de Comercio]',
```

"Sintel" aparece decenas de veces en el cuerpo legal (cláusulas de propiedad, responsabilidad, PI, base de tratamiento de datos), y el campo `razonSocial` es literalmente un placeholder sin llenar incluso para el negocio actual. `kyc/models.py` solo registra la *aceptación* de estos documentos (booleano/consentimiento), no su contenido. El enlace "Política de privacidad" en `CustomerFooter.vue` es un ancla muerta (`#privacidad`), no está conectado a ninguna fuente de contenido.

**Veredicto:** metadata legal bien modelada; el contenido legal vinculante es 100% prosa de frontend horneada a "Sintel", sin modelo detrás, incluyendo un placeholder sin resolver — **el bloqueador individual más grande de toda la auditoría**, por delante del prompt hardcodeado del chatbot y del título estático de `index.html`.
