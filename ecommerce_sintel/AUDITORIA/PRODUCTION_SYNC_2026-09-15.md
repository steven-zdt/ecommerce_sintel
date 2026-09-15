# PRODUCTION_SYNC_2026-09-15 — Sincronización de producción + diagnóstico real de chat mudo

Registro operativo del despliegue a producción del estado del proyecto hasta el commit
`6b38e0c` (cierre de la misión RAG Enterprise, ver `AUDITORIA/RAG_V2_FINAL_CERTIFICATION.md`),
y de la investigación real que siguió cuando el usuario reportó "el chat de soporte no contesta"
en ambos entornos, dev y producción, inmediatamente después del deploy.

---

## 1. Estado encontrado antes de sincronizar

Verificación real de las imágenes en ejecución en producción (no asumida):

| Imagen | Build real | Gap frente al código actual |
|---|---|---|
| `ecommerce_sintel:prod-runtime` (django) | 2026-08-31 | 16 días — previo a `ai_knowledge` (pgvector), `SupportTicket`, rotación de secreto SMS, fixes de nginx/vite, y toda la misión RAG |
| `ecommerce_sintel_ai_adk:prod` | 2026-09-14 21:50 | Previo a toda la misión RAG Enterprise (hybrid retrieval, reranking, grounding, métricas reales) |
| `ecommerce_sintel_ai:prod` (OLD, LangGraph) | 2026-08-31 | Contenedor detenido (rollback-only), sin tráfico real (`AI_ENGINE_URL` apunta a ADK) |

## 2. Pasos ejecutados (orden real)

1. **Backup completo pre-deploy** (`./deploy/backup.sh`) — DB + media + config, integridad
   verificada. Snapshot `20260915_150413`.
2. **`./deploy/deploy.sh`** — reconstruyó `django` sin caché, migraciones aplicadas (incluye
   `ai_knowledge.0001_initial` y `support.0010_supportticket`, verificado con
   `showmigrations`), health-gate en verde, superusuario ya existente (sin duplicar).
3. **Hallazgo durante el deploy**: `deploy.sh` no reconstruye `sintel_ai_adk` — ver detalle y
   causa en `.AGENT.md` sección "0-C" (corregida el mismo día). Compensado manualmente:
   `build --no-cache sintel_ai_adk` + `up -d --no-deps sintel_ai_adk`, health-gate verificado.
4. `sintel_ai` (runtime OLD) se recreó sin querer como efecto secundario de `deploy.sh` (`up
   -d` recrea todo el stack) — confirmado sin tráfico real, detenido de vuelta a su estado
   documentado (rollback-only), con confirmación explícita del usuario antes de la acción.
5. `./deploy/healthcheck.sh` — todos los contenedores sanos, `GET /api/v1/health/` interno OK.
6. Verificación externa real (no interna): `curl` contra `https://sintel.net.co/` desde fuera
   del host — `200 OK`, bundle JS/CSS del panel (`admin-*.js/css`) `200`, `/panel/login` `200`,
   headers CSP/HSTS normales, `Server: cloudflare`.

## 3. "El chat no contesta" — diagnóstico real, 2 causas independientes

Reportado por el usuario justo después del sync, en dev y producción simultáneamente. Se
investigó de punta a punta en vez de asumir una regresión del deploy — resultó ser 2 problemas
reales, ninguno introducido por el código de esta sesión:

### 3.1 `ChatRoom.ai_paused=True` sin ningún camino de vuelta (bug de producto preexistente,
ya documentado en `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` pero nunca confirmado
con impacto real hasta hoy)

Cuando el AI Engine escala una conversación a un humano (`abrir_ticket_soporte`), `support/
consumers.py::_save_ai_message_and_maybe_pause` pone `room.ai_paused = True`. **No existe
ningún endpoint ni control de panel para revertirlo** — la única forma real hoy es
`manage.py shell`. Confirmado con evidencia real:

- **Dev**: la sala de prueba del usuario (`f6450250-...`) tenía `ai_paused=True` desde
  **2026-08-08** — ni un solo mensaje en más de un mes tuvo respuesta de IA.
- **Producción**: la sala de `ceo@sintel.net.co` quedó con `ai_paused=True` durante las
  pruebas de esta misma sesión.

Fix aplicado: `ai_paused=False` manual en ambas salas, verificado con un turno real
end-to-end en cada entorno.

**Gap que sigue abierto** (decisión de producto, no ejecutada): construir un control real
"Reanudar IA" en `/panel/soporte`.

### 3.2 Contenedor de IA de desarrollo con código desactualizado (gotcha operacional, no un
bug de código)

El contenedor **de larga duración** `ecommerce_sintel_ai_adk` (el que atiende el chat real en
dev) llevaba corriendo desde las 10:36 del día, sin recrearse tras reconstruir su imagen a las
14:29 durante la corrida de la suite completa de tests de la misión RAG. `docker compose build`
reconstruye la imagen pero **no recrea un contenedor ya corriendo** — hace falta `docker
compose up -d <servicio>` después. Confirmado con evidencia directa: un turno de prueba real
contra ese contenedor devolvió `metrics: None` (código previo a FASE 11); tras `docker compose
up -d --no-deps sintel_ai_adk`, el mismo turno devolvió métricas reales completas.

Mismo patrón de fondo que el hallazgo de `deploy.sh` (sección 2.3) y que el gotcha ya
documentado en memoria (`project_pytest_not_installed_gotcha` / regla "build antes de run")
— pero esta vez afectando al contenedor **persistente** que sirve tráfico real, no solo a
corridas efímeras de test.

## 4. Verificación final post-fix (ambos entornos, turno real end-to-end)

```
dev:  agent=OrderAgent intent=order_status tool_calls=1 needs_confirmation=False
      metrics={agent, intent, handoff, tool_calls, needs_confirmation, retrieval_used,
               knowledge_state, grounding_result, duration_ms} -- todos presentes
prod: mismo resultado, mismo shape de metrics, respuesta coherente
```

## 5. Lecciones para la próxima sincronización

1. `deploy.sh` necesita actualizarse para reconstruir también `sintel_ai_adk` (y evaluar si
   `sintel_ai` debe seguir con `build:` en el compose de producción si nunca se despliega) —
   pendiente, decisión de si vale la pena tocar el script o dejarlo manual y documentado.
2. Después de cualquier `docker compose build` de un servicio con contenedor de larga duración
   ya corriendo (dev o prod), **recrear explícitamente con `up -d --no-deps <servicio>`** — un
   build exitoso no implica que el tráfico real esté usando el código nuevo.
3. Antes de certificar "el chat no responde" como bug de código, verificar primero
   `ChatRoom.ai_paused`/`assigned_admin`/`status` de la sala real en cuestión — es la causa más
   común y no requiere ningún cambio de código para confirmarla o descartarla.
