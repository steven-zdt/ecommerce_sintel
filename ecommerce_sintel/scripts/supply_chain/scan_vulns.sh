#!/bin/bash
# HARDENING F16/C3 -- escaneo de vulnerabilidades (plan sec. 20.2): Trivy (imagenes), pip-audit (Python), Bandit (codigo).
# LO EJECUTA EL USUARIO A MANO (regla del proyecto: el asistente no ejecuta escaneos ni pruebas). Solo lectura; los informes van a
# scripts/supply_chain/_out/vuln/. Las excepciones JUSTIFICADAS se registran en docs/security/VULN_EXCEPTIONS.md (con fecha de revision).
#
#   ./scripts/supply_chain/scan_vulns.sh            # todo
#   ./scripts/supply_chain/scan_vulns.sh images     # solo Trivy sobre imagenes
#   ./scripts/supply_chain/scan_vulns.sh python     # solo pip-audit (lock del ADK y del sistema OLD)
#   ./scripts/supply_chain/scan_vulns.sh code       # solo Bandit
set -uo pipefail
export MSYS_NO_PATHCONV=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/_out/vuln"
mkdir -p "$OUT"
WHAT="${1:-all}"
STATUS=0

if [ "$WHAT" = "all" ] || [ "$WHAT" = "images" ]; then
    echo ">>> Trivy (imagenes; HIGH/CRITICAL con fix disponible)"
    for image in ecommerce_sintel_ai_adk:prod ollama/ollama:0.30.10 ecommerce_sintel:prod-runtime ecommerce_sintel_celery_worker:prod-runtime \
                 redis:7.2-alpine pgvector/pgvector:pg16 nginx:1.26-alpine; do
        name="$(echo "$image" | tr '/:' '__')"
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro -v trivy-cache:/root/.cache aquasec/trivy:latest image \
            --severity HIGH,CRITICAL --ignore-unfixed --format json --output /dev/stdout "$image" > "$OUT/trivy_${name}.json" || STATUS=1
        echo "    $image -> $OUT/trivy_${name}.json"
    done
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "python" ]; then
    echo ">>> pip-audit (contra los lock files; no instala nada del proyecto)"
    docker run --rm -v "$ROOT:/src:ro" python:3.12-slim sh -c \
        "pip install -q pip-audit && pip-audit -r /src/ai_engine_adk/requirements.lock.txt --progress-spinner off -f json" \
        > "$OUT/pip_audit_adk.json" || STATUS=1
    docker run --rm -v "$ROOT:/src:ro" python:3.12-slim sh -c \
        "pip install -q pip-audit && pip-audit -r /src/ai_engine/requirements.lock.txt --progress-spinner off -f json" \
        > "$OUT/pip_audit_ai_engine.json" || STATUS=1
    echo "    informes en $OUT/pip_audit_*.json (Django/poetry: exportar con 'poetry export' y auditar aparte)"
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "code" ]; then
    echo ">>> Bandit (codigo propio; excluye tests, migraciones, node_modules)"
    if command -v bandit >/dev/null 2>&1; then
        bandit -r "$ROOT/ai_engine_adk" "$ROOT/ai_engine" "$ROOT/support" "$ROOT/customer_memory" "$ROOT/ai_knowledge" "$ROOT/security" \
            -x '*/tests/*,*/migrations/*,*/test_*.py,*/eval/*' -ll -f json -o "$OUT/bandit.json" || STATUS=1
        echo "    -> $OUT/bandit.json (solo severidad media o mayor)"
    else
        echo "    bandit no esta instalado (pip install bandit)"
    fi
fi

echo ">>> Revisa los informes y registra cada hallazgo aceptado en docs/security/VULN_EXCEPTIONS.md (motivo, mitigacion, fecha de revision)."
exit $STATUS
