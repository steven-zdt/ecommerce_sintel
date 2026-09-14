FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY ai_engine_adk/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modulos REALES compartidos de ai_engine/ (reuso, no duplicacion de
# codigo fuente -- ver AUDITORIA/ADK_CUTOVER_PLAN.md) -- SOLO los que no
# dependen de LangChain/LangGraph. NUNCA copiar action_graph.py/
# llm_factory.py/redis_checkpointer.py/main.py/gateway.py aqui: dependen
# de langchain-core/langgraph, incompatible con litellm en este venv
# (conflicto real de versiones de `openai`, confirmado en ADK-10).
COPY ai_engine/tools/ ./tools/
COPY ai_engine/agents/ ./agents/
COPY ai_engine/capabilities/ ./capabilities/
COPY ai_engine/auth.py .
COPY ai_engine/retrievers.py .
COPY ai_engine/routing.py .
COPY ai_engine/model_chain.py .
COPY ai_engine/cost_control.py .
COPY ai_engine/config.py .
COPY ai_engine/observability.py .

COPY ai_engine_adk/ .

EXPOSE 8101

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8101"]
