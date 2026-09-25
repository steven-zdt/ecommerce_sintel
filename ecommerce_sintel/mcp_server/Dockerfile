# SINTEL E-Commerce MCP Server -- imagen PROPIA (no reusa Django, Celery ni ai_engine_adk). Build desde la raiz del repo:
#   docker build -f mcp_server/Dockerfile -t sintel_ecommerce_mcp:latest .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY mcp_server/requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install -r /tmp/requirements.lock.txt && rm /tmp/requirements.lock.txt
COPY mcp_server/ /app/mcp_server/
# No root, sin shell de login, sin home: el proceso no puede escribir en la imagen (compose la monta read-only).
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin mcp
USER 10001
EXPOSE 8200
# El proceso vivo = healthy: /mcp-health responde 503 si Django esta caido (degradado), y eso NO debe reiniciar el contenedor.
HEALTHCHECK --interval=30s --timeout=6s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request,urllib.error,sys\ntry:\n urllib.request.urlopen('http://127.0.0.1:8200/mcp-health', timeout=4)\nexcept urllib.error.HTTPError as e:\n sys.exit(0 if e.code == 503 else 1)\nexcept Exception:\n sys.exit(1)"]
CMD ["python", "-m", "mcp_server"]
