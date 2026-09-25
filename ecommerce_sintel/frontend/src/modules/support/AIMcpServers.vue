<template>
  <div class="card mt-3">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-1">
        <h6 class="mb-0">Servidores MCP (herramientas y contexto)</h6>
        <button class="btn btn-sm btn-outline-primary" @click="openCreate">+ Nuevo servidor MCP</button>
      </div>
      <p class="text-muted small mb-2">
        MCP es una integracion <strong>independiente</strong> de los proveedores de IA: sirve Tools/Contexto, no reemplaza al modelo del chat.
        Aqui solo se registra y se prueba el handshake; la API key se guarda cifrada y nunca se muestra.
      </p>

      <div v-if="!store.mcpServers.length && !editing" class="text-muted small">Sin servidores MCP registrados.</div>

      <div v-for="s in store.mcpServers" :key="s.uuid" class="border rounded px-2 py-2 mb-2">
        <div class="d-flex justify-content-between align-items-start gap-2">
          <div>
            <strong>{{ s.name }}</strong>
            <span class="badge ms-2" :class="statusClass(s.status)">{{ s.status }}</span>
            <div class="text-muted small text-break">{{ s.server_url }} · {{ s.transport }}
              <span v-if="s.has_api_key"> · <i class="bi bi-key-fill"></i> key configurada</span>
            </div>
            <div class="small" v-if="s.last_checked_at">
              {{ s.tools_count }} tool(s) · {{ Object.keys(s.capabilities || {}).join(', ') || 'sin capacidades declaradas' }}
              <span class="text-muted">({{ formatTime(s.last_checked_at) }}<span v-if="s.last_latency_ms"> · {{ s.last_latency_ms }}ms</span>)</span>
            </div>
            <div class="small text-danger" v-if="s.last_error">{{ s.last_error }}</div>
          </div>
          <div class="d-flex gap-2 flex-shrink-0">
            <button class="btn btn-sm btn-outline-secondary" :disabled="testingUuid === s.uuid" @click="test(s)">
              <span v-if="testingUuid === s.uuid" class="spinner-border spinner-border-sm"></span>
              <template v-else>Probar</template>
            </button>
            <button class="btn btn-sm btn-outline-secondary" @click="openEdit(s)">Editar</button>
            <button v-if="confirmingDelete !== s.uuid" class="btn btn-sm btn-outline-danger" @click="confirmingDelete = s.uuid">Eliminar</button>
          </div>
        </div>
        <div v-if="confirmingDelete === s.uuid" class="bg-danger-subtle rounded p-2 mt-2 d-flex justify-content-between align-items-center">
          <span class="small">¿Eliminar "{{ s.name }}"?</span>
          <span class="d-flex gap-2">
            <button class="btn btn-sm btn-outline-secondary" @click="confirmingDelete = null">Cancelar</button>
            <button class="btn btn-sm btn-danger" @click="remove(s)">Confirmar</button>
          </span>
        </div>
      </div>

      <form v-if="editing" class="border rounded p-2 mt-2" @submit.prevent="submit">
        <h6 class="small text-uppercase text-muted">{{ editing.uuid ? 'Editar servidor MCP' : 'Nuevo servidor MCP' }}</h6>
        <div class="row g-2">
          <div class="col-md-4">
            <label class="form-label small mb-0">Nombre</label>
            <input v-model="form.name" class="form-control form-control-sm" required />
          </div>
          <div class="col-md-8">
            <label class="form-label small mb-0">URL del servidor</label>
            <input v-model="form.server_url" class="form-control form-control-sm" required placeholder="http://sintel_mcp:8000/mcp" />
            <div v-if="isLoopbackUrl" class="text-danger small">
              <code>localhost</code> dentro de Docker es el propio contenedor: usa <code>http://host.docker.internal:PUERTO</code> o el nombre del servicio.
            </div>
          </div>
          <div class="col-md-4">
            <label class="form-label small mb-0">Transporte</label>
            <select v-model="form.transport" class="form-select form-select-sm">
              <option value="streamable-http">Streamable HTTP</option>
              <option value="sse">SSE (legado, sin prueba)</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small mb-0">Autenticacion</label>
            <select v-model="form.auth_type" class="form-select form-select-sm">
              <option value="none">Sin autenticacion</option>
              <option value="bearer">Bearer</option>
              <option value="header">Cabecera personalizada</option>
            </select>
          </div>
          <div class="col-md-4" v-if="form.auth_type === 'header'">
            <label class="form-label small mb-0">Cabecera</label>
            <input v-model="form.api_key_header" class="form-control form-control-sm" placeholder="x-api-key" />
          </div>
          <div class="col-md-12" v-if="form.auth_type !== 'none'">
            <label class="form-label small mb-0">
              API key <span v-if="editing.uuid && editing.has_api_key" class="text-muted">(configurada — vacio = no cambiarla)</span>
            </label>
            <input v-model="form.api_key" type="password" class="form-control form-control-sm" autocomplete="new-password" />
          </div>
          <div class="col-md-6 form-check form-switch ms-2 mt-2">
            <input v-model="form.verify_tls" type="checkbox" class="form-check-input" id="mcp-tls" />
            <label class="form-check-label small" for="mcp-tls">Verificar certificado TLS</label>
          </div>
          <div class="col-md-5 form-check form-switch mt-2">
            <input v-model="form.is_active" type="checkbox" class="form-check-input" id="mcp-active" />
            <label class="form-check-label small" for="mcp-active">Activo</label>
          </div>
        </div>
        <div class="d-flex justify-content-end gap-2 mt-2">
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="editing = null">Cancelar</button>
          <button type="submit" class="btn btn-sm btn-primary" :disabled="store.actionLoading">Guardar</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useAIProviderAdminStore } from '@/store/aiProviderAdmin';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const store = useAIProviderAdminStore();
const toast = useToast();
const { handleError } = useErrorHandler();

const editing = ref(null);
const testingUuid = ref(null);
const confirmingDelete = ref(null);
const form = reactive({
  name: '', server_url: '', transport: 'streamable-http', auth_type: 'none', api_key_header: '', api_key: '', verify_tls: true, is_active: true,
});

onMounted(() => store.fetchMcpServers());

const isLoopbackUrl = computed(() => {
  try {
    const host = new URL(form.server_url).hostname.replace(/^\[|\]$/g, '').toLowerCase();
    return ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(host);
  } catch { return false; }
});

function fill(s) {
  form.name = s?.name || '';
  form.server_url = s?.server_url || '';
  form.transport = s?.transport || 'streamable-http';
  form.auth_type = s?.auth_type || 'none';
  form.api_key_header = s?.api_key_header || '';
  form.api_key = '';
  form.verify_tls = s?.verify_tls ?? true;
  form.is_active = s?.is_active ?? true;
}
function openCreate() { fill(null); editing.value = {}; }
function openEdit(s) { fill(s); editing.value = s; }

const statusClass = (status) => ({
  HEALTHY: 'bg-success', DEGRADED: 'bg-warning text-dark', UNAVAILABLE: 'bg-danger', MISCONFIGURED: 'bg-danger', DISABLED: 'bg-secondary',
}[status] || 'bg-secondary');

function formatTime(iso) {
  try { return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return ''; }
}

async function submit() {
  const payload = { ...form };
  if (payload.auth_type === 'none') { delete payload.api_key; delete payload.api_key_header; }
  const res = await store.saveMcpServer(editing.value?.uuid || null, payload);
  if (res.ok) {
    toast.success('Servidor MCP guardado.');
    editing.value = null;
  } else {
    handleError(res.error, 'No se pudo guardar el servidor MCP.');
  }
}

async function test(s) {
  testingUuid.value = s.uuid;
  const res = await store.testMcpServer(s.uuid);
  testingUuid.value = null;
  if (!res.ok) return handleError(res.error, 'No se pudo probar el servidor MCP.');
  if (res.data.ok) toast.success(`Handshake MCP correcto: ${res.data.tools_count} tool(s).`);
  else toast.error(`Prueba fallida: ${res.data.message || res.data.error_code}`);
}

async function remove(s) {
  const res = await store.deleteMcpServer(s.uuid);
  confirmingDelete.value = null;
  if (res.ok) toast.success('Servidor MCP eliminado.');
  else handleError(res.error, 'No se pudo eliminar el servidor MCP.');
}
</script>
