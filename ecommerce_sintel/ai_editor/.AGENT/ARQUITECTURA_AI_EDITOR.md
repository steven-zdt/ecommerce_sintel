# Arquitectura de `ai_editor/`

Vision general -- para el detalle fase-por-fase (bugs reales encontrados,
verificacion contra el repo real, cifras de tests) ver
`AI_EDITOR_BASELINE.md`. Este documento es el mapa de alto nivel.

## 1. Que es `ai_editor/`

Convierte una solicitud humana de cambio de software en un cambio
trazable, controlado, validado y auditable -- construido sobre el "Site
Knowledge Graph" (`project_knowledge_graph/`, ya cerrado y estable), sin
volver a implementar nada de ese modulo.

## 2. Los 3 sistemas y su frontera

```
AI ENGINE          = SUPPORT CHATBOT       -- ai_engine/
PROJECT KNOWLEDGE GRAPH = ENTIENDE EL SITIO -- project_knowledge_graph/
AI EDITOR           = CAMBIA EL SITIO       -- ai_editor/ (este paquete)
```

**Regla arquitectonica absoluta**: `ai_editor` NUNCA importa `ai_engine`
(verificado por `test_ai_editor_never_imports_ai_engine`, AST-walk real).
`ai_editor` NUNCA importa `project_knowledge_graph.*` directo salvo a
traves de `ai_editor.graph_client` (verificado por
`test_graph_client_is_read_only_reexport_of_graph_sdk`).

```
AI EDITOR -> graph_client -> project_knowledge_graph.graph_sdk -> project_knowledge_graph
```

## 3. Los 10 submodulos (todos con logica real desde POST-GRAPH 8)

| Submodulo | Fase | Que hace | Alcance |
|---|---|---|---|
| `graph_client/` | Fase 14 / POST-GRAPH 1 | Frontera de solo lectura hacia el grafo, 16 operaciones | Completo |
| `llm/` | POST-GRAPH 2 | Cliente LLM independiente (Ollama/OpenAI/Anthropic, HTTP puro) | Completo |
| `intent/` | POST-GRAPH 2 | Interpreta solicitud humana, confirma dominio contra el grafo | Completo |
| `resolver/` | POST-GRAPH 3 | Resuelve entidades del intent contra el grafo (exacto, no fuzzy) | Completo |
| `planner/` | POST-GRAPH 4/5 | ChangePlan + validacion contra el filesystem real | Completo |
| `repository/` | POST-GRAPH 7/12/16 | Sandbox aislado, promocion gateada, rollback | Completo (mecanismo) |
| `patch/` | POST-GRAPH 6/18 | Aplica un cambio ya decidido de forma segura | **Acotado: no genera codigo** |
| `validation/` | POST-GRAPH 8/9/10 | Sintaxis real; tests/contratos/grafo/reconciliacion | **Acotado: solo Nivel 1** |
| `approval/` | POST-GRAPH 11 | CHANGE SUMMARY + registro de decision humana | Completo |
| `audit/` | POST-GRAPH 13/17 | Registro append-only + metricas agregadas | Completo |

## 4. Que NO existe (documentado, no omitido en silencio)

- **Generacion de codigo real**: `patch/` aplica un `new_content` ya
  decidido (por un humano o un test) -- no hay una capa de LLM
  escribiendo diffs reales sobre Django/Vue. Este es EL gap real mas
  importante del sistema: sin esto, `ai_editor` puede planificar,
  validar y aprobar cambios, pero no generarlos.
- **Graph Reconciliation** (POST-GRAPH 9): NOT_IMPLEMENTED, ver
  `VALIDATION_MODEL.md`.
- **Ejecucion real de tests / rebuild del grafo dentro del sandbox**
  (Niveles 2-5 de Validation): el sandbox es una copia PARCIAL de
  archivos, no un entorno Docker completo -- decision explicita del
  usuario (2026-08-11) de mantenerlo asi.
- **Multi-step change / DAG multi-modulo** (POST-GRAPH 15): requeriria
  extender `planner/` de topologia estrella a grafo real, diferido sin
  caso de uso real que lo motive.

## 5. Donde seguir

- Flujo completo paso a paso: `CHANGE_FLOW.md`.
- Modelo de seguridad (todos los guardrails): `SECURITY_MODEL.md`.
- Detalle del Patch Engine: `PATCH_ENGINE.md`.
- Que esta validado y que no: `VALIDATION_MODEL.md`.
- Las 16 operaciones del Graph Client: `GRAPH_CLIENT.md`.
- Como usar el sistema en la practica: `OPERATIONS_GUIDE.md`.
- Historial completo fase por fase: `AI_EDITOR_BASELINE.md`.
- Diseno del loop autonomo (no implementado, por que): `AUTONOMOUS_CHANGE_LOOP.md`.
