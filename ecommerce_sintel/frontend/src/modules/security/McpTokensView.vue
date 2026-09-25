<script setup>
import { computed, onMounted, ref } from 'vue';
import { mcpTokenService } from '@/services/security/mcpTokenService';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const toast = useToast();
const { handleError } = useErrorHandler();

const tokens = ref([]);
const loading = ref(false);
const saving = ref(false);
const name = ref('');
const days = ref(30);
const newToken = ref(null); // { name, token } visible UNA sola vez
const confirmingRevoke = ref(null);

const activeCount = computed(() => tokens.value.filter(t => t.is_active).length);
const mcpUrl = `${window.location.origin}/mcp`;

async function load() {
  loading.value = true;
  try {
    tokens.value = await mcpTokenService.list();
  } catch (e) {
    handleError(e, 'No se pudieron cargar los tokens MCP.');
  } finally {
    loading.value = false;
  }
}

async function create() {
  saving.value = true;
  try {
    const res = await mcpTokenService.create(name.value.trim(), Number(days.value));
    newToken.value = { name: res.name, token: res.token };
    name.value = '';
    await load();
  } catch (e) {
    handleError(e, 'No se pudo crear el token.');
  } finally {
    saving.value = false;
  }
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(newToken.value.token);
    toast.success('Token copiado.');
  } catch {
    toast.error('No se pudo copiar: seleccionalo y copialo a mano.');
  }
}

async function revoke(t) {
  try {
    await mcpTokenService.revoke(t.uuid);
    toast.success('Token revocado.');
    confirmingRevoke.value = null;
    await load();
  } catch (e) {
    handleError(e, 'No se pudo revocar el token.');
  }
}

function fmt(v) {
  return v ? new Date(v).toLocaleString('es-CO') : '—';
}
function state(t) {
  if (t.revoked_at) return { label: 'Revocado', cls: 'bg-secondary' };
  if (!t.is_active) return { label: 'Vencido', cls: 'bg-warning text-dark' };
  return { label: 'Activo', cls: 'bg-success' };
}

onMounted(load);
</script>

<template>
  <div class="container-fluid py-3">
    <h2 class="h4 mb-1">Tokens MCP</h2>
    <p class="text-muted small">
      Credenciales personales para conectar un cliente MCP (por ejemplo un asistente de IA) a la administracion de la tienda.
      El token actua con TUS permisos de administrador, con vigencia limitada, y se muestra una sola vez.
      Endpoint MCP: <code>{{ mcpUrl }}</code> · Activos: {{ activeCount }}
    </p>

    <div v-if="newToken" class="alert alert-warning">
      <strong>Token "{{ newToken.name }}" creado. Guardalo ahora: no se volvera a mostrar.</strong>
      <div class="input-group input-group-sm my-2">
        <input class="form-control font-monospace" :value="newToken.token" readonly @focus="$event.target.select()" />
        <button class="btn btn-outline-secondary" type="button" @click="copyToken">Copiar</button>
      </div>
      <button class="btn btn-sm btn-outline-dark" @click="newToken = null">Ya lo guarde</button>
    </div>

    <form class="card card-body mb-3" @submit.prevent="create">
      <div class="row g-2 align-items-end">
        <div class="col-md-5">
          <label class="form-label small mb-0">Nombre (para identificarlo)</label>
          <input v-model="name" class="form-control form-control-sm" maxlength="100" required placeholder="Ej: Claude Desktop - portatil" />
        </div>
        <div class="col-md-3">
          <label class="form-label small mb-0">Vigencia (dias, max. 90)</label>
          <input v-model="days" type="number" min="1" max="90" class="form-control form-control-sm" required />
        </div>
        <div class="col-md-4">
          <button class="btn btn-sm btn-primary" :disabled="saving || !name.trim()">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>Crear token
          </button>
        </div>
      </div>
    </form>

    <div v-if="loading" class="text-center py-4"><span class="spinner-border"></span></div>
    <div v-else-if="!tokens.length" class="text-muted">Aun no has creado tokens.</div>
    <div v-else class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr><th>Nombre</th><th>Prefijo</th><th>Estado</th><th>Creado</th><th>Vence</th><th>Ultimo uso</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="t in tokens" :key="t.uuid">
            <td>{{ t.name }}</td>
            <td><code>{{ t.token_prefix }}…</code></td>
            <td><span class="badge" :class="state(t).cls">{{ state(t).label }}</span></td>
            <td>{{ fmt(t.created_at) }}</td>
            <td>{{ fmt(t.expires_at) }}</td>
            <td>{{ fmt(t.last_used_at) }}</td>
            <td class="text-end">
              <template v-if="t.is_active">
                <button v-if="confirmingRevoke !== t.uuid" class="btn btn-sm btn-outline-danger" @click="confirmingRevoke = t.uuid">Revocar</button>
                <span v-else class="d-inline-flex gap-1">
                  <button class="btn btn-sm btn-danger" @click="revoke(t)">Confirmar</button>
                  <button class="btn btn-sm btn-outline-secondary" @click="confirmingRevoke = null">Cancelar</button>
                </span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="text-muted small">Al revocar, el token deja de funcionar en hasta 2 minutos (cache del servidor MCP).</p>
    </div>
  </div>
</template>
