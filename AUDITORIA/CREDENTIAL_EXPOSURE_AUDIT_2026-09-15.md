# CREDENTIAL_EXPOSURE_AUDIT — 2026-09-15

**Disparador:** tarea transversal pendiente registrada en `AUDITORIA/ADK_CUTOVER_PLAN.md` y en
memoria de sesion: `notas.txt` fue excluido de toda imagen Docker el 2026-09-14 (typo real en
`.dockerignore` corregido), pero la rotacion de las credenciales que el archivo pudo haber
expuesto quedo pendiente. Esta auditoria (FASE 0A/0C del "MISION: SANEAMIENTO DE SEGURIDAD Y
CONTINUACION CONTROLADA DE META BUSINESS") cierra el inventario antes de rotar nada.

**Regla de esta auditoria:** ningun valor real de secreto se imprime aqui ni se imprimio en la
sesion. Todo se referencia por fragmento identificador ya usado en las busquedas (nunca el
secreto completo) o por ubicacion/linea.

---

## Alcance revisado (checklist FASE 0A)

- [x] Contenido actual de `notas.txt`
- [x] `.gitignore` / `.dockerignore` (raiz y `ai_engine/`)
- [x] Dockerfiles (raiz `ecommerce_sintel/Dockerfile`, contexto de build)
- [x] Historial Git: `git log --all --full-history`, `git log --all -S<fragmento>` (pickaxe,
      todas las ramas) para los 3 secretos de `notas.txt`
- [x] `git grep` sobre el working tree trackeado (todas las ramas via checkout implicito no
      necesario: el archivo nunca estuvo trackeado)
- [x] Objetos Git inalcanzables (`git fsck --unreachable`, 698 blobs) — escaneados uno por uno
      por si alguno quedo de un `git add` revertido nunca commiteado
- [x] `git stash list` (vacio) y `git reflog --all` (revisado, sin operaciones que sugieran
      commit/stash de `notas.txt`)
- [x] Archivos `.env`, `.env.production`, `.env.production.example` (filesystem real, no solo
      lo trackeado)
- [x] `deploy/backup.sh` (que archiva) y `/c/Users/Administrator/sintel_backups/` (destino real
      en este mismo host) — grep directo sobre el contenido de los backups
- [x] `.github/workflows/ci.yml` (unico workflow del repo)
- [ ] Logs de aplicacion/servicios — no revisados en esta pasada (no hay indicio de que
      `notas.txt` se haya leido/cateado desde ningun script trackeado; si se requiere certeza
      total habria que revisar logs historicos de terminal fuera del repo, no accesibles desde
      aqui)

## Hallazgo estructural (confirma memoria previa)

El Dockerfile raiz (`ecommerce_sintel/Dockerfile`) usa como contexto de build la raiz del repo,
pero **solo copia el subdirectorio `ecommerce_sintel/`**:
```
COPY ecommerce_sintel/pyproject.toml ecommerce_sintel/poetry.lock* ./
COPY ecommerce_sintel/frontend/ ./
COPY ecommerce_sintel/ /code/
```
`notas.txt` vive en la raiz del repo, **fuera** de `ecommerce_sintel/` — nunca entra al build
sin importar el estado de `.dockerignore`. El fix del typo (`.notas.txt` -> `notas.txt`) cerrado
el 2026-09-14 fue una capa de defensa correcta, pero la exposicion real por imagen Docker nunca
existio con esta estructura de Dockerfile. Confirmado leyendo el Dockerfile directamente, no
solo citando la memoria anterior.

## Resultado de las busquedas (0 coincidencias en todos los canales)

Para los 3 fragmentos identificadores de `notas.txt` (login del apartado "CONFLICTO CRM",
fragmento de la password de `admin@sintel.com`, fragmento de la password junto a la URL de
Cloudflare):

| Canal buscado | Metodo | Resultado |
|---|---|---|
| Historial Git, todas las ramas | `git log --all -S<fragmento>` (pickaxe) | 0 commits |
| Working tree trackeado | `git grep` | 0 archivos |
| Objetos inalcanzables | `git fsck --unreachable` + `git cat-file` sobre cada blob (698) | 0 blobs |
| `.env` / `.env.production` / `.env.production.example` | grep directo sobre filesystem | 0 lineas |
| Backups locales (`sintel_backups/db`, `/media`, `/config`) | grep recursivo | 0 lineas |
| CI (`.github/workflows/ci.yml`) | grep | 0 lineas |

**Conclusion de FASE 0A/0C: la exposicion esta 100% confinada al archivo `notas.txt` en texto
plano, en este unico host, version actual. Nunca entro a git (ni commit, ni stash, ni blob
huerfano), nunca a una imagen Docker, nunca a un backup, nunca a CI/CD.** Esto reduce el riesgo
frente al peor caso (fuga distribuida via git/imagen), pero no lo elimina: cualquiera con acceso
de lectura a este filesystem (o a una copia futura no controlada del archivo) ve las credenciales
en claro hoy.

---

## Matriz de credenciales potencialmente expuestas

| Secreto | Tipo | Sistema | Posible exposicion | Evidencia | Riesgo | Accion recomendada |
|---|---|---|---|---|---|---|
| Login #1 (`notas.txt`, seccion "CONFLICTO CRM — Dos proyectos en la misma maquina", etiquetado "produccion user") | Usuario + password | **Sin confirmar** — aparece en el contexto de coordinar puertos entre "CRM Sintel" (otro proyecto en esta misma maquina) y `ecommerce_sintel`; no hay evidencia en el codigo de este repo de que este login pertenezca a un servicio de `ecommerce_sintel` | Solo filesystem local (`notas.txt` actual) | `notas.txt` L23-26; 0 hits en todas las busquedas git/backup/CI de la tabla anterior | **INDETERMINADO** hasta confirmar sistema dueno — si es de produccion real, ALTO | Preguntar al usuario a que sistema pertenece antes de decidir si rotar aqui o derivarlo al otro proyecto |
| Password de `admin@sintel.com` (`notas.txt`) | Password de superusuario Django | `ecommerce_sintel` (coincide con el superusuario real citado en memoria) | Solo filesystem local | `notas.txt` L26-27; memoria `project_adk_migration_cutover_and_reasoning_fix` registra que esta cuenta fue rotada explicitamente el 2026-09-14 via `User.set_password()`, con el valor nuevo solo en `$env:E2E_ADMIN_PASSWORD` (nunca escrito a archivo ni a git) | **BAJO si es el valor previo a la rotacion del 09-14 (ya invalido)** — pero no verificado con certeza en esta auditoria | Confirmar con el usuario si el valor de `notas.txt` es anterior a esa rotacion; si es asi, solo requiere limpiar el archivo (no rotar de nuevo); si no, rotar |
| Password junto a URL de Cloudflare (agregar security key) (`notas.txt`) | Password de cuenta Cloudflare (dashboard, MFA) | Cloudflare — controla el Tunnel real de `sintel.net.co` (produccion) | Solo filesystem local | `notas.txt` L53-54; 0 hits en todas las busquedas | **ALTO si sigue vigente** (acceso a infraestructura de produccion) | Confirmar vigencia con el usuario; si vigente, la rotacion debe hacerla el usuario en el dashboard de Cloudflare (fuera del alcance de herramientas de este agente) |

*(Nota: no se muestran los secretos reales en esta tabla ni se mostraron en ningun momento de la
sesion — solo ubicacion y fragmentos ya usados como criterio de busqueda, nunca impresos aqui.)*

---

## Checkpoint de seguridad (Seccion 6 de la mision) — ACTUALIZADO

Las 3 confirmaciones del usuario:
1. Login #1 (`ce@sintel.net.co`) pertenece a este proyecto ("de este proyecto (ecommerce_sintel)").
   Verificado por esta sesion que **NO** es un usuario Django: `User.objects.filter(email=
   'ce@sintel.net.co')` da `NOT FOUND` tanto en `ecommerce_sintel_django` (dev) como en
   `sintel_prod_django` (produccion real), y tampoco coincide con `DEFAULT_FROM_EMAIL`/
   `EMAIL_HOST_USER` de ningun entorno (`sintel.technology@gmail.com` en dev,
   `contacto@sintel.net.co` en produccion). El usuario confirmo que es un **login de panel de
   hosting/servidor**, fuera del alcance de las herramientas de este agente.
2. Password de `admin@sintel.com`: confirmada por el usuario como la version **anterior** a la
   rotacion del 2026-09-14, ya invalida.
3. Password de Cloudflare (junto a la URL de agregar security key): confirmada por el usuario
   como **ya no vigente**.

### FASE 0B ejecutada (parcial, dentro de lo que este agente puede hacer)

- `notas.txt`: password vieja de `admin@sintel.com` **retirada** (dead, ya invalida, sin accion
  de rotacion necesaria). Password de Cloudflare **retirada** (dead, ya no vigente). Ambas
  reemplazadas por un comentario fechado que referencia este documento, sin reintroducir ningun
  secreto.
- `ce@sintel.net.co` / password: **se deja temporalmente en `notas.txt`**, marcado
  explicitamente `PENDIENTE: el usuario debe rotarlo manualmente en el panel de hosting`. No se
  elimino porque el usuario todavia lo necesita para iniciar sesion en ese panel externo y
  cambiarlo -- borrarlo ahora bloquearia su propia rotacion. Este agente no tiene acceso a ese
  panel y no puede ejecutar la rotacion ni verificar que la credencial anterior dejo de
  funcionar.

### Estado final

`PARTIAL` -- 2 de 3 credenciales cerradas (confirmadas muertas, retiradas del archivo). La
tercera (`ce@sintel.net.co`, panel de hosting) queda **pendiente de accion manual del usuario**;
este agente hara el retiro final de `notas.txt` en cuanto el usuario confirme que la rotacion en
el panel se completo.

No se toco produccion (solo se hizo una lectura de solo-lectura de `User.objects.filter(...)`
contra ambas bases de datos para descartar que fuera una cuenta Django). No quedan secretos
reales en este documento ni en ningun archivo trackeado por git.

**FASE 0 de Meta Business permanece bloqueada aparte** (no depende de esta auditoria de
`notas.txt` — es un bloqueo independiente por falta de `META_APP_ID`, `META_WABA_ID`,
`META_AD_ACCOUNT_ID`, `META_CATALOG_ID`, `META_PIXEL_ID`, `META_DATASET_ID`, ninguno disponible
en `.env`/`.env.production` hoy). Ver seccion "Meta Business FASE 0" en la respuesta de la
sesion para el detalle completo.
