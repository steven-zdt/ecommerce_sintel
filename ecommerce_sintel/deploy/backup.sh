#!/bin/bash
# =============================================================================
# backup.sh -- Respaldo local de Sintel E-Commerce (produccion)
# Ver docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md, Fase 19.
#
# Respalda: PostgreSQL (dump), media/ (uploads), config (.env.production,
# certificados de origen, docker-compose.prod.yml). Todo queda fuera del
# repositorio, en BACKUP_ROOT (mismo patron que cloudflared/certs: secretos
# y datos reales nunca dentro de ecommerce_sintel/).
#
# Uso: ./deploy/backup.sh
# Requiere: el stack de produccion corriendo (docker compose -f
#           docker-compose.prod.yml --env-file .env.production up -d)
# =============================================================================
set -euo pipefail

# Evita que Git Bash/MSYS2 (Windows) traduzca rutas del lado del contenedor
# (ej. /backup_out en "docker run -v host:/backup_out") como si fueran rutas
# de host -- sin esto, docker recibe una ruta corrupta tipo
# "C:/Program Files/Git/backup_out". No-op inofensivo en Linux real.
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_ROOT="${SINTEL_BACKUP_ROOT:-/c/Users/Administrator/sintel_backups}"
RETENTION_DAYS="${SINTEL_BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOCK_DIR="$BACKUP_ROOT/.backup.lock"

DB_CONTAINER="sintel_prod_db"
DJANGO_CONTAINER="sintel_prod_django"

ENV_FILE="$PROJECT_DIR/.env.production"
CERTS_DIR="/c/Users/Administrator/sintel_secrets/certs"
CLOUDFLARED_DIR="/c/Users/Administrator/.cloudflared/sintel-production"

mkdir -p "$BACKUP_ROOT/db" "$BACKUP_ROOT/media" "$BACKUP_ROOT/config"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "ERROR: ya existe un backup en ejecucion ($LOCK_DIR). Aborta." >&2
    exit 1
fi

DB_DUMP_FINAL="$BACKUP_ROOT/db/sintel_db_${TIMESTAMP}.dump"
DB_DUMP_TMP="${DB_DUMP_FINAL}.tmp"
MEDIA_ARCHIVE_FINAL="$BACKUP_ROOT/media/sintel_media_${TIMESTAMP}.tar.gz"
MEDIA_ARCHIVE_TMP="${MEDIA_ARCHIVE_FINAL}.tmp"

cleanup() {
    rm -f "$DB_DUMP_TMP" "$MEDIA_ARCHIVE_TMP"
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT

echo ">>> [1/5] Respaldo de PostgreSQL..."
if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    echo "ERROR: el contenedor $DB_CONTAINER no esta corriendo. Aborta." >&2
    exit 1
fi
# shellcheck disable=SC2016
DB_NAME="$(docker exec "$DB_CONTAINER" sh -c 'echo $POSTGRES_DB')"
DB_USER="$(docker exec "$DB_CONTAINER" sh -c 'echo $POSTGRES_USER')"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom \
    > "$DB_DUMP_TMP"
if ! docker exec -i "$DB_CONTAINER" pg_restore --list < "$DB_DUMP_TMP" >/dev/null; then
    echo "ERROR: el dump PostgreSQL no supero la verificacion de integridad. Aborta." >&2
    exit 1
fi
mv "$DB_DUMP_TMP" "$DB_DUMP_FINAL"
echo "    -> $DB_DUMP_FINAL (integridad verificada)"

echo ">>> [2/5] Respaldo de media/..."
if ! docker ps --format '{{.Names}}' | grep -qx "$DJANGO_CONTAINER"; then
    echo "ERROR: el contenedor $DJANGO_CONTAINER no esta corriendo. Aborta." >&2
    exit 1
fi
docker run --rm \
    --volumes-from "$DJANGO_CONTAINER" \
    -v "$BACKUP_ROOT/media:/backup_out" \
    alpine:3.20 \
    tar -czf "/backup_out/$(basename "$MEDIA_ARCHIVE_TMP")" -C /code media private_media
if ! tar -tzf "$MEDIA_ARCHIVE_TMP" >/dev/null; then
    echo "ERROR: el archivo de media no supero la verificacion de integridad. Aborta." >&2
    exit 1
fi
mv "$MEDIA_ARCHIVE_TMP" "$MEDIA_ARCHIVE_FINAL"
echo "    -> $MEDIA_ARCHIVE_FINAL (integridad verificada)"

echo ">>> [3/5] Respaldo de configuracion (.env.production, certificados, compose)..."
CONFIG_BACKUP_DIR="$BACKUP_ROOT/config/${TIMESTAMP}"
mkdir -p "$CONFIG_BACKUP_DIR"
cp "$ENV_FILE" "$CONFIG_BACKUP_DIR/.env.production"
cp "$PROJECT_DIR/docker-compose.prod.yml" "$CONFIG_BACKUP_DIR/docker-compose.prod.yml"
cp "$PROJECT_DIR/nginx.prod.conf" "$CONFIG_BACKUP_DIR/nginx.prod.conf"
if [ -d "$CERTS_DIR" ]; then
    mkdir -p "$CONFIG_BACKUP_DIR/certs"
    cp "$CERTS_DIR"/origin.pem "$CERTS_DIR"/origin.key "$CONFIG_BACKUP_DIR/certs/" 2>/dev/null || true
fi
if [ -d "$CLOUDFLARED_DIR" ]; then
    mkdir -p "$CONFIG_BACKUP_DIR/cloudflared"
    cp "$CLOUDFLARED_DIR"/*.yml "$CLOUDFLARED_DIR"/*.json "$CONFIG_BACKUP_DIR/cloudflared/" 2>/dev/null || true
fi
echo "    -> $CONFIG_BACKUP_DIR/"

echo ">>> [4/5] Aplicando retencion (${RETENTION_DAYS} dias)..."
find "$BACKUP_ROOT/db" -name 'sintel_db_*.dump' -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_ROOT/media" -name 'sintel_media_*.tar.gz' -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_ROOT/config" -maxdepth 1 -mindepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} +

echo ">>> [5/5] Verificacion final completada."
echo ">>> Backup completo: ${TIMESTAMP}"
