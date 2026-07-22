#!/bin/bash
# =============================================================================
# healthcheck.sh -- Estado del stack de produccion Sintel
# Ver docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md, Fase 18 y 22.
#
# Uso: ./deploy/healthcheck.sh
# Solo lee estado, no modifica nada.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Estado de contenedores (docker compose ps) ==="
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=== Uso de recursos (docker stats, snapshot) ==="
docker stats --no-stream sintel_prod_redis sintel_prod_db sintel_prod_django \
    sintel_prod_celery_worker sintel_prod_celery_beat sintel_prod_nginx sintel_prod_cloudflared 2>/dev/null

echo ""
echo "=== Health interno de Django (via el contenedor, no expuesto al host) ==="
docker exec sintel_prod_django curl -sf http://localhost:8000/api/v1/health/ && echo " -> OK" || echo " -> FALLO"

echo ""
echo "=== Ultimas 10 lineas de logs de Nginx (acceso) ==="
tail -n 10 "$PROJECT_DIR/logs/nginx/access.log" 2>/dev/null || echo "(sin actividad todavia)"

echo ""
echo "=== Ultimas 10 lineas de logs de Nginx (error) ==="
tail -n 10 "$PROJECT_DIR/logs/nginx/error.log" 2>/dev/null || echo "(sin errores registrados)"

echo ""
echo "=== Estado del tunel Cloudflare ==="
cloudflared tunnel info sintel-production 2>&1 || echo "(no se pudo consultar -- revisar 'docker logs sintel_prod_cloudflared')"
