# HARDENING — FASE 1 (aislamiento del model runtime): PROPUESTA (estado: APPROVAL_REQUIRED)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §5. Nada de esto esta aplicado.
Toca red/Docker de produccion => requiere aprobacion humana explicita (§0.3, LOOP-08).

## ChangeIntent
Que ningun componente de inferencia (Ollama, ADK, AI Gateway) ni servicio de datos (Postgres, Redis) sea alcanzable desde
fuera de su red Docker o de loopback, y que el runtime de modelos viva en un segmento privado propio.

## Evidencia de partida (F0)
- Prod: ningun `sintel_prod_*` publica puertos (nginx 80/443 internos). Ollama prod: solo `11434/tcp` interno. OK.
- Dev (`docker-compose.yml`) publica en TODAS las interfaces: `db 5432`, `redis 6380`, `django 8000`, `frontend 5173`,
  `sintel_ai 8100`, `sintel_ai_adk 8101` (`netstat` los mostraba en `0.0.0.0`/`[::]`). Ollama dev ya esta en `127.0.0.1:11434`.
- Host con IPs de LAN (`192.168.2.15`, `192.168.2.197`). Firewall de Windows activo en los 3 perfiles, pero NO se verifico si
  hay reglas de entrada para esos puertos => exposicion en LAN NO confirmada ni descartada.
- Quien habla con Ollama en prod: `sintel_ai_adk` (chat) **y Django** (embeddings de `ai_knowledge` via `AIProvider`,
  `embedding_service._embed_via_ollama`). Esto contradice el diagrama del plan (§5.3: "ai_private con solo ADK y ollama").

## Cambios propuestos (minimos, en este orden)

### C1 — DEV: bind a loopback (riesgo bajo, solo desarrollo)
En `docker-compose.yml` cambiar `"6380:6379"`, `"5432:5432"`, `"8000:8000"`, `"5173:5173"`, `"8100:8100"`, `"8101:8101"` por
`"127.0.0.1:<host>:<container>"` (mismo patron que ya usa Ollama dev). Efecto: siguen accesibles desde el propio host (debug,
navegador, psql) pero no desde la LAN. Si algun consumidor externo legitimo usa esos puertos (p. ej. otra maquina de la red),
se rompe: confirmar antes.
Verificacion: `netstat -ano | findstr LISTENING` => solo `127.0.0.1:*`; el frontend dev sigue abriendo en `localhost:5173`.
Rollback: revertir el commit del compose y `docker compose up -d`.

### C2 — PROD: red `ai_private` (riesgo medio, requiere recrear contenedores)
Crear la red `ai_private` (bridge, `internal: true` no aplica porque ADK necesita salida a LM Studio del host como fallback;
sin `internal`) y conectar:
- `sintel_ollama`: SOLO `ai_private` (sale de `sintel-network`).
- `sintel_ai_adk`: `sintel-network` (Django, Redis, Postgres) + `ai_private` (Ollama).
- `django`: ademas `ai_private`, porque hace embeddings contra Ollama. Alternativa mas estricta: que Django no toque Ollama y los
  embeddings pasen por el ADK (cambio de codigo, fuera de esta fase) — no recomendado ahora.
- `celery_worker`: solo si embebe chunks (`EmbeddingCommands.embed_pending_chunks` corre en Celery?) — verificar antes; si si, tambien `ai_private`.
Beneficio real: Redis/Postgres/nginx/cloudflared dejan de estar en el mismo segmento que el runtime de inferencia.
Riesgo: si se olvida algun consumidor de Ollama, el chat/embeddings fallan con "connection refused" hasta corregirlo.
Verificacion: `docker network inspect`, `docker exec` NO en prod => usar contenedor temporal en cada red; healthchecks; test de
embedding y de chat (no `/chat` real: requiere JWT de cliente).
Rollback: volver a poner `sintel-network` en `sintel_ollama` y recrear ese servicio y los que cambiaron.

### C3 — Health separado (F1 §5.4, riesgo bajo, cambio de codigo en ADK)
Hoy solo existe `GET /health` en `ai_engine_adk/main.py`. Anadir `/liveness`, `/readiness` (DB+Redis) y `/model-health`
(sin detalles sensibles: `{"status","model":"configured","provider":"configured"}`) y apuntar el `healthcheck` de compose a
`/readiness`. Requiere rebuild de `sintel_ai_adk`. Se propone como PR aparte (F1b).

## No incluido a proposito
- No se cambia LM Studio (host): documentar su bind (`127.0.0.1` o interfaz privada) es una accion manual en su aplicacion.
- No se cierran puertos 80/443 de nginx (los usa el tunel de Cloudflare dentro de la red Docker).

## Preguntas para aprobar
1. C1: ¿hay algo fuera de este host que use 5432/6380/8000/5173/8100/8101 de desarrollo?
2. C2: ¿aprobado crear `ai_private` recreando `sintel_ollama`, `sintel_ai_adk` y `django` (segundos de corte del chat/embeddings)?
3. ¿Confirmas ventana de mantenimiento o lo hago fuera de horas de tienda?
4. C3: ¿lo hago en un PR aparte?
