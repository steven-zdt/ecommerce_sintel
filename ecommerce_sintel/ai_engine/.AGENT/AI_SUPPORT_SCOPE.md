# AI Support Scope — Alcance congelado del Support Agent

> Fase 1 del `PLAN_DE_EJECUCION_SUPPORT_AGENT`. Define, de forma vinculante, qué es y qué
> no es el `SINTEL SUPPORT AI AGENT`. Ningún cambio posterior de las Fases 2-18 puede
> ampliar el alcance "Prohibido" de este documento sin editarlo explícitamente primero.
>
> **[Revisión 2026-08-08, decisión del usuario]** La auditoría de Bloque 2/3
> (`AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md` seccion 6) encontró que `AgentRegistry`
> (`agents/__init__.py`) ya enruta `/chat` entre **9 Agent Profiles**, no uno solo. El
> plan original describía Sales/Marketing/Admin Agent como trabajo *futuro*, posterior a
> certificar un único Support Agent — en el código ese futuro ya está implementado. El
> usuario decidió **ampliar el alcance de este documento** para reconocerlo: "Support
> Agent" en todo este plan significa la plataforma completa de 9 agentes de negocio, no
> solo `agents/profiles/support_agent.yaml`. La seccion 1 de abajo refleja esa decisión.

---

## 1. Objetivo

El AI Agent de SINTEL tiene, por ahora, una única responsabilidad: atender conversaciones
de negocio y soporte mediante chat. Esa responsabilidad se implementa hoy como una
**plataforma de 9 Agent Profiles** ruteados por intención (`AgentRegistry`,
`agents/profiles/*.yaml`), no como un agente único:

```text
SupportAgent    -- reclamos, escalamientos, casos que requieren un humano
AccountAgent    -- KYC / upgrade de perfil profesional
AdminAgent      -- contenido del home, mantenimiento, [excepcion] impacto de arquitectura
MarketingAgent  -- dashboard, recomendaciones personalizadas
OrderAgent      -- estado de pedidos
PaymentAgent    -- consultas de pago
RentalAgent     -- alquileres: estado, busqueda, cancelacion, stock
SalesAgent      -- promociones, cotizaciones, conocimiento (RAG)
ServiceAgent    -- servicios tecnicos
```

Todos comparten:

> Comprender la intención del usuario, consultar información autorizada del sistema,
> ejecutar acciones de negocio permitidas y escalar a un agente humano cuando
> corresponda.

El AI Agent **no** es un generador de código.

---

## 2. Permitido

- Recibir mensajes de clientes.
- Identificar intención y enrutarla al Agent Profile correspondiente de los 9
  (`AgentRegistry.route` — ver `SUPPORT_AGENT_SPEC.md` seccion Intents).
- Recuperar contexto del usuario (Customer Context).
- Consultar información del sistema vía Tools (nunca ORM directo).
- Consultar conocimiento documental mediante RAG.
- Ejecutar acciones de negocio permitidas (Tools READ y WRITE con Policy).
- Solicitar confirmación antes de acciones sensibles (WRITE / HIGH RISK).
- Mantener conversaciones con memoria de conversación + cliente.
- Recordar el contexto de la conversación (Redis, TTL 7 días — `redis_checkpointer.py`).
- Derivar conversaciones a soporte humano (`ChatRoom.ai_paused`).
- Responder por Web Chat.
- Responder por WhatsApp (fase posterior, mismo Support Agent — ver Fase 11).
- Registrar métricas y auditoría por turno (`observability.py`).

## 3. Prohibido

Quedan fuera del Support Agent, sin excepción:

- Generación de código.
- Modificación automática del código.
- Creación de modelos Django.
- Creación de ViewSets.
- Creación de serializers.
- Creación de componentes Vue.
- Generación de migraciones.
- Los endpoints `/generate`, `/validate`, `/plan`, `/impact`, `/breakage`.
- CodePlan, CodeGuard (guardrails.py / guardrails_frontend.py).
- Generación automática de frontend o backend.

Estas capacidades **existen hoy en el mismo proceso `ai_engine`** (mismo `main.py`,
mismo puerto 8100 — ver `FLIJO_COMPLETO_IA_ENGINE.md`), pero pertenecen conceptualmente a
un **AI Engineering Agent independiente**, a separar en la Fase 17. Hasta esa separación,
el Support Agent no debe invocar, importar ni depender en tiempo de ejecución de:
`graph.py`, `chains.py`, `chains_frontend.py`, `guardrails.py`, `guardrails_frontend.py`,
`planner.py`, `auditor.py`, `project_map.py`, `knowledge_graph.py`, `dependency_graph.py`.

## 4. Regla de dependencia

> El Support Agent debe poder operar completamente sin `/generate`, `/validate`, `/plan`,
> `/impact`, `/breakage`, CodePlan, CodeGenerator, FrontendGenerator, ArchitectureGuard.

Cualquier PR que agregue al camino de ejecución de `/chat` (`action_graph.py` y lo que
éste importa) una dependencia sobre los módulos de generación de código listados arriba
incumple este documento y debe rechazarse en revisión, incluso si el resto del cambio es
correcto.

### 4bis. Excepción documentada — **CERRADA 2026-08-10, ya no existe**: `AdminAgent` / `architecture_impact`

> **[CORREGIDO, Fase 20 "Limpieza Documental", 2026-08-10]** Esta seccion describia una
> excepción **vigente**. Ya no lo es: `tools/graph_tools.py` (`GraphImpactAnalysisTool`) fue
> **eliminado por completo** el 2026-08-10 (Fase 0 del rediseno "Site Knowledge Graph / AI Editor
> Runtime", ver `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md`), junto con el intent
> `architecture_impact` y la capability `analizar_impacto_arquitectura` que lo ruteaban. La regla
> de esta sección 4 es hoy **absoluta, sin excepciones**: "AI Engine no conoce ni importa
> `project_knowledge_graph`" aplica a TODO `ai_engine`, incluido `AdminAgent`. Se deja el
> contenido original abajo por valor historico (documenta por que existio la excepcion y bajo que
> condiciones se acepto en su momento), pero **no es precedente utilizable hoy** -- cualquier
> intento de reintroducir una dependencia similar debe tratarse como una propuesta NUEVA, no como
> "restaurar" esta excepción.

`tools/graph_tools.py` importa `dependency_graph.py` y `knowledge_graph.py` directamente,
para exponer la capability de solo lectura `analizar_impacto_arquitectura`
(`GraphImpactAnalysisTool`) al intent `architecture_impact`, ruteado exclusivamente a
`AdminAgent` (`agents/profiles/admin_agent.yaml`) y protegido con `IsAdminUser`. Se agregó
el 2026-08-04 (antes de este plan de scope-freeze), per
`AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md`.

Fue la **única** violación conocida de la regla de dependencia de esta sección, y quedó
**aceptada deliberadamente** por decisión del usuario (2026-08-08): era de solo lectura,
restringida a administradores, y le daba a un admin visibilidad de impacto arquitectónico
sin salir del chat. No fue precedente para agregar más dependencias de código-gen a
`/chat` — cualquier módulo nuevo que quiera tocar `graph.py`, `chains*.py`,
`guardrails*.py`, `planner.py` sigue prohibido por esta sección (`auditor.py`/`project_map.py`
ya ni siquiera existen, ver `FLIJO_COMPLETO_IA_ENGINE.md` sección 17), sin excepción adicional
sin pasar antes por este documento.

## 5. Resultado de esta fase

El AI Agent queda formalmente definido como **SINTEL SUPPORT AI AGENT**: la plataforma de
9 Agent Profiles descrita en la seccion 1, con una única excepción documentada (seccion
4bis). El contrato funcional detallado (identity, intents, tools, policy, memory,
handoff) está en [`SUPPORT_AGENT_SPEC.md`](SUPPORT_AGENT_SPEC.md), y la evidencia
componente-por-componente en
[`AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md`](AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md).
