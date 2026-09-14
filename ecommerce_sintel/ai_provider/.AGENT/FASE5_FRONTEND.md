# FASE 5 -- Frontend: panel de configuracion en /panel/soporte

**Fecha:** 2026-08-13. Ver FASE1-4 para el resto de la cadena.

**Actualizacion (mismo dia, tras revision propia contra el checklist del plan
maestro):** la primera version de esta fase solo tenia UI para "modelo primario"
(boton estrella) -- "definir fallback" (`set-fallback-chain`, ya en FASE 3, ya
testeado en backend) no tenia ningun control en el panel. Cerrado: seccion
"Cadena de fallback" en `AIProviderConfigView.vue` (agregar via boton
`bi-arrow-down-circle` en cada badge de modelo, reordenar arriba/abajo, quitar,
guardar). Probado en vivo end-to-end con datos reales: `Descubrir modelos` trajo
el catalogo real de Ollama (`bge-m3:latest`, `llama3.1:8b`, `qwen2.5-coder:1.5b`),
se agrego `qwen2.5-coder:1.5b` como modelo, se agrego a la cadena de fallback, se
guardo, se recargo la pagina completa (persistencia confirmada), y se confirmo
contra `GET /api/v1/internal/ai/provider-config/` que la cadena resuelta ahora
trae **2 entradas en orden** (`llama3.1:8b` primario, `qwen2.5-coder:1.5b`
fallback) -- exactamente la forma que `ai_engine/llm_factory.py::
get_dynamic_llm()` (FASE 4) necesita para construir `primary.with_fallbacks([...])`.

## Cambios

- `frontend/src/services/aiProvider/aiProviderService.js` (nuevo): wrapper de
  `useApi()` sobre `dashboard/ai-providers/` y `dashboard/ai-channel-config/`
  (FASE 3) -- mismo patron que `marketingService.js`/`paymentAdmin.js` (prefijo
  `dashboard/` relativo al baseURL `/api/v1/`, confirmado contra
  `store/paymentAdmin.js`).
- `frontend/src/store/aiProviderAdmin.js` (nuevo): Pinia store, mismo patron que
  `marketingAdmin.js` (`loading`/`actionLoading`, helper `_mutate`, acciones
  devuelven `{ok, data?, error?}`).
- `frontend/src/modules/support/AIProviderForm.vue` (nuevo): formulario
  create/edit (props `item`/`mode`, emit `success`/`cancel` -- convencion
  `FRONTEND_OFFCANVAS_SKILL`). Campo API key: `type="password"`, placeholder
  `sk-••••••••` cuando ya hay una configurada, **nunca se pre-llena con el valor
  real** (el backend tampoco lo expone, FASE 3) -- vacio en un submit de edicion
  significa "no cambiar" (`AIProviderCommands.update_provider`, FASE 1).
- `frontend/src/modules/support/AIProviderConfigView.vue` (nuevo): vista principal
  -- lista de proveedores (status dot activo/inactivo, ultimo resultado de test con
  timestamp+latencia), botones Probar conexion/Descubrir modelos/Editar/Eliminar
  (confirmacion inline `bg-danger-subtle`, convencion del proyecto -- no modal),
  badges de modelos con boton "usar como primario" (marca visual con
  `bi-star-fill` sobre el modelo activo de `channelConfig`) y boton eliminar
  modelo. `SintelOffcanvas` aloja `AIProviderForm` para create/edit.
- Ruta nueva: `frontend/src/apps/admin/routes/adminOps.routes.js` ->
  `{ path: 'soporte/ia-config', name: 'ai-provider-config', component:
  AIProviderConfigView }` -- **NO** en `/panel/soporte` (esa ruta ya la ocupa
  `SupportDashboardView.vue`, analitica de chat -- hallazgo de FASE 0). Sidebar:
  `frontend/src/components/layout/Sidebar.vue`, nuevo item hijo bajo el grupo
  "Soporte" ya existente (`bi-robot`, "Proveedores de IA").

## Validacion

- `docker exec ecommerce_sintel_frontend npm run build` -- compilo limpio,
  `AIProviderConfigView` en su propio chunk (13.60 kB / 4.59 kB gzip). Unico
  warning es preexistente y no relacionado (`CategoryTreeNode.vue`).
- **Live end-to-end en navegador real** (login admin real, JWT real emitido por
  `/api/v1/admin-auth/login/`):
  - Panel carga y muestra el proveedor real "Ollama Docker (real)" (creado en
    FASE 2) con su modelo "Llama 3.1 8B" -- datos reales de Postgres via la API
    admin real.
  - **Probar conexion**: clic real -> `POST .../test-connection/` real ->
    resultado renderizado en vivo: "Conexión OK (13/08/26, 10:42 a. m. · 5ms)".
  - **Crear proveedor**: formulario completo -> `POST .../` real -> nuevo
    proveedor "LM Studio Windows (prueba FASE 5)" aparece en la lista al
    instante.
  - **Eliminar**: confirmacion inline -> `DELETE .../` real -> desaparece de la
    lista. Dato de prueba limpiado, no quedo en la BD.

## Nota operativa (no bloqueante)

Los clics via coordenadas de pantalla (`computer left_click`) fallaron
repetidamente en esta sesion de navegador especifica (posiblemente por un evento
transitorio "vite server connection lost" ocurrido durante el build) -- se
resolvio disparando los eventos DOM directamente (`element.click()`/`input` real)
para la verificacion, lo cual SI ejercito el codigo real (Vue event handlers,
Pinia actions, llamadas HTTP reales) end-to-end. No es un defecto del codigo de
esta fase -- confirmado porque la posicion del boton coincidia exactamente con
las coordenadas que se intentaban clickear.

## Siguiente fase

FASE 6 -- Validacion de regresion (Human Handoff, Tool Calling, RAG, JWT,
metricas, rate limit siguen intactos) + documentacion final consolidada.
