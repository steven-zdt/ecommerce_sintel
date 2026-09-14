# 33 - Auditoria de readiness para produccion

> **Fecha de evidencia:** 2026-08-04
>
> **Alcance:** configuracion del stack `sintel_production`, estado vivo, seguridad perimetral,
> secretos, despliegue, salud y recuperacion. No se modificaron contenedores ni secretos de
> produccion; posteriormente se aplico un reinicio autorizado de cuentas mediante borrado logico.
> Esta
> auditoria no sustituye una prueba de restauracion controlada ni una prueba de carga.

## Dictamen

El servicio esta **operativo y apto para continuar atendiendo trafico**. La automatizacion de
backup fue corregida y verificada el 2026-08-04; permanecen como condiciones para readiness
completa la rotacion de credenciales expuestas y la replica de copias cifradas fuera del host.

| Dominio | Estado | Resultado |
|---|---|---|
| Configuracion Compose | Cumple | `docker compose ... config --quiet` finalizo correctamente. |
| Servicios y salud | Cumple | Redis, PostgreSQL, Django, Celery worker, Celery beat y Nginx estaban `healthy`; cloudflared estaba `running`. |
| Disponibilidad extremo a extremo | Cumple | `https://api.sintel.net.co/api/v1/health/` respondio HTTP 200. |
| Configuracion Django | Cumple | `DEBUG=False`, hosts explicitos y CORS global deshabilitado. |
| Seguridad de red y secretos | No cumple | No hay puertos publicados y `.env.production` no esta versionado, pero se detectaron credenciales en notas operativas. |
| Recuperacion y backups | Cumple con observacion | Backup programado exitoso y artefactos validados; falta una copia independiente del host. |

## Evidencia verificada

### Controles que cumplen

1. **Aislamiento de red.** [docker-compose.prod.yml](../ecommerce_sintel/docker-compose.prod.yml)
   no declara `ports:`. Los puertos observados en Compose son solo puertos internos expuestos a
   la red `sintel-network`; no hay enlace de host. La entrada publica depende del tunel saliente
   de Cloudflare y Nginx.
2. **Salud real de aplicacion.** El endpoint interno de Django devolvio
   `{"status":"ok","db":true,"redis":true,"celery":true}`. El mismo endpoint publico
   devolvio HTTP 200. El healthcheck no se limita a confirmar que el proceso Daphne exista.
3. **Hardening Django.** La instancia activa confirma `DEBUG=False`,
   `CORS_ALLOW_ALL_ORIGINS=False` y una lista concreta de cuatro hosts permitidos. La configuracion
   de produccion exige `WOMPI_EVENTS_SECRET` al iniciar.
4. **Hardening de proxy.** [nginx-common.conf](../ecommerce_sintel/nginx-common.conf) establece
   TLS 1.2/1.3, HSTS, CSP, `X-Frame-Options: DENY`, `nosniff`, politica de referer, permisos
   restrictivos, limite por IP y bloqueo de `/api/v1/internal/` antes del proxy.
5. **Secretos fuera del control de versiones.** `git check-ignore` confirma que
   `.env.production` se ignora y `git ls-files` confirma que no esta versionado. Los certificados
   y las credenciales del tunel se montan desde rutas externas y de solo lectura.
6. **Despliegue reproducible.** [deploy.sh](../ecommerce_sintel/deploy/deploy.sh) usa
   `--no-cache` al construir la unica imagen de runtime y espera la salud de Django. No hay
   bind mount de codigo fuente en el servicio de produccion.
7. **Celery beat monitorizado.** El healthcheck de proceso de `celery_beat` ya existe y se
   encuentra `healthy`. Es una mejora cerrada en [31_REPASO_BACKLOG_QUICK_WINS.md](31_REPASO_BACKLOG_QUICK_WINS.md).

### Reinicio autorizado de cuentas de produccion

Por instruccion expresa del responsable del entorno, se retiraron todas las cuentas existentes
sin borrar fisicamente sus relaciones historicas. El estado previo contenia tres cuentas activas,
incluido un usuario con privilegios de administracion. La operacion transaccional marco las tres
cuentas como eliminadas logicamente e inactivas, retiro privilegios de personal y superusuario,
y reemplazo sus credenciales por contrasenas inutilizables. Tambien se invalidaron los codigos de
verificacion pendientes.

La verificacion inicial confirmo cero cuentas activas, visibles o con privilegios y cero codigos
de verificacion pendientes. Posteriormente, se restauro de forma controlada una unica cuenta
administradora existente mediante el terminal de produccion: se reactivo, se retiro su marca de
borrado logico, se le asignaron privilegios de personal y superusuario y se establecio una nueva
contrasena. La verificacion final confirma que esa cuenta esta activa, visible y habilitada como
administradora; las otras cuentas permanecen eliminadas logicamente. El contenedor
`sintel_prod_django` permanecio `healthy`. No se aplico `DELETE` fisico, ya que el modelo de
datos conserva pedidos, pagos, rentas y demas historial relacionado mediante el patron obligatorio
de borrado logico.

## Hallazgos abiertos

### P1-01 - Resuelto: el respaldo automatico no podia comunicarse con Docker

**Evidencia.** La tarea `SintelEcommerceBackup` figura `Ready`, pero su ultima ejecucion fue el
2026-08-04 08:14:14 con `LastTaskResult=1`. El log de backup informa:

`failed to connect to the docker API at npipe:////./pipe/docker_engine`

Las dos ejecuciones fallidas mas recientes abortaron antes de crear el dump, al no poder acceder
al daemon Docker. El ultimo dump disponible es del 2026-08-02 03:00:03. La causa probable es que
la tarea se ejecuta bajo una identidad sin acceso al named pipe de Docker Desktop.

**Impacto.** El RPO real ya excedio la retencion diaria esperada. Ante fallo del host, el negocio
solo puede restaurar hasta el ultimo dump existente, perdiendo los cambios posteriores. Esto
incumple el objetivo operativo anunciado en la documentacion de despliegue.

**Correccion y evidencia.** Se instalo
[install_backup_task.ps1](../ecommerce_sintel/deploy/install_backup_task.ps1) con la cuenta
`Administrator`, en vez de `SYSTEM`. La tarea se inicio manualmente el 2026-08-04 12:10:10 y
finalizo con `LastTaskResult=0`. Genero `sintel_db_20260804_121043.dump` y
`sintel_media_20260804_121043.tar.gz`; [backup.sh](../ecommerce_sintel/deploy/backup.sh) valido
el dump y el archivo de media antes de publicarlos. Se restauro ese backup el mismo dia; el script
creo antes el snapshot preventivo `20260804_121324`, PostgreSQL respondio correctamente y Django,
Celery worker y Celery beat quedaron `healthy`. El endpoint publico de salud respondio HTTP 200.

**Seguimiento.** Repetir la restauracion en un entorno aislado al cambiar el esquema, la estrategia
de volúmenes o la infraestructura de backup, y registrar RTO/RPO medidos.

### P1-02 - Resuelto: el script aceptaba dumps sin verificar su integridad

**Correccion y evidencia.** [backup.sh](../ecommerce_sintel/deploy/backup.sh) publica los archivos
solo despues de validar el dump con `pg_restore --list` y el archivo de media con `tar -tzf`; tambien
evita ejecuciones concurrentes. La ejecucion programada del 2026-08-04 genero los dos artefactos
validados indicados en P1-01.

**Impacto.** Un dump truncado o corrupto puede permanecer como supuesto punto de recuperacion
sin deteccion previa al incidente.

**Control adicional aplicado.** [restore.sh](../ecommerce_sintel/deploy/restore.sh) crea ahora un
snapshot preventivo antes de sobrescribir datos. Mantener una prueba de restauracion periodica
fuera del host productivo.

### P1-03 - Credenciales almacenadas en notas operativas

**Evidencia.** Durante la revision se detectaron credenciales y material sensible en
[notas.txt](../notas.txt). Fueron retirados del archivo de trabajo para evitar exposicion futura.

**Impacto.** Si el archivo fue sincronizado, compartido o versionado antes de la retirada, las
credenciales deben considerarse comprometidas. Un atacante con acceso al repositorio o a copias
del archivo podria autenticarse o reutilizar el material expuesto.

**Accion requerida.** Rotar de inmediato las credenciales afectadas, invalidar sesiones y tokens
asociados cuando aplique, y revisar el historial Git, copias de seguridad y canales donde el
archivo pudo haberse compartido. Centralizar los secretos en el gestor aprobado y no volver a
incluirlos en notas, scripts o documentacion.

### P2-01 - Las copias permanecen en el mismo host de produccion

**Evidencia.** [backup.sh](../ecommerce_sintel/deploy/backup.sh) usa por defecto
`C:\Users\Administrator\sintel_backups`, en el mismo equipo que contiene los volumenes y los
secretos de produccion.

**Impacto.** Un fallo de disco, ransomware o perdida completa del host puede afectar a la vez los
datos activos, los backups y la configuracion necesaria para recuperar.

**Recomendacion.** Replicar copias cifradas a almacenamiento fuera del host con retencion
independiente e incluir una comprobacion automatica de exito de esa replica.

## Limitaciones y controles pendientes de verificar

- `cloudflared` no declara un `HEALTHCHECK` Docker propio. La disponibilidad publica HTTP 200
  confirma el camino completo en el momento de la auditoria, pero no reemplaza monitoreo externo
  continuo ni alertas de expiracion de certificados.
- No se ejecutaron pruebas de carga, rotacion de secretos, pagos reales ni pruebas de failover;
   requieren una ventana y un entorno controlado. La restauracion controlada de backup se ejecuto
   el 2026-08-04 y recupero salud operativa.
- La validacion de cabeceras HTTP se limita a los controles que el proxy y la configuracion
  declaran. Cualquier cambio de Cloudflare debe seguir revisandose desde fuera de la red local.

## Criterio de cierre

La readiness de produccion puede pasar a **cumple** cuando se evidencien: un destino de copia
independiente del host y la rotacion verificada de las credenciales expuestas.