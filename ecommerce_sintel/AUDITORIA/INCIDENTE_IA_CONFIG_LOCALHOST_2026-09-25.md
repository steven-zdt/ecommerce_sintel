# Incidente: "Conexion fallo" en /panel/soporte/ia-config con LM Studio (2026-09-25)

Estado: RESUELTO en produccion. Post-mortem para que no se repita.

## Sintoma
En `https://panel.sintel.net.co/panel/soporte/ia-config`, "Probar conexion" del proveedor LM Studio respondia **"Conexion fallo: No se pudo establecer conexion."**
sin ninguna pista, aunque LM Studio estaba corriendo y respondia en el host.

## Causas (dos, encadenadas)
1. **URL guardada = `http://localhost:1234/v1`.** Es la URL que LM Studio muestra en su ventana (vista desde el equipo donde corre). Dentro de un
   contenedor Docker `localhost` es el propio contenedor: la peticion nunca sale hacia el host. El panel de prod tenia una sola fila
   (`LM Studio`, `config_version 1`, nunca editada). Hallada con una consulta de solo lectura a `AIProvider` en `sintel_prod_django`.
2. **`django` de prod no resolvia `host.docker.internal`.** El servicio fija `dns: 1.1.1.1 / 8.8.8.8` y no tenia `extra_hosts`; con DNS publicos ese
   nombre no resuelve (reproducido: `Name or service not known`). `sintel_ai` y `sintel_ai_adk` ya lo tenian por el mismo hallazgo de 2026-09-14.
   Aunque se hubiera corregido la URL, "Probar conexion" y "Detectar modelos" (que corren en Django) habrian fallado.

## Por que costo tanto diagnosticarlo
- El mensaje era generico ("No se pudo establecer conexion.") para cualquier `requests.ConnectionError`: ocultaba si era DNS, puerto cerrado, ruta o localhost.
- El log de LM Studio sirvio de prueba: **a la hora de la prueba no llego ninguna peticion** => el fallo era antes del servidor (red/URL), no LM Studio.
- Las pruebas en dev pasaban (`host.docker.internal` resuelve solo con Docker Desktop y sin `dns:` publicos), asi que dev no reproducia lo de prod.
- Un 401 en la consola parecia un fallo y era solo el refresh normal del token (15 min de vida del access token).

## Correcciones
| Donde | Cambio |
|---|---|
| `docker-compose.prod.yml` | `extra_hosts: host.docker.internal:host-gateway` en `django` |
| `ai_provider/services/providers/base.py` | `connection_failure()`: mensajes especificos por causa (DNS, rechazada, sin ruta, timeout) y deteccion de `localhost` con la instruccion de usar `host.docker.internal` |
| `ai_provider/models.py` (`AIProvider.clean`) | **Rechaza `localhost/127.0.0.1/::1/0.0.0.0` al guardar** (setting `AI_PROVIDER_ALLOW_LOOPBACK`, false por defecto, solo para Django fuera de Docker) |
| `frontend/.../AIProviderForm.vue` | Aviso rojo en vivo al escribir una URL loopback |
| `ai_engine_adk/provider_registry.py` | El ADK descarta entradas del Registry con URL loopback; si el **primario** es invalido ignora todo el Registry y usa `LOCAL_MODEL_CHAIN` (sin promover un fallback en silencio) |
| Produccion (datos) | URL del proveedor corregida a `http://host.docker.internal:1234/v1` con `AIProviderCommands.update_provider` (deja historial, version 2) |

## Reglas para que no vuelva a pasar
1. **Desde un contenedor, el host se llama `host.docker.internal`, nunca `localhost`/`127.0.0.1`.** LM Studio (1234) y Ollama nativo (11434) muestran `localhost`
   porque lo ven desde el equipo; dentro de Docker usar `http://host.docker.internal:PUERTO`. Servicios Docker: su nombre (`http://sintel_ollama:11434`).
2. **Todo servicio de `docker-compose.prod.yml` que deba llegar al host necesita `extra_hosts: host.docker.internal:host-gateway`** (hoy: `django`, `sintel_ai`,
   `sintel_ai_adk`). Sobre todo si define `dns:` publicos. Al agregar un servicio nuevo que llame al host, verificarlo.
3. Probar la red de un servicio de prod **en dev con las mismas opciones** (`--network` de usuario, `--dns 1.1.1.1 --dns 8.8.8.8`, `--add-host`), no con los defaults.
4. Diagnostico rapido de "no conecta con LM Studio": (a) `curl http://127.0.0.1:1234/v1/models` en el host; (b) revisar el log de LM Studio: si la peticion **no aparece**,
   el problema es red/URL; (c) URL guardada en la fila del proveedor; (d) `docker inspect <contenedor> --format '{{.HostConfig.ExtraHosts}}'` debe listar
   `host.docker.internal`; (e) `docker network inspect` y contenedor desechable con las mismas redes/DNS.
5. Cambios de `environment:`/`extra_hosts:` requieren `up -d --force-recreate <servicio>`; un `restart` no los aplica. Cambios de codigo requieren rebuild de la imagen.
6. Un mensaje de error de infraestructura debe decir **la causa y la accion** (no "No se pudo establecer conexion").
7. Un solo proveedor con `config_version 1` en prod significa "nunca se guardo una edicion": mirar el historial (`ai-providers/<uuid>/history/`) antes de asumir que un cambio se aplico.

## Pendiente / relacionado
- El formulario de edicion no llego a guardar la URL del usuario y no se identifico por que (en dev el mismo flujo por API guarda). Con el rechazo de loopback ahora
  el servidor devuelve un 400 explicito y el panel lo muestra. Si vuelve a ocurrir sin mensaje, revisar `handleError` en `AIProviderConfigView.vue`.
- El chat NO sigue el panel hasta activar `AI_PROVIDER_REGISTRY_ENABLED` en produccion (flag ya en `.env.production`, ADK sin recrear). Ver
  `AUDITORIA/LLM_PROVIDER_REGISTRY_F0_F4_2026-09-25.md` y `ai_engine_adk/.AGENT/MODEL_RUNTIME.md`.
- Excepcion registrada a la regla 0-DEV-FIRST: en este incidente se hicieron consultas de solo lectura y una correccion de datos (URL) en `sintel_prod_django`
  por autorizacion expresa del usuario. No es un precedente general.
