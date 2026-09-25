#!/usr/bin/env bash
# Verificacion de lo escrito y NO ejecutado (hardening F21/F22 y PLAN_LLMDINAMICO). Solo DESARROLLO (regla 0-DEV-FIRST): nunca sintel_prod_*.
# Lo corre el usuario a mano; ningun agente lo ejecuta. Uso:  bash scripts/verify/run_pending_tests.sh [paso]
#   pasos: migrate | django | adk | copies | all (por defecto: all)
# Ejecutar desde la raiz del proyecto (donde esta docker-compose.yml). Cada paso se detiene al primer fallo.
set -euo pipefail

DJANGO=ecommerce_sintel_django
ADK=ecommerce_sintel_ai_adk
STEP="${1:-all}"
PYTEST_OPTS="--no-cov -p no:cacheprovider -q"   # --no-cov: el umbral de cobertura global (25%) falla en corridas parciales

step_migrate() {
  echo "== 1. Migracion ai_provider 0007 =="
  # Compara modelo vs migraciones (la 0007 se escribio a mano): debe decir "No changes detected".
  docker exec "$DJANGO" python manage.py makemigrations --check --dry-run ai_provider
  docker exec "$DJANGO" python manage.py migrate ai_provider
  docker exec "$DJANGO" python manage.py showmigrations ai_provider
}

step_django() {
  echo "== 2. Tests del lado Django (ai_provider registry + ai_editor F22) =="
  # Los archivos tests_*.py no entran por el patron python_files de pytest.ini: se pasan por ruta explicita.
  docker exec "$DJANGO" python -m pytest $PYTEST_OPTS \
    ai_provider/tests.py \
    ai_provider/tests_providers.py \
    ai_provider/tests_url_guard.py \
    ai_provider/tests_revisions.py \
    ai_provider/tests_activation.py \
    ai_editor/approval/tests_security_gate.py
  # Regresion cercana: el chat de soporte usa is_ai_mode_active (F21 agrego AI_GLOBAL_ENABLED) y el gateway del panel admin.
  docker exec "$DJANGO" python -m pytest $PYTEST_OPTS support/test_handoff_f18.py
}

step_adk() {
  echo "== 3. Tests del ADK (F21 kill switches + registry) =="
  # El ADK NO tiene bind-mount: hay que reconstruir la imagen para que lleve el codigo nuevo.
  docker compose build sintel_ai_adk
  docker compose up -d --force-recreate sintel_ai_adk
  docker exec "$ADK" python -m pytest $PYTEST_OPTS \
    tests/test_kill_switches.py \
    tests/test_provider_registry.py \
    tests/test_model_runtime.py \
    tests/test_tool_hardening.py \
    tests/test_permissions.py \
    tests/test_output_guard.py
  # Suite completa del ADK (regresion; tarda ~ varios minutos):
  # docker exec "$ADK" python -m pytest $PYTEST_OPTS tests
}

step_copies() {
  echo "== 4. Las dos copias del guard SSRF no deben divergir =="
  python - <<'PY'
from pathlib import Path
def body(p):
    t = Path(p).read_text(encoding="utf-8")
    return t[t.index("import ipaddress"):]
a, b = body("ai_engine_adk/url_guard.py"), body("ai_provider/services/url_guard.py")
print("OK: iguales" if a == b else "FALLA: divergen")
raise SystemExit(0 if a == b else 1)
PY
}

case "$STEP" in
  migrate) step_migrate ;;
  django)  step_django ;;
  adk)     step_adk ;;
  copies)  step_copies ;;
  all)     step_migrate; step_django; step_adk; step_copies ;;
  *) echo "paso desconocido: $STEP"; exit 2 ;;
esac
echo "Listo. Los E2E, el fallback real y la prueba visual de /panel/soporte/ia-config siguen siendo manuales (ver el reporte)."
