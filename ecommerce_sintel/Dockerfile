# ═════════════════════════════════════════════════════════════════════════════
# 🛍️  DOCKERFILE — E-Commerce Sintel REST  |  PROYECTO INDEPENDIENTE
# ═════════════════════════════════════════════════════════════════════════════
#
# ⚠️  IMPORTANTE:
#     Este Dockerfile está diseñado ÚNICAMENTE para el proyecto ecommerce_sintel.
#     No debe ser usado para levantar contenedores de otros proyectos.
#     Las imágenes construidas aquí son independientes de secop_system u otros.
#
# Estructura multi-stage:
#   1. Stage "builder"          — Compilación y preparación de dependencias Python
#   2. Stage "frontend-builder" — Compilación del bundle de Vue.js con Vite
#   3. Stage "runtime"          — Imagen final minimizada para producción
#
# ═════════════════════════════════════════════════════════════════════════════

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
# Instala solo las dependencias del proyecto en una imagen temporal.
# Esto evita contaminar la imagen final con herramientas de build.
FROM python:3.13-slim AS builder

WORKDIR /build

# Instalar dependencias del sistema necesarias para compilar paquetes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry y el plugin de exportación (compatible con el nuevo formato de pyproject.toml)
RUN pip install --no-cache-dir poetry poetry-plugin-export

# Copiar solo los archivos de dependencias primero (cache-friendly)
# Copiar pyproject y el lock (si existe) desde la subcarpeta ecommerce_sintel
COPY ecommerce_sintel/pyproject.toml ecommerce_sintel/poetry.lock* ./

# Regenerar el poetry.lock dentro del builder para mantenerlo sincronizado
# con cualquier cambio en pyproject.toml (por ejemplo al añadir dependencias).
# Luego validar que el lockfile está correcto.
RUN poetry lock && poetry check --lock

# Exportar dependencias a requirements.txt (evita tener poetry en producción)
RUN poetry export --without-hashes --format=requirements.txt -o requirements.txt

# Instalar dependencias en un directorio aislado.
# --ignore-installed fuerza la instalación en /install aunque el paquete ya
# exista en la imagen base del builder (e.g. idna viene pre-instalado en
# python:3.13-slim). Sin este flag pip lo omite y el runtime queda sin él.
RUN pip install --no-cache-dir --prefix=/install --ignore-installed -r requirements.txt


# ─── Stage 2: Frontend Builder ───────────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /app
COPY ecommerce_sintel/frontend/package*.json ./
# npm ci (no npm install): build reproducible -- respeta package-lock.json exacto
# y falla si esta desincronizado, en vez de mutarlo silenciosamente.
RUN npm ci
COPY ecommerce_sintel/frontend/ ./
RUN npm run build


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
# Imagen final mínima solo con lo necesario para correr la app.
# Esta imagen es independiente y NO comparte cambios con otros proyectos.
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

WORKDIR /code

# Solo instalar libpq-dev runtime (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias instaladas del builder
COPY --from=builder /install /usr/local

# Copiar el código del proyecto (desde la subcarpeta ecommerce_sintel)
COPY ecommerce_sintel/ /code/

# Copiar bundle de frontend generado (vite.config.js outDir: 'dist' → /app/dist)
COPY --from=frontend-builder /app/dist /code/static/panel/js/bundle

# Crear directorios de volumen con ownership correcto ANTES de switch de usuario.
# Si Docker monta un volumen en un directorio que ya existe en la imagen con los
# permisos correctos, el volumen vacio hereda esos permisos. Sin esto, el volumen
# es creado por root y el usuario sintel no puede escribir en el.
RUN mkdir -p /code/staticfiles /code/media

# Crear usuario sin privilegios para mayor seguridad
RUN addgroup --system sintel && adduser --system --ingroup sintel sintel
RUN chown -R sintel:sintel /code
USER sintel

# Puerto expuesto (Daphne ASGI)
EXPOSE 8000

# Entrypoint: ejecuta setup (migrations, collectstatic) y luego el comando
# pasado como argumento. CMD define el comando por defecto para el servicio
# django; los workers sobreescriben CMD via docker-compose 'command:'.
COPY --chown=sintel:sintel ecommerce_sintel/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "ecommerce.asgi:application"]

# ═════════════════════════════════════════════════════════════════════════════
# ✅ FIN DE DOCKERFILE — E-Commerce Sintel REST
#
# Esta imagen es completamente independiente.
# No comparte capas, volúmenes ni networks con otros proyectos como secop_system.
# ═════════════════════════════════════════════════════════════════════════════
