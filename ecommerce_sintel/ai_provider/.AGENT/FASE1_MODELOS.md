# FASE 1 -- Dominio AIProvider/AIModel/AIChannelConfig

**Fecha:** 2026-08-13. Plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES PARA
CHAT SUPPORT". Ver `ai_engine/.AGENT/CERTIFICACION_E2E_CHAT_IA_2026-08-13.md` para el
contexto que motivo este plan (certificacion E2E previa del chat) y FASE 0 (auditoria)
para el precedente arquitectonico (`core/` app) que este dominio sigue.

## Cambios

- Nueva app `ai_provider/` (registrada en `INSTALLED_APPS`, `ecommerce/settings/base.py`):
  - `models.py`: `AIProvider` (nombre, `kind` en {ollama-nativo, openai-compatible,
    anthropic} -- mismo vocabulario que `ai_engine/llm_factory.py::_build_model()`,
    `base_url`, `api_key` cifrada, `is_active`, `display_order`, campos de ultimo test
    de conexion), `AIModel` (FK a provider, `model_id`, `display_name`, `is_active`,
    `discovered_automatically`), `AIChannelConfig` (canal -> modelo primario, hoy solo
    `support_chat`), `AIChannelFallback` (cadena ordenada de fallback por canal).
  - `services/selectors.py`: `AIProviderSelector`, `AIChannelConfigSelector` (incluye
    `get_resolved_chain()` -- primary+fallbacks activos en orden, la forma que consumira
    el endpoint interno de AI Engine en FASE 2).
  - `services/commands.py`: `AIProviderCommands` (create/update/delete-soft/
    record_test_result -- update con `api_key=''` NO borra la key existente, para que el
    frontend nunca tenga que reenviar la key real), `AIModelCommands`,
    `AIChannelConfigCommands` (set_primary/set_fallback_chain).
  - `admin.py`: registrado en Django admin (gestion de emergencia si el panel dedicado
    de FASE 5 no esta disponible).
  - `tests.py`: 13 tests reales (incluye lectura SQL cruda de Postgres para confirmar
    que `api_key` NUNCA queda en texto plano en la columna).
- `shared/fields.py` (nuevo): `EncryptedTextField` -- Fernet vía `cryptography` (ya
  dependencia transitiva, ahora declarada explicita en `pyproject.toml`). No existia
  ningun mecanismo de cifrado en el repo (confirmado en FASE 0) -- se construyo desde
  cero, deliberadamente sin sumar `django-cryptography` como dependencia nueva.
- `ecommerce/settings/base.py`: `AI_PROVIDER_ENCRYPTION_KEY` (opcional, cae a derivar de
  `SECRET_KEY` si no esta configurada -- funciona en dev sin configuracion extra, se
  recomienda fijarla en produccion para poder rotarla independiente).

## Tests

`docker exec ecommerce_sintel_django python manage.py test ai_provider -v 2` -- **13/13
PASS** contra Postgres real (no sqlite, no mocks). Migraciones `0001_initial` y
`0002_alter_aiprovider_last_test_ok` (fix real: `BooleanField(null=True)` sin
`blank=True` hacia que `full_clean()` lo tratara como obligatorio -- encontrado por los
tests, no por inspeccion).

## Validacion en vivo

`docker restart ecommerce_sintel_django` -- arranco limpio, `GET /api/v1/health/` ->
`{"status": "ok", "db": true, "redis": true, "celery": true}`. `ai_provider` no rompe
nada existente (app completamente nueva, unico riesgo era el registro en
`INSTALLED_APPS`, confirmado sin errores).

## Decisiones tomadas

1. **Cifrado:** `cryptography`/Fernet directo en vez de `django-cryptography` -- ya
   presente como dependencia transitiva, evita sumar una dependencia nueva y rebuild de
   imagen para esta fase.
2. **Fallback ordenado:** modelo `AIChannelFallback` explicito (con `order`) en vez de
   un M2M implicito -- refleja 1:1 el concepto de `LOCAL_MODEL_CHAIN` (primario + cadena
   ordenada), sera la fuente que FASE 4 use para reconstruir el equivalente de
   `primary.with_fallbacks(fallbacks)`.
3. **`api_key=''` en un update = no cambiar** -- decision necesaria para que el
   frontend (FASE 5) pueda mostrar un campo de key enmascarado sin tener que reenviar
   el valor real cifrado/descifrado en cada guardado.

## Limitaciones conocidas (no implementado aun, fases siguientes)

- AI Engine **no** lee esta configuracion todavia -- sigue usando `LOCAL_MODEL_CHAIN`
  exclusivamente (FASE 2 agrega el endpoint interno, FASE 4 conecta `ai_engine` a el).
- No hay API REST expuesta para este dominio todavia (FASE 3, dashboard admin).
- No hay UI (FASE 5).
- `docker-compose.prod.yml` no define `sintel_ai`/`sintel_ollama` (confirmado en FASE 0)
  -- esta fase no cambia eso, sigue siendo una limitacion de la topologia de produccion
  actual, no de este dominio.

## Siguiente fase

FASE 2 -- Internal API: `GET /api/v1/internal/ai/provider-config/` (solo lectura,
mismo patron/aislamiento de red que `api/v1/internal/ai/core/*` ya existente) para que
`ai_engine` pueda resolver la cadena primary+fallback sin importar Django ORM ni tocar
Postgres directo.
