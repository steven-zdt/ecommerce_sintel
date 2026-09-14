"""
Cliente del MCP oficial de Meta Ads (https://mcp.facebook.com/ads) -- FASE 10
del plan de integracion Meta Business
(Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).

Se llama `mcp_client` y NO `mcp` a proposito: ai_engine pone su raiz al frente
de sys.path (imports "planos": `from auth import ...`), asi que un paquete
llamado `mcp` ensombreceria el SDK oficial del Model Context Protocol, que se
importa justamente como `import mcp`.

Reglas duras (iguales que el resto de ai_engine):
- El LLM NUNCA ve el MCP directamente. Pasa por capabilities/registry.py ->
  tools/registry.py -> Policy Layer (llega en FASE 11-14).
- ai_engine NUNCA toca el ORM de Django. El MCP es un canal aparte hacia Meta.
- El refresh token del MCP vive SOLO en mcp_client/storage.py (volumen montado);
  nunca en logs, ni en el prompt, ni en el estado del Action Graph, ni en Django.
- FASE 10 es SOLO LECTURA: policy.py deniega toda tool de escritura mientras
  MCP_META_ADS_ALLOW_WRITES sea False.
"""
from mcp_client.client import MetaAdsMCPClient, MCPClientError
from mcp_client.policy import classify_mcp_tool
from mcp_client.registry import MCPServerRegistry

__all__ = [
    "MetaAdsMCPClient",
    "MCPClientError",
    "classify_mcp_tool",
    "MCPServerRegistry",
]
