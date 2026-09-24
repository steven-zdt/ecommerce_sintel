# HARDENING LLM/AGENTES — FASE 0 (baseline forense) + acciones de FASE 1/3 aplicadas

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md`
Fecha: 2026-09-24. Estado: `HARDENING_STATUS = IN_PROGRESS` (solo Wave 1 / F0 + parte de F1; el resto sin iniciar).
Evidencia: comandos de solo lectura (`docker ps/inspect/logs`, `docker compose config`, `netstat`, lectura de codigo).
No se ejecuto ningun experimento destructivo en produccion.

## Decision fija (plan §1.2)
```text
PRIMARY_MODEL_PROVIDER  = OLLAMA         (contenedor sintel_prod_ollama)
PRIMARY_MODEL           = qwen3.5:9b     (Qwen/Qwen3.5-9B, Q4_K_M, 6.59 GB)
OLLAMA_PRIMARY_MODEL_TAG    = qwen3.5:9b
OLLAMA_PRIMARY_MODEL_DIGEST = 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7 (verificado en prod y dev)
FALLBACK_MODEL_PROVIDER = LM_STUDIO      (host Windows, host.docker.internal:1234)
OLLAMA_ENABLED          = si (integrado 2026-09-24, commit ca5bc7d)
LM_STUDIO_ENABLED       = NO OPERATIVO hoy (conexion rechazada / red inalcanzable desde el contenedor)
```

## Hallazgo raiz del incidente "Soporte en Linea no responde" (2026-09-24)
Configuracion heredada `LM Studio -> (nada)`: `LOCAL_MODEL_CHAIN` de `sintel_ai_adk` tenia LM Studio como UNICO
proveedor y LM Studio (aplicacion de escritorio) no estaba corriendo => el motor no podia generar. Contradice la
politica del plan (Ollama primario). Correccion en `docker-compose.prod.yml` (servicio `sintel_ai_adk`):
`ollama|ollama-nativo|http://sintel_ollama:11434|qwen3.5:9b;lmstudio|openai-compatible|...|qwen/qwen3.5-9b`
+ `depends_on: sintel_ollama (service_healthy)`.
Causa adicional independiente (no verificable sin la BD de produccion): la sala de prueba probablemente estaba
`ai_paused` tras un handoff (`is_ai_mode_active`, `support/services/ai_bridge.py:49`) — no habia ninguna traza
`AI request status=started` en los logs.

## Inventario real vs. plan

| Ítem del plan | Estado real (evidencia) | Gap |
|---|---|---|
| Ollama no expuesto (F1) | Prod: `sintel_prod_ollama` publica solo `11434/tcp` interno (`Ports={"11434/tcp":null}`), sin bind al host. Imagen fijada `0.30.10` | OK. Falta red `ai_private` separada (hoy todo en `sintel-network`) |
| Puertos de prod al host (F0 §4.3) | Ningun contenedor `sintel_prod_*` publica puertos salvo nginx 80/443 internos | OK |
| **Puertos de DEV en el mismo host** | `netstat`: `0.0.0.0:5432`, `0.0.0.0:8100`, `0.0.0.0:8101` y `:6380` (Postgres/AI/ADK/Redis de DESARROLLO) escuchan en todas las interfaces; Ollama dev solo en `127.0.0.1:11434` | **P0 potencial**: si el firewall de Windows/red no los bloquea, son alcanzables desde la LAN. No modificado (requiere aprobacion) |
| Auth servicio-a-servicio (F2) | `/chat` exige un JWT de Django valido (`ai_engine/auth.py::get_validated_token`) y resuelve identidad via `/internal/ai-context/`. NO hay token de servicio separado (`X-AI-Service-Token`) | Gap P0 F2 (sin implementar) |
| Rate limit de chat (F3) | Django: `AI_CHAT_RATE_LIMIT=20` turnos / 10 min por sala (`ai_bridge.py`); por Tool en ADK (Redis, fail-open). Sin limite por IP/usuario/canal/costo en `/chat` | Parcial |
| Presupuesto de turno (F3) | `MAX_TOOL_CALLS_PER_TURN=6`, `_LLM_TIMEOUT_SECONDS=90`, `AI_CHAT_TIMEOUT_SECONDS=300`, `message max_length=4000`. Sin `max_llm_calls`/`max_output_tokens`/`max_context_tokens` | Parcial |
| Circuit breaker / fallback (F3) | El ADK usa solo la entrada PRIMARIA de la cadena (`sintel_root_workflow.py`, "sin fallback multi-entry todavia") | **Gap**: la 2da entrada (LM Studio) documenta el orden pero NO se activa sola |
| Degradacion controlada (F3 §7.4) | Si el motor falla: `main.py` responde texto de "asistente no disponible" + `engine_unavailable`; `ai_bridge` guarda marcador degradado | OK basico |
| Kill switches (F21) | Solo `AI_SUPPORT_CHAT_ENABLED` y `ADMIN_AI_ASSISTANT_ENABLED` (+ `MCP_META_ADS_ENABLED`). No existen `AI_GLOBAL_ENABLED`, `AI_TOOLS_ENABLED`, `AI_WRITE_TOOLS_ENABLED`... | Gap |
| Pin de version del modelo (F16) | Imagen `ollama/ollama:0.30.10` fijada. Tag `qwen3.5:9b` (sin digest registrado aun) | Pendiente digest |
| Migracion/eval de modelos (F10/F12) | Banco `scripts/ai_eval/chat_model_bench.py` (dev, 16 casos sinteticos) | Sin golden dataset de 200+ casos |
| Rotacion de credenciales / backup offsite (F15) | Sin evidencia nueva; se rotó la contrasena de admin compartida en chat el 2026-09-24 | Pendiente segun documentacion previa (`notas.txt`) |

## Restricciones que NO se tocaron (plan §1.3)
Routing determinista, Agent Profiles, Policy Layer, rate limit por Tool, `require_confirmation`, separacion
`source=customer|admin`, JWT fuera de `Session.state`, filtro `Part.thought`, endpoints `/internal/ai/*` privados.

## Despliegue aplicado (2026-09-24, autorizado por el usuario)
`docker compose ... up -d --no-deps --force-recreate sintel_ai_adk` (sin rebuild de imagen). `sintel_prod_ai_adk` healthy,
`LOCAL_MODEL_CHAIN` verificado en el contenedor. Resto de contenedores sin reiniciar. Smoke del modelo en `sintel_prod_ollama`:
respuesta correcta en espanol; carga en frio 57 s, ~7 tok/s, 6.2 GB de los cuales 4.9 GB en VRAM (offload parcial a CPU) con el
Ollama de dev ocupando VRAM a la vez. NO se probo `/chat` real (requiere un JWT de cliente).

## Banco de pruebas en dev (16 casos sinteticos, 1 corrida, `scripts/ai_eval/chat_model_bench.py`)
| Modelo | tool% | args% | seguro% | espanol% | p50 s | max s | tok/s |
|---|---|---|---|---|---|---|---|
| llama3.1:8b | 62.5 | 100 | 93.8 | 100 | 1.0 | 1.5 | 49.2 |
| qwen3.5:9b | 93.8 | 100 | 87.5 | 100 | 27.1 | 67.2 | 7.8 |
Lectura: qwen3.5 acierta mucho mas la herramienta (llama llama herramientas en saludos/agradecimientos), pero su latencia es ~27x
peor en esta GPU de 8 GB (offload parcial + razonamiento). Muestra pequena; no es un veredicto (ver F10/F13 del plan).

## Pendiente / siguiente (todo requiere propuesta + aprobacion segun §0.3)
1. Registrar `OLLAMA_PRIMARY_MODEL_DIGEST` cuando termine `ollama pull qwen3.5:9b` en produccion.
2. Correr `chat_model_bench.py` (dev) sobre `qwen3.5:9b` vs `llama3.1:8b` antes de dar por bueno el primario.
3. F1: red `ai_private`; decidir si se cierran los puertos `0.0.0.0` del stack de desarrollo.
4. F2: token de servicio Django->ADK. F3: fallback multi-entry real + circuit breaker + presupuesto de turno completo.
5. F21: jerarquia de kill switches. F23/F24: matriz de seguridad y SLO tras tener baseline funcional (TTFT, p95).
6. Riesgo de VRAM: RTX 4060 (8 GB) compartida por Ollama dev, Ollama prod (`bge-m3` 1,2 GB + `qwen3.5:9b` ~6,6 GB) y
   LM Studio => contencion posible; medir en F13 antes de dar carga real.
