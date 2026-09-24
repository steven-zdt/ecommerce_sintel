# HARDENING — FASE 8 (seguridad de la salida)

**Estado: C1-C3 APROBADOS (2026-09-24; enlaces en monitor primero con `sintel.net.co`/`panel.sintel.net.co`/`wa.me`, reemplazo TOTAL de la respuesta ante fuga de infraestructura o prompt, tope de 3800 caracteres). IMPLEMENTADO EN DEV; NO se ejecutaron tests (regla del usuario); PRODUCCION SIN DESPLEGAR.** Ver "Resultado en DEV" al final.

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §12. Nada implementado. Toca lo que ve el cliente => `SECURITY_REVIEW_REQUIRED` + aprobacion humana (§0.3).
Regla vigente del usuario: los tests se ESCRIBEN pero NO se ejecutan sin su autorizacion; la verificacion es por inspeccion de codigo y pruebas de humo de UI.

## Recorrido real de la salida (inspeccion de codigo)
`run_sintel_turn` -> `public_response.extract_public_response()` (filtra `Part.thought` y `<think>...</think>`) -> `main.py::ChatResponse.response` -> `support/services/ai_bridge.py::_process_chat_response`
-> `support/consumers.py::_ai_reply` -> `ChatCommands.save_message` + WebSocket (widget web / panel de soporte) | `notifications/tasks.py` (WhatsApp).

## Estado por punto del plan §12
| Control | Estado |
|---|---|
| Razonamiento privado fuera de la respuesta (§12.1) | **OK**: `Part.thought` + regex `<think>...</think>` (`public_response.py`) |
| Render en la UI web (§12.2) | **OK por inspeccion**: `SupportChatWidget.vue` pinta `{{ msg.message }}` (interpolacion escapada) y no hay `v-html` en el widget ni en `CommunicationPanel/Center` ni en `SupportDashboardView`. No hay Markdown renderizado (los `**` se ven literales: cosmetico) |
| Argumentos de Tools (§12.3) | **OK tras F4** (validacion antes de ejecutar; sin `eval/exec/subprocess`) |
| Salida a WhatsApp / base de datos | Texto plano; **sin limite de largo ni saneo** en el camino ADK -> Django -> WhatsApp (WhatsApp admite ~4096 caracteres) |
| URLs en la respuesta (§12.2) | **Sin control**: el modelo puede emitir cualquier enlace (phishing) y WhatsApp lo convierte en enlace pulsable |
| Fuga de secretos / infraestructura | **Sin control**: nada revisa que la respuesta no contenga un JWT, el `AI_SERVICE_TOKEN`, hostnames internos (`sintel_ollama`, `host.docker.internal`), rutas (`/app/`, `/code/`), trazas de Python |
| Fuga del prompt de sistema | **Sin control** (F5 ya introdujo `PRECEDENCE_POLICY`, que el modelo podria repetir); solo mitigado por instruccion |
| Etiqueta `<think>` sin cerrar | **Gap**: la regex exige cierre; con el tope de tokens de F3 (`AI_*_MAX_OUTPUT_TOKENS`) una respuesta truncada dentro de un razonamiento en linea (proveedor tipo LM Studio) dejaria pasar el texto de razonamiento |
| Trazabilidad de lo redactado | No existe |

## Cambios propuestos (dev primero)

### C1 — `ai_engine_adk/output_guard.py` (riesgo bajo/medio)
`guard_public_response(text, *, surface)` aplicado a `final_text` justo despues de `extract_public_response` y antes de devolverlo:
1. **Razonamiento**: quita `<think>...</think>` y, ademas, desde un `<think>` SIN cerrar hasta el final y cualquier `</think>` suelto.
2. **Saneo Unicode** (`sanitize_text` de F5).
3. **Secretos** (siempre activo): JWT (`eyJ...\.....\....`), `Bearer <token>`, claves tipo `sk-...`/`api_key=...`, y el valor EXACTO de secretos configurados (`AI_SERVICE_TOKEN`, `JWT_SECRET_KEY`, contrasenas de BD/Redis si estan en el entorno del proceso; solo valores >= 16 caracteres) => `[dato oculto]` + `security_event=output_redacted category=...` (sin el valor).
4. **Infraestructura / prompt**: si aparecen hostnames internos, rutas del contenedor, `Traceback (most recent call last)` o frases distintivas del prompt de sistema (`Politica de precedencia (no negociable)`, el canario de configuracion) => se reemplaza TODA la respuesta por un mensaje seguro y se registra `security_event=output_blocked reason=infra_or_prompt_leak`.
5. **Enlaces** (superficie cliente): dominios permitidos `AI_OUTPUT_ALLOWED_LINK_HOSTS` (default `sintel.net.co`, `panel.sintel.net.co`, `wa.me`); el resto => `[enlace removido]`. `AI_OUTPUT_LINKS_ENFORCE=false` (default) = MONITOR (solo registra `output_link_flagged`), luego `true`.
6. **Largo**: tope `AI_OUTPUT_MAX_CHARS=3800` (deja margen bajo el limite de WhatsApp) con recorte en el ultimo limite de frase y registro `output_truncated`.
Devuelve `(texto, flags)`; `metrics.output_flags` lleva las categorias (sin contenido). La superficie admin solo aplica 1-4 y 6 (los admins si necesitan enlaces).

### C2 — Segunda capa en Django (riesgo bajo) — `support/services/ai_bridge.py`
Django es la frontera de persistencia/entrega: en `_process_chat_response` acotar `response` a `AI_OUTPUT_MAX_CHARS` y quitar caracteres de control antes de `ChatCommands.save_message`/WhatsApp (defensa en profundidad si el ADK cambia o se reemplaza). No repite el analisis de secretos (eso vive en el ADK).

### C3 — Frontend: prohibir `v-html` en el chat (riesgo bajo)
Regla ESLint `vue/no-v-html` para `components/customer/ui/SupportChatWidget.vue`, `components/customer/communication/**` y `modules/support/**` (hoy no hay ninguno: se fija para que no reaparezca). Sin cambio de comportamiento. (Requiere que el proyecto tenga ESLint con `eslint-plugin-vue`; si no, se documenta la regla en `frontend/CLAUDE.md`.)

### C4 — Fuera de alcance de esta fase
Veracidad de cifras/precios que vienen de Tools (misinformation, se cubre con F10 golden dataset) y render de Markdown en el widget (mejora de UX aparte).

## Tests (SE ESCRIBEN, NO SE EJECUTAN sin autorizacion)
`ai_engine_adk/tests/test_output_guard.py`: razonamiento (cerrado, sin cerrar, `</think>` suelto); JWT/Bearer/clave redactados; valor exacto de `AI_SERVICE_TOKEN` redactado; hostnames/rutas/traceback => bloqueo; frase del prompt => bloqueo;
enlace no permitido (monitor vs enforce); largo; texto legitimo intacto (URL de `sintel.net.co`, "aceptamos PSE", precios); `metrics.output_flags` sin contenido; superficie admin conserva enlaces.

## Riesgos / rollback
Falsos positivos del bloqueo (p. ej. un cliente que pregunta por "host") => el mensaje seguro sustituye la respuesta: por eso la lista de infraestructura es ESTRECHA (nombres reales de este stack, no palabras genericas). Rollback: `AI_OUTPUT_GUARD_ENABLED=false`
o imagen anterior. Los enlaces empiezan en monitor.

## Preguntas para aprobar
1. ¿Apruebas C1-C3 (dev primero)?
2. Enlaces: ¿monitor primero y luego enforce? ¿dominios permitidos: `sintel.net.co`, `panel.sintel.net.co`, `wa.me` (¿otros: redes sociales, Wompi)?
3. Bloqueo por fuga de infraestructura/prompt: ¿reemplazar TODA la respuesta por un mensaje seguro (recomendado) o solo redactar el fragmento?
4. Tope de `3800` caracteres: ¿de acuerdo?

## Resultado en DEV (2026-09-24)
Implementado (SIN ejecutar tests, regla del usuario; solo `py_compile`): `ai_engine_adk/output_guard.py` (razonamiento cerrado/sin cerrar/suelto, saneo Unicode, secretos JWT/Bearer/claves/`clave=valor`/valor exacto de secretos del entorno,
fuga de infraestructura o del prompt => se REEMPLAZA toda la respuesta por un mensaje seguro, enlaces con dominios permitidos en MONITOR, tope de 3800 caracteres), integrado en `sintel_root_workflow.run_sintel_turn` con `metrics.output_flags`
(superficie admin: sin control de enlaces); variables `AI_OUTPUT_GUARD_ENABLED`, `AI_OUTPUT_MAX_CHARS`, `AI_OUTPUT_LINKS_ENFORCE`, `AI_OUTPUT_ALLOWED_LINK_HOSTS` en `ai_engine/config.py`; segunda capa en Django
(`support/services/ai_bridge.py::_bound_response_text`: quita controles y acota el largo, `AI_OUTPUT_MAX_CHARS` en settings); regla "prohibido `v-html` en el chat" documentada en `frontend/CLAUDE.md` (el proyecto no tiene ESLint).
Tests ESCRITOS y NO ejecutados: `ai_engine_adk/tests/test_output_guard.py`. La imagen del ADK de dev NO se reconstruyo con F8: la guardia de salida no estaba activa durante las pruebas de humo.

### Pruebas de humo de UI (dev, Chrome headless, sesion inyectada; no son tests automatizados de regresion)
- F7 Mi cuenta -> Memoria del asistente: pagina, aviso de privacidad, 2 recuerdos con canal y caducidad, borrar uno con confirmacion en linea, "Olvidar todo", entrada en el menu: OK.
  **Bug real hallado y corregido**: `CustomerCard` trae `height: 100%` y `flex-direction: column`; la tarjeta ocupaba todo el alto y empujaba la lista debajo del footer (imposible de pulsar). Corregido con doble clase en `CustomerAssistantMemoryView.vue`.
- Home Builder (`?section=` persistente, recargar conserva la seccion, ocultar/mostrar vista previa) y Marketing (lista, "Nueva Campana"): OK.
- Chat de soporte con IA: el flujo real funciono (mensaje -> ADK -> Qwen3.5 -> respuesta persistida por WebSocket, 86 s, `RentalAgent`, 2 llamadas a Tools, `ai_tool_audit` de F4 visible en el log del ADK).
  Mis dos primeras lecturas de esta prueba fueron falsos positivos (tomaban mensajes antiguos del historial): se corrigio el criterio y la respuesta se verifico en la base de datos.
- Hallazgos NO causados por F2-F8: (1) las salas escaladas quedan `ai_paused` para siempre (varios usuarios de dev; explica que la IA no responda en esas salas, tambien en produccion) -> Fase 18; (2) la pregunta "cuanto dura la garantia de las camaras?"
  se enruto a `RentalAgent` (`renting_search`) en vez de conocimiento y la respuesta fue relleno ("voy a consultar...") -> calidad de routing/RAG (Fase 10, dataset dorado); (3) `/cart/` y `/cart/wishlist/` dan 403 al usuario de prueba;
  (4) las opciones del centro de comunicacion no son botones semanticos (accesibilidad).

## Pasos pendientes para PRODUCCION (no ejecutados)
Rebuild de `sintel_ai_adk` y despliegue de `django` (defaults activos, sin cambios en `.env.production`). Observar `security_event=output_blocked|output_redacted|output_link_flagged` y luego `AI_OUTPUT_LINKS_ENFORCE=true`.
Rollback: `AI_OUTPUT_GUARD_ENABLED=false` o imagen anterior.
