# INCIDENT_RESPONSE — respuesta a incidentes del asistente (v1, F19; se amplía en F20)

> Documento vivo (HARDENING F19, 2026-09-24). Regla del proyecto: **nunca `docker exec` ni comandos ad-hoc sobre `sintel_prod_*`** salvo scripts sancionados (`deploy/*.sh`); los pasos de producción los ejecuta el usuario. Sin secretos en este documento.

## 1. Severidad
| Nivel | Criterio | Objetivo de reacción |
|---|---|---|
| SEV1 | Fuga confirmada de secretos/datos de clientes, acción no autorizada ejecutada, asistente respondiendo lo que no debe a todos | contener de inmediato (kill switch), luego investigar |
| SEV2 | Asistente caído o degradado para todos (motor, GPU, Redis, BD); inyección exitosa sin efecto | restaurar servicio / handoff humano |
| SEV3 | Degradación parcial, un agente/tool fallando, latencia alta | corregir en horario |

## 2. Dónde mirar (evidencia)
- **Logs con `request_id`** (`rid=` o JSON con `LOG_FORMAT=json`): Django y ADK comparten el id (F9). Streams: `SECURITY` (`security_event=`), `AI_OPERATION` (`ai_operation_event=`, `ai_tool_audit`, `memory_event=`), `PERFORMANCE` (`ai_turn_metrics`).
- **BD**: `security.SecurityEvent` (`AI_SECURITY_FLAG`: salidas bloqueadas/secretos redactados/inyección, con `request_id` y `engine_track`); `ChatMessage.ai_metrics`.
- **Comandos** (los corre el usuario): `manage.py ai_observability_report --days 1`, `manage.py ai_canary_report --hours 24`.
- Auditoría de tools: líneas `ai_tool_audit` (sin argumentos ni contenido).

## 3. Interruptores de contención (de menor a mayor impacto)
1. `AI_CANARY_ENGINE_URL=` (vacía): todo el tráfico al ADK estable.
2. `AI_OUTPUT_LINKS_ENFORCE=true` / `AI_RAG_QUARANTINE_FLAGGED=true` / `AI_TOOL_STRICT_ARGS=true`: endurecer sin desplegar (ver `SECURITY_MODEL.md` §5).
3. `AI_MAX_CONCURRENT_TURNS=N`: limitar la carga si hay sobrecarga.
4. `AI_SUPPORT_CHAT_ENABLED=false` (Django): apaga la IA del chat; los mensajes llegan a humanos.
5. Pausar IA en una sala concreta: responder como admin (pausa automática, F18); reactivar con `POST /api/v1/support/chats/<uuid>/resume-ai/`.
6. `./deploy/release_ai.sh rollback adk|django|all` (vuelve a la imagen anterior; ver `PRODUCTION_RUNBOOK.md`).
Cada cambio de variable: en `.env` **y** `.env.production` en el mismo cambio.

## 4. Playbooks
**A. Asistente no responde / degradado (SEV2)** — Síntoma: mensajes «asistente no disponible», `engine_unavailable`. 1) Logs ADK: `provider_failed`, `breaker_opened`, `turn_timeout`, `turn_rejected`. 2) Ollama caído -> reinicio del contenedor (usuario); breaker cae a LM Studio (¿abierto? es la misma GPU). 3) Sobrecarga -> admisión (`turn_rejected`) y F13. 4) Redis/Postgres -> ver F14 (fail-open salvo idempotencia opcional). 5) Los admins reciben «[Asistente no disponible]» (F18): atender a mano.
**B. Sospecha de prompt injection / suplantación (SEV2->SEV1 si hubo efecto)** — 1) Buscar `security_event=prompt_injection_suspected` y `SecurityEvent` por `request_id`. 2) Verificar auditoría de tools: ¿escritura ejecutada? (`ai_tool_audit status=ok` nivel >= 1) y confirmación. 3) Si hubo efecto: revertir el dato en Django (los servicios son la autoridad) y elevar a SEV1. 4) Contener: `AI_TOOL_STRICT_ARGS=true`, cuarentena RAG, y añadir el ataque a `eval/redteam.py` (regresión).
**C. Fuga de secretos / infraestructura en una respuesta (SEV1)** — 1) `output_blocked`/`output_redacted` en logs: la guardia debió bloquear; si algo salió, el secreto está comprometido. 2) **Rotar** según el runbook de `HARDENING_F15_SECRETS_AUDIT_2026-09-24.md` §3. 3) Revisar logs/backups por el mismo valor (el escáner `scripts/security/scan_secrets.py`). 4) Añadir el patrón a `output_guard.py` + `tests/security`.
**D. Fuga de memoria/datos entre clientes (SEV1)** — 1) Desactivar extracción: `AI_MEMORY_GATE_STRICT` + apagar IA del chat si es necesario. 2) `memory_event=` para trazar; `forget_customer_memory`/`purge_expired_memories`. 3) Notificar según la política de privacidad vigente.
**E. Documento RAG envenenado** — 1) `rag_chunk_quarantined`; localizar el documento (`AIKnowledgeDocument`), `rollback_to_version`, pasar a `needs_review`/interno. 2) Revisar quién lo ingresó (`source`, versiones).
**F. Despliegue defectuoso** — `deploy/release_ai.sh rollback`, o vaciar `AI_CANARY_ENGINE_URL` si es del canary; restaurar banderas desde `flags_<ts>.env`; migraciones aplicadas NO se revierten con la imagen (`restore.sh` solo si hace falta).

## 5. Después del incidente
Línea de tiempo con `request_id`; causa raíz; caso nuevo en el golden dataset / red team; actualizar este documento y `SECURITY_MODEL.md`; si hubo secretos, verificar la invalidación de los antiguos.

## 6. Pendiente (F20)
Contactos y escalamiento (quién/cuándo), plantillas de comunicación a clientes, retención de evidencias, simulacro trimestral y métricas de tiempo de contención.
