# SECURITY_MODEL — modelo de seguridad del asistente (ADK)

> Documento vivo (HARDENING F19, 2026-09-24). Es parte del contrato arquitectónico: un cambio que toque una capa de abajo debe actualizar este archivo en el mismo cambio. Detalle de cada decisión: `HARDENING_F*_PROPOSAL_*.md` en esta carpeta. Estado de despliegue: ver `PRODUCTION_RUNBOOK.md` §5.

## 1. Principio rector
**La política sobrevive al input adversarial.** Ni el mensaje del cliente, ni un documento RAG, ni un recuerdo, ni la salida de una tool pueden dar permisos, cambiar el rol o saltar una confirmación. La autorización la decide la aplicación (Django + adaptador de tools), nunca el LLM ni el texto. La *detección* de inyección es solo monitor; la defensa es **estructural**.

## 2. Modelo de confianza (de mayor a menor)
1. Instrucciones de sistema de la app (perfil del agente + `PRECEDENCE_POLICY` de `input_guard.py`).
2. Política de la aplicación y de las tools (niveles, permisos, confirmación).
3. Petición del usuario. 4. Datos recuperados (RAG, memoria). 5. Contenido externo / salidas de tools.
Los niveles 3–5 son **datos no confiables**: se sanean y se enmarcan en una cerca con nonce (`<<<DATOS_NO_CONFIABLES ... id=nonce>>>`); los delimitadores dentro del contenido se neutralizan.

## 3. Capas de defensa (entrada -> salida)
| Capa | Qué hace | Dónde | Modo / flag (default) |
|---|---|---|---|
| Frontera de servicio (F2) | `X-AI-Service-Token` entre Django y ADK; rotación con `*_PREVIOUS` | `ai_engine/auth.py`, `ai_bridge.build_ai_headers` | monitor (`AI_SERVICE_TOKEN_REQUIRED=false`) |
| Identidad | JWT del usuario real; falla cerrado (401) si Django no resuelve el perfil | `auth.py`, `main.py` | siempre |
| Admisión (F13) | concurrencia y cola acotadas; rechazo con handoff | `admission.py` | apagado (`AI_MAX_CONCURRENT_TURNS=0`) |
| Presupuesto de turno (F3) | `max_llm_calls`, timeout total, 2 intentos de modelo | `sintel_root_workflow.py`, `model_runtime.py` | `AI_TURN_MAX_SECONDS=120`, `AI_TURN_MAX_LLM_CALLS=6` |
| Entrada (F5) | saneo Unicode, cerca de datos no confiables, detección (8 categorías), recorte de historial | `input_guard.py` | saneo/cerca activos; detección monitor |
| Routing | determinista; `source=admin` nunca cae en agente de cliente | `resolve_turn_agent` | siempre |
| Tools (F4) | niveles 0–3, permisos, confirmación forzada, rate limit, idempotencia, validación de args, auditoría | `sintel_adapter.py`, `tools/classification.py` | ver `TOOL_SECURITY.md` |
| RAG (F6) | ingesta con revisión humana, cuarentena, vigencia, `access-aware` | `ai_knowledge/` | ver `RAG_SECURITY.md` |
| Memoria (F7) | barrera server-side, TTL, auditoría, olvido, solo del cliente | `customer_memory/`, `should_extract_memory` | `AI_MEMORY_GATE_STRICT` |
| Salida (F8) | razonamiento fuera, secretos redactados, fuga de infra/prompt -> respuesta segura, enlaces (monitor), tope de longitud | `output_guard.py`, `ai_bridge._bound_response_text` | guardia activa; enlaces monitor |
| Observabilidad (F9) | `request_id` extremo a extremo, redacción global de logs, `SecurityEvent` de señales de IA | `observability_logging.py`, `ai_bridge.record_ai_security_events` | siempre |
| Handoff (F18) | un humano que responde pausa la IA; reactivación solo explícita; aviso a admins en degradación | `support/consumers.py`, `ChatCommands` | activo |

## 4. Superficies y controles clave
- **Prompt injection directa/indirecta**: cerca + precedencia + tools gated. Cobertura medida en `EVALUATION_BASELINE.md` (F11: 2444 casos de política).
- **Escalada de tools / suplantación admin**: `IsAdminUser` en toda escritura del agente admin; escrituras nivel >= 2 exigen confirmación humana; ninguna tool de borrado ni nivel 4.
- **Fuga de secretos/infra/prompt**: `output_guard` (bloquea la respuesta completa) + `RedactionFilter` en logs + gestión de secretos (F15).
- **Consumo no acotado**: topes de turno, tools, historial, salida, resultado de tool, admisión.
- **Aislamiento**: idempotencia por sesión+usuario+tool+args; memoria solo del propio cliente; canal solo atribuye memoria.
- **Datos de clientes**: sin contenido de mensajes en logs/métricas; memoria con TTL y derecho al olvido.

## 5. Monitor vs enforce (interruptores)
Se enciende primero en monitor y se activa con datos: `AI_TOOL_STRICT_ARGS`, `AI_RAG_QUARANTINE_FLAGGED`, `AI_OUTPUT_LINKS_ENFORCE`, `AI_TOOL_RESULT_ENFORCE`, `AI_SERVICE_TOKEN_REQUIRED`, `AI_TOOL_IDEMPOTENCY_FAIL_CLOSED`. Regla: **toda bandera nueva se replica en `.env` y `.env.production` en el mismo cambio** (incidente del 503 de 2026-09-23).

## 6. Riesgos residuales conocidos
- Detección no cubre base64/rot13/hex/homoglifos ni inglés en algunos patrones (`system_prompt_extraction` EN, `system:` a mitad de línea); la estructura los contiene (F11).
- Guardia de salida distingue mayúsculas en hosts/rutas (`SINTEL_OLLAMA`).
- Rate limits, idempotencia (por defecto) y breaker son fail-open sin Redis.
- Confirmaciones pendientes en memoria del proceso (`_PENDING_CONFIRMATIONS`): se pierden al reiniciar el ADK.
- Sin disparadores deterministas de handoff (solo el LLM abre tickets).
- Memoria entre usuarios y RAG con BD real solo se prueban en `env=django`/en vivo.
- Backups en el mismo host (cifrados con `openssl` si existe la clave); sin copia externa.
