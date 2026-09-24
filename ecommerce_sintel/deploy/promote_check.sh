#!/bin/bash
# =============================================================================
# promote_check.sh -- HARDENING F17/C4 (2026-09-24): puerta previa a promover a produccion (DEV -> STAGING -> CANARY -> PRODUCCION).
# LO EJECUTA EL USUARIO en el equipo de desarrollo, ANTES de ./deploy/deploy.sh. Solo lectura: no despliega, no toca contenedores, no
# imprime valores de secretos (solo nombres de variables). Sale con 1 si algun requisito automatico falla.
#
#   ./deploy/promote_check.sh --reports l1.json [--reports l1_django.json] [--reports live.json]
#
# STAGING = el stack de DESARROLLO (docker-compose.yml, imagenes construidas desde el mismo arbol) con las MISMAS banderas que produccion:
# el requisito 5 compara los NOMBRES de banderas AI_*/LOG_FORMAT entre .env y .env.production (incidente del 503 por banderas desincronizadas).
# =============================================================================
set -uo pipefail
export MSYS_NO_PATHCONV=1
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
PY="$(command -v python3 || command -v python)"
FAILS=0
ok()   { echo "  [OK]   $*"; }
fail() { echo "  [FALLA] $*"; FAILS=$((FAILS + 1)); }
warn() { echo "  [AVISO] $*"; }

REPORTS=()
while [ $# -gt 0 ]; do
    case "$1" in --reports) REPORTS+=("$2"); shift 2 ;; *) echo "argumento desconocido: $1" >&2; exit 2 ;; esac
done

echo "1. Git"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then warn "hay cambios sin commitear en archivos rastreados (se desplegaria el arbol de trabajo, no un commit)"; else ok "arbol limpio"; fi
if [ "$(git rev-parse HEAD)" = "$(git rev-parse '@{u}' 2>/dev/null || echo none)" ]; then ok "HEAD publicado en el remoto"; else warn "HEAD no coincide con su upstream (hacer push)"; fi

echo "2. Benchmark F10 (regression gate)"
if [ ${#REPORTS[@]} -eq 0 ]; then
    fail "sin reportes: correr el benchmark F10 y pasar --reports (el plan sec. 14.2 lo exige ante cambio de modelo/prompt/agente/tool/RAG/embedding/memoria)"
else
    args=(); for r in "${REPORTS[@]}"; do args+=(--report "$r"); done
    if "$PY" ai_engine_adk/eval/gate.py "${args[@]}" >/tmp/promote_gate.txt 2>&1; then ok "gate F10 OK"; else fail "gate F10: $(tr '\n' ' ' < /tmp/promote_gate.txt | cut -c1-300)"; fi
fi

echo "3. Secretos"
if "$PY" scripts/security/scan_secrets.py --tree >/tmp/promote_secrets.txt 2>&1; then ok "sin secretos en los archivos rastreados"; else fail "posibles secretos: $(tail -3 /tmp/promote_secrets.txt | tr '\n' ' ')"; fi

echo "4. Supply chain (manifest de referencia)"
if [ -f docs/supply_chain/manifest.json ]; then
    if "$PY" scripts/supply_chain/collect_versions.py --verify docs/supply_chain/manifest.json >/tmp/promote_sc.txt 2>&1; then ok "versiones = manifest"; else fail "deriva de versiones: $(head -3 /tmp/promote_sc.txt | tr '\n' ' ')"; fi
else
    warn "no existe docs/supply_chain/manifest.json (F16: generar y versionar la referencia de produccion)"
fi

echo "5. Banderas sincronizadas dev/prod (solo nombres)"
if [ -f .env ] && [ -f .env.production ]; then
    names() { grep -E '^(AI_|LOG_FORMAT|ADK_|CANARY_)' "$1" | sed 's/=.*//' | sort -u; }
    only_dev="$(comm -23 <(names .env) <(names .env.production) | tr '\n' ' ')"
    only_prod="$(comm -13 <(names .env) <(names .env.production) | tr '\n' ' ')"
    [ -z "$only_dev" ] && ok "toda bandera de dev existe en prod" || fail "banderas SOLO en .env (replicar en .env.production): $only_dev"
    [ -z "$only_prod" ] && ok "toda bandera de prod existe en dev" || warn "banderas solo en .env.production: $only_prod"
else
    warn "falta .env o .env.production en este equipo"
fi

echo "6. Checklist manual (confirmalo tu antes de seguir)"
echo "   [ ] Snapshot:  ./deploy/release_ai.sh snapshot   (deja :prev para rollback)"
echo "   [ ] STAGING:   stack de dev reconstruido con este arbol y humo manual del widget/panel OK"
echo "   [ ] CANARY:    docker-compose.canary.yml levantado; empezar con AI_CANARY_USER_EMAILS (internos) y AI_CANARY_PERCENT=0"
echo "   [ ] Medir:     python manage.py ai_canary_report --hours 24  (HOLD / PROCEED / ROLLBACK); subir 5 -> 25 -> 50 -> 100"
echo "   [ ] Rollback:  probado en dev al menos una vez (./deploy/release_ai.sh rollback adk)"

echo ""
if [ $FAILS -gt 0 ]; then echo "PROMOCION BLOQUEADA: $FAILS requisito(s) automatico(s) fallan."; exit 1; fi
echo "Requisitos automaticos OK. Continua con la checklist manual."
