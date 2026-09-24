#!/bin/bash
# =============================================================================
# release_ai.sh -- HARDENING F17/C3 (2026-09-24): snapshot y ROLLBACK de imagenes de produccion (plan sec. 21.2).
# LO EJECUTA EL USUARIO (ventana de despliegue). Nada de esto se ejecuto al escribirlo.
#
# Problema que resuelve: `docker compose build` REEMPLAZA el tag `:prod`; sin copia previa, volver a la version anterior obliga a
# reconstruirla desde git. Aqui cada release deja `:prev` (la anterior) y `:rel-<timestamp>` (etiqueta permanente) + un manifiesto.
#
#   ./deploy/release_ai.sh snapshot      # ANTES de construir/desplegar: etiqueta lo que corre hoy como :prev y :rel-<ts>
#   ./deploy/release_ai.sh list          # releases guardados
#   ./deploy/release_ai.sh rollback adk  # vuelve sintel_ai_adk a :prev (tambien: django | all)
#
# Alcance del rollback (plan 21.2): imagen Docker, prompt/perfiles de agente, registro de tools y config de codigo viajan DENTRO de la
# imagen => volver a :prev los revierte. NO revierte: (a) migraciones ya aplicadas (usar migraciones aditivas; restore.sh si hiciera
# falta), (b) el MODELO de Ollama (ver abajo), (c) el indice RAG (F6: `rollback_to_version` por documento), (d) `.env.production`
# (el snapshot guarda una copia de las banderas NO secretas para poder volver a ellas a mano).
# Modelo: antes de un `ollama pull` que cambie qwen3.5:9b, `docker exec sintel_prod_ollama ollama cp qwen3.5:9b qwen3.5:9b-prev`;
# rollback del modelo = `ollama cp qwen3.5:9b-prev qwen3.5:9b` (o cambiar el tag en LOCAL_MODEL_CHAIN) y re-correr F10.
# =============================================================================
set -euo pipefail
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
BACKUP_ROOT="${SINTEL_BACKUP_ROOT:-/c/Users/Administrator/sintel_backups}"
REL_DIR="$BACKUP_ROOT/releases"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

# servicio -> imagen de produccion
declare -A IMAGES=(
    [sintel_ai_adk]="ecommerce_sintel_ai_adk:prod"
    [django]="ecommerce_sintel:prod-runtime"
    [celery_worker]="ecommerce_sintel_celery_worker:prod-runtime"
    [celery_beat]="ecommerce_sintel_celery_beat:prod-runtime"
)

cmd="${1:-}"
case "$cmd" in
snapshot)
    TS="$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$REL_DIR"
    MANIFEST="$REL_DIR/release_${TS}.json"
    echo "{" > "$MANIFEST"
    echo "  \"timestamp\": \"$TS\"," >> "$MANIFEST"
    echo "  \"git_commit\": \"$(git rev-parse HEAD 2>/dev/null || echo unknown)\"," >> "$MANIFEST"
    echo "  \"images\": {" >> "$MANIFEST"
    first=1
    for svc in "${!IMAGES[@]}"; do
        image="${IMAGES[$svc]}"
        if docker image inspect "$image" >/dev/null 2>&1; then
            id="$(docker image inspect "$image" --format '{{.Id}}')"
            base="${image%%:*}"
            docker tag "$image" "${base}:prev"
            docker tag "$image" "${base}:rel-${TS}"
            [ $first -eq 0 ] && echo "," >> "$MANIFEST"
            printf '    "%s": {"image": "%s", "id": "%s", "tags": ["%s:prev", "%s:rel-%s"]}' "$svc" "$image" "$id" "$base" "$base" "$TS" >> "$MANIFEST"
            first=0
            echo "    $image -> ${base}:prev y ${base}:rel-${TS}"
        else
            echo "    (omitido) $image no existe localmente"
        fi
    done
    echo "" >> "$MANIFEST"
    echo "  }," >> "$MANIFEST"
    # Banderas NO secretas (lista blanca por prefijo; se excluyen TOKEN/SECRET/PASSWORD/KEY) para poder volver a la config anterior.
    FLAGS="$REL_DIR/flags_${TS}.env"
    grep -E '^(AI_|LOG_FORMAT|ADK_|LOCAL_MODEL_CHAIN|EMBEDDING_|OLLAMA_|CANARY_)' .env.production 2>/dev/null \
        | grep -viE 'TOKEN|SECRET|PASSWORD|KEY' > "$FLAGS" || true
    echo "  \"flags_file\": \"$FLAGS\"" >> "$MANIFEST"
    echo "}" >> "$MANIFEST"
    echo ">>> Snapshot listo: $MANIFEST (banderas no secretas en $FLAGS)"
    ;;
list)
    ls -1 "$REL_DIR"/release_*.json 2>/dev/null || echo "No hay releases guardados en $REL_DIR"
    for base in ecommerce_sintel_ai_adk ecommerce_sintel ecommerce_sintel_celery_worker ecommerce_sintel_celery_beat; do
        docker images --format '{{.Repository}}:{{.Tag}}  {{.ID}}  {{.CreatedSince}}' | grep -E "^${base}:(prev|rel-)" || true
    done
    ;;
rollback)
    target="${2:-}"
    case "$target" in
        adk)    services="sintel_ai_adk" ;;
        django) services="django celery_worker celery_beat" ;;
        all)    services="sintel_ai_adk django celery_worker celery_beat" ;;
        *) echo "Uso: $0 rollback adk|django|all" >&2; exit 1 ;;
    esac
    echo "Plan de rollback (imagen actual :prod  ->  :prev):"
    for svc in $services; do
        image="${IMAGES[$svc]}"; base="${image%%:*}"; tag="${image##*:}"
        docker image inspect "${base}:prev" >/dev/null 2>&1 || { echo "ERROR: no existe ${base}:prev (nunca se hizo snapshot). Aborta." >&2; exit 1; }
        echo "   $svc: ${image}  ->  ${base}:prev ($(docker image inspect "${base}:prev" --format '{{.Id}}' | cut -c1-19))"
    done
    echo "AVISO: no revierte migraciones, modelo, indice RAG ni .env.production (ver cabecera)."
    read -r -p "Escribe 'ROLLBACK' para confirmar: " CONFIRM
    [ "$CONFIRM" = "ROLLBACK" ] || { echo "Cancelado."; exit 1; }
    for svc in $services; do
        image="${IMAGES[$svc]}"; base="${image%%:*}"
        docker tag "${base}:prev" "$image"
        $COMPOSE up -d --no-deps --no-build "$svc"
        echo ">>> $svc recreado con ${base}:prev"
    done
    echo ">>> Verifica con ./deploy/healthcheck.sh y prueba un turno de soporte real."
    ;;
*)
    echo "Uso: $0 snapshot | list | rollback adk|django|all" >&2
    exit 1
    ;;
esac
