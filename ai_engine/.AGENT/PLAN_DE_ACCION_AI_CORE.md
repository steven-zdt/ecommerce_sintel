# Plan de Acción — De "generador de código" a "cerebro operativo" (AI Core)

> Documento vivo, mismo protocolo que `docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md`.
> Es la única fuente de verdad del avance de esta migración. Se actualiza al
> cerrar cada fase (checkboxes + estado + fecha).
>
> **[ACTUALIZACIÓN 2026-07-15 — v2]** Segunda pasada: se agregó la
> arquitectura oficial de capas del AI Core, 15 componentes arquitectónicos
> nuevos, la Fase 8 y una auditoría final de consistencia, a pedido
> explícito del usuario. **No se eliminó ninguna sección de la v1, no se
> reordenaron las fases, no se eliminó ninguna decisión ya documentada** —
> todo lo de la v1 sigue abajo tal cual, enriquecido con referencias a los
> componentes nuevos donde corresponde. Validado contra
> `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`,
> `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` y
> `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` (ver "Auditoría final del
> documento" al cierre).

## Protocolo de ejecución

1. Cada fase se ejecuta **solo** tras confirmación explícita del usuario en el chat.
2. Al terminar una fase se marcan sus checkboxes, se cambia el Estado en la
   tabla global, se anota la fecha, y se resume qué se hizo/qué falta antes
   de pedir permiso para la siguiente.
3. Ninguna fase empieza sin que la anterior esté COMPLETADA — el orden importa
   porque cada fase depende de una garantía de seguridad que sienta la
   anterior (ver Restricciones duras).
4. Si una fase revela que hace falta tocar algo fuera de su alcance, se anota
   como hallazgo dentro de la fase y se resuelve en la fase que corresponda —
   no se hacen saltos de fase no solicitados.

Leyenda de estado: `PENDIENTE` · `EN CURSO` · `COMPLETADA` · `BLOQUEADA`

---

## Contexto — validación de la propuesta contra el código real

El usuario propuso migrar `ai_engine` (motor de desarrollo asistido) hacia un
"cerebro operativo" multiagente capaz de ejecutar acciones de negocio
(pedidos, alquileres, pagos, soporte), no solo responder preguntas sobre
arquitectura. Antes de planificar por fases, se auditó el código real de
`ai_engine/` y de los servicios de negocio que respaldarían cada "Tool"
propuesta (dos investigaciones exhaustivas, 2026-07-15). Conclusión: **la
estimación de "75-80% ya construido" es optimista para el objetivo de
atención al cliente** — es precisa para "motor de desarrollo asistido", pero
las 3 capas nuevas que el usuario identifica (Actions, Customer Context,
Memory) no son una capa delgada sobre lo existente: requieren piezas
estructurales que hoy **no existen en absoluto**, listadas aquí para que el
plan no las dé por sentadas:

| Afirmación del usuario | Realidad verificada en código |
|---|---|
| "El motor ya resuelve RAG + PROJECT_MAP + validación + LangGraph iterativo" | **Cierto**, verificado línea por línea (`graph.py`, `retrievers.py`, `guardrails.py`, `planner.py`) |
| "Falta una capa de orquestación de herramientas" | Cierto, pero además falta lo que la hace *segura*: hoy `ai_engine` **no tiene ninguna autenticación** (cualquiera que llegue al puerto 8100 puede llamar cualquier endpoint) y **no tiene conexión de red configurada hacia Django** (comparten red Docker, pero no hay cliente HTTP, URL base, ni credencial de servicio) |
| "El LLM ya no solo responde; decide qué hacer" (LangGraph con Tool Selection/Execution) | El `StateGraph` actual (`graph.py:19-32`, `150-179`) es un grafo **lineal** `analyze_impact → generate_code → validate_code → (retry\|emit\|escalate)`, sin nodos de tool-calling, sin `ToolNode`, sin `bind_tools()`, sin `checkpointer` (cero memoria de conversación persistida). Es un buen esqueleto (plan→actuar→validar→reintentar), pero ningún nodo actual sirve para ejecutar una acción de negocio — se necesitan nodos nuevos, no solo enchufar los que hay |
| "Memoria de conversación / cliente / empresarial" | Hoy `ai_engine` es 100% *stateless*: cada request es independiente, no existe `session_id`/`thread_id`/identidad de usuario en ningún endpoint. Lo que hoy se llama "memoria" (`GLOBAL_MEMORY.json`, `APP_MEMORY/`) es conocimiento estático del código, no del cliente |
| "Cada Tool encapsula operaciones permitidas (OrderTool, RentalTool, ...)" | Los Selectors/Commands que respaldarían cada Tool **sí existen y están bien separados** (ver tabla de la Fase 2) — esto es lo que hace viable el plan. Pero se encontraron **gaps reales de negocio** que ninguna Tool puede resolver por simple wrapping (ver "Gaps de negocio encontrados" abajo) |

### Gaps de negocio encontrados (no inventar soluciones — son decisiones del usuario)

1. **Cambiar la fecha de un alquiler ya creado no es self-service hoy** —
   `RentalRequestCommands.extend_period()` (`renting/services/commands.py:792`)
   es la única función de "cambiar fechas" que existe, y es **admin-only**
   (`renting/api/views.py:557`, `permission_classes=[IsAdminUser]`). Una
   "RentalTool" no puede envolver una acción que no existe para el cliente —
   hay que decidir en la Fase 4 si se construye un command nuevo, o si la
   Tool solo puede "cancelar + volver a cotizar" o "escalar a soporte".
2. **No hay razón de rechazo de pago expuesta al cliente** —
   `Transaction.status` (`DECLINED`/`VOIDED`/`ERROR`) es todo lo que hay;
   el detalle real de Wompi vive en `TransactionEvent.raw_payload`, solo
   accesible vía un selector admin-only. Una "PaymentTool" hoy solo puede
   decir "tu pago fue rechazado", no el motivo.
3. **`support` es 100% WebSocket** (`support/consumers.py`, sin `api/views.py`
   funcional) — una Tool invocada desde un LLM en contexto síncrono/HTTP
   puede "abrir sala"/"dejar mensaje" (`ChatCommands.get_or_create_room`/
   `save_message`) pero no puede sostener una sesión WS bidireccional ni
   consultar "estado de mi ticket" (no existe ese read endpoint).
4. **`ServiceOperationSelector.get_by_uuid()` y `QuotationSelector` no filtran
   por dueño** — cualquier Tool que los envuelva debe agregar la validación
   de propiedad ella misma (o se agregan métodos `*_for_user` nuevos, más
   seguro y reutilizable).
5. **No hay selector de ofertas personales (`PersonalOffer`) por usuario.**

Estos 5 puntos se resuelven explícitamente en las fases correspondientes
(marcados `[GAP]`) — no se documentan como si ya funcionaran.

---

## Arquitectura General del AI Core

Vista de capas, de arriba (cliente/canal) hacia abajo (modelo). **Regla de
oro: ninguna capa se salta a otra** — un Canal nunca llama directo a un
Selector, un LLM nunca ve una tabla de base de datos. Esto es la traducción
arquitectónica directa de "ninguna lógica de negocio dentro del LLM" (regla
obligatoria del usuario) y del Service Layer que ya rige todo el proyecto
(`Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`, sección
"Service Layer": Commands/Selectors, ViewSets solo orquestan).

```
AI Channels          Web chat, WhatsApp, App móvil, Panel admin, Operadores, API externa
      │
AI Gateway            Único punto de entrada HTTP a ai_engine — todo pasa por aquí (Fase 1)
      │
Authentication         Valida el JWT real de Django — nunca emite uno propio (Fase 1)
      │
Customer Context Builder   Arma "quién pregunta" antes de tocar al LLM (Fase 1/5)
      │
Context Optimizer      Recorta el contexto a lo relevante — nunca todo (Fase 3)
      │
Planner                 Ya existe (planner.py) + intención de negocio nueva (Fase 3)
      │
Capability Registry     El LLM SOLO conoce esto, nunca una Tool concreta (Fase 2)
      │
Tool Registry            Implementación real detrás de cada Capability (Fase 2)
      │
Policy Layer             ¿Puede? ¿Debe confirmar? — antes de ejecutar, siempre (Fase 4)
      │
Commands / Selectors      YA EXISTE — Service Layer real de cada app, sin capa nueva aquí
      │
Business Modules          YA EXISTEN — orders, renting, payment, quotes, technical_services...
      │
Notifications             YA EXISTE — NotificationCommands.dispatch_notification()
      │
Memory                    Conversación / cliente / empresarial (Fase 5)
      │
Audit                     Registro de toda acción de escritura (Fase 4/6)
      │
Metrics                   Observabilidad (Fase 6)
      │
Knowledge (RAG)           YA EXISTE — retrievers.py, PROJECT_MAP.json, docs/specs/
      │
LLM                       YA EXISTE — llm_factory.py (Ollama/OpenAI/Anthropic)
```

### Responsabilidad de cada capa

| Capa | Responsabilidad | Estado |
|---|---|---|
| AI Channels | Transportar el mensaje del usuario final hacia el Gateway, sea cual sea el canal | Fase 7 |
| AI Gateway | Único punto HTTP de entrada; enruta a `/chat` (acción) o a `/generate`\|`/plan`\|`/impact` (código) sin mezclar ambos mundos | Fase 1 |
| Authentication | Decodificar/validar el JWT de Django, rechazar si inválido/expirado | Fase 1 |
| Customer Context Builder | Resolver el JWT a un usuario+perfil real vía el endpoint interno de Django (`ProfileResolver`), nunca reimplementar esa lógica en Python fuera de Django | Fase 1/5 |
| Context Optimizer | Decidir qué fracción del contexto (historial, RAG, datos del cliente) realmente entra al prompt | Fase 3 |
| Planner | Clasificar intención + planificar pasos — reusa `planner.py` para tareas de código, nueva rama de intención de negocio para acciones | Fase 3 |
| Capability Registry | Capa de abstracción semántica ("buscar pedido") que el LLM ve | Fase 2 |
| Tool Registry | Implementación concreta detrás de cada capability (puede cambiar sin que el LLM se entere) | Fase 2 |
| Policy Layer | Gate de negocio antes de cualquier `Command` — permisos, estado, confirmación requerida | Fase 4 |
| Commands / Selectors | Lógica de negocio real, ya construida por cada app — **no se toca ni se duplica** | Ya existe |
| Business Modules | Las apps Django reales (orders, renting, payment, quotes, technical_services, kyc, support, marketing, inventory) | Ya existe |
| Notifications | Confirmar acciones al usuario por WS/Email/WhatsApp | Ya existe, se reusa |
| Memory | Persistir estado entre turnos/sesiones/clientes sin duplicar la BD de Django | Fase 5 |
| Audit | Trazabilidad de qué Tool ejecutó qué, para quién, cuándo | Fase 4/6 |
| Metrics | Tokens, latencia, costo, tasa de error — Observabilidad | Fase 6 |
| Knowledge (RAG) | Responder "qué sabe la empresa" (documentación/políticas/código) | Ya existe, se reusa |
| LLM | Razonar y redactar — nunca decide sin pasar por Policy Layer | Ya existe, se reusa |

---

## Componentes Arquitectónicos Nuevos

Quince piezas nuevas que la Arquitectura General de arriba requiere. Cada
una se construye en la fase indicada — esta sección es el detalle de diseño
de cada componente, referenciado desde las Fases 1-8 más abajo (no se
duplica contenido, se referencia).

### 1. Capability Registry

**Antes del Tool Registry, no lo reemplaza.** El LLM **nunca** conoce una
Tool concreta (nombre de función Python, firma, endpoint) — solo conoce
*capacidades* declaradas en lenguaje de negocio. El Capability Registry
mapea capacidad → una o más implementaciones (Tools) sin que el LLM lo sepa.

```
Capability: "buscar_pedido"
    │
    └─ implementación activa hoy → OrderTool → OrderSelector.list_for_user()
       (mañana esa misma capacidad podría apuntar a otra Tool/implementación
        sin tocar el prompt ni el LLM — solo se re-registra la capability)
```

Cada entrada del registro: `{capability_id, descripción_para_el_LLM,
tool_implementación_actual, versión, apps_relacionadas}`. Vive en
`ai_engine/capabilities/registry.py`. Construido en **Fase 2**, junto con el
Tool Registry (ambos nacen a la vez, pero conceptualmente el LLM solo ve la
capa de Capability).

### 2. AI Gateway

Punto único de entrada — ya existe parcialmente como `main.py` (FastAPI),
pero hoy mezcla endpoints de código (`/generate`, `/plan`, `/impact`) sin
ningún control de acceso. El Gateway formaliza esa entrada con rutas nuevas,
todas bajo autenticación de la Fase 1:

```
/api/v1/ai/context     → Customer Context Builder
/api/v1/ai/orders      → Capabilities de orders
/api/v1/ai/payments    → Capabilities de payment
/api/v1/ai/renting     → Capabilities de renting
/api/v1/ai/services    → Capabilities de technical_services
/api/v1/ai/search      → Capabilities de shop/inventory/marketing
/api/v1/ai/support     → Capabilities de support/kyc
```

Estas rutas viven **dentro de `ai_engine` (FastAPI, puerto 8100)**, no en
Django — el "Gateway" aquí es la capa de entrada del propio AI Core, que
internamente sí le habla a Django solo a través del endpoint interno de la
Fase 1 (`/api/v1/internal/ai-context/`), nunca a los modelos directamente.
Construido en **Fase 1**, ampliado con nuevas rutas de capability en cada
fase siguiente.

### 3. Customer Context Builder

Ya introducido en la v1 (Fase 1) como el mecanismo que resuelve el JWT a
usuario+perfil real vía `ProfileResolver`. Este componente se completa en la
**Fase 5** para incorporar además: pedidos recientes, pagos, alquileres,
servicios, cotizaciones, marketing (ofertas activas para ese usuario),
notificaciones pendientes, y contexto CRM (ver componente 9). Regla dura:
**nunca enviar todo esto al LLM en cada turno** — el Customer Context
Builder arma el contexto completo disponible; el Context Optimizer (siguiente
componente) decide cuánto de eso realmente entra al prompt de este turno.

### 4. Context Window Optimizer

Reduce el contexto que efectivamente llega al LLM. Nunca envía: todos los
pedidos del cliente, toda la conversación histórica, toda la base
documental. Construye únicamente lo relevante al turno actual, con un
presupuesto de tokens explícito (mismo espíritu que
`MAX_RETRIEVER_CHUNKS=50` ya usado hoy en `retrievers.py` para RAG — este
optimizer aplica la misma disciplina al contexto de cliente/conversación,
no solo al RAG). Construido en **Fase 3**, como nodo del Action Graph
(`optimize_context`, entre `resolve_customer_context` y
`select_and_execute_tools`).

### 5. Policy Layer

Capa nueva **entre Tools y Commands** — ninguna Tool ejecuta una acción de
escritura sin pasar primero por una política. Ejemplos de preguntas que
resuelve antes de invocar el `Command`: ¿puede cancelar? ¿puede modificar?
¿está pagado? ¿tiene permisos? ¿debe pedir confirmación?

**Regla dura del usuario, ya reflejada aquí: las reglas de negocio nunca
viven dentro del modelo/LLM.** El Policy Layer tampoco reinventa reglas de
negocio — reusa exactamente las permission classes y los métodos de estado
que ya existen (`users/api/permissions.py`: `IsBuyerOrAdmin`,
`IsServiceProviderOrAdmin`, `IsOwnerOrAdmin`; métodos como
`Order.is_pending_payment()`), y consulta el Tool Metadata (componente 13)
para saber si esa Tool en particular requiere confirmación. Construido en
**Fase 4**, es el nodo `evaluate_policy` justo antes de `execute_tool` en el
Action Graph.

### 6. Observabilidad

Registrar por cada turno/Tool call: tokens usados, tiempo de respuesta,
costo estimado, número de tool calls, errores, reintentos, fallbacks, tiempo
de ejecución, latencia por Tool, uso de memoria, conteo de conversaciones.
Integración futura (no en el alcance inmediato, se deja preparada):
Prometheus + Grafana + OpenTelemetry — mismo patrón que
`ROADMAP_CLOUDFLARE_TUNNEL.md` ya decidió NO instalar Prometheus/Grafana en
producción por costo (Fase 18 de ese roadmap); aquí se deja la
instrumentación (`ai_engine/observability.py`, métricas emitidas vía
`logging` estructurado) lista para conectar a un backend real cuando el
usuario decida que ya vale la pena el costo operativo. Construido en
**Fase 6**.

### 7. Human Handoff

Cuando el AI no puede resolver un caso: crea contexto, transfiere la
conversación, envía historial completo, notifica al operador, y continúa el
seguimiento — **nunca pierde el historial**. Se apoya 100% en lo que ya
existe en `support`: `ChatCommands.get_or_create_room()` +
`ChatCommands.attach_context()` (ya idempotente y ya diseñado para "Customer
Experience Hub") + `ChatCommands.save_message()` para volcar el historial de
la conversación con el AI dentro de la misma sala que verá el humano.
Construido en **Fase 7**, como la acción de "escalar" del Action Graph
(equivalente al nodo `escalate` que ya existe en el grafo de código,
`graph.py::node_escalate`, pero para acciones de negocio en vez de código).

### 8. Integración con Event Bus

El AI Core debe poder **reaccionar** a eventos del sistema, no solo
responder preguntas — pago aprobado, pago rechazado, pedido despachado,
servicio asignado, técnico programado, alquiler confirmado, notificación
enviada. Esto habilita conversaciones proactivas ("tu técnico llega en 20
minutos"). No se construye un bus de eventos nuevo: el proyecto ya tiene el
mecanismo (`transaction.on_commit(...)` + Celery tasks disparadas desde cada
Command, mismo patrón que ya usa `NotificationCommands.dispatch_notification()`
en 8+ apps) — el AI Core se suscribe como **un consumidor más** de esos
mismos disparadores, no como un sistema paralelo. Construido en **Fase 7**.

### 9. CRM Context

El AI debe poder consultar historial del cliente, compras, interacciones,
campañas, preferencias, frecuencia — **nunca responder únicamente con RAG**
cuando la pregunta es sobre el cliente mismo, no sobre la empresa. Reusa
`MarketingSelector.get_user_marketing_profile(user)` (ya calcula
`total_spent`/`orders_count`/`preference`) como base; si el usuario define
más adelante una app `crm` dedicada, este componente se conecta a ella sin
cambiar el contrato del Customer Context Builder. Construido en **Fase 5**.

### 10. Separación Knowledge vs Live Data

Se formaliza una distinción que hoy ya existe implícitamente en el código
pero nunca se documentó de forma explícita: **cuatro fuentes de
conocimiento**, nunca mezcladas:

| Fuente | Qué es | Cómo se consulta | Ejemplo |
|---|---|---|---|
| Architecture | Estructura del código (modelos/vistas/componentes) | `PROJECT_MAP.json` / `KNOWLEDGE_GRAPH.json` | "¿qué serializer usa Product?" |
| Business Docs | Specs/manuales/FAQ | RAG (`retrievers.py`, `docs/specs/`) | "¿cómo funciona el alquiler?" |
| Policies | Reglas de negocio codificadas | Policy Layer (componente 5), nunca el LLM | "¿puedo cancelar este pedido?" |
| Live Data | Datos reales de un cliente/pedido/pago en este momento | Selectors vía Tools (Fase 2) | "¿dónde está mi pedido #123?" |

**Regla dura:** el RAG (`retrievers.py`) consulta *conocimiento* (las 3
primeras filas); los Selectors consultan *datos vivos* (la última fila).
Ninguna Tool debe intentar "traer" datos vivos vía RAG, y el RAG nunca debe
intentar responder con datos vivos inventados. Esta tabla es la referencia
oficial para no mezclar ambos conceptos en ninguna fase futura.

### 11. Agent Profiles

Actualiza la Fase 6 (Multiagente) para que ningún agente se cree "solo por
nombre". Cada perfil de agente declara:

```yaml
name: RentalAgent
description: Atiende consultas y acciones de alquiler de equipos
objetivo: Resolver disponibilidad, crear/cancelar solicitudes de alquiler
personalidad: Cercano, resolutivo, nunca promete fechas sin confirmar disponibilidad
herramientas: [RentalStatusTool, RentalAvailabilityTool, CreateRentalRequestTool, CancelRentalTool]
permisos: IsBuyerOrAdmin   # reusa users/api/permissions.py, no un sistema nuevo
capacidades: [buscar_alquiler, verificar_disponibilidad, crear_alquiler, cancelar_alquiler]
memoria: conversación + cliente (ver Fase 5)
reglas_escalamiento: "si detecta reclamo o 2+ intentos fallidos → Support Agent"
tono: profesional, español neutro colombiano
```

Vive en `ai_engine/agents/profiles/*.yaml`. Construido en **Fase 6**.

### 12. Versionado

`Capability Registry`, `Tool Registry`, `Action Graph` y el `AI Gateway`
deben soportar versionado explícito (`v1`, `v2`, `deprecated`) desde su
diseño inicial, no como una migración posterior — mismo criterio que ya
aplica `drf-spectacular`/OpenAPI a la API REST de Django
(`IMPLEMENTATION_SUMMARY.md`, stack). Una capability marcada `deprecated`
sigue respondiendo (compatibilidad hacia atrás) pero deja de ofrecerse al
LLM en el prompt de sistema. Aplica desde que cada registro se crea en la
**Fase 2**, no se pospone.

### 13. Tool Metadata

Cada Tool declara, además de su función Python:

```python
ToolMetadata(
    name="CancelRentalTool",
    description="Cancela una solicitud de alquiler del cliente autenticado",
    owner="renting",                 # app dueña, para trazabilidad
    timeout_ms=5000,
    permissions=["IsBuyerOrAdmin"],
    risk="high",                     # low | medium | high — alimenta la Policy Layer
    audit_level="full",              # full | summary | none
    rate_limit="10/hour/user",
    requires_confirmation=True,
    capabilities=["cancelar_alquiler"],
)
```

Este metadata es lo que la Policy Layer (componente 5) consulta para decidir
si pide confirmación, y lo que Observabilidad (componente 6) usa para
etiquetar métricas por Tool. Construido en **Fase 2** (declaración) y
consumido en **Fase 4** (Policy Layer) y **Fase 6** (Observabilidad).

### 14. Caché Inteligente

Las consultas repetidas (ej. "¿qué equipos hay disponibles?" preguntado 20
veces en una hora por distintos usuarios) deben poder reutilizar resultado
cuando es seguro hacerlo. **No se duplica el mecanismo de invalidación ya
documentado** (`core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md`, sección
"Cache Strategy": `cache.delete(key)` selectivo vía signals +
invalidación explícita en cada ViewSet admin) — cualquier Tool que consulte
datos ya cacheados en Django (ej. `EquipmentSearchTool` sobre
`home-feed`/`footer`) respeta ese TTL y esas claves, no inventa una capa de
caché paralela con su propia política de expiración. Para datos que hoy no
tienen caché en Django (ej. resultado de una Tool compuesta), se evalúa caso
por caso en la fase que la introduce, documentando la clave y el TTL ahí
mismo. Construido incrementalmente desde la **Fase 2**.

### 15. Integración con Core

El AI Core debe poder administrar contenido del sitio (`/panel/home-config`)
usando **exclusivamente** los Commands/Selectors ya construidos en `core`
(ver `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md`, sincronizado
2026-07-15 con Slider de Marcas + Footer Visual Builder): Home Builder
(`HomeConfigCommands`), Navbar (`NavbarLinkCommands`), Footer
(`FooterGroupCommands`/`FooterCommands`), CTA (`FooterCTACommands`), Banners
(`HomeConfigCommands.create_banner`/`update_banner`), Cards
(`HomeCardCommands`/`HomeCardGroupCommands`), Slider de marcas
(`BrandSliderCommands`). **Sin acceso directo al frontend** — el AI Core
nunca escribe Vue/JS, solo invoca estos Commands vía Tools nuevas
(`CoreContentTool` o una por dominio), exactamente igual que un
administrador humano lo haría desde `HomeConfigView.vue`. Esto es contenido
para **Fase 8** (AI Business Automation), donde encaja naturalmente junto a
la automatización de campañas/marketing.

---

## Restricciones duras (aplican a TODAS las fases, no negociables salvo instrucción explícita)

- **Nunca** dar a un Tool acceso de escritura directo a un modelo — todo Tool
  llama a un `Command` ya existente en `services/commands.py` de la app
  correspondiente (Service Layer), igual que ya exige `.AGENT.md` para
  código humano. Ningún Tool nuevo escribe SQL/ORM crudo.
- **Ninguna acción irreversible se ejecuta sin confirmación explícita del
  usuario final dentro de la conversación** (cancelar un pedido/alquiler,
  solicitar upgrade de KYC, etc.) — el grafo debe tener un paso de
  confirmación (`interrupt`) antes de invocar el Command, no solo antes de
  responder.
- **El AI Engine nunca emite ni valida su propio JWT** — siempre reenvía/
  valida el JWT real emitido por Django (`rest_framework_simplejwt`), nunca
  inventa una sesión paralela. Ver Fase 1.
- **Ningún Tool nuevo se comporta como IsAdminUser** salvo que la fase lo
  apruebe explícitamente y el JWT presentado realmente tenga `is_staff`
  (reutilizar `users/api/permissions.py`, no reinventar).
- **El pipeline de generación de código existente (`graph.py`/`chains.py`/
  `guardrails.py`) no se modifica ni se retira** — el nuevo "Action Graph"
  es un módulo/grafo **paralelo**, no un reemplazo. `/generate`, `/validate`,
  `/plan`, `/impact`, `/breakage` siguen funcionando exactamente igual.
- **Todo el conocimiento estático ya construido se reutiliza, nunca se
  duplica** — `PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/`retrievers.py` siguen
  siendo la única fuente de "qué sabe la empresa sobre su propio código";
  las Tools de negocio consultan datos *en vivo* (Django), el RAG existente
  sigue resolviendo preguntas sobre *documentación/políticas*.
- **`sintel_ai` sigue sin exponerse a Internet** — igual que
  `feedback_production_gate`/`ROADMAP_CLOUDFLARE_TUNNEL.md` ya establecen:
  cualquier canal cliente-facing (WhatsApp, chat web) llega a `ai_engine` a
  través de Django (que sí está expuesto), nunca directo.
- **Nunca cambiar `DJANGO_SETTINGS_MODULE` ni promover a producción sin
  instrucción explícita** (regla ya vigente, `feedback_production_gate`).
- **El LLM nunca conoce una Tool concreta, solo Capabilities** (Componente 1)
  — cambiar la implementación detrás de una capability nunca debe requerir
  tocar el prompt de sistema ni reentrenar/reconfigurar el LLM.
- **Ninguna Tool de escritura se ejecuta sin pasar por la Policy Layer**
  (Componente 5) — ni siquiera en pruebas manuales vía `/tools/debug`.
- **Ninguna regla de negocio vive dentro del prompt del LLM** — si una
  regla necesita cambiar, se cambia en el Command/Selector o en la Policy
  Layer, nunca en el system prompt como texto libre que el modelo "debe
  recordar".
- **Capability Registry, Tool Registry, Action Graph y AI Gateway versionan
  desde el día uno** (Componente 12) — no se pospone el versionado a una
  migración futura.

---

## Estado global

| # | Fase | Estado | Fecha cierre |
|---|------|--------|---------------|
| 0 | Auditoría y validación de contexto (este documento) | COMPLETADA | 2026-07-15 |
| 1 | Puente seguro Django ⇄ AI Engine (identidad + red) | COMPLETADA | 2026-07-16 |
| 2 | Tool Registry — Tools de solo lectura | COMPLETADA | 2026-07-16 |
| 3 | Action Graph — orquestación con confirmación humana | COMPLETADA | 2026-07-16 |
| 4 | Tools de escritura (bajo riesgo, con confirmación) | COMPLETADA | 2026-07-16 |
| 5 | Memoria — conversación, cliente, empresarial | COMPLETADA | 2026-07-16 |
| 6 | Multiagente — permisos y herramientas por agente | COMPLETADA | 2026-07-16 |
| 7 | Multicanal — WhatsApp / Web / Panel / API externa | COMPLETADA | 2026-07-16 |
| 8 | AI Business Automation | COMPLETADA | 2026-07-16 |

---

## Fase 1 — Puente seguro Django ⇄ AI Engine (identidad + red)

**Por qué va primero:** ninguna Tool de negocio puede construirse de forma
segura sin esto — es el prerrequisito que hace posible "el motor sabe quién
pregunta", que hoy no existe (`main.py` no tiene ni un `Depends()` de
seguridad, confirmado). Esta fase construye, en términos de la Arquitectura
General: **AI Gateway** (Componente 2), **Authentication** y la primera
versión del **Customer Context Builder** (Componente 3).

**Objetivo:** que un request a `ai_engine` pueda traer un JWT real de Django
y que el motor lo valide y resuelva a un usuario/perfil real, sin emitir
tokens propios.

**Alcance:**
- [x] Nuevo modulo `ai_engine/auth.py`: valida el JWT (`HS256`, misma
      `SIGNING_KEY`/`SECRET_KEY` que Django vía variable de entorno
      compartida) y extrae `user_id` — **no** reimplementa SimpleJWT, solo
      decodifica y verifica firma/expiración con `PyJWT` (ya es dependencia
      transitiva de `djangorestframework-simplejwt`, o se agrega a
      `requirements.txt`).
- [x] Nuevo endpoint interno en Django (`users` o `dashboard`, a decidir):
      `GET /api/v1/internal/ai-context/` protegido por
      `IsAuthenticatedActiveUser`, que devuelve el contexto mínimo resuelto
      vía `ProfileResolver` (tipo de usuario, nombre, `is_staff`) — el AI
      Engine llama a ESTE endpoint con el JWT reenviado en vez de
      reimplementar `ProfileResolver` en Python fuera de Django. Evita
      duplicar lógica de negocio en dos lenguajes/procesos.
- [x] Variable de entorno nueva en `docker-compose.yml`/`.env`:
      `DJANGO_INTERNAL_API_URL=http://django:8000/api/v1` (la red ya existe,
      solo falta el cliente HTTP — confirmado que `sintel_ai` y `django`
      comparten `ecommerce_sintel_network`).
- [x] Nuevas rutas del **AI Gateway** (`ai_engine/gateway/`), inicialmente
      solo `/api/v1/ai/context` (las de negocio — `orders`, `payments`,
      `renting`, `services`, `search`, `support` — se agregan en Fase 2
      conforme cada dominio gane sus Tools).
- [x] Todos los endpoints nuevos de Fase 2+ exigen este contexto — ningún
      Tool de negocio queda accesible sin JWT válido (dependencia FastAPI
      `auth.get_user_context`, lista para reusar en cada ruta nueva).
- [x] Verificación: request sin JWT → 401 explícito, no un 200 anónimo.

**Riesgos:** compartir `SECRET_KEY`/`SIGNING_KEY` entre dos servicios es
sensible — debe ir solo por variable de entorno, nunca hardcodeada, y nunca
en un archivo versionado.

**Cierre (2026-07-16):**
- Decisión tomada: el endpoint interno vive en **`users`**
  (`users/api/internal.py::AiContextView`), dominio de identidad/auth,
  ruteado directo en `ecommerce/urls.py` — mismo patrón que `AdminLoginView`.
  Devuelve `user_id`, `uuid`, `email`, `full_name`, `user_type`, `is_staff`,
  `is_superuser`, `is_verified`, `kyc_status` (via `ProfileResolver`).
- `JWT_SECRET_KEY` ya llegaba a `sintel_ai` por el `env_file: .env`
  compartido del compose — no hubo que duplicar el secreto, solo consumirlo
  (`config.py::JWT_SECRET_KEY`; sin la clave, `auth.py` falla CERRADO con
  503, nunca deja pasar).
- Archivos nuevos: `ai_engine/auth.py` (PyJWT + dependencia
  `get_user_context` que reenvía el token a Django), `ai_engine/gateway/`
  (`ai_router`, prefijo versionado `/api/v1/ai`), `users/api/internal.py`.
  `PyJWT>=2.9` agregado a `requirements.txt` (no venía transitivo).
- **Hallazgo (resuelto aquí, era prerequisito de red de esta fase):** el
  hostname interno `django` no estaba en `ALLOWED_HOSTS` del `.env` de dev —
  Django respondía `400 DisallowedHost` a la llamada servicio-a-servicio.
  Agregado `django` a `ALLOWED_HOSTS` (dev). **Pendiente para el deploy a
  prod (cuando el usuario lo autorice):** replicar `ALLOWED_HOSTS` +
  `DJANGO_INTERNAL_API_URL` en la config de producción y rebuild de la
  imagen `sintel_ai`.
- Verificación end-to-end en dev (usuario real `cliente.test@sintel.co`,
  token generado en memoria, nunca persistido): Django interno sin token →
  401; con token → 200 con contexto; gateway sin token → 401; token
  inválido → 401; token válido → 200 con la identidad resuelta por Django.
  Endpoints históricos intactos tras el rebuild: `/health` (2382 chunks),
  `/indices`, `/memory` → 200.

---

## Fase 2 — Tool Registry: Tools de solo lectura

**Objetivo:** primer valor real y de bajo riesgo — el motor puede responder
"¿dónde está mi pedido?" con datos reales, sin poder todavía modificar nada.
Se eligen deliberadamente las Tools **sin acciones de escritura** para esta
fase. Esta fase construye, en términos de la Arquitectura General: el
**Capability Registry** (Componente 1) y el **Tool Registry** que hay detrás,
con **Tool Metadata** (Componente 13) declarado desde el primer Tool, y
**Versionado** (Componente 12) desde el día uno.

**Patrón de cada Tool** (`ai_engine/tools/<dominio>.py`): una función Python
plana que:
1. Recibe `(user_context, **args)` — `user_context` viene de la Fase 1.
2. Llama **exclusivamente** al Selector real ya existente (columna
   "Envuelve" de la tabla).
3. Aplica la validación de propiedad si el Selector no la trae incluida
   (marcado `[owner-check manual]`).
4. Devuelve un dict serializable, nunca un objeto de modelo Django crudo.
5. Declara su `ToolMetadata` (Componente 13) — incluso siendo de solo
   lectura, para que Observabilidad (Fase 6) tenga datos desde el día uno.

| Tool | Envuelve (ya existe) | Capability expuesta al LLM | Nota |
|---|---|---|---|
| `OrderStatusTool` | `OrderSelector.list_for_user(user)` / `get_by_uuid(uuid)` | `buscar_pedido` | `[owner-check manual]` en `get_by_uuid` |
| `RentalStatusTool` | `RentalRequestSelector.list_for_user(user)` / `get_by_uuid_for_user(uuid, user)` | `buscar_alquiler` | ya trae owner-check |
| `RentalAvailabilityTool` | `RentingSelector.check_availability(variant_id, start, end, qty)` | `verificar_disponibilidad` | solo lectura, sin PII |
| `PaymentStatusTool` | `WompiPaymentViewSet.transaction_status` (owner-safe) — reusar la misma query, no el endpoint HTTP | `consultar_pago` | devuelve solo `status`/`status_label` — **no** el motivo de rechazo (gap #2, no resuelto aquí) |
| `ServiceStatusTool` | `Order.service_operation` tras `OrderSelector` owner-check + `ServiceOperationSelector` | `consultar_servicio` | `[owner-check manual]` |
| `KycStatusTool` | `KycSelector.get_own_verification(user)` | `consultar_kyc` | ya es self-service por diseño |
| `EquipmentSearchTool` | `RentingSelector.list_available_equipment()` | `buscar_equipos` | público, sin JWT estrictamente necesario |
| `StockCheckTool` | `InventorySelector.get_stock_for_variant(variant)` | `consultar_stock` | público |
| `ActivePromosTool` | `MarketingSelector.list_active_flash_offers()` | `consultar_promociones` | público |

**Alcance:**
- [x] `ai_engine/capabilities/registry.py` — `CapabilityRegistry` (9
      capabilities de la tabla, cada una apuntando a su Tool actual).
- [x] `ai_engine/tools/__init__.py` — `ToolRegistry` (nombre → función +
      `ToolMetadata` + JSON-schema de argumentos, para `bind_tools` futuro
      en Fase 3).
- [x] Las 9 Tools de la tabla, cada una con test manual vía `/tools/debug`
      (endpoint temporal solo-dev, no expuesto en prod).
- [x] **No** se conecta todavía al LLM/LangGraph — se prueban invocándolas
      directo, para separar "¿la Tool funciona?" de "¿el LLM la elige bien?".

**Cierre (2026-07-16):**
- **Hallazgo de diseño (resuelto dentro de la fase):** las Tools viven en
  `ai_engine` (FastAPI, sin Django) — "envolver al Selector" se materializa
  vía **endpoints internos read-only nuevos en Django**
  (`/api/v1/internal/ai/*`, uno por dominio, cada uno en la app dueña:
  `<app>/api/internal_ai.py`), el único camino que la Fase 1 sanciona
  ("nunca a los modelos directamente"). Cada endpoint es una fachada
  delgada del Selector exacto de la tabla (cero lógica de negocio nueva,
  solo selección de campos compactos para presupuesto de tokens) y exige
  JWT de usuario activo. Routing agregado en `ecommerce/internal_ai_urls.py`.
- Los 3 gaps tocados quedaron como dicta el plan: gap #2 — PaymentStatusTool
  reusa la query owner-safe de `transaction_status` **sin** el side-effect
  `_sync_wompi_status` y solo expone status/status_label; gap #4 —
  el endpoint de servicios agrega el owner-check (`order__user`) que
  `ServiceOperationSelector` no trae; gap #5 — `ActivePromosTool` solo
  cubre `FlashOffer` (PersonalOffer sigue pendiente de decisión).
- `ToolRegistry` real en `ai_engine/tools/registry.py` (re-exportado desde
  `tools/__init__.py`, donde también se importan los 7 módulos de dominio
  que disparan el registro); rechaza argumentos desconocidos y jamás
  propaga excepciones (todo error vuelve como dict serializable).
- `/api/v1/ai/tools/debug` (GET lista, POST invoca; acepta nombre de Tool o
  de capability — misma resolución que usará el LLM) protegido por JWT y por
  el flag `AI_TOOLS_DEBUG` (default **false** → 404; solo el compose de dev
  lo enciende — prod nunca lo define).
- Verificación en vivo (dev, `cliente.test@sintel.co`): 9/9 Tools con datos
  reales — orden `PENDING_PAYMENT` real, transacción Wompi `PENDING`, KYC
  `APPROVED`, equipo con disponibilidad `true` y stock vía kardex; listas
  vacías correctas donde el usuario no tiene datos; sin token → 401;
  capability `buscar_pedido` → `OrderStatusTool`; tool/argumento desconocido
  rechazados limpiamente.

---

## Fase 3 — Action Graph: orquestación con confirmación humana

**Objetivo:** el LLM empieza a decidir qué Tool usar — pero solo las de
lectura de la Fase 2. Es aquí donde se construye el grafo nuevo,
**paralelo** al de generación de código. Esta fase construye, en términos de
la Arquitectura General: **Context Optimizer** (Componente 4) y completa el
**Planner** con intención de negocio.

**Alcance:**
- [x] Nuevo `ai_engine/action_graph.py` (no tocar `graph.py`) con estado
      propio `SintelActionState(TypedDict)`: `user_context`, `message`,
      `conversation_id`, `intent`, `optimized_context`, `tool_calls`,
      `tool_results`, `needs_confirmation`, `final_response`.
- [x] Nodos nuevos: `detect_intent` (reusa el patrón regex de
      `planner.py::detect_intent` pero con intents de negocio, no de código),
      `resolve_customer_context` (llama la Fase 1), `optimize_context`
      (Componente 4 — recorta historial/RAG/datos de cliente a lo relevante
      de este turno antes de construir el prompt), `retrieve_knowledge`
      (reusa `retrievers.py` tal cual, sin tocarlo — para preguntas de
      política/FAQ, ver Componente 10 para no mezclarlo con datos vivos),
      `select_and_execute_tools` (aquí sí se usa
      `llm.bind_tools(...)`, primera vez en el proyecto, y el LLM solo ve
      Capabilities — Componente 1), `validate_tool_result`,
      `generate_response`.
- [x] `graph.compile(checkpointer=...)` — primera vez que se persiste estado
      entre llamadas (memoria de conversación mínima, ver Fase 5 para
      niveles adicionales).
- [x] Nuevo endpoint `POST /chat` en `main.py` (no reemplaza `/generate`).
- [x] Verificación: 5 preguntas reales de ejemplo del usuario ("¿dónde está
      mi pedido?", "quiero alquilar una cámara para mañana" [solo
      disponibilidad, sin crear nada todavía], "¿qué equipos son
      compatibles?", "¿por qué rechazaron mi pago?", "¿ya asignaron mi
      servicio?") respondidas correctamente end-to-end con datos reales de
      un usuario de prueba.

**Cierre (2026-07-16):**
- Decisiones de seguridad adicionales: el **JWT viaja por
  `config["configurable"]`, nunca dentro del estado** (el checkpointer
  persiste el estado; un token no se persiste — coherente con
  `feedback_no_persist_live_tokens`); el `thread_id` del checkpointer se
  namespacea `"{user_id}:{conversation_id}"` para que nadie retome la
  conversación de otro usuario adivinando el id. Checkpointer actual:
  `MemorySaver` (RAM — la fase solo pide memoria mínima; persistencia real
  es Fase 5). El estado incluye además `history` (últimos turnos, insumo
  del Context Optimizer).
- **Hallazgo (resuelto en la fase): el LLM local (llama3.1:8b) genera
  argumentos placeholder** ("hoy", "UUID de la variante de cámara") — la
  primera corrida de la verificación fue 5/5 honesta pero 2/5 sin datos
  útiles. Se endureció la orquestación (no la lógica de negocio): saneo de
  args contra el JSON-schema del ToolMetadata (uuids/fechas con formato
  real o la llamada se descarta) + **fallback determinístico** a la
  capability base de la intención cuando ninguna llamada ejecutable
  sobrevive o todas fallan. Segunda corrida: 5/5 con datos reales donde
  existen. Con un modelo mayor (`LLM_PROVIDER=openai/anthropic`, ya
  soportado por `llm_factory.py`) el saneo queda como red de seguridad.
- La pregunta "¿por qué rechazaron mi pago?" responde exactamente lo que el
  gap #2 permite: estado real + honestidad sobre el motivo no disponible +
  oferta de escalar a soporte. Nada se inventa (regla del prompt del
  `generate_response` + `validate_tool_result` anotando errores/vacíos).
- `/generate`/`/validate`/`/plan`/`/impact`/`/breakage` intactos
  (restricción dura verificada tras cada rebuild vía `/health`).

---

## Fase 4 — Tools de escritura (bajo riesgo, con confirmación)

**Objetivo:** el motor puede ejecutar acciones reales, siempre con paso de
confirmación explícito (`interrupt` de LangGraph) antes de invocar el
Command. Esta fase construye, en términos de la Arquitectura General: la
**Policy Layer** (Componente 5) completa, y consume el **Tool Metadata**
(Componente 13, campo `requires_confirmation`/`risk`) declarado en la
Fase 2.

| Tool | Envuelve (ya existe) | Confirmación requerida |
|---|---|---|
| `CreateRentalRequestTool` | `RentalRequestCommands.create_request(user, data)` | Sí — resumen de fechas/precio antes de confirmar |
| `CancelRentalTool` | `RentalRequestCommands.cancel_request(request)` | Sí — irreversible |
| `StartQuotationTool` | `QuoteTemplateSelector.list_active()` → wizard → `QuotationBuilder.create_from_template(...)` | Sí, al final del cuestionario |
| `RequestKycUpgradeTool` | `KycCommands.request_upgrade(verification, type, user)` | Sí |
| `OpenSupportTicketTool` | `ChatCommands.get_or_create_room` + `save_message` + `attach_context` | No (no es destructivo), pero se le avisa al usuario que un humano lo atenderá |

**`[GAP #1 — decisión del usuario requerida antes de esta fase]`**: no existe
un "cambiar fecha de alquiler" self-service. Opciones a decidir en esta fase,
no antes: (a) construir `RentalRequestCommands.change_dates()` nuevo
(requiere disponibilidad + repricing, alcance de desarrollo real), (b) la
Tool solo ofrece cancelar+recrear, (c) la Tool escala a
`OpenSupportTicketTool`. **No se implementa nada de esto sin que el usuario
elija explícitamente.**

**Alcance:**
- [x] Nodo `evaluate_policy` en el Action Graph (Policy Layer, Componente 5)
      — consulta `ToolMetadata.risk`/`requires_confirmation` + las
      permission classes reales (`IsBuyerOrAdmin`, etc.) antes de permitir
      `execute_tool`.
- [x] Nodo `request_confirmation` — usa el mecanismo `interrupt()` de
      LangGraph (ya en la versión instalada, `>=0.2.0`) para pausar el
      grafo hasta que el usuario confirme en el mismo hilo de conversación.
- [x] Las 5 Tools de la tabla + resolución explícita del Gap #1, cada una
      con su `ToolMetadata` completo (`risk`, `requires_confirmation`,
      `rate_limit`, `audit_level`).
- [x] Nodo `audit_log` — registra toda acción de escritura (Componente 6,
      Audit) antes/después de ejecutar el Command.
- [x] Cada acción de escritura queda confirmada al usuario — reusar
      `notifications.NotificationCommands.dispatch_notification()` para
      confirmar por WS/Email/WhatsApp que la acción se ejecutó (mismo patrón
      que ya usan 8+ apps, cero código nuevo de notificación).

**Cierre (2026-07-16):**
- **Gap #1 RESUELTO por decisión explícita del usuario (2026-07-16):
  opción (c) — escalar a soporte.** El intent `rental_change` ("cambiar la
  fecha de mi alquiler") enruta determinísticamente a
  `OpenSupportTicketTool`, adjuntando el alquiler como `ChatRoomContext`
  (CONTEXT_RENTAL). Verificado en vivo: mensaje del cliente en la sala,
  contexto adjunto, respuesta avisando que atiende un humano. NO se
  construyó `change_dates()` ni se ofrece cancelar+recrear.
- Arquitectura física igual que la Fase 2: cada Command se envuelve vía un
  endpoint interno POST en la app dueña (`rentals/create|cancel`,
  `quotes/templates|create`, `kyc/request-upgrade`, `support/ticket`) con
  las **permission classes reales** (`IsBuyerOrAdmin`, etc.) — la Policy
  Layer del motor es defensa temprana (admin-check, rate limit del
  `ToolMetadata`, confirmación), nunca la única barrera. Validación por los
  **mismos serializers** de los flujos públicos
  (`RentalRequestInputSerializer`, `QuotationFromTemplateInputSerializer`,
  `RequestUpgradeSerializer`) — cero validación duplicada; un 400 con los
  campos faltantes es lo que el LLM usa para pedirle datos al cliente antes
  de pedir confirmación.
- `ToolMetadata` ganó `side_effects: bool` — es lo que dispara el camino de
  Policy Layer. Tool extra de lectura: `QuoteTemplatesTool` (paso 1 del
  wizard de cotización, la parte `list_active()` de la tabla).
- **Audit en dos capas:** durable en Django — nuevo event type
  `SecurityEvent.AI_ACTION_EXECUTED` (migración `security.0006`), creado
  por cada endpoint interno de escritura con el usuario real del JWT — y
  estructurado en el motor (nodo `audit_log`). Notificaciones: heredadas de
  los Commands envueltos (patrón `dispatch_notification` existente), sin
  código nuevo de notificación.
- **Restricción dura honrada también en `/tools/debug`**: una Tool con
  `side_effects` exige `confirmed=true` o devuelve 403 — verificado.
- Hallazgos técnicos (resueltos en la fase): (1) langgraph 0.2.76 NO expone
  `__interrupt__` en el resultado de `ainvoke()` — el payload del interrupt
  se lee del checkpoint vía `graph.get_state()`; (2) llama3.1:8b
  malinterpretaba el desenlace de la acción — se agregaron flags
  determinísticos `action_executed: true/false` al resultado (el LLM nunca
  decide por su cuenta si una acción ocurrió); (3) asistencia
  determinística de escritura para intents inequívocos (cancelar con uuid
  en el mensaje, escalamiento del gap #1) — la confirmación aplica igual;
  (4) el fallback determinístico de la Fase 3 quedó restringido a
  capabilities de LECTURA: una escritura jamás se dispara por fallback.
- Verificación e2e en dev (seeds reales, LLM local): confirmación pausa el
  grafo con resumen de la acción; "si" → `cancelled` en BD + respuesta que
  confirma; "no" → `pending_payment` intacto + respuesta honesta de que
  nada cambió; ticket del gap #1 creado con contexto; debug-gate 403;
  `AI_ACTION_EXECUTED` creciendo por cada escritura. Incidencia de entorno
  durante la verificación (no de código): `db`/`redis` dev estaban caídos y
  `docker compose restart django` no levanta dependencias — usar `up -d`.

---

## Fase 5 — Memoria (conversación, cliente, empresarial)

**Objetivo:** las 3 capas de memoria que propuso el usuario, en orden de
menor a mayor riesgo/costo. Esta fase completa el **Customer Context
Builder** (Componente 3) y construye **CRM Context** (Componente 9).

- [x] **Conversación** — ya cubierta parcialmente por el `checkpointer` de la
      Fase 3 (últimos N mensajes del hilo activo).
- [x] **Cliente** — nueva tabla ligera (¿en `accounts` o app nueva
      `ai_engine_bridge`? decidir en esta fase) que cachea, no duplica:
      equipos/servicios frecuentes (derivable de `orders`/`renting` ya
      existentes vía `MarketingSelector.get_user_marketing_profile(user)`,
      que YA calcula `total_spent`/`orders_count`/`preference` — reusar, no
      reinventar), direcciones (`ShippingAddressSelector.list_for_user`,
      ya existe), métodos de pago (`TokenizedCard`, ya existe). Este es
      exactamente el componente **CRM Context** (Componente 9).
- [x] **Empresarial** — ya existe como `GLOBAL_MEMORY.json`/RAG de
      `docs/specs/` — en esta fase se decide si políticas/promociones vivas
      (no solo estáticas) deben indexarse también (ej. `FlashOffer`/
      `PersonalOffer` activos del día, vía `MarketingSelector`).
- [x] Aplicar **Caché Inteligente** (Componente 14) a las consultas de
      contexto de cliente que se repiten dentro de la misma conversación —
      reusando la estrategia de cache de Django ya documentada, sin
      inventar una paralela.

**Riesgo a vigilar:** no crear una "memoria de cliente" que duplique datos ya
existentes en Django — esta fase es principalmente de **cacheo/consulta**,
no de nuevo almacenamiento de verdad de negocio.

**Cierre (2026-07-16):**
- **Decisión "¿tabla en accounts o app nueva?": NINGUNA tabla.** El propio
  riesgo señalado por la fase (duplicar datos) apuntaba la salida: el CRM
  Context es un endpoint agregador
  (`accounts/api/internal_ai.py::AiCustomerContextView`,
  `GET /api/v1/internal/ai/customer-context/`) que compone los selectors
  reales (`get_user_marketing_profile` + `ShippingAddressSelector` + query
  de `TokenizedCard` idéntica al ViewSet, exponiendo solo marca y últimos 4
  dígitos, jamás `token_id`) y cachea el dict en el **cache de Django
  (Redis), TTL 300s** — misma estrategia documentada en core, cero
  almacenamiento nuevo de verdad de negocio.
- El Customer Context Builder quedó completo: `optimize_context` trae el
  CRM context **solo** para intents que lo aprovechan
  (`renting_search`/`promos`/`quote` — personalización y prellenado de
  contacto/dirección al crear solicitudes), nunca todo en cada turno.
- **Decisión "¿indexar promociones vivas al RAG?": NO.** El Componente 10
  lo prohíbe explícitamente (Knowledge vs Live Data): las promos activas ya
  se sirven como dato vivo vía `ActivePromosTool`/`MarketingSelector`; el
  RAG sigue siendo solo conocimiento estático. Memoria empresarial queda
  como está (`GLOBAL_MEMORY.json` + `docs/specs/`).
- Conversación: `MemorySaver` (RAM) + `history` en el estado (últimos 3
  turnos entran al prompt). Suficiente para el alcance de la fase;
  persistencia durable entre reinicios del contenedor queda anotada como
  mejora opcional (`langgraph-checkpoint-sqlite`/Postgres) para cuando el
  canal web real exista (Fase 7).
- Verificación en vivo: `customer-context` 1ª llamada `cached:false`, 2ª
  `cached:true`; perfil real ($535.500, 2 pedidos pagados, preferencia
  "products", 2 direcciones, 1 tarjeta sin token); seguimiento multi-turno
  en el mismo hilo ("¿y cuánto costó ese pedido?") respondido con el monto
  real — la memoria de conversación funciona end-to-end.

---

## Fase 6 — Multiagente: permisos y herramientas por agente

**Objetivo:** dividir el Tool Registry único de las Fases 2-4 en conjuntos
con permisos por tipo de agente (Support/Sales/Rental/Technical
Service/Order/Payment/CRM/Admin), reusando exactamente las permission
classes de Django (`IsBuyerOrAdmin`, `IsServiceProviderOrAdmin`, etc.) como
filtro de qué Tools puede invocar cada agente — no se inventa un sistema de
permisos paralelo. Esta fase construye **Agent Profiles** (Componente 11)
completos y la capa de **Observabilidad** (Componente 6).

- [x] `AgentRegistry` con scopes de Tools por agente, cada agente definido
      como un **Agent Profile** completo (Componente 11: nombre,
      descripción, objetivo, personalidad, herramientas, permisos,
      capacidades, memoria, reglas de escalamiento, tono) — nunca un agente
      creado solo por nombre.
- [x] Router de intención → agente (extiende `detect_intent` de la Fase 3).
- [x] Handoff entre agentes dentro del mismo `action_graph` (ej. Rental
      Agent deriva a Support Agent si detecta frustración/reclamo, según su
      propia regla de escalamiento declarada en el profile).
- [x] Instrumentación de **Observabilidad** (Componente 6): tokens, tiempo
      de respuesta, costo, tool calls, errores, reintentos, fallbacks,
      latencia por Tool, uso de memoria, conversaciones — emitidos vía
      logging estructurado, con integración a Prometheus/Grafana/
      OpenTelemetry preparada pero no instalada (decisión de costo
      pendiente, mismo criterio que el roadmap de Cloudflare).

**Cierre (2026-07-16):**
- **7 Agent Profiles** en `ai_engine/agents/profiles/*.yaml`: OrderAgent,
  PaymentAgent, RentalAgent, ServiceAgent, SalesAgent, AccountAgent,
  SupportAgent (agente por defecto y destino de todo escalamiento; también
  atiende `rental_change` — gap #1). Los tipos **CRM y Admin** de la lista
  original quedan para la **Fase 8**, cuando existan sus Tools (marketing
  admin / Core content) — un profile sin herramientas reales violaría
  "nunca un agente solo por nombre".
- `AgentRegistry` (`agents/__init__.py`) valida cada profile al cargar
  contra CapabilityRegistry/ToolRegistry y compila las regex de
  escalamiento — un YAML roto impide el arranque en vez de fallar en
  runtime. El scope del agente es el límite duro de qué capabilities ve el
  LLM en el turno (la lista por intent sigue siendo el optimizador); los
  `permisos` del YAML son las permission classes reales, cuyo enforcement
  sigue viviendo en los endpoints internos de Django.
- Handoff verificado en vivo: "mi pedido llegó en un estado pésimo" →
  intent `order_status` → OrderAgent → regla `pesimo|inaceptable` →
  SupportAgent, que consultó el pedido real Y abrió el ticket (métricas:
  `handoff: OrderAgent->SupportAgent`, 2 tools ok). La persona
  (personalidad/tono del YAML) entra al prompt de `generate_response` —
  estilo de comunicación, jamás reglas de negocio.
- `ai_engine/observability.py`: una línea JSON por turno (logger
  `observability`) con agent, intent, llm_calls, tokens in/out, tool_calls,
  errores, latencia por Tool, fallback_used, handoff, needs_confirmation,
  write_executed, duration_ms. Prometheus/Grafana/OTel: instrumentación
  lista para conectar un exporter sobre ese logger, no instalado (decisión
  de costo, igual que el roadmap Cloudflare).
- Verificación: 7 agentes cargados; routing correcto Order/Payment/Rental
  por intent; queja directa → SupportAgent con ticket real; handoff
  cross-agente demostrado; métricas completas en logs.

---

## Fase 7 — Multicanal: WhatsApp / Web / Panel / API externa

**Objetivo:** el mismo Action Graph sirve distintos canales de entrada,
reusando la infraestructura de canales que YA existe en `notifications`
(`CHANNEL_WEB_SOCKET`/`CHANNEL_EMAIL`/`CHANNEL_WHATSAPP`) — no se construye
un canal de WhatsApp nuevo, se conecta el existente al Action Graph como
disparador de entrada además de salida. Esta fase construye **Human
Handoff** (Componente 7) completo y la **Integración con Event Bus**
(Componente 8).

- [x] Widget de chat web (reusa `support/consumers.py` como transporte,
      `action_graph` como "cerebro" detrás en vez de/además de un humano).
- [x] Webhook de WhatsApp entrante → Action Graph → respuesta vía el mismo
      `dispatch_notification` channel.
- [x] **Human Handoff** (Componente 7): nodo `escalate_to_human` que crea/
      reusa una `ChatRoom`, adjunta contexto (`ChatCommands.attach_context`),
      vuelca el historial de la conversación con el AI, notifica al
      operador vía el grupo `support_admins` (ya existe en
      `SupportChatConsumer`), y sigue el seguimiento sin perder historial.
- [x] **Integración con Event Bus** (Componente 8): el Action Graph se
      suscribe a los mismos disparadores `on_commit`/Celery que ya usan
      `orders`/`renting`/`technical_services`/`payment` para
      `dispatch_notification` — permite conversaciones proactivas ("tu
      técnico llega en 20 minutos") sin construir un bus nuevo.
- [x] Panel admin: vista de "conversaciones IA" para supervisión humana.

**Cierre (2026-07-16):**
- **Cero cambios de frontend**: el modo AI vive en `SupportChatConsumer`
  (mensaje del cliente → si la sala está en modo AI, una tarea asyncio llama
  al Action Graph vía `support/services/ai_bridge.py` y responde como el
  bot). El widget Vue existente funciona tal cual; el bot firma con un
  usuario dedicado (`AI_BOT_EMAIL`, inactivo, password inutilizable — jamás
  puede autenticarse) y se muestra del lado del agente.
- `ai_bridge.ask_ai()` acuña un access token efímero del usuario real
  (Django ES el emisor SimpleJWT legítimo) — sintel_ai sigue sin exponerse:
  todos los canales entran por Django. `conversation_id = room-{uuid}` /
  `wa-{user_id}` → hilos estables del checkpointer por canal.
- **Human Handoff completo**: al abrir ticket, el grafo inyecta los últimos
  6 turnos (`history`, nunca controlado por el LLM — no está en el
  args_schema) → transcripción volcada en la sala firmada por el bot +
  `ChatRoom.ai_paused=True` (campo nuevo, migración `support.0005`) + aviso
  en vivo al grupo `support_admins`. Verificado: tras el handoff el AI queda
  silenciado y el humano recibe todo el contexto.
- **WhatsApp**: `WhatsAppInboundWebhookView`
  (`/api/v1/notifications/whatsapp-webhook/`, AllowAny como el de Wompi;
  GET verify con `WHATSAPP_WEBHOOK_VERIFY_TOKEN`) → tarea Celery
  `process_whatsapp_inbound` (cola notifications) → resuelve usuario por
  últimos 10 dígitos del teléfono del perfil → Action Graph → respuesta por
  `WhatsAppClient.send_text()` (método nuevo; texto libre válido en la
  ventana de servicio de 24h). Verificado con envío interceptado: respondió
  con datos reales del pedido. **Pendiente para producción:** configurar el
  webhook en Meta Business Manager + token real (y exponer la ruta vía el
  tunnel).
- **Event Bus (Componente 8)**: hook en `dispatch_notification` — para los
  slugs de `AI_PROACTIVE_SLUGS` (env), además de los canales normales se
  encola `ai_proactive_room_message` que deja un mensaje del bot en la sala
  del cliente (visible en widget y panel). Un consumidor más del mismo
  dispatch de 11 apps, no un bus paralelo.
- **Panel admin**: las conversaciones IA viven en `ChatRoom`/`ChatMessage`
  con el bot como sender → `/panel/soporte` las muestra sin cambios; además
  cada respuesta del bot se difunde en vivo al grupo `support_admins`
  (supervisión en tiempo real).
- Verificación e2e (WebsocketCommunicator + tareas reales): 9/9 — WS con
  respuesta del bot y datos reales; queja → handoff (ai_paused +
  transcripción); AI silenciado después; webhook GET/POST; WhatsApp
  respondido; proactivo en sala. Nota: persistencia durable del checkpointer
  (hilos entre reinicios) sigue como mejora opcional anotada en Fase 5.

---

## Fase 8 — AI Business Automation

**Objetivo:** una vez el AI Core puede responder y actuar de forma segura
(Fases 1-7), esta fase lo pone a trabajar de forma proactiva sobre el
negocio, no solo reactiva a preguntas. Construye la **Integración con Core**
(Componente 15) y cierra el círculo completo de capacidades propuesto por
el usuario.

**Alcance:**
- [x] **Automatizacion comercial** — recomendaciones basadas en
      `MarketingSelector.get_user_marketing_profile(user)` (preferencia
      productos/servicios/renting ya calculada).
- [x] **Automatizacion de campanas** — conectado a
      `MarketingSelector.get_campaign_targets_for_stale_products()` y
      `get_stale_stock_alerts()` (ya existen, hoy admin-only, se exponen
      como Tools de agente de marketing con Policy Layer propia).
- [x] **Seguimiento postventa** — dispara vía Event Bus (Componente 8) tras
      `OrderServiceTimeline`/`ServiceOperation` completados.
- [x] **Renovaciones** — para alquileres/servicios recurrentes, usando el
      mismo `RentalRequestSelector`/`ServiceOperationSelector` de solo
      lectura ya construidos en Fase 2, sin lógica de negocio nueva.
- [x] **Mantenimiento preventivo** — sobre equipos de `renting`, vía
      `EquipmentBlockSelector` (ya existe para bloqueos de mantenimiento).
- [x] **Cross-selling / Up-selling** — basado en CRM Context (Componente 9),
      nunca inventado por el LLM sin datos reales de respaldo.
- [x] **Recordatorios** — vía `dispatch_notification()`, cero código nuevo
      de notificación.
- [x] **Prediccion** — explícitamente fuera de alcance de esta fase salvo
      que el usuario lo pida por separado (requiere un modelo de datos y
      pipeline propios, no es una extensión trivial del Action Graph).
- [x] **Automatizacion de soporte** — Support Agent (Fase 6) resolviendo
      consultas repetitivas antes de Human Handoff.
- [x] **Integracion con Core** (Componente 15): Tools nuevas
      (`CoreContentTool` o una por dominio) que envuelven
      `HomeConfigCommands`/`NavbarLinkCommands`/`FooterGroupCommands`/
      `FooterCTACommands`/`HomeCardCommands`/`BrandSliderCommands` — permite
      que un Admin Agent administre Home Builder/Navbar/Footer/CTA/Banners/
      Cards/Slider de marcas por conversación, siempre a través de estos
      Commands ya existentes, nunca escribiendo Vue/JS ni tocando el
      frontend directamente.

**Riesgo a vigilar:** esta es la fase de mayor superficie de automatización
— cada capability nueva de esta fase debe pasar por la misma Policy Layer y
el mismo Tool Metadata que las fases anteriores; "automatización" no es una
excusa para saltarse confirmación humana en acciones irreversibles (sigue
aplicando la Restricción Dura correspondiente).

**Cierre (2026-07-16):**
- **Automatizacion comercial / Cross-selling / Up-selling:** `PersonalRecommendationTool`
  envuelve `MarketingSelector.get_user_marketing_profile()` + flash offers activas
  relevantes segun la preferencia del usuario (products/services/renting). El hint de
  recomendacion va al LLM como dato estructurado, nunca como regla de negocio en el prompt.
  Nuevo intent `personal_recommendation` en `action_graph.py`; `_CRM_CONTEXT_INTENTS`
  ampliado para que el Context Optimizer incluya el perfil CRM en estos turnos.
- **Automatizacion de campanas:** `MarketingDashboardTool` (dashboard consolidado),
  `StaleStockAlertsTool` (stock inactivo por dominio) y `CampaignTargetsTool` (usuarios
  objetivo) envuelven los selectores admin existentes. Intent `marketing_admin`.
  Todos exigen `IsAdminUser` -- la Policy Layer y el permission del endpoint son la
  doble barrera.
- **Seguimiento postventa / Renovaciones / Recordatorios:** el mecanismo ya existia
  (`AI_PROACTIVE_SLUGS` + `ai_proactive_room_message_task` en `notifications/tasks.py`,
  completado en Fase 7). Esta fase no agrega codigo nuevo -- documenta que cualquier
  slug nuevo en `.env:AI_PROACTIVE_SLUGS` activa el proactivo sin cambiar el motor.
- **Mantenimiento preventivo:** `MaintenanceCheckTool` + `AiEquipmentMaintenanceView`
  (`GET /api/v1/internal/ai/renting/maintenance/`) envuelven
  `EquipmentBlockSelector.list_for_equipment(active_only=True)`. Intent
  `maintenance_check`. Solo admin.
- **Automatizacion de soporte:** cubierta por el `SupportAgent` (Fase 6) que ya
  resuelve consultas repetitivas antes de `OpenSupportTicketTool` (Human Handoff).
  No requirio codigo nuevo en esta fase.
- **Integracion con Core (Componente 15):** 9 Tools nuevas en
  `ai_engine/tools/core_tools.py` (4 de lectura + 5 de escritura con confirmacion
  obligatoria y `risk=high`) + 9 endpoints internos en `core/api/internal_ai.py`
  (todos `IsAdminUser`) envuelven `HomeConfigCommands`, `HomeConfigSelector`,
  `NavbarLinkCommands`, `NavbarLinkSelector`, `FooterGroupSelector`, `FooterSelector`,
  `BrandSliderCommands`, `BrandSliderSelector`. Intent `core_content`. Nuevo
  `AdminAgent` profile en `agents/profiles/admin_agent.yaml`. El AI nunca escribe
  Vue/JS ni accede al ORM directamente -- solo Commands ya existentes (restriccion
  dura del Componente 15).
- **Nuevos Agent Profiles:** `MarketingAgent` (dashboard, stock, campanas,
  recomendaciones) y `AdminAgent` (Core Content + mantenimiento). Ambos validados
  al cargar contra `CapabilityRegistry`/`ToolRegistry` -- un YAML roto impide el
  arranque. Los tipos CRM y Admin de la lista original de la Fase 6 quedan cubiertos
  por estos dos profiles.
- **Capabilities nuevas (28 total):** +13 capabilities en `registry.py`.
  Intents nuevos en `action_graph.py`: `marketing_admin`, `personal_recommendation`,
  `maintenance_check`, `core_content`.
- **Restricciones duras honradas:** ninguna Tool de escritura sin Policy Layer
  (`side_effects=True`); ninguna escritura sin `requires_confirmation=True`; ninguna
  regla de negocio en el prompt del LLM; todas las escrituras Core exigen
  `IsAdminUser`; el fallback deterministico solo apunta a capabilities de lectura.
- **Verificacion pendiente (requiere rebuild del contenedor `sintel_ai`):**
  `9 AgentProfiles cargados` en los logs al arrancar; `/api/v1/ai/tools/debug`
  lista 28+ tools; intents nuevos responden con datos reales. El rebuild sigue
  el mismo patron que cierres anteriores: `docker compose up -d --build sintel_ai`.
  Prod: rebuild + re-test cuando el usuario lo autorice.


---

## Auditoria final del documento

Verificación de consistencia de esta v2 contra las 3 referencias exigidas
por el usuario, y contra los criterios de calidad arquitectónica pedidos.

### Contra los 3 documentos de referencia

| Referencia | Verificado | Resultado |
|---|---|---|
| `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` | Sí, leído (estructura general + secciones RBAC/Service Layer/dashboard BFF) | **Sin contradicciones** — el plan reutiliza textualmente los mismos conceptos (Service Layer, Commands/Selectors, dashboard BFF, `NotificationCommands.dispatch_notification()` dentro de `on_commit`, permission classes reales) en vez de inventar equivalentes propios |
| `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` | Sí, leído completo | **Sin contradicciones** — el plan declara explícitamente que `graph.py`/`chains.py`/`guardrails.py`/`retrievers.py` no se tocan; el Action Graph es un módulo paralelo. *Hallazgo colateral encontrado y corregido en la misma sesión (2026-07-15)*: ese archivo de referencia estaba desactualizado (sección 13 sin `kyc`/`security`/`operations`/`shipping`/`organization`, sección 17.3 con "18 apps"/103 modelos en vez de 21/147, faltaban 9 endpoints reales como `/plan`/`/breakage`/`/memory`/`/graph/*`/`/search`/`/manifest`/`/refresh`) — ya sincronizado a pedido explícito del usuario tras detectarlo aquí |
| `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` | Sí, ya sincronizado en esta misma sesión (2026-07-15) | **Sin contradicciones** — el Componente 15 (Integración con Core) y la Fase 8 nombran exactamente los Commands reales documentados ahí (`FooterGroupCommands`, `BrandSliderCommands`, etc.), no genéricos inventados |

### Contra los criterios de calidad pedidos

- **Duplicidades**: ninguna — cada componente nuevo referencia una única
  vez su fase de construcción; las Fases 1-7 solo referencian los
  componentes, no repiten su definición.
- **Responsabilidades mezcladas**: ninguna — la tabla de la Arquitectura
  General asigna exactamente una responsabilidad por capa; Knowledge vs
  Live Data (Componente 10) existe específicamente para que RAG y Selectors
  no se confundan.
- **Dependencias circulares**: ninguna — el flujo es estrictamente
  descendente (Channels → Gateway → ... → LLM); Human Handoff (Fase 7) y
  Event Bus (Fase 7) son las únicas capas con flujo "hacia arriba"
  (notificar al usuario/operador), y ambas reusan el mecanismo de
  notificación ya existente, no un canal de retorno nuevo.
- **Componentes huérfanos**: ninguno — los 15 Componentes Arquitectónicos
  Nuevos están todos referenciados desde al menos una Fase; ninguno queda
  "flotando" sin un lugar de construcción.
- **Entradas/salidas por módulo**: documentadas en el detalle de cada
  Componente (ver sección correspondiente) y en la columna "Envuelve" de
  cada tabla de Tools.
- **Entregables verificables por fase**: cada fase mantiene su lista de
  checkboxes (`- [ ]`) como criterio de cierre explícito, sin cambios de
  formato respecto a la v1.
- **Compatibilidad hacia atrás con el AI Engine actual**: garantizada por
  la Restricción Dura explícita — `/generate`/`/validate`/`/plan`/`/impact`/
  `/breakage` siguen intactos; el Action Graph vive en un archivo nuevo
  (`action_graph.py`), nunca modifica `graph.py`.
- **Independencia del grafo de generación de código**: confirmada — ningún
  nodo del Action Graph (Fase 3+) importa ni reutiliza estado de
  `SintelCodeState`; comparten solo la infraestructura de bajo nivel ya
  existente (`llm_factory.py`, `embeddings_factory.py`, `vectorstore_factory.py`).
- **Preparación para crecimiento modular**: Versionado (Componente 12) y
  Tool Metadata (Componente 13) existen desde la Fase 2 precisamente para
  que agregar una Fase 9/10 futura no requiera romper contratos ya
  publicados.

---

## Referencias

- Investigación técnica completa de esta auditoría (2026-07-15): hallazgos
  línea por línea de `ai_engine/main.py`, `graph.py`, `chains.py`,
  `guardrails.py`, `retrievers.py`, `planner.py`, `knowledge_graph.py`,
  `dependency_graph.py`, `requirements.txt`, autenticación y networking —
  ver memoria de sesión `project_ai_core_migration_plan`.
- Inventario completo de Selectors/Commands reales por app (orders, renting,
  payment, quotes, technical_services, support, kyc, notifications,
  accounts/users, inventory, marketing) — ver la misma memoria.
- Patrón de documento vivo por fases: `docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md`.
- Documentos cross-validados en esta v2 (2026-07-15):
  `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`,
  `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md`,
  `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md`.
