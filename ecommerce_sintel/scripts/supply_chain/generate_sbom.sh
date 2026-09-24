#!/bin/bash
# HARDENING F16/C2 -- SBOM (CycloneDX JSON) de las imagenes del plan (sec. 20.1): ai_engine_adk, ollama, django, celery.
# LO EJECUTA EL USUARIO A MANO. Usa syft (anchore/syft) en un contenedor efimero con acceso de LECTURA al socket de Docker; no ejecuta
# nada dentro de las imagenes ni toca contenedores en marcha. Descarga la imagen de syft la primera vez.
#
#   ./scripts/supply_chain/generate_sbom.sh                # imagenes de PRODUCCION (tags prod/prod-runtime)
#   ./scripts/supply_chain/generate_sbom.sh dev            # imagenes de desarrollo
#
# Salida: scripts/supply_chain/_out/sbom/<imagen>.cdx.json (no se versiona: son artefactos de cada release; guardar el de cada despliegue).
set -euo pipefail
export MSYS_NO_PATHCONV=1
MODE="${1:-prod}"
OUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_out/sbom"
mkdir -p "$OUT_DIR"

if [ "$MODE" = "dev" ]; then
    IMAGES="ecommerce_sintel_ai_adk:latest ollama/ollama:0.30.10 ecommerce_sintel:runtime ecommerce_sintel_celery_worker:runtime"
else
    IMAGES="ecommerce_sintel_ai_adk:prod ollama/ollama:0.30.10 ecommerce_sintel:prod-runtime ecommerce_sintel_celery_worker:prod-runtime ecommerce_sintel_celery_beat:prod-runtime"
fi

for image in $IMAGES; do
    name="$(echo "$image" | tr '/:' '__')"
    echo ">>> SBOM de $image -> $OUT_DIR/${name}.cdx.json"
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro anchore/syft:latest "$image" -o cyclonedx-json > "$OUT_DIR/${name}.cdx.json"
done
echo ">>> Listo. Compara entre releases con: diff <(jq -r '.components[]|.name+\"@\"+.version' viejo.json|sort) <(jq -r ... nuevo.json|sort)"
