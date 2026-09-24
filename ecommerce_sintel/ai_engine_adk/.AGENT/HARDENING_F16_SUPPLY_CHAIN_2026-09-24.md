# HARDENING — FASE 16 (modelo / versionado / supply chain, P1): AUDITORIA + HERRAMIENTAS (estado: LISTO PARA QUE EL USUARIO ESCANEE)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §20. Regla firme del usuario: **el asistente no ejecuta tests, escaneos ni benchmarks**. Las lecturas hechas aqui fueron de solo metadatos (`git`, `docker image inspect`/`history`, `pip freeze` de la imagen de DEV, `ollama list`). **SBOM y escaneos de vulnerabilidades NO se ejecutaron**: se entregan los scripts para que los corras tu.

## 1. Estado real de los pines (evidencia de lectura)
| Elemento §20 | Hoy | Veredicto |
|---|---|---|
| Ollama (servidor) | **prod**: `ollama/ollama:0.30.10` (tag fijo). **dev**: `ollama/ollama:latest` (flotante; el contenedor dev hoy reporta 0.30.10 por casualidad) | dev deriva de prod -> **corregido** (dev fijado a `0.30.10`, mismo pin que prod) |
| Tag del modelo | `qwen3.5:9b` en `LOCAL_MODEL_CHAIN` (dev y prod). Un `ollama pull` puede cambiar lo que hay detras de un tag | Solo tag; el **digest** no esta registrado -> ver C1 |
| Digest del modelo (dev, hoy) | `qwen3.5:9b` ID `6488c96fa5fa` (6.6 GB); tambien `qwen3:8b` `500a1f067a9f`, `llama3.1:8b` `46e0c10c039e`, `bge-m3:latest` `790764642607` (embeddings), `qwen2.5-coder:1.5b` `d7372fd82851` (IDs cortos de `ollama list`; el digest COMPLETO lo entrega `collect_versions.py`) | Registrar el de prod desde el propio host de prod |
| LiteLLM / Google ADK | `litellm==1.100.1`, `google-adk==2.9.0` **fijados** en `ai_engine_adk/requirements.txt` | OK |
| Paquetes Python del ADK | `requirements.txt` fija solo lo directo (y deja rangos `>=` en httpx, python-multipart, PyJWT, redis); **las transitivas flotan en cada build**. Existe `requirements.lock.txt` (snapshot exacto) pero **no esta conectado al Dockerfile** ("decision operativa del usuario"). Comparado con la imagen de DEV vigente: **29 lineas de deriva** (p. ej. `filelock` 3.x -> **4.x**, `google-genai` 2.23 -> 2.25, `boto3` 1.43.94 -> .100) y `asyncpg` **faltaba** en el lock (lo necesita `ADK_SESSION_BACKEND=database`) | **Gap**. Lock **regenerado** desde la imagen de dev (89 paquetes); conectarlo al build = decision tuya (C4) |
| Paquetes de Django | Poetry, pero el `Dockerfile` ejecuta **`poetry lock` dentro del builder en cada build** (regenera el lock: las versiones se resuelven al construir, no las del lock commiteado) | **Gap** (no cambiado: toca el build de produccion; C4) |
| Imagenes base | `python:3.13-slim`, `python:3.12-slim`, `node:24-alpine`, `node:24-bookworm-slim` **sin digest**; en prod: `redis:7.2-alpine`, `pgvector/pgvector:pg16`, `nginx:1.26-alpine`, `cloudflare/cloudflared:2026.7.1` (tags de version, sin digest) | Tags de version aceptables; **ninguna fijada por digest** (C1 lo mide y C4 propone fijarlas) |
| Imagenes construidas | 12 imagenes `sintel*` (incl. `prod`, `prod-runtime`): 0 `ENV` con secretos, 0 capas con `.env`/`notas.txt` (F15) | OK |
| SBOM (§20.1) | No existe; `syft`, `trivy`, `pip-audit` **no estan instalados** en este equipo (solo `bandit 1.9.4`) | **Gap** -> scripts (C2/C3) |
| Escaneos (§20.2) | Nunca ejecutados | **Gap** -> scripts (C3) |

## 2. Entregado (dev; nada aplicado en produccion, nada ejecutado)
- **Dev fijado a Ollama `0.30.10`** (`docker-compose.yml`): sin recrear el contenedor (ya corre esa version). Regla dev/prod sincronizados.
- **`ai_engine_adk/requirements.lock.txt` regenerado** (89 paquetes, `pip freeze` de la imagen de dev: la misma que corrio F2-F14). Sigue sin conectarse al Dockerfile.
- **C1 `scripts/supply_chain/collect_versions.py`**: inventario de imagenes de ambos compose (digest local, aviso por tag flotante o sin `@sha256`), version de Ollama y **digest completo por modelo** (`/api/tags`), y `pip freeze` de las imagenes que indiques. `--verify manifest.json` sale con 1 si cambia un id de imagen, la version de Ollama, el digest de un modelo o un paquete. Solo lectura (`docker image inspect`, HTTP a Ollama, y `docker run --rm --entrypoint pip <imagen> freeze` opcional: contenedor efimero de la IMAGEN, nunca `exec` en contenedores de produccion).
- **C2 `scripts/supply_chain/generate_sbom.sh`**: SBOM CycloneDX con syft (contenedor efimero con el socket en solo lectura) de `ai_engine_adk`, `ollama`, `django`, `celery worker/beat` (`prod` por defecto, `dev` como argumento).
- **C3 `scripts/supply_chain/scan_vulns.sh`**: Trivy (imagenes, HIGH/CRITICAL con fix), pip-audit (locks del ADK y de `ai_engine`), Bandit (codigo propio, severidad media+). Informes a `scripts/supply_chain/_out/vuln/`.
- **`docs/security/VULN_EXCEPTIONS.md`**: registro de excepciones justificadas (vacio; con reglas y caducidad).

## 3. Como usarlo (tu, en este orden)
1. `python scripts/supply_chain/collect_versions.py --ollama http://localhost:11434 --pip-images ecommerce_sintel_ai_adk:latest --out scripts/supply_chain/_out/manifest_dev.json` (dev) y lo mismo **en el host de prod** con `--ollama http://localhost:<puerto>` (Ollama de prod no expone puerto al host: usar `docker exec sintel_prod_ollama ollama list`/`ollama show` a mano o el `/api/tags` desde la red Docker) -> guarda el resultado de prod como `ecommerce_sintel/docs/supply_chain/manifest.json` (referencia versionada) y usa `--verify` despues de cada despliegue o `ollama pull`.
2. `./scripts/supply_chain/generate_sbom.sh` y `./scripts/supply_chain/scan_vulns.sh` (descargan `anchore/syft` y `aquasec/trivy` la primera vez). Registrar excepciones en `docs/security/VULN_EXCEPTIONS.md`.
3. Con los resultados: aplicar actualizaciones con evidencia (y F10 si toca modelo/ADK/LiteLLM/Ollama).

## 4. Decisiones que quedan para ti (C4, no aplicadas)
1. **Conectar el lock del ADK al build** con un cambio de una linea y sin cambiar `requirements.txt`: `RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock.txt` (los pines transitivos quedan fijos y las directas siguen mandando). Recomendado, ahora que el lock esta al dia.
2. **Django**: quitar `poetry lock` del builder (usar el `poetry.lock` commiteado con `poetry install --no-root` y `poetry check --lock` que falle si esta desactualizado). Cambia el build de produccion: hacerlo con tu visto bueno y una reconstruccion completa.
3. **Digests de imagenes**: fijar `image: ...@sha256:<digest>` para Ollama, Redis, pgvector, nginx, cloudflared (y `FROM ...@sha256` en los Dockerfile) tras generar el manifest de prod; hay que actualizarlos a proposito en cada upgrade.
4. **Modelo por digest**: registrar el digest de prod en `docs/supply_chain/manifest.json` y verificar en el despliegue que `qwen3.5:9b` coincide; un cambio de digest exige re-correr F10.
