#!/bin/bash
# =============================================================================
# restore.sh -- Restauracion de un backup de Sintel E-Commerce (produccion)
# Ver docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md, Fase 19.
#
# Uso: ./deploy/restore.sh <timestamp>
#   <timestamp>  El sufijo usado por backup.sh, ej: 20260710_120000
#                (ver archivos en $SINTEL_BACKUP_ROOT/db/sintel_db_<timestamp>.dump)
#
# ADVERTENCIA: sobreescribe la base de datos y los archivos media/KYC
# actuales del stack de produccion. Requiere confirmacion interactiva.
# =============================================================================
set -euo pipefail

# Ver backup.sh: evita que Git Bash/MSYS2 (Windows) corrompa rutas del lado
# del contenedor en "docker run -v host:/ruta_container".
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_ROOT="${SINTEL_BACKUP_ROOT:-/c/Users/Administrator/sintel_backups}"
DB_CONTAINER="sintel_prod_db"
DJANGO_CONTAINER="sintel_prod_django"

TIMESTAMP="${1:-}"
if [ -z "$TIMESTAMP" ]; then
    echo "Uso: $0 <timestamp>" >&2
    echo "Backups disponibles:" >&2
    ls "$BACKUP_ROOT/db" 2>/dev/null | sed 's/sintel_db_//; s/\.dump$//' >&2
    exit 1
fi

DB_DUMP="$BACKUP_ROOT/db/sintel_db_${TIMESTAMP}.dump"
MEDIA_TAR="$BACKUP_ROOT/media/sintel_media_${TIMESTAMP}.tar.gz"

if [ ! -f "$DB_DUMP" ]; then
    echo "ERROR: no existe $DB_DUMP" >&2
    exit 1
fi

echo "!!! Esto SOBREESCRIBIRA la base de datos y media/KYC actuales de produccion."
echo "!!! Backup a restaurar: $TIMESTAMP"
read -r -p "Escribe 'RESTAURAR' para confirmar: " CONFIRM
if [ "$CONFIRM" != "RESTAURAR" ]; then
    echo "Cancelado."
    exit 1
fi

echo ">>> [1/4] Creando snapshot preventivo del estado actual..."
"$SCRIPT_DIR/backup.sh"
echo "    -> snapshot preventivo completado"

echo ">>> [2/4] Restaurando PostgreSQL..."
DB_NAME="$(docker exec "$DB_CONTAINER" sh -c 'echo $POSTGRES_DB')"
DB_USER="$(docker exec "$DB_CONTAINER" sh -c 'echo $POSTGRES_USER')"
# --clean --if-exists: dropea objetos existentes antes de recrearlos (evita
# conflictos de "already exists" al restaurar sobre una BD no vacia).
docker exec -i "$DB_CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists < "$DB_DUMP"
echo "    -> base de datos restaurada"

if [ -f "$MEDIA_TAR" ]; then
    echo ">>> [3/4] Restaurando media/ y private_media/..."
    docker run --rm \
        --volumes-from "$DJANGO_CONTAINER" \
        -v "$BACKUP_ROOT/media:/backup_in:ro" \
        alpine:3.20 \
        tar -xzf "/backup_in/sintel_media_${TIMESTAMP}.tar.gz" -C /code
    echo "    -> media/private_media restaurados"
else
    echo ">>> [3/4] No hay backup de media para $TIMESTAMP, se omite."
fi

echo ">>> [4/4] Reiniciando django y celery para tomar los datos restaurados..."
# Uno por uno (no "docker restart A B C" atomico): si un worker esta caido
# por una razon no relacionada, no debe hacer parecer que la restauracion
# de BD/media (lo critico, ya confirmado arriba) fallo.
for c in "$DJANGO_CONTAINER" sintel_prod_celery_worker sintel_prod_celery_beat; do
    if docker restart "$c" >/dev/null 2>&1; then
        echo "    -> $c reiniciado"
    else
        echo "    -> AVISO: no se pudo reiniciar $c (¿esta corriendo?), revisar manualmente" >&2
    fi
done

echo ">>> Restauracion completa: ${TIMESTAMP}"
echo ">>> Nota: .env.production/certs/cloudflared NO se restauran automaticamente"
echo "    (son configuracion, no datos) -- estan en $BACKUP_ROOT/config/${TIMESTAMP}/ si se necesitan."
