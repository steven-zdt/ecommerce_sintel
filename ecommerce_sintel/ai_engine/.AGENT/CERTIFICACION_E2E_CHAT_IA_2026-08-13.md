# CERTIFICACION E2E DEL CHAT IA -- 2026-08-13

> A diferencia de `SUPPORT_AI_CERTIFICATION.md` (certificacion de codigo/componentes del
> AI Engine en aislamiento, 2026-08-08), este documento certifica que los componentes
> **estan realmente conectados y funcionando simultaneamente contra el stack vivo**
> (`docker compose up`, sin mocks) en el orden exacto solicitado: infraestructura -> AI
> Engine -> ai_bridge -> gate de modo IA -> WebSocket -> primer mensaje -> respuesta IA ->
> frontend -> multi-turno -> Tool -> Human Handoff -> caida del motor -> refresh JWT ->
> resiliencia de Docker. Cada fila tiene evidencia real (logs, respuestas HTTP/WS reales,
> registros de base de datos, o interaccion real en navegador) -- ninguna es una
> afirmacion sin verificar. Alcance respetado: sin rediseñar `support`, sin conectar Vue
> directamente al AI Engine, sin reconstruir el AI Engine -- solo certificacion.

## Hallazgo critico inicial (PASO 1)

El stack de desarrollo completo (`ecommerce_sintel_*`) estaba **caido 19 horas** al
iniciar esta certificacion -- `django`, `sintel_ai`, `redis`, `db`, `chromadb`, `ollama`,
`celery_worker/beat` en `Exited (0)` (cierre limpio, consistente con un reinicio del
host/Docker Desktop) y `frontend` especificamente en `Exited (137)` (SIGKILL). Se
recupero con `docker compose up -d` (todo salvo `nginx`, bloqueado por el puerto 80 del
host -- fuera del alcance de esta certificacion, `nginx` no participa del flujo de chat en
dev). Este hallazgo es precisamente el escenario que motivo el PASO 1 del usuario: un
stack muerto produce la apariencia de "chatbot roto" sin que el codigo tenga ningun bug.

## Matriz de certificacion (23 capas)

| # | Capa | Resultado | Evidencia real |
|---|------|-----------|-----------------|
| 1 | Frontend Vite (dev server) | **PASS** (arranque) / **FAIL** (resiliencia, ver PASO 14) | `VITE v8.0.9 ready in 218-437ms` tras `docker start` manual |
| 2 | `SupportChatWidget.vue` | **PASS** | Conexion real en navegador, historial de 11+ mensajes renderizado, envio/recepcion en vivo (DOM inspeccionado via JS) |
| 3 | JWT (Django, general) | **PASS** | `AccessToken.for_user()` real, login de cliente real (`/auth/login/`), refresh real via interceptor Axios |
| 4 | WebSocket -- ruta exacta | **PASS** | Unicamente `ws/support/chat/` (`support/routing.py:5`), conectado con `?token=` real, sin variantes |
| 5 | Django Channels | **PASS** | `SupportChatConsumer` real via `channels.testing.WebsocketCommunicator` contra la app real (Redis channel layer real, no mock) |
| 6 | ChatRoom (creacion/reuso) | **PASS** | `get_or_create_room` reutilizo la sala OPEN existente en reconexiones; UUIDs reales verificados en Postgres |
| 7 | `is_ai_mode_active(room)` (4 condiciones) | **PASS** | Caso positivo (`ai_paused=False` -> IA responde) Y caso negativo (`ai_paused=True` -> IA NO responde, esperado 15s) ambos verificados en vivo |
| 8 | `ai_bridge.ask_ai()` | **PASS** | Roundtrip real Django -> `sintel_ai:8100`, logs `[AI_BRIDGE] request/response` reales, `AI_ENGINE_URL=http://sintel_ai:8100` confirmado en `settings` |
| 9 | AI Engine `POST /chat` | **PASS** | HTTP 200 real, schema completo (`conversation_id, intent, tool_calls, tool_results, response, metrics`) |
| 10 | JWT en AI Engine (`auth.py`) | **PASS** | `decode_django_jwt()` acepto tokens reales firmados por Django (misma `JWT_SECRET_KEY`) en cada llamada exitosa |
| 11 | Action Graph (enrutamiento) | **PASS** | Enruto correctamente a `OrderAgent` (order_status) y `SupportAgent` (unknown/soporte) segun el mensaje real |
| 12 | Agent (`SupportAgent`/`OrderAgent`) | **PASS, con nota de calidad** | Ver "Hallazgo de comportamiento" abajo -- `SupportAgent` abrio un ticket real ante un saludo generico |
| 13 | LLM (Ollama `llama3.1:8b` via Action Graph) | **PASS** | 0 alucinaciones en consultas de datos reales (respondio honestamente "no tengo pedidos" para un usuario sin ordenes reales) |
| 14 | Redis Checkpoint (estado conversacional) | **PASS** | Turno 2 ("¿y cuando llega?") se entendio en el contexto del turno 1 (pedido) bajo el mismo `conversation_id` |
| 15 | Tool Registry (`OrderStatusTool`, `OpenSupportTicketTool`) | **PASS** | Ambas tools (lectura y escritura) ejecutadas realmente, resultados reales devueltos |
| 16 | Generacion de respuesta | **PASS** | Coherente y correctamente fundamentada en datos reales devueltos por la Tool |
| 17 | `ChatMessage` del bot | **PASS** | `sender=asistente.ia@sintel.internal` persistido real en Postgres, `ai_metrics` guardado correctamente |
| 18 | WebSocket -- `group_send` dual (`chat_{uuid}` + `support_admins`) | **PARCIAL** | Confirmado por codigo + entrega real al lado cliente; entrega al lado `support_admins` NO observada con una segunda sesion admin real conectada simultaneamente (queda como brecha residual, no confirmada ni refutada) |
| 19 | Render Vue (burbujas, sender, hora) | **PASS** | Inspeccion real del DOM en navegador: `.chat-bubble`, `bubble-user`/`bubble-admin`, contenido exacto |
| 20 | Multi-turno | **PASS** | 2 turnos reales bajo el mismo `conversation_id`, contexto retenido |
| 21 | Human Handoff (`OpenSupportTicketTool` -> `ai_paused=True`) | **PASS** | `ai_paused` se seteo real en Postgres; IA verificadamente dejo de responder (15s de espera, ningun frame adicional) |
| 22 | Fallback (caida del AI Engine) | **PASS** | `docker stop ecommerce_sintel_ai` real -> mensaje exacto "Un agente humano revisara tu mensaje pronto" + `ai_metrics.engine_unavailable=true` persistido, confirmado en backend Y en la UI real del navegador |
| 23 | Refresh JWT en sesion activa | **PASS** | Access token expirado real (firmado, `exp` en el pasado) inyectado en `localStorage` -> interceptor detecto 401 -> refresh automatico exitoso (4/4, sin colision de la race condition ya corregida) -> widget reconecto solo, sesion y 11 mensajes de historial preservados, sin logout |

## Hallazgo de comportamiento (PASO 2, no bloqueante)

Ante el mensaje "Hola, necesito ayuda" (sin contexto de pedido/alquiler), `SupportAgent`
invoco `OpenSupportTicketTool` automaticamente -- sin pedir confirmacion -- y la respuesta
generada menciono "tu pedido de alquiler", un dato que el usuario nunca proporciono. **No
es un bug del mecanismo**: `OpenSupportTicketTool` tiene `requires_confirmation=False` por
diseño explicito (`support_tools.py:27`, "no destructivo -- pero se avisa que atendera un
humano"), y el campo `tool_calls[].pending_confirmation=true` es metadata informativa, no
un gate real -- confirmado leyendo `action_graph.py:496-502`. El hallazgo real es de
calidad del prompt/agente: abre tickets con facilidad y puede fabricar contexto menor
ante mensajes ambiguos. No bloquea la certificacion (el mecanismo de escritura, gate y
persistencia funcionaron correctamente) pero es candidato a ajuste de prompt aparte.

## Hallazgo critico (PASO 14) -- `restart: unless-stopped` no se activo en un crash real

El `docker-compose.yml` declara `restart: unless-stopped` en `frontend` desde 2026-08-10
(fix documentado en el propio compose, en respuesta al incidente real de
`project_frontend_container_crash_no_restart.md`), y `docker inspect` confirma que la
politica esta correctamente grabada en el contenedor real (`RestartPolicy.Name:
unless-stopped`). Sin embargo, al simular un crash real (`docker kill
ecommerce_sintel_frontend`, exit code 137 -- el mismo codigo que aparecio originalmente
tras 19h caido), **Docker NO reinicio el contenedor automaticamente** (`State.Restarting:
false`, `Status: exited`, verificado durante mas de 2 minutos de espera). Se requirio
`docker start` manual para recuperarlo. Esto reproduce exactamente el modo de falla que
el fix de 2026-08-10 debia prevenir -- la politica esta bien declarada pero no se
comporta como se espera en este host (Docker Desktop sobre Windows Server 2022). No se
investigo la causa raiz especifica (podria ser una particularidad del backend WSL2/Hyper-V
de Docker Desktop en este host) ni se modifico nada -- por alcance, esta certificacion es
de observacion, no de rediseño.

## Estado final

**APTA con 2 hallazgos abiertos, ninguno bloqueante para uso normal:**

1. **PASO 18 (parcial)**: entrega real al canal `support_admins` no verificada con una
   segunda sesion admin conectada en simultaneo -- recomendacion: repetir con 2 sesiones
   WS reales (cliente + admin) antes de dar por cerrado ese eslabon especifico.
2. **PASO 14 (fallo real, no de codigo)**: la resiliencia ante un crash real del
   contenedor `frontend` depende hoy de que alguien reinicie manualmente, pese a la
   politica `restart: unless-stopped` declarada -- recomendacion: verificar si es un
   problema del Docker Desktop de este host especifico (reinicio del daemon, o probar
   `docker-compose.yml` version/`stop_grace_period`) antes de asumir que el fix de
   2026-08-10 esta resuelto en produccion real.

Todos los demas eslabones de la cadena (22 de 23 filas de la matriz) fueron verificados
end-to-end con evidencia real, sin mocks, contra el stack vivo completo.
