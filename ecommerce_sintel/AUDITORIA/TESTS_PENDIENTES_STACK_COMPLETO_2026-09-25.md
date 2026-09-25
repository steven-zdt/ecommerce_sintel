# Tests que fallan sin el stack completo de dev - anotados (2026-09-25)

Decision del usuario: dejar estos fallos **anotados, sin investigarlos mas**, y no levantar Ollama/ADK/Django dev completos por ahora.
Corrida: hardening F21/F22 y PLAN_LLMDINAMICO, solo dev. Los tests que dependen del codigo nuevo pasan (ver el reporte de la sesion).

## A. `ai_provider/tests_providers.py` (3) - necesitan el contenedor real `sintel_ollama` con `llama3.1:8b`
- `TestOllamaAdapter::test_connection_success` (error `DNS`: el host `sintel_ollama` no resuelve, el contenedor esta apagado)
- `TestConnectionTestServiceAndDiscovery::test_service_delegates_to_correct_adapter`
- `TestConnectionTestServiceAndDiscovery::test_discover_models_delegates_to_correct_adapter` (ademas fija el modelo `llama3.1:8b`, que dev ya no usa: dato de test desactualizado)
No se verifico que fallaran antes de los cambios de esta sesion; el error observado es de red, no de logica.

## B. Suite completa del ADK (`ai_engine_adk/tests`, 40 fallos de 2779 tests) - contenedor suelto con `--env-file .env`
Corrida: 2696 pasan, 40 fallan, 3 se saltan, 41 xfail, 25 min. Requiere `eval/` montado (`-v ...ai_engine_adk/eval:/app/eval:ro`; no viaja en la imagen a proposito).
Causa probable comun: tests "e2e/real" que necesitan un LLM real (Ollama dev), Redis y/o Django en la red de compose.
| Grupo | Tests | Causa |
|---|---|---|
| RAG evaluation battery | `rag_evaluation/test_rag_evaluation_battery.py` NA-1/2/3, AMB-1/2, ADV-1, MT-1, PI-1 | necesitan LLM/RAG en vivo (no verificado) |
| customer_memory | `test_extraccion_real_detecta_preferencia_de_contacto_real`, `test_metrics_memory_used_true/false_*`, `test_extraccion_corre_en_background_*`, `test_metrics_memory_extraction_scheduled_false_*` | extraccion "real" con LLM/Django (no verificado) |
| evaluation battery | `test_eb1_*`, `test_eb2_*` | LLM en vivo (no verificado) |
| grounding integration | 3 tests de `test_grounding_integration.py` | LLM en vivo (no verificado) |
| memory poisoning e2e | `test_pi7_*` (2), `test_pi8_*` | e2e con modelo (no verificado) |
| prompt injection | `test_pi4_e2e_*` | e2e con modelo (no verificado) |
| prompt injection | `test_pi3_routing_de_agente_es_regex_determinista_no_semantico` | **test desactualizado**: asegura `resolve_turn_agent(message)` con solo el parametro `message`, pero la funcion tiene `source` (del Admin AI Assistant). Confirmado leyendo el codigo; el cambio de esta sesion en `sintel_root_workflow.py` es solo `kill_switch_tools_before` |
| RAG poisoning e2e | `test_pi5_*`, `test_pi6_*` | e2e con modelo (no verificado) |
| rate limit | `test_rl1_*`, `test_rl3_*` | usan Redis; el contenedor suelto no alcanza el Redis de compose (inferido, no verificado) |
| reasoning separation | `test_t6_*`, `test_t12_*` | e2e con modelo (no verificado) |
| security matrix | `test_sm2_*` (confirmado: `ModelUnavailableError ... APIConnectionError:lmstudio`, no hay modelo), `test_sm3_*` | necesitan modelo; sm3 tambien puede ser firma antigua de `chat()` (F9 agrego `request`) |
| turn metrics | 9 tests de `test_turn_metrics.py` | e2e con modelo/Django (no verificado) |

## C. Como cerrarlos cuando se decida (comandos del usuario, dev)
1. Levantar dev completo: `docker compose up -d db redis django sintel_ollama sintel_ai_adk` (Ollama con el modelo primario instalado).
2. `docker exec ecommerce_sintel_ai_adk python -m pytest --no-cov -q tests` con `eval/` montado con `-v` y el `.env` de dev.
3. Corregir `test_pi3` (agregar `source` a la firma esperada) y `llama3.1:8b` (usar el modelo vigente) en `tests_providers.py`.
4. Estos fallos NO deben bloquear el commit de F21-F24 ni del Registry, pero no se pueden dar por verificados los flujos e2e hasta cerrarlos.
