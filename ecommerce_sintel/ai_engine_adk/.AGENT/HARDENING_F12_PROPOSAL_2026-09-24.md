# HARDENING — FASE 12 (eficiencia del modelo primario Ollama/Qwen3.5-9B): PROPUESTA (estado: APPROVAL_REQUIRED)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §16. Nada implementado. Regla vigente: no se corren benchmarks/tests sin tu autorizacion (las mediciones de esta fase usan la GPU compartida de 8 GB y el modelo; cada corrida la autorizas). Primero se MIDE, despues se cambia: el plan prohibe optimizar "porque suena bien" (cuantizacion, keep_alive, tiers de modelo).

## Estado real (inspeccion read-only en DEV, 2026-09-24)
| Punto §16 | Hallazgo |
|---|---|
| **Contexto del modelo** | `ollama ps`: `qwen3.5:9b`, **CONTEXT = 4096** (default de Ollama; nadie fija `num_ctx`), `20%/80% CPU/GPU` (6.3 GB: no cabe entero en 8 GB de VRAM). Ni el compose ni `model_runtime.py`/`model_chain.py` pasan `num_ctx` ni `keep_alive` |
| **Presupuesto de contexto inconsistente** | F5 acota el historial a 12 turnos / **48 000 caracteres (~12 000 tokens)**, pero el modelo solo ve 4096 tokens. Si el prompt lo supera Ollama recorta en silencio (con riesgo de perder instrucciones del sistema o el inicio del historial). Nunca se midio cuanto se acerca un turno real a ese techo |
| **Coste fijo de las tools por agente** (chars/4 de nombre+descripcion+schema, sin historial) | CatalogAgent 24 tools ≈ **3 040 tokens** (75 % del contexto!), AdminAgent 10 ≈ 1 030, RentalAgent 6 ≈ 750, MarketingAgent 9 ≈ 610, SupportAgent 3 ≈ 400, resto < 320. + politica de precedencia (~130) + perfil/objetivo |
| Turno real medido (F9, RentalAgent, 6 llamadas al modelo) | 13 360 tokens de entrada / 1 337 de salida / 12.1 tok/s / 111 s: ~2 200 tokens de entrada POR llamada, crece con cada tool call |
| Limites de salida (§16.3) | Por superficie, no por agente: `AI_SUPPORT_MAX_OUTPUT_TOKENS=1024`, `AI_ADMIN_MAX_OUTPUT_TOKENS=2048` (incluyen los tokens de razonamiento de Qwen). No existe limite por agente ni por tool |
| Limite de resultado por tool (§16.3) | **No existe**: `http_bridge`/`sintel_adapter` no acotan filas ni bytes del resultado que vuelve al modelo (solo saneo/escaneo de F5). Un listado grande de catalogo entra completo al contexto |
| Contexto minimo (§16.4) | Ya cumple: cada agente solo recibe SUS tools; RAG es top-k; el historial se recorta (F5). Falta el recorte de resultados de tools y la coherencia con `num_ctx` |
| Model routing FAST/STANDARD/STRONG (§16.2) | El enrutamiento de intencion ya es determinista (sin LLM). No hay evidencia de que un segundo modelo aporte: la GPU (8 GB) ya esta al limite con UN modelo de 9B y compartida con LM Studio |
| Cuantizacion (§16.5) / keep_alive (§16.6) | Modelo `qwen3.5:9b` en la cuantizacion por defecto de Ollama; `keep_alive` = default 5 min (`UNTIL: 4 minutes from now`). Sin medicion de cold start |

## Cambios propuestos (dev primero; cada cambio de comportamiento solo tras medir)

### C1 — Medicion baseline del turno (riesgo nulo, solo lectura) — *requiere autorizacion (GPU)*
Script `scripts/ai_eval/efficiency_baseline.py` (stdlib) que, contra el ADK de DEV con las metricas de F9, ejecuta un conjunto FIJO de turnos representativos (los casos `live` del golden dataset F10 por agente: Support, Rental, Order, Catalog admin...) y reporta por agente: tokens de entrada por llamada (max/p95), llamadas por turno, tokens de salida (razonamiento incluido), tok/s, latencia, y **margen contra `num_ctx`**. Tambien mide cold start (1er turno tras `ollama stop`) y `ollama ps` (split CPU/GPU, VRAM). Resultado = tabla en este documento; sin cambiar nada.

### C2 — Coherencia contexto/`num_ctx` (riesgo medio; depende de C1)
Segun lo que muestre C1 hay tres salidas, y se elige con datos (no de antemano):
  a. Si los turnos caben con holgura en 4096: dejar `num_ctx` y **bajar `AI_MAX_CONTEXT_CHARS` a un valor coherente** (~10 000-12 000 chars) para que F5 recorte ANTES que Ollama.
  b. Si CatalogAgent (3 000 tokens solo de tools) no cabe: declarar `num_ctx` explicito para el admin (p. ej. 8192, midiendo el coste en VRAM/velocidad por el offload a CPU) **o** reducir sus tools por turno (subconjunto por intencion) — decision aparte, con eval.
  c. `num_ctx` se fija de forma explicita (parametro de la peticion via LiteLLM/`options`, o Modelfile) para que deje de depender del default; replicado en dev y prod (`.env`/`.env.production` mismo cambio).
Cualquier cambio de `num_ctx` cambia la huella del modelo (F10) => se re-corre el benchmark antes de produccion.

### C3 — Limites de salida por agente (riesgo bajo)
Mapa `AI_AGENT_MAX_OUTPUT_TOKENS` (Support/Order/Payment/Account/Service/Sales: valor de superficie cliente; Rental/Marketing: intermedio; Catalog/Admin: superficie admin) con **valores tomados de los p95 medidos en C1** + margen para el razonamiento; el default sigue siendo el actual por superficie (comportamiento identico si no se configura). Reemplaza `_max_output_tokens_for` sin cambiar su firma.

### C4 — Tope de resultado por tool (riesgo bajo/medio)
En `sintel_adapter` (etapa de saneo de la salida, F4/F5): si el resultado serializado excede `AI_TOOL_MAX_RESULT_CHARS` (default propuesto 8 000 chars ≈ 2 000 tokens), recortar listas (`max filas`, conservando el orden) y anadir un marcador explicito `"[resultado recortado: N de M elementos]"` para que el modelo no invente el resto. Registrado como `ai_operation_event=tool_result_truncated` (sin contenido) y contado en `ai_turn_metrics`. Modo monitor primero (`AI_TOOL_RESULT_ENFORCE=false`: solo registra que se habria recortado), luego enforce tras ver los datos.

### C5 — keep_alive / precarga (riesgo bajo; depende de C1)
Con el cold start medido: proponer `OLLAMA_KEEP_ALIVE` (p. ej. 30m, NO `-1`) para el Ollama de dev y, si aplica, prod; verificar el efecto en VRAM compartida con LM Studio (la GPU es una sola). Decision con la medicion, no de antemano.

### C6 — Decisiones documentadas (sin cambios de codigo)
- **Sin cuantizacion nueva ni modelos FAST/STRONG** en esta fase: sin evidencia (§16.5 exige baseline + golden + latencia + memoria + concurrencia + seguridad + canary; concurrencia es F13).
- **Modo pensamiento (razonamiento) de Qwen**: es el mayor consumidor de tokens/latencia (F9: ~3 700 caracteres de razonamiento por 1 470 publicos). Desactivarlo por intencion simple podria bajar la latencia a la mitad, pero cambia la calidad: solo como **experimento con el golden dataset** (F10) y tu aprobacion aparte; no se toca aqui.

## Tests (SE ESCRIBEN, NO SE EJECUTAN)
Mapa de limites por agente (default/override/valores invalidos), recorte de resultados (listas, dicts anidados, marcador, monitor vs enforce, resultado pequeno intacto, sin contenido en el log), coherencia `AI_MAX_CONTEXT_CHARS` vs `num_ctx` (invariante configurable). Verificacion: `py_compile` + inspeccion + las mediciones de C1 (con tu autorizacion).

## Riesgos / rollback
C1 no cambia nada. C2-C5 se activan por variable de entorno con default = comportamiento actual (rollback = quitar la variable). Riesgo principal: subir `num_ctx` aumenta el offload a CPU y ralentiza (la GPU ya trabaja al 80 %): por eso se decide con C1 y se re-evalua en F10/F13. Kill switches nuevos: `AI_TOOL_RESULT_ENFORCE` y `AI_AGENT_MAX_OUTPUT_TOKENS` (vacio = comportamiento actual), replicados dev/prod.

## Preguntas para aprobar
1. ¿Apruebas C1-C6? En particular: ¿autorizas la medicion C1 en DEV (usa GPU/modelo; unos 20-30 min) y el analisis de `num_ctx`?
2. ¿C2/C3/C5 se deciden con los datos de C1 y me pides confirmacion antes de aplicar cada cambio de comportamiento (recomendado), o aplico lo que los datos indiquen?
3. ¿El experimento de modo-pensamiento queda fuera de esta fase (recomendado) y se propone aparte con el golden dataset?

## Resultado en DEV (2026-09-24) -- "continua con el plan" + regla firme: el asistente NO ejecuta tests ni benchmarks (los corre el usuario)
Implementado solo lo que NO depende de mediciones y con defaults = comportamiento anterior. **Nada de esto se ejecuto** (solo `py_compile` + ASCII + inspeccion); el ADK de dev no se reconstruyo (sin volumenes: `docker compose up -d --build sintel_ai_adk` cuando lo quieras aplicar).
| Cambio | Estado |
|---|---|
| C1 medicion | **Script listo, NO ejecutado**: `scripts/ai_eval/efficiency_baseline.py` (lo corres tu: 8 turnos x N corridas por agente contra el ADK de dev; imprime tokens de entrada por llamada, margen contra `num_ctx`, p95 de salida, tok/s, cold start con `--cold`, `/api/ps` de Ollama). Es la unica fuente para decidir C2/C3(valores)/C5 |
| C3 limite de salida por agente | Hecho: `AI_AGENT_MAX_OUTPUT_TOKENS` (formato `RentalAgent=1536,SupportAgent=768`; vacio = comportamiento actual por superficie) en `ai_engine/config.py`, usado por `_max_output_tokens_for`. **Sin valores**: se fijan con los p95 de C1 |
| C4 tope de resultado de Tool | Hecho: `ai_engine_adk/result_limits.py` (puro, determinista) + integrado en `sintel_adapter` tras el saneo F5. `AI_TOOL_MAX_RESULT_CHARS=8000`, `AI_TOOL_RESULT_ENFORCE=false` (MONITOR: solo `ai_operation_event=tool_result_truncated ...` sin contenido; con `true` recorta la lista mas larga conservando el orden y deja marcador `_truncated: {shown,total}`, y acorta cadenas gigantes) |
| C2 `num_ctx` / `AI_MAX_CONTEXT_CHARS` | **Pendiente de datos**. Hipotesis a confirmar con C1: el prompt de CatalogAgent (~3 000 tokens solo de tools) no deja margen en 4096; F5 permite ~12 000 tokens de historial contra un contexto de 4096. No se cambia nada sin la medicion |
| C5 `keep_alive` | **Pendiente de datos** (cold start de C1). Propuesta: `OLLAMA_KEEP_ALIVE=30m`, nunca `-1`; replicar dev/prod |
| C6 | Sin cambios de codigo (sin cuantizacion nueva, sin modelos FAST/STRONG, experimento de razonamiento aparte con F10) |
Tests escritos, NO ejecutados: `ai_engine_adk/tests/test_result_limits.py`.
Flags nuevos (defaults inocuos): si algun dia se activan `AI_TOOL_RESULT_ENFORCE`/`AI_AGENT_MAX_OUTPUT_TOKENS`, replicarlos en `.env` y `.env.production` en el mismo cambio (incidente del 503).
La huella F10 cambio (tool/agent/model): los baselines `l1_*` quedan obsoletos hasta que los regeneres tu.
