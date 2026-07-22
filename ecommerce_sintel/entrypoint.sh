#!/bin/sh
set -e

# Solo el servicio web (daphne) ejecuta migraciones y collectstatic.
# Los workers de Celery arrancan directamente; docker-compose ya garantiza
# que la BD esta lista via depends_on + healthcheck antes de iniciar workers.
if [ "$1" = "daphne" ]; then
    echo ">>> Aplicando migraciones..."
    python manage.py migrate --noinput

    echo ">>> Recopilando archivos estáticos (limpiando previos)..."
    python manage.py collectstatic --noinput --clear --verbosity 1
    echo ">>> Archivos estáticos recopilados correctamente."

    # DEV_RELOAD=true activa watchmedo auto-restart con polling (stat-based).
    # Necesario porque inotify no funciona en volúmenes montados desde Windows/WSL2.
    # Daphne no tiene auto-reload incorporado; sin esto cada cambio de archivo .py
    # requiere un docker restart manual para que el servidor cargue el nuevo código.
    if [ "${DEV_RELOAD:-false}" = "true" ]; then
        echo ">>> DEV_RELOAD activo: envolviendo Daphne con watchmedo (force-polling cada 2s)..."
        exec watchmedo auto-restart \
            --patterns="*.py" \
            --recursive \
            --debug-force-polling \
            --interval=2 \
            -- "$@"
    fi
fi

echo ">>> Iniciando: $@"
exec "$@"
