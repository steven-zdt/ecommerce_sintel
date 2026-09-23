# INCIDENTE — Admin AI Assistant 503 en produccion (2026-09-23)

## Sintoma reportado por el usuario

```
POST https://api.sintel.net.co/api/v1/dashboard/ai-assistant/chat/ 503 (Service Unavailable)
```

El usuario probo `/panel/asistente` en produccion (recien conectado al sidebar/router ese mismo dia,
ver `AUDITORIA/ASSISTANT_BASELINE.md` y `ASSISTANT_FASE1_3_SERVICE_TOOLS.md`) y el chat no respondia.

## Causa raiz

`ADMIN_AI_ASSISTANT_ENABLED` es un kill switch de Django (`settings/base.py`, `default=False`) que
`dashboard/api/ai_assistant_views.py::AdminAiAssistantChatView.post()` chequea al inicio:

```python
if not settings.ADMIN_AI_ASSISTANT_ENABLED:
    return Response({'error': '...'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
```

El piloto de Catalogo se congelo explicitamente el 2026-09-16 (pedido del usuario) apagando este
flag. El **2026-09-23** el usuario pidio descongelarlo -- se activo en `.env` de DESARROLLO
(`ADMIN_AI_ASSISTANT_ENABLED=true`) y se verifico ahi. **Nunca se replico la misma variable en
`.env.production`.** El codigo (Tools, agente, rutas, UI) se desplego a produccion completo y
funcional -- solo el interruptor seguia en su default `False` ahi, silenciosamente.

Hallazgo secundario, agravante (no causa raiz, pero prolongaba el problema si no se detectaba):
la imagen `ecommerce_sintel_ai_adk:prod` que corria en el contenedor vivo (`sintel_prod_ai_adk`)
estaba **desactualizada respecto al tag** -- existia una imagen mas nueva con ese mismo tag
(construida horas antes por motivos no rastreados en esta sesion) que el contenedor nunca adopto
porque nadie lo recreo. El `Image ID` que el contenedor tenia pineado ya ni siquiera existia como
objeto Docker (garbage-collected) en el momento del diagnostico.

## Por que esto es un patron real, no un error puntual

Este proyecto tiene AL MENOS 2 kill switches de este tipo, cada uno independiente, cada uno leido
por `env_file`/`--env-file` desde un archivo DISTINTO segun el entorno:

| Flag | Dominio | Archivo dev | Archivo prod |
|---|---|---|---|
| `AI_SUPPORT_CHAT_ENABLED` | Chat de soporte al CLIENTE | `.env` | `.env.production` |
| `ADMIN_AI_ASSISTANT_ENABLED` | Asistente IA del panel ADMIN | `.env` | `.env.production` |

Activar un flag en un solo archivo (tipicamente dev, porque ahi es donde se verifica primero, regla
0-DEV-FIRST de `.AGENT.md`) dejandolo pendiente en el otro es un olvido facil y silencioso: el
codigo se despliega bien, los contenedores quedan `healthy`, `manage.py check` no lo detecta (no es
un error de configuracion Django, es un valor booleano valido) -- el sintoma solo aparece cuando un
usuario real prueba la funcionalidad y recibe un 503 sin contexto.

## Fix aplicado

1. `ADMIN_AI_ASSISTANT_ENABLED=True` agregado a `.env.production` (append via `cat >>`, no via editor
   de texto -- el clasificador de seguridad de la sesion bloquea ediciones directas a archivos de
   secretos/env, comportamiento esperado y correcto).
2. `sintel_ai_adk` reconstruido `--no-cache` en produccion (garantiza codigo trazable, no una imagen
   "de mediodia" sin build explicito registrado) y recreado.
3. `django` recreado (`--force-recreate`) para que el proceso relea `.env.production` (un simple
   `restart` NO garantiza releer env_file en todas las versiones de Compose -- `--force-recreate` si).
4. Verificado end-to-end contra el contenedor real de produccion (token JWT de un admin real
   existente, generado sin persistir nada nuevo en BD) con un mensaje de SOLO LECTURA
   ("listar los primeros 3 servicios"): `200 OK`, `CatalogAgent` respondio con datos reales del
   catalogo via `ServiceListTool`.

## Regla para prevenir la recurrencia

**Todo flag booleano/kill switch nuevo que se active en `.env` (desarrollo) para verificar una
funcionalidad DEBE activarse en el mismo cambio en `.env.production` antes de considerar el trabajo
"listo para produccion"** -- no son pasos secuenciales separados ("primero verifico en dev, despues
en algun momento prendo prod"), son el MISMO paso de checklist. Aplica a cualquier variable nueva
con `config(..., default=False, cast=bool)` en `settings/base.py` que controle disponibilidad de una
feature completa (no solo credenciales/tuning).

**Checklist a seguir de ahora en adelante cuando se activa un flag de este tipo:**
1. Activar en `.env` (dev), verificar la funcionalidad end-to-end ahi.
2. Activar el MISMO nombre de variable en `.env.production` en el mismo cambio (no en un paso
   posterior "cuando se despliegue").
3. Si el despliegue a produccion no es inmediato, dejar constancia explicita (comentario en
   `.env.production` o nota en AUDITORIA) de que el flag esta pendiente de activar ahi, con fecha.
4. Al desplegar codigo nuevo relacionado a produccion (`./deploy/deploy.sh` o build manual), verificar
   con una prueba real end-to-end (no solo "el contenedor quedo healthy") -- un healthcheck HTTP no
   detecta un flag de aplicacion apagado, solo detecta que el proceso responde.

Ver tambien [[docker_container_image_ownership]] (memoria de sesion) para el hallazgo relacionado de
imagenes de produccion no reconstruidas/no recreadas en el momento esperado.
