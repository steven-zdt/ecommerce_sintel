import useApi from '@/composables/useApi';

// Tokens personales del servidor MCP del admin autenticado (backend: dashboard/api/mcp_views.py).
export const mcpTokenService = {
  list() {
    return useApi().get('dashboard/mcp-tokens/').then(r => r.data);
  },
  create(name, days) {
    return useApi().post('dashboard/mcp-tokens/', { name, days }).then(r => r.data);
  },
  revoke(uuid) {
    return useApi().delete(`dashboard/mcp-tokens/${uuid}/`).then(r => r.data);
  },
};
