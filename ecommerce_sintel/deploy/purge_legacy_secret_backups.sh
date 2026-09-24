#!/bin/bash
# =============================================================================
# purge_legacy_secret_backups.sh -- HARDENING F15 (2026-09-24)
#
# Los backups ANTERIORES a F15 guardaron en claro, dentro de $BACKUP_ROOT/config/<timestamp>/, el archivo .env.production, la carpeta
# certs/ (origin.key) y la carpeta cloudflared/ (credenciales del tunel). Este script las ELIMINA de esos backups viejos (deja intactos
# compose/nginx, los dumps y la media).
#
# Uso:
#   ./deploy/purge_legacy_secret_backups.sh          # DRY-RUN: solo lista lo que borraria
#   ./deploy/purge_legacy_secret_backups.sh --yes    # borra
#
# ANTES de usar --yes: confirma que .env.production, origin.key y las credenciales del tunel estan guardados en tu gestor de
# contrasenas (esta es la unica copia "de respaldo" que existia). El borrado en NTFS no es un borrado seguro: si sospechas del host,
# ademas rota las credenciales (ver ai_engine_adk/.AGENT/HARDENING_F15_SECRETS_AUDIT_2026-09-24.md, seccion 3).
# =============================================================================
set -euo pipefail
export MSYS_NO_PATHCONV=1

BACKUP_ROOT="${SINTEL_BACKUP_ROOT:-/c/Users/Administrator/sintel_backups}"
APPLY="no"
[ "${1:-}" = "--yes" ] && APPLY="yes"

count=0
for dir in "$BACKUP_ROOT"/config/*/; do
    [ -d "$dir" ] || continue
    for target in "$dir.env.production" "$dir/certs" "$dir/cloudflared"; do
        if [ -e "$target" ]; then
            count=$((count + 1))
            if [ "$APPLY" = "yes" ]; then
                rm -rf "$target"
                echo "BORRADO  $target"
            else
                echo "(dry-run) borraria $target"
            fi
        fi
    done
done

if [ "$count" -eq 0 ]; then
    echo "No hay secretos en claro en $BACKUP_ROOT/config/. Nada que hacer."
elif [ "$APPLY" != "yes" ]; then
    echo ""
    echo "$count elementos con secretos en claro. Vuelve a ejecutar con --yes cuando tus secretos ya esten en el gestor de contrasenas."
fi
