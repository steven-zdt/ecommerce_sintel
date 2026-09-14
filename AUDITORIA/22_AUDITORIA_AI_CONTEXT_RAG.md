# 22 — Auditoría Enterprise: AI — Context Window y calidad de RAG (Fase 8)

> **Fase 8 completada 2026-08-01** — la mayoría de los ítems del brief original
> (`ai_bridge`, Memoria, Prompt Builder, Knowledge Graph como componente, Tool Calls, Human
> Handoff, Fallback, Intent Detection, Observabilidad, Costos, Tokens) ya se auditaron a fondo en
> [16_AUDITORIA_AI_ENGINE_SYNC.md](16_AUDITORIA_AI_ENGINE_SYNC.md) (Fase 2). Esta fase revisó
> específicamente lo que quedaba genuinamente sin tocar: **Context Window** y **calidad real del
> RAG** (`retrievers.py`).

## Hallazgos

**Context Window: bien acotado, con presupuestos explícitos.** `action_graph.py`:
`MAX_CONTEXT_CHARS=6000`, `MAX_HISTORY_TURNS=3`, `MAX_KNOWLEDGE_CHUNKS=6` — todos aplicados
realmente (no solo declarados): `node_optimize_context` trunca a `MAX_CONTEXT_CHARS`,
`node_retrieve_knowledge` trunca chunks individuales a 800 chars y el conocimiento agregado a
`MAX_CONTEXT_CHARS`. Nota menor, no bug: cuando SÍ hay retrieval de conocimiento, el contexto
final se trunca a `MAX_CONTEXT_CHARS * 2` (12000), el doble del presupuesto que
`node_optimize_context` documenta como "explícito" — parece deliberado (dar más espacio a
preguntas de FAQ/política) pero no está comentado como tal. Cosmético, no se corrige.

**RAG: arquitectura sólida — ensemble BM25+semántico, filtrado por app, deduplicación real.**
`build_ensemble_retriever` combina `BM25Retriever` (35%) + búsqueda semántica MMR (65%,
`lambda_mult=0.6` para diversidad), con filtro real por `app_name` cuando aplica. La
deduplicación (`retrieve_context_for_task`) usa hash de los primeros 200 caracteres — suficiente
para el volumen de documentos de este proyecto, sin falsos negativos observables. Nada que
corregir — no se encontró un bug concreto y verificable en la lógica de retrieval.

## Resumen ejecutivo

Sin hallazgos nuevos accionables. El diseño de Context Window y RAG es consistente con las buenas
prácticas ya observadas en el resto de `ai_engine` (presupuestos explícitos, invariantes de
arranque, separación de responsabilidades) — confirma, no contradice, la evaluación general
favorable de Fase 2. Con esto, el brief de Fase 8 queda cubierto en su totalidad entre esta fase
y la Fase 2.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-7 | Hechas — ver documentos 15-21 |
| 8 — AI (Context Window, RAG) | **Hecha (este documento) — sin hallazgos nuevos accionables** |
| 9-16 | Pendientes |
