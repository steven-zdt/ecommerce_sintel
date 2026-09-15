# RAG_POST2 — FASE 16 (Performance Loop) y FASE 17 (Cost Control)

**Misión RAG-POST2, 2026-09-16.** Igual que en FASE 2 (retrieval evaluation), esta fase declara
explícitamente qué es medible con evidencia real de esta sesión y qué requeriría una carga
controlada que no se ejecutó — sin fabricar percentiles que no existen.

---

## FASE 16 — Performance Loop

### Lo que SÍ se midió (real, de corridas reales de esta sesión — no un benchmark formal)

| Componente | Latencia real observada | Fuente |
|---|---|---|
| Turno completo, sin evidencia RAG, sin grounding | 15-38s (domina `agent_latency_ms`, la generación real del LLM) | Múltiples turnos reales de esta sesión (ej. `duration_ms=29224`, `agent_latency_ms=28779` para el caso NA-3 del eval battery) |
| Retrieval (`retrieval_latency_ms`) | 361ms (caso real medido) | Turno NA-3, ver arriba — HTTP interno a Django + pgvector, rápido, no es el cuello de botella |
| Grounding (`grounding_latency_ms`) | No aparece como cuello de botella en las corridas reales (max_tokens=10, respuesta corta) | `test_grounding_integration.py`, corridas reales de esta sesión |
| Extracción de memoria (LLM) | 30-40s, ~700 tokens de razonamiento interno del modelo local | Medido explícitamente en vivo durante FASE 10 (ver `customer_memory_adapter.py` docstring) |
| Sesión persistente (`DatabaseSessionService` vs `InMemorySessionService`) | Overhead no aislado — el turno real con backend persistente activo tardó lo mismo que turnos previos con memoria (dominado igual por el LLM); no hay una comparación A/B controlada | — |

### Por qué la extracción de memoria NO afecta la latencia del turno (decisión de diseño, FASE 10)

Corre en background (`asyncio.create_task`), nunca `await` directo — el hallazgo de 30-40s
llevó DIRECTAMENTE a esa decisión de diseño (ver `customer_memory_adapter.py` y
`AUDITORIA/RAG_POST2_BASELINE.md`). Verificado con un test real
(`test_extraccion_corre_en_background_no_bloquea_la_respuesta`): un mock deliberadamente de 60s
no hace que el turno tarde eso.

### Lo que NO se midió (`NOT MEASURABLE` explícito, y por qué)

| Métrica pedida | Estado | Razón |
|---|---|---|
| p50/p95 de latencia | **NOT MEASURABLE** | Ninguna corrida de esta sesión fue una carga controlada (requests concurrentes, volumen representativo) — son turnos individuales de test/debug. Un percentil con N=1 por escenario no es un percentil real, sería fabricar precisión que no existe |
| Latencia LLM aislada (sin retrieval/grounding/memoria) | **PARCIAL** | `agent_latency_ms` YA es esa medición real (incluye Tools, no aísla "solo generación de texto") — no hay una versión sin Tools para comparar |
| Comparación formal RAG V2 vs RAG V2+metrics vs +sesión vs +memoria | **NOT MEASURABLE como delta cuantificado** | Cada fase se verificó funcionalmente (tests reales, pasan), no se corrió el MISMO conjunto de turnos 4 veces con/sin cada feature para aislar el delta de latencia de cada una — hacerlo requeriría una sesión de benchmarking dedicada, fuera del alcance real de esta iteración de la misión |

### Recomendación (no ejecutada)

Si se necesita un p50/p95 real: un script de carga (ej. `locust`/`k6` o un loop simple de N
turnos secuenciales/concurrentes reales) contra el `sintel_ai_adk` de dev, midiendo
`metrics.duration_ms` de cada respuesta real — la instrumentación (FASE 5/6) YA expone todo lo
necesario para calcularlo, solo falta la carga de prueba en sí.

## FASE 17 — Cost Control

### Dato real medido (proxy de tokens, único disponible — ver limitación abajo)

Único punto de datos exacto obtenido en esta misión (debug explícito de FASE 10, no
extrapolado): una llamada real de extracción de memoria —
`Usage(completion_tokens=719, prompt_tokens=346, total_tokens=1065, reasoning_tokens=699)`.

### Por qué el resto es `NOT AVAILABLE` (monetario) / `NOT MEASURABLE SISTEMÁTICAMENTE` (tokens)

- **Costo monetario real**: `NOT AVAILABLE` — el proveedor real (LM Studio local, Ollama) no
  factura por token, no hay ningún proveedor de pago activo en `LOCAL_MODEL_CHAIN` hoy. Un
  "costo por conversación" real solo tendría sentido si algún día se usa un proveedor de pago —
  documentado como N/A, no como 0 (fingir "$0" sería inexacto para un despliegue futuro con un
  proveedor real).
- **Conteo de tokens sistemático por turno**: sigue sin exponerse — ADK no expone
  `usage_metadata` por Event de forma directa (gap ya documentado desde la misión RAG
  Enterprise, FASE 11). No se resolvió en esta fase porque requeriría instrumentar cada llamada
  litellm individualmente (grounding, extracción de memoria, generación del agente) por
  separado, cambio de mayor alcance que esta misión no justifica sin evidencia de que el costo
  real sea un problema operativo hoy (proveedor local, sin facturación).

### Qué SÍ cambió el perfil de costo real de esta misión (cualitativo, no cuantificado en $)

| Cambio | Impacto real en volumen de llamadas LLM |
|---|---|
| Grounding (FASE 7, RAG Enterprise) | +1 llamada LLM, pero SOLO si `intent=="knowledge"` Y hay evidencia real — hoy, con F-1 sin resolver, esto casi nunca se dispara en producción real |
| Extracción de memoria (FASE 10, RAG-POST2) | +1 llamada LLM en **CADA turno**, sin importar el intent — este es el mayor incremento real de volumen de llamadas que introdujo esta misión. Mitigado en latencia (background), NO mitigado en volumen de llamadas/cómputo |

### Recomendación (no ejecutada)

Si el volumen de tráfico real crece lo suficiente para que el cómputo de la extracción de
memoria en background empiece a competir por recursos con los turnos en primer plano (mismo
proceso LM Studio/Ollama, capacidad finita), considerar: (a) un filtro heurístico barato ANTES
de la llamada LLM (ej. longitud mínima del mensaje, o palabras clave de preferencia) para reducir
cuántos turnos disparan la extracción, o (b) un modelo más pequeño/rápido dedicado solo a esta
clasificación. Ninguna de las dos se implementó aquí por falta de evidencia de que el volumen
actual lo justifique (Regla 2 de la misión).

## Checkpoint FASE 16-17 — Estado

**PASS, con límites declarados.** Ninguna métrica de latencia/costo se fabricó — cada número en
este documento es trazable a una corrida real de esta sesión, y cada `NOT MEASURABLE`/`NOT
AVAILABLE` viene con la razón concreta, no un placeholder vacío.
