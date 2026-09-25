# HARDENING F21 - Kill switches (2026-09-25)

Estado: VALIDATION_REQUIRED (codigo escrito y compilado; tests escritos, NO ejecutados por instruccion del usuario).

## Jerarquia
| Variable | Donde se lee | Efecto al ponerla en `false` |
|---|---|---|
| `AI_GLOBAL_ENABLED` | Django (`is_ai_mode_active`, vista del Admin AI Assistant) y ADK (`/chat`) | Apaga TODA la IA: chat de soporte y asistente admin. El ADK responde con handoff sin tocar modelo ni tools |
| `AI_SUPPORT_CHAT_ENABLED` | Django (ya existia) | Apaga solo el chat al cliente |
| `ADMIN_AI_ASSISTANT_ENABLED` | Django (ya existia) | Apaga solo el asistente admin |
| `AI_MODEL_CHAIN_ENABLED` | ADK `/chat` | No se invoca ningun modelo: respuesta segura + handoff |
| `AI_TOOLS_ENABLED` | ADK `kill_switch_tools_before` | Niega toda Tool (503) |
| `AI_WRITE_TOOLS_ENABLED` | ADK idem | Niega Tools nivel >= 1 y las sin clasificar (fail-closed) |
| `AI_EXTERNAL_ACTIONS_ENABLED` | ADK idem | Niega Tools nivel >= 3 |

Todos default `true` (comportamiento anterior). Se leen en cada llamada, sin cache; el cambio requiere recrear el contenedor
(`docker compose ... up -d --force-recreate <servicio>`), no un `restart`.

## Reglas
- La denegacion es codigo determinista y se evalua primero en `before_tool_callback`; el modelo no participa.
- Denegaciones auditadas: `security_event=ai_kill_switch_tool_denied` y `ai_kill_switch_turn_denied` (sin contenido).
- Cambiar un flag: en `.env` y `.env.production` en el mismo cambio. Django y ADK tienen cada uno su `AI_GLOBAL_ENABLED`: ponerlo en ambos.
- Sin migraciones ni cambios de compose (las variables llegan por `env_file`).

## Archivos
`ai_engine/config.py`, `ecommerce/settings/base.py`, `support/services/ai_bridge.py`, `dashboard/api/ai_assistant_views.py`,
`ai_engine_adk/main.py`, `sintel_adapter.py`, `sintel_root_workflow.py`, `tests/test_kill_switches.py`.

## Verificacion manual sugerida (la corre el usuario, en dev)
1. `AI_TOOLS_ENABLED=false` + recrear `ecommerce_sintel_ai_adk`: pedir estado de un pedido en el chat -> respuesta degradada, log `ai_kill_switch_tool_denied`.
2. `AI_GLOBAL_ENABLED=false` en ADK: mensaje de chat -> respuesta de handoff.
3. Opcional: `pytest ai_engine_adk/tests/test_kill_switches.py` en el contenedor ADK.
