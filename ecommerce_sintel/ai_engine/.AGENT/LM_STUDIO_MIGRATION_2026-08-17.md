# LM STUDIO MIGRATION — 2026-08-17

> **[CORREGIDO, misma noche]** La primera versión de este documento certificaba el E2E
> y la matriz de concurrencia (sección 7) como si hubieran corrido contra LM Studio.
> **Eso era incorrecto**: existía una configuración dinámica preexistente en la tabla
> `ai_provider` (de una sesión anterior, "LM Studio Windows (prueba FASE 5)") que tiene
> precedencia sobre `LOCAL_MODEL_CHAIN` — y esa configuración dinámica apuntaba el canal
> `support_chat` a **Ollama** (`llama3.1:8b` @ `sintel_ollama:11434`, contenedor que
> nunca se bajó en dev), no a LM Studio. Confirmado con el log real:
> `[llm] /chat usando config dinamica (ai_provider) (2 motores)`. Todo el E2E y la
> matriz de concurrencia de la version anterior de este documento en realidad
> ejercitaron Ollama, no LM Studio. Corregido (ver sección 10) y vuelto a medir contra
> LM Studio genuino — los números reales son sustancialmente peores, ver sección 7.

> Migración del proveedor LLM productivo del AI Engine: **Ollama -> LM Studio Server**.
> Sin arquitectura híbrida (regla explícita del prompt maestro de esta auditoría) — el
> AI Editor y `project_knowledge_graph` no fueron tocados ni ampliados. Documento nuevo,
> no reemplaza el historial de `SUPPORT_AI_CERTIFICATION.md`/`CERTIFICACION_E2E_CHAT_IA_
> 2026-08-13.md` (esos quedan como registro histórico de cuando el motor corría con
> Ollama).

## 1. Qué es LM Studio en esta arquitectura

**Servicio externo local**, ejecutándose en el **Windows HOST**, NO un contenedor
Docker. `docker-compose.yml`/`docker-compose.prod.yml` no lo definen ni lo definirán —
es una dependencia de infraestructura del host, igual que Docker Desktop mismo.

```
CUSTOMER -> Support Chat -> Django/Channels -> ai_bridge -> AI Engine
    -> LM Studio Server (Windows HOST) -> qwen/qwen3.5-9b -> AI Engine
    -> Policy/Tools/RAG -> respuesta -> ai_bridge -> Support Chat -> CUSTOMER
```

## 2. Operación — cómo arrancar

1. Abrir LM Studio en Windows.
2. Cargar el modelo `qwen/qwen3.5-9b` (chat) — confirmar que quedó "loaded", no solo
   descargado.
3. Iniciar el **Local Server** de LM Studio (puerto 1234 por defecto).
4. Verificar: `curl http://localhost:1234/v1/models` desde una terminal del HOST — debe
   devolver una lista JSON con al menos `qwen/qwen3.5-9b` y
   `text-embedding-nomic-embed-text-v1.5`.
5. Si `sintel_ai` ya está corriendo, no hace falta reiniciarlo — `LOCAL_MODEL_CHAIN`
   apunta a la URL fija (`http://host.docker.internal:1234/v1`), no al proceso de LM
   Studio en sí; el cliente `ChatOpenAI` se conecta por request, no mantiene un socket
   persistente que dependa de que LM Studio ya estuviera arriba al construirse.

**Si LM Studio está apagado**: `sintel_ai` sigue arrancando sin problema (el cliente LLM
es lazy, no pinguea al construirse). Un `/chat` real fallará al intentar generar —
capturado por el `try/except` de `main.py`, el Customer recibe "nuestro asistente no
está disponible" en vez de un error crudo (verificado, ver sección 6).

## 3. Bind address y seguridad de red

**LM Studio escucha en `127.0.0.1:1234` (loopback), NO `0.0.0.0`** — confirmado con
`Get-NetTCPConnection -LocalPort 1234` en el host. Esto significa:

- **No es alcanzable desde la LAN ni desde Internet** — correcto, es exactamente lo que
  pide la Fase 17/33 del prompt maestro ("sin exposición pública").
- **Sí es alcanzable desde contenedores Docker** vía `host.docker.internal:1234` —
  Docker Desktop en Windows implementa un ruteo especial para ese hostname que llega al
  loopback del host aunque el servicio no esté bindeado a `0.0.0.0`. Verificado en vivo:
  `docker exec ecommerce_sintel_ai curl http://host.docker.internal:1234/v1/models` ->
  HTTP 200, mismo JSON que desde el host.
- **No requirió ningún cambio de firewall de Windows** — el mecanismo de Docker Desktop
  ya resuelve la conectividad sin ampliar la superficie de exposición del proceso de LM
  Studio.

## 4. Modelos reales (confirmados via `GET /v1/models`, no inventados)

| Model ID | Uso |
|---|---|
| `qwen/qwen3.5-9b` | Chat (`LOCAL_MODEL_CHAIN`) |
| `text-embedding-nomic-embed-text-v1.5` | Embeddings/RAG (`EMBEDDING_MODEL`) |
| `meta/muse-glimmer` | **No usado** — no es un modelo de chat/embeddings reconocible, se dejó fuera deliberadamente (regla del prompt: "no asumir que todos los modelos deben usarse") |

**Hallazgo real sobre `qwen/qwen3.5-9b`**: es un modelo "razonador" — emite un campo
`reasoning_content` con su cadena de pensamiento completa antes de la respuesta final en
`content`. Una prueba controlada ("Responde OK.") gastó **476 tokens de reasoning** para
producir 2 caracteres de respuesta real. Esto tiene impacto directo en:
- **Latencia por turno** más alta que un modelo no-razonador equivalente.
- **`max_tokens`** — antes la rama `openai-compatible` de `llm_factory.py::_build_model()`
  no tenía límite (a diferencia de `ollama-nativo`, que sí tenía `num_predict=1500`). Sin
  límite, un turno real podía generar de forma prácticamente ilimitada antes de que
  `request_timeout` cortara la conexión. Corregido: `max_tokens=2048`.

## 5. Variables de configuración (nombres, no valores)

Reutiliza el mecanismo YA existente (`LOCAL_MODEL_CHAIN`, `ai_engine/config.py`) — no se
crearon variables `AI_LLM_*` nuevas y duplicadas, per la regla explícita del prompt
maestro de "no duplicar si ya existe un equivalente".

| Variable | Rol | Valor real (dev) |
|---|---|---|
| `LOCAL_MODEL_CHAIN` | Cadena de motores LLM (chat), formato `nombre\|tipo\|base_url\|modelo` | `lmstudio\|openai-compatible\|http://host.docker.internal:1234/v1\|qwen/qwen3.5-9b` — una sola entrada, sin fallback a Ollama |
| `EMBEDDING_PROVIDER` | Cliente de embeddings a usar | `openai` (reutiliza `OpenAIEmbeddings`, ahora con `base_url` configurable — antes solo servía para la API real de OpenAI) |
| `EMBEDDING_MODEL` | Modelo de embeddings | `text-embedding-nomic-embed-text-v1.5` |
| `EMBEDDING_BASE_URL` | **Variable nueva** (única agregada) — URL del motor de embeddings cuando `EMBEDDING_PROVIDER != "ollama"` | `http://host.docker.internal:1234/v1` |
| `OLLAMA_BASE_URL` / `LLM_MODEL` | Legado, solo se usan si `LOCAL_MODEL_CHAIN` no está definida explícitamente | Sin efecto hoy — `LOCAL_MODEL_CHAIN` está definida |

## 6. Fallback / resiliencia

| Escenario | Resultado |
|---|---|
| LM Studio apagado | `/chat` captura la excepción, responde "asistente no disponible" (mensaje controlado, sin traceback ni URL interna) — mismo mecanismo ya certificado el 2026-08-13 contra Ollama, no se reescribió |
| **LM Studio lento** (encontrado en vivo, no simulado) | El nodo `node_generate_response` excede `LLM_TIMEOUT_SECONDS=90` con `qwen3.5-9b` en este hardware -> `openai.APITimeoutError` -> mismo fallback controlado que "apagado". Correcto en resultado, pero **~100s de espera real** para el cliente (ver sección 7) — el mecanismo de fallback no es el problema, la latencia real del modelo/hardware sí |
| ChromaDB apagado | Motor arranca igual (fix de esta misma auditoría, `main.py::lifespan`), RAG degradado sin crashear el proceso |
| Redis apagado | Cubierto genéricamente por el catch-all de `/chat` (gap cosmético ya documentado en `SUPPORT_AGENT_SPEC.md`, no introducido por este cambio) |

## 7. Latencia real (corregido — la matriz anterior era inválida)

**La matriz 1/2/4/8/12 de la primera versión de este documento en realidad corrió
contra Ollama** (ver corrección al inicio del documento), no LM Studio — se eliminó de
aquí para no dejar datos falsos.

**Datos reales contra LM Studio genuino** (config dinámica corregida, `kind` real
`openai-compatible`, sin fallback a Ollama, provider Ollama desactivado):

| Prueba | Resultado |
|---|---|
| Turno único, primer intento (con `max_retries` default del SDK de `openai`) | **288.7s**, terminó en fallback (`engine_unavailable: true`) — el SDK reintentó automáticamente 4 veces tras cada `APITimeoutError`, acumulando minutos en vez de fallar rápido |
| Turno único, tras fix `max_retries=0` en `llm_factory.py` | **100.7s**, terminó igual en fallback |

**Causa raíz confirmada con traceback real** (`ai_engine/main.py` logs): el nodo
`node_generate_response` del Action Graph (la llamada que genera la respuesta final
para el cliente, con el system prompt completo del Support Agent — mucho más largo que
un mensaje de prueba trivial) excede consistentemente `LLM_TIMEOUT_SECONDS=90` con
`qwen/qwen3.5-9b` en este hardware, lanzando `openai.APITimeoutError`. El mecanismo de
fallback de `main.py` funciona correctamente (nunca un 500 crudo, siempre el mensaje
controlado) — pero **~100 segundos de espera para el cliente es inaceptable para un
chat en vivo**, incluso después del fix.

**No se corrió una matriz de concurrencia real contra LM Studio** — con cada turno
individual ya tardando ~100s en el mejor caso reproducido, una matriz 1/2/4/8/12
completa (27 requests) tomaría un tiempo excesivo y probablemente mostraría
degradación severa, no la degradación lineal que se había reportado (incorrectamente)
contra Ollama.

**Esto es un hallazgo de viabilidad, no un bug de configuración.** Antes de considerar
esta integración lista para producción, hace falta una decisión real: modelo más
liviano/no-razonador, mejor aceleración de hardware para LM Studio, o aceptar timeouts
mucho más altos (con el costo de experiencia de usuario que eso implica en un chat en
vivo).

## 8. Qué NO cambió

- `ai_editor` — congelado, no tocado.
- `project_knowledge_graph` — mantenimiento, test AST de frontera sigue pasando.
- Tool Registry, Policy Layer, Human Handoff, WhatsApp gate, rate limiting Redis — sin
  cambios de código; sus tests (mockeados, no dependen del proveedor LLM real) siguen
  pasando sin modificación.

## 9. `docker-compose.prod.yml` — actualizado, no activado

El servicio `sintel_ai` (agregado en la auditoría de puesta en producción anterior)
ahora referencia LM Studio en su `environment:` (`LOCAL_MODEL_CHAIN`/`EMBEDDING_*`,
mismo criterio de la sección 5 — dev y producción corren en el mismo host Windows, asi
que `host.docker.internal:1234` aplica igual). Validado con
`docker compose config --quiet` (solo código de salida, sin volcar el env completo).
**No se levantó en el host real, `AI_SUPPORT_CHAT_ENABLED` sigue en `false` en
producción.**

## 10. Corrección de la configuración dinámica (`ai_provider`)

Se encontró y corrigió una configuración preexistente (de una sesión anterior,
"prueba FASE 5") que dejaba el canal `support_chat` apuntando a Ollama como proveedor
dinámico primario, con precedencia sobre `LOCAL_MODEL_CHAIN` — la arquitectura híbrida
que esta auditoría prohíbe explícitamente seguía existiendo en la práctica hasta este
punto. Corregido vía el ORM de Django (cambio de datos en desarrollo, no de código):

- `AIProvider` "LM Studio Windows": `kind` corregido de `ollama-nativo` a
  `openai-compatible` (protocolo real).
- Nuevo `AIModel` `qwen/qwen3.5-9b` creado bajo ese provider (antes no tenía ningún
  modelo registrado).
- `AIChannelConfig` del canal `support_chat`: `primary_model` apunta ahora al modelo
  real de LM Studio.
- `AIChannelFallback` hacia Ollama — eliminado.
- `AIProvider` "Ollama Docker (real)" — desactivado (`is_active=False`).

Verificado en logs tras el cambio: `[llm] /chat usando config dinamica (ai_provider)
(1 motores)` (antes decía "(2 motores)").

## 11. Logs de LM Studio

Viven en `C:\Users\Administrator\.lmstudio\apps\bionic\server-logs` en el HOST — **no se
copiaron al repositorio, no se montaron como volumen Docker**. Política: quedan fuera de
Git (ni siquiera se referencian por ruta absoluta en código versionado) y su
retención/rotación la maneja LM Studio mismo, no este proyecto.
