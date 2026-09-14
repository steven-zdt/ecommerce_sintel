# Plan de Separación Física — Support Agent vs AI Engineering

> Bloque 11 (Fase 17-18) del `PLAN_DE_EJECUCION_SUPPORT_AGENT`. Este documento es una
> **propuesta de diseño, no una ejecución**. El plan general ordena este bloque
> deliberadamente al final, después de la certificación (Bloque 10).
>
> **[Actualización 2026-08-08]** La certificación del Bloque 10 ya se corrió en runtime:
> 56/56 tests unitarios pasan dentro del contenedor `sintel_ai`, y `/chat` fue probado en
> vivo (login real, `order_status` y `knowledge` intents, ambos con respuesta correcta) —
> ver `SUPPORT_AGENT_SPEC.md` seccion 13ter. El bloqueo que motivaba no ejecutar este
> plan ya no aplica; sigue siendo, de todas formas, una decisión de infraestructura que
> el usuario debe autorizar explícitamente antes de tocar `Dockerfile`/
> `docker-compose.yml`/`main.py`.

---

## 1. Hallazgo clave que simplifica todo lo demás

**El código de generación (`/generate`, `/validate`, `/plan`, `/impact`, `/breakage`) no
tiene ningún consumidor en producción.** Verificado por grep exhaustivo:

- `nginx-common.conf` no expone `sintel_ai` a Internet en absoluto — ni `/chat` ni
  `/generate` son rutas públicas. `sintel_ai` solo es alcanzable dentro de la red Docker
  interna.
- El único código Django que llama a `sintel_ai` es
  `support/services/ai_bridge.py::ask_ai()`, contra `settings.AI_ENGINE_URL` (default
  `http://sintel_ai:8100`), y **solo** golpea `/chat`.
- Ningún otro archivo `.py` del proyecto (fuera de `ai_engine/` mismo) referencia
  `/generate`, `/validate`, `/plan`, `/impact` o `/breakage`.

Conclusión: `/generate` y compañía son **herramientas de desarrollo** (invocadas a mano
por un desarrollador o un agente de IA tipo Claude Code durante el desarrollo, nunca por
el sistema en producción), no una dependencia de runtime del e-commerce. Esto baja
mucho el riesgo de separar: no hay que coordinar un cutover de tráfico de producción,
solo dejar de compartir el mismo proceso/imagen.

## 2. Qué es realmente compartido hoy (recordatorio de `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md`)

```text
Proceso:      main.py (un solo FastAPI, un CMD, un puerto 8100)
Imagen:       Dockerfile (COPY . . hornea TODO junto)
Dependencias: requirements.txt (mismo set para ambos, aunque casi no se solapan en uso real)
Datos:        misma coleccion ChromaDB (retrievers.py / bootstrap.py -- ya resuelto en
              Bloque 4 a nivel de query, sigue compartido a nivel de ingesta, por diseno)
Infra:        embeddings_factory.py, vectorstore_factory.py, llm_factory.py, config.py
```

Todo lo demás (`action_graph.py`, `agents/`, `capabilities/`, `tools/`, `gateway/`,
`auth.py`, `observability.py`, `redis_checkpointer.py` del lado Support;
`chains.py`, `chains_frontend.py`, `graph.py`, `guardrails*.py`, `planner.py`,
`auditor.py`, `project_map.py`, `knowledge_graph.py`, `dependency_graph.py` y la familia
Graphify del lado Engineering) **ya no se importa entre sí** — confirmado por grep de
imports en el Bloque 2. La separación de código ya está hecha; falta la separación de
*despliegue*.

## 3. Opciones consideradas

| Opción | Descripción | Esfuerzo | Riesgo |
|---|---|---|---|
| **A. Dos entrypoints, mismo repo/imagen** | `main_support.py` (monta solo `/chat`+gateway+`/health`) y `main_engineering.py` (todo lo demás), como dos `CMD` distintos sobre la misma imagen Docker ya construida. Un segundo servicio en `docker-compose.yml` (`sintel_ai_support`) apuntando al mismo build context, distinto `command:`. | Bajo | Bajo — no toca imports ya separados, no reingesta, no cambia `AI_ENGINE_URL` (sigue siendo el servicio de soporte) |
| **B. Dos imágenes Docker, mismo repo** | Dos `Dockerfile` (`Dockerfile.support`, `Dockerfile.engineering`) con distinto `requirements.txt` recortado (Support no necesita `auditor.py`'s dependencias de análisis estático de más peso, aunque hoy casi todo el `requirements.txt` es compartido igual por RAG/LLM). | Medio | Bajo-medio — build pipeline duplicado, pero rollback trivial (son solo Dockerfiles) |
| **C. Dos repos separados** | `ai_engine` (Support, deployable de producción) sale a su propio repo; el motor de generación de código queda en éste o se archiva aparte. | Alto | Alto — reescribe historia de imports relativos, CI, y rompe el flujo actual donde un solo `docker compose build sintel_ai` sirve para ambos durante desarrollo |

## 4. Recomendación

**Opción A**, y solo cuando el Bloque 10 esté runtime-verificado. Razones:

1. El hallazgo de la seccion 1 elimina la urgencia — no hay tráfico de producción que
   proteger de un incidente en el motor de generación de código, así que el argumento de
   "blast radius" que motiva Fase 17 es real pero no urgente.
2. La separación de imports ya está hecha (Bloque 2); lo único mecánico que falta es
   partir `main.py` en dos archivos de endpoints y dos entradas de `docker-compose.yml`
   — no hay que tocar `action_graph.py`, `tools/`, `agents/`, etc.
3. Mantiene un solo `requirements.txt`/imagen mientras el proyecto es pequeño; la Opción
   B/C se vuelven razonables más adelante si el motor de generación de código crece o se
   quiere versionar independientemente.

## 5. Lo que NO se hizo en esta sesión

No se movió ni un archivo, no se tocó `main.py`, `Dockerfile` ni `docker-compose.yml`.
Este documento es la preparación para cuando el usuario decida ejecutar Fase 17 — que,
según el orden del plan general, corresponde **después** de correr y confirmar la suite
de tests del Bloque 10 dentro del contenedor `sintel_ai`.
