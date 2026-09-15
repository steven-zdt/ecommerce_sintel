# RAG_KNOWLEDGE_DATA_AUDIT — FASE 1

**Misión: "Perfeccionamiento Enterprise del RAG del Chat de Soporte", 2026-09-16.**
Objetivo de esta fase: determinar si el problema real está en el mecanismo de retrieval o en la
calidad/estructura de los datos. Deliverable formal separado del baseline (`RAG_SUPPORT_
BASELINE.md`), aunque el hallazgo central ya se registró ahí como F-1 — este documento lo
desarrolla con el detalle que pide explícitamente FASE 1 de la misión.

---

## Verificación real (repetida aquí, no asumida del baseline)

```
documentos totales:          0
documentos activos+públicos: 0
documentos activos+internos: 0
chunks totales:               0
chunks con embedding:         0
chunks sin embedding:         0
```

Verificado contra `ecommerce_sintel_django` (dev) en el momento de escribir este documento.

## Respuesta directa a la pregunta de FASE 1

**El problema NO está en el mecanismo de retrieval — no hay datos sobre los cuales el mecanismo
pueda fallar o acertar.** No existen documentos, chunks duplicados, contenido obsoleto, metadata
inconsistente, versiones conflictivas ni relaciones entre documentos que auditar, porque no
existe ningún documento. Cualquier checklist de calidad de datos (chunking semántico,
preservación de contexto, consistencia del modelo de embeddings) es, hoy, una pregunta sin objeto.

Esto **no invalida** el trabajo de las fases siguientes (2-7, 11-12 ya ejecutadas en esta misión):
el mecanismo de retrieval/reranking/confidence/grounding se construyó y se probó igual, con datos
sintéticos controlados (mismo patrón que ya usaba `ai_knowledge/tests.py` antes de esta misión) —
pero su beneficio real en producción queda **bloqueado**, no por una falla de esos mecanismos,
sino por la ausencia total de contenido que indexar.

## Lo que SÍ está listo para recibir contenido real

Verificado, no asumido:

| Componente | Estado |
|---|---|
| Modelo de datos (`AIKnowledgeDocument`/`AIKnowledgeChunk`) | Real, migrado, con campos de gobernanza (`visibility`, `is_active`) ya funcionando |
| Proveedor de embeddings | Configurado y activo en dev (`bge-m3` vía Ollama) — confirmado con una llamada real, no mockeada |
| Ingesta (`AIKnowledgeDocumentCommands.upsert_document`) | Real, funcional — chunking por párrafos (1200/150 chars) |
| Embedding diferido (`AIKnowledgeEmbeddingCommands.embed_pending_chunks`) | Real, funcional |
| Retrieval híbrido + reranking + confidence + grounding (FASE 3-7 de esta misión) | Real, probado con datos sintéticos |

## Lo que NO existe (y no se puede inventar, Regla 6 de la misión)

- **Ningún mecanismo de ingesta desde el panel admin.** `AIKnowledgeDocumentCommands.
  upsert_document()` existe como función de servicio, pero **no está conectada a ningún endpoint
  HTTP ni a ninguna vista de `/panel/soporte`** — verificado revisando `ai_knowledge/api/views.py`
  (solo contiene `AiKnowledgeRetrieveView`, de solo lectura para el motor de IA). Hoy, la única
  forma real de cargar un documento es `manage.py shell` directo. Esto es un hallazgo adicional
  no registrado antes en el baseline — se agrega aquí como **F-10**.
- **Ningún documento fuente real** (políticas, FAQs, garantías, horarios) — ni siquiera en
  borrador. No existe una fuente de la verdad textual fuera del código para poblar esto.

## Clasificación de hallazgos de esta fase

| ID | Hallazgo | Severidad |
|---|---|---|
| F-1 (heredado del baseline) | Base de conocimiento completamente vacía | **CRITICAL** |
| **F-10 (nuevo)** | No existe ningún mecanismo de ingesta vía API/panel admin — solo `manage.py shell` directo | HIGH |

## Recomendación (no ejecutable por este agente — decisión de producto/contenido)

Para que el trabajo de las FASE 2-12 de esta misión se traduzca en valor real de producción, se
necesitan, en este orden:
1. Una decisión de negocio sobre qué contenido publicar (FAQs, políticas, garantías, horarios
   reales de SINTEL) — no es algo que este agente pueda inventar sin violar la Regla 6 de la
   misión ("no inventar datos").
2. Un mecanismo real de ingesta desde `/panel/soporte` (F-10) — esto SÍ es una tarea técnica
   ejecutable, pero está fuera del alcance explícito de esta misión (que se enfoca en retrieval/
   contextualización/grounding/memoria/evaluación/observabilidad, no en construir un CRUD nuevo
   de contenido). Se deja documentado como recomendación siguiente, no se construye aquí sin que
   el usuario lo pida explícitamente (evita expandir el alcance de la misión sin autorización).

## Checkpoint 1 — Estado

**PASS**, con la salvedad explícita del hallazgo F-1/F-10: el "audit de calidad de datos" que
pide FASE 1 concluye honestamente que no hay datos que auditar, y documenta por qué (y qué falta
para que algún día los haya). No se fabricó contenido de prueba en la base de datos real de
desarrollo para simular una corpus poblado — los tests de FASE 2-7/12 usan datos sintéticos
efímeros dentro de cada test (`TestCase`, revertidos automáticamente), nunca datos persistentes
en `ai_knowledge` real.
