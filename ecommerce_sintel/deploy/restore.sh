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
    ls "$BACKUP_ROOT/db" 2>/dev/null | sed 's/sintel_db_//; s/\.dump\(\.enc\)\{0,1\}$//' >&2
    exit 1
fi

BACKUP_KEY_FILE="${SINTEL_BACKUP_KEY_FILE:-/c/Users/Administrator/sintel_secrets/backup.key}"
DB_DUMP="$BACKUP_ROOT/db/sintel_db_${TIMESTAMP}.dump"
MEDIA_DIR="$BACKUP_ROOT/media"
MEDIA_FILE="sintel_media_${TIMESTAMP}.tar.gz"
MEDIA_TAR="$MEDIA_DIR/$MEDIA_FILE"

# HARDENING F15: backups cifrados (.enc, openssl AES-256/PBKDF2, ver backup.sh). Se descifran a un directorio temporal que se borra al salir.
RESTORE_TMP="$BACKUP_ROOT/.restore_tmp_$$"
trap 'rm -rf "$RESTORE_TMP"' EXIT
decrypt_to_tmp() {
    mkdir -p "$RESTORE_TMP"
    [ -f "$BACKUP_KEY_FILE" ] || { echo "ERROR: falta la clave $BACKUP_KEY_FILE para descifrar $1" >&2; exit 1; }
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in "$1" -out "$RESTORE_TMP/$2" -pass "file:$BACKUP_KEY_FILE" \
        || { echo "ERROR: no se pudo descifrar $1 (clave incorrecta o archivo danado)" >&2; exit 1; }
}
if [ ! -f "$DB_DUMP" ] && [ -f "${DB_DUMP}.enc" ]; then
    decrypt_to_tmp "${DB_DUMP}.enc" "$(basename "$DB_DUMP")"
    DB_DUMP="$RESTORE_TMP/$(basename "$DB_DUMP")"
fi
if [ ! -f "$MEDIA_TAR" ] && [ -f "${MEDIA_TAR}.enc" ]; then
    decrypt_to_tmp "${MEDIA_TAR}.enc" "$MEDIA_FILE"
    MEDIA_DIR="$RESTORE_TMP"
    MEDIA_TAR="$RESTORE_TMP/$MEDIA_FILE"
fi

if [ ! -f "$DB_DUMP" ]; then
    echo "ERROR: no existe el backup de BD para $TIMESTAMP (ni .dump ni .dump.enc)" >&2
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
        -v "$MEDIA_DIR:/backup_in:ro" \
        alpine:3.20 \
        tar -xzf "/backup_in/$MEDIA_FILE" -C /code
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
echo ">>> Nota: .env.production/certs/cloudflared NO se restauran ni se respaldan (F15): son secretos y viven en el"
echo "    gestor de contrasenas del usuario. En $BACKUP_ROOT/config/${TIMESTAMP}/ solo hay compose/nginx (sin secretos)."
