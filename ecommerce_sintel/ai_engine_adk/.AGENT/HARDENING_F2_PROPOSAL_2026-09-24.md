# HARDENING — FASE 2 (autenticacion servicio-a-servicio Django -> ADK)

**Estado: DISEÑO APROBADO (2026-09-24). IMPLEMENTADO Y VERIFICADO EN DEV; PRODUCCION SIN DESPLEGAR** (ver "Resultado en DEV" al final).

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §6. Nada esta aplicado ni programado.
Toca autenticacion => `SECURITY_REVIEW_REQUIRED` + aprobacion humana (§0.3, §26.2).

## Evidencia (codigo real)
- `ai_engine_adk/main.py:65` `/chat` depende de `get_validated_token` (`ai_engine/auth.py:102`): exige `Authorization: Bearer <JWT>` y valida
  firma/expiracion HS256 con `JWT_SECRET_KEY` compartida; despues resuelve identidad llamando a `/internal/ai-context/` de Django.
- Django firma ese JWT el mismo (`AccessToken.for_user(user)`) en `support/services/ai_bridge.py:ask_ai` y `ask_ai_async`; ademas
  `notifications/tasks.py` (WhatsApp) reusa `ask_ai`. Es decir: el JWT prueba QUIEN es el usuario, NO QUIEN llama al ADK.
- No existe ningun secreto de servicio (`grep AI_INTERNAL|INTERNAL_TOKEN|X-Internal` solo halla el token del gateway de WhatsApp).
- El ADK no se publica al host en prod y nginx no lo enruta; la unica barrera de red hoy es la red Docker (plan §2, P0).
- Otros endpoints del ADK: solo `GET /health` (sin auth, correcto para healthcheck).

## Amenaza que cierra
Cualquier proceso con alcance de red al puerto 8101 (otro contenedor comprometido, o el puerto de DEV publicado en LAN) que posea
un JWT valido de un usuario (p. ej. su propio token de cliente o uno robado) puede invocar `/chat` directamente, saltandose el
rate limit por sala y el estado de sala (`ai_paused`) de Django, y consumir LLM/herramientas sin pasar por `ai_bridge`.

## Diseno propuesto
1. Secreto `AI_SERVICE_TOKEN` (>= 32 bytes aleatorios, `secrets.token_urlsafe(48)`) en `.env.production` **y** en `.env` (dev) en el
   MISMO paso (regla aprendida del incidente 503 del 2026-09-23). Nunca en frontend, prompts, memoria ni logs.
2. ADK: nueva dependencia `require_service_token` en `ai_engine/auth.py` (o `ai_engine_adk/`): compara `X-AI-Service-Token` con
   `hmac.compare_digest`; 401 uniforme sin revelar cual parte fallo; aplicada a `/chat` (y a todo endpoint futuro salvo `/health`).
   Acepta tambien `AI_SERVICE_TOKEN_PREVIOUS` (rotacion sin corte).
3. Django: `ai_bridge.ask_ai`/`ask_ai_async` agregan el header `X-AI-Service-Token` desde `settings.AI_SERVICE_TOKEN`.
4. Modo de despliegue progresivo con flag `AI_SERVICE_TOKEN_REQUIRED` (default `false`): con `false` el ADK **loguea una advertencia**
   si falta/no coincide el token pero deja pasar; con `true` responde 401. Orden de rollout:
   a) desplegar ADK con el flag en false; b) desplegar Django enviando el header; c) verificar en logs que no hay advertencias;
   d) poner `AI_SERVICE_TOKEN_REQUIRED=true` (y recrear ADK); e) verificar que una llamada sin header devuelve 401.
5. Observabilidad: contador/log `security_event=ai_service_token_rejected` (sin valores del token, con origen).
6. Tests: `ai_engine_adk/tests/`: sin header => 401; header incorrecto => 401; correcto => pasa; `PREVIOUS` valido pasa;
   `/health` sigue sin auth; comparacion en tiempo constante; el token no aparece en logs.
7. F2b (aparte): direccion inversa ADK -> Django `/internal/ai/*` hoy usa JWT + cabeceras de host; evaluar el mismo secreto.

## Riesgos
- Olvidar actualizar `.env.production` o recrear `django`/`sintel_ai_adk` => con `REQUIRED=true` el chat cae (401 -> el widget muestra
  "asistente no disponible"). Mitigado por el rollout en 5 pasos y por la regla de replicar env en el mismo cambio.
- Requiere rebuild de `sintel_ai_adk` y de la imagen `django` (codigo en ambos). Se hace con `deploy.sh` mas el rebuild manual de
  `sintel_ai_adk` (deploy.sh no lo reconstruye).
- Rollback: `AI_SERVICE_TOKEN_REQUIRED=false` (y recrear ADK); si hiciera falta, revertir el commit.

## Preguntas para aprobar
1. ¿Apruebas el diseno (header + flag progresivo + rotacion con `PREVIOUS`)?
2. ¿Genero yo el secreto y lo escribo en `.env`/`.env.production`, o prefieres generarlo tu? (No lo mostrare en el chat.)
3. ¿Ejecuto primero todo en DEV (codigo + tests) y solo entonces preparo el despliegue?

## Resultado en DEV (2026-09-24)
Implementado segun el diseno: `ai_engine/config.py` (3 variables), `ai_engine/auth.py::require_service_token`, `ai_engine_adk/main.py`
(dependencia de `/chat`), `ecommerce/settings/base.py::AI_SERVICE_TOKEN`, `support/services/ai_bridge.py::build_ai_headers`
(usado por `ask_ai`, `ask_ai_async` y por el Admin AI Assistant, `dashboard/api/ai_assistant_views.py`).
Hallazgo durante la implementacion: el Admin AI Assistant es un SEGUNDO llamador de `/chat`; sin cubrirlo, activar el modo
obligatorio lo habria roto (misma clase de incidente que el 503 del 2026-09-23).
Tests: `ai_engine_adk/tests/test_service_token.py` (9) y `support/test_ai_service_token.py` (5), todos en verde. Regresion: suite del
ADK (sin `rag_evaluation` ni `test_persistent_session`) da 31 fallos con y sin los cambios (dependen del LLM de dev; preexistentes) y
55 -> 64 aprobados (+9 nuevos).
E2E real en contenedores de dev (ADK reconstruido, Django recreado con el secreto):
- REQUIRED=false: sin header y con header incorrecto => llegan al JWT (401 "Token invalido") y el ADK loguea
  `security_event=ai_service_token_missing_or_invalid mode=monitor`; con header correcto no hay advertencia.
- REQUIRED=true (contenedor ADK de prueba): sin header e incorrecto => 401 "Servicio no autorizado." + `ai_service_token_rejected`;
  correcto => pasa a la capa JWT; `/health` sigue 200 sin auth.
No verificado: un turno real de chat autenticado con JWT de cliente (dev), ni las suites completas de `support`/`dashboard` (requieren BD).

## Pasos pendientes para PRODUCCION (no ejecutados)
1. Generar el secreto y escribirlo en `.env.production` (`AI_SERVICE_TOKEN`, `AI_SERVICE_TOKEN_REQUIRED=false`) en el MISMO paso.
2. Rebuild de `sintel_ai_adk` (`build --no-cache` + `up -d --no-deps`) y `./deploy/deploy.sh` para `django` (Django lleva el cambio de codigo).
3. Comprobar en logs de prod que no hay `ai_service_token_missing_or_invalid`; luego `AI_SERVICE_TOKEN_REQUIRED=true` y recrear `sintel_ai_adk`.
4. Verificar 401 sin header. Rollback: `AI_SERVICE_TOKEN_REQUIRED=false`.
