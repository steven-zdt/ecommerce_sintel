#!/bin/bash
# =============================================================================
# deploy.sh -- Despliegue/actualizacion del stack de produccion Sintel
# Ver docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md, Fase 22.
#
# Uso: ./deploy/deploy.sh
# Es seguro re-ejecutar (idempotente): reconstruye imagenes, aplica
# migraciones (via entrypoint.sh de cada contenedor django), no duplica el
# superusuario si ya existe.
#
# REGLA OPERATIVA (2026-07-31, confirmada por el usuario): la imagen de
# produccion NUNCA se edita directamente -- todo cambio se hace en el
# codigo de desarrollo (ecommerce_sintel_* containers) y se sincroniza a
# produccion UNICAMENTE via este script. El build usa --no-cache a
# proposito (solo el servicio `django`, el unico con `build:` en
# docker-compose.prod.yml -- celery_worker/celery_beat reusan la MISMA
# imagen `ecommerce_sintel:prod-runtime`, se actualizan solos al recrearse)
# para garantizar que la imagen de produccion siempre refleja el codigo
# fuente actual, sin arriesgar una capa de Docker cacheada desactualizada.
#
# 2026-08-08: `ecommerce_sintel:prod-runtime` es un tag EXCLUSIVO de
# produccion (antes se llamaba igual que la imagen de dev,
# `ecommerce_sintel:runtime` -- un build cualquiera del lado de dev
# sobreescribia silenciosamente lo que produccion iba a correr en su
# proximo restart; hallazgo real de auditoria). No renombrar de vuelta.
# =============================================================================
set -euo pipefail
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

if [ ! -f ".env.production" ]; then
    echo "ERROR: .env.production no existe (ver Fase 16 del roadmap). Aborta." >&2
    exit 1
fi

echo ">>> [1/5] Construyendo imagenes (--no-cache, solo django -- ver nota arriba)..."
$COMPOSE build --no-cache django

echo ">>> [2/5] Levantando el stack..."
$COMPOSE up -d

echo ">>> [3/5] Esperando a que django este healthy..."
for i in $(seq 1 60); do
    STATUS="$(docker inspect --format='{{.State.Health.Status}}' sintel_prod_django 2>/dev/null || echo 'starting')"
    if [ "$STATUS" = "healthy" ]; then
        echo "    django healthy"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: django no quedo healthy despues de 5 minutos. Revisar 'docker logs sintel_prod_django'." >&2
        exit 1
    fi
    sleep 5
done

echo ">>> [4/5] Creando superusuario (si no existe)..."
SU_OUTPUT="$(docker exec sintel_prod_django python manage.py createsuperuser --noinput 2>&1)" && SU_EXIT=0 || SU_EXIT=$?
if [ "$SU_EXIT" -eq 0 ]; then
    echo "    superusuario creado"
elif echo "$SU_OUTPUT" | grep -qi "already"; then
    echo "    superusuario ya existia, se omite"
else
    echo "    AVISO: no se pudo crear el superusuario: $SU_OUTPUT" >&2
fi

echo ">>> [5/5] Estado final:"
$COMPOSE ps

echo ""
echo ">>> Despliegue completo. Verificar con ./deploy/healthcheck.sh"
