<template>
  <div class="border rounded p-2 mt-2 bg-body-tertiary">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <strong class="small">Historial de "{{ provider.name }}"</strong>
      <button type="button" class="btn-close btn-sm" aria-label="Cerrar" @click="$emit('close')"></button>
    </div>
    <p class="text-muted small mb-2">
      Cada edicion crea una version. Restaurar es un cambio nuevo y NO toca la API key (para cambiarla, edita el proveedor).
      Selecciona dos versiones para compararlas.
    </p>

    <div v-if="loading" class="text-center py-2"><span class="spinner-border spinner-border-sm"></span></div>
    <div v-else-if="!items.length" class="text-muted small">Sin versiones registradas.</div>

    <div v-else class="table-responsive">
      <table class="table table-sm align-middle mb-2">
        <thead><tr><th></th><th>Version</th><th>Accion</th><th>URL</th><th>Por</th><th>Fecha</th><th></th></tr></thead>
        <tbody>
          <tr v-for="rev in items" :key="rev.version">
            <td><input type="checkbox" :checked="selected.includes(rev.version)" @change="toggle(rev.version)" /></td>
            <td>v{{ rev.version }} <span v-if="rev.version === provider.config_version" class="badge bg-success">actual</span></td>
            <td class="small">{{ rev.action }}</td>
            <td class="small text-break">{{ rev.snapshot.base_url || '-' }}</td>
            <td class="small">{{ rev.changed_by || '-' }}</td>
            <td class="small">{{ formatTime(rev.created_at) }}</td>
            <td class="text-end">
              <template v-if="rev.version !== provider.config_version">
                <button
                  v-if="confirming !== rev.version" class="btn btn-sm btn-outline-primary py-0"
                  :disabled="store.actionLoading" @click="confirming = rev.version"
                >Restaurar</button>
                <span v-else class="d-inline-flex gap-1">
                  <button class="btn btn-sm btn-primary py-0" :disabled="store.actionLoading" @click="restore(rev.version)">Confirmar</button>
                  <button class="btn btn-sm btn-outline-secondary py-0" @click="confirming = null">Cancelar</button>
                </span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="diff.length" class="small">
      <strong>Diferencias v{{ selected[0] }} → v{{ selected[1] }}</strong>
      <ul class="mb-0 mt-1">
        <li v-for="d in diff" :key="d.field"><code>{{ d.field }}</code>: {{ d.before }} → <strong>{{ d.after }}</strong></li>
      </ul>
    </div>
    <div v-else-if="selected.length === 2" class="small text-muted">Sin diferencias entre esas versiones.</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useAIProviderAdminStore } from '@/store/aiProviderAdmin';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({ provider: { type: Object, required: true } });
defineEmits(['close']);

const store = useAIProviderAdminStore();
const toast = useToast();
const { handleError } = useErrorHandler();

const items = ref([]);
const loading = ref(false);
const selected = ref([]);
const confirming = ref(null);

async function load() {
  loading.value = true;
  const res = await store.fetchProviderHistory(props.provider.uuid);
  loading.value = false;
  if (res.ok) items.value = res.data;
  else handleError(res.error, 'No se pudo cargar el historial del proveedor.');
}
onMounted(load);

function toggle(version) {
  selected.value = selected.value.includes(version)
    ? selected.value.filter((v) => v !== version)
    : [...selected.value, version].slice(-2);
}

const show = (v) => (v === undefined || v === null || v === '' ? '-' : typeof v === 'object' ? JSON.stringify(v) : String(v));

// Compara los snapshots (sin secretos por construccion) de las dos versiones elegidas, de la mas antigua a la mas nueva.
const diff = computed(() => {
  if (selected.value.length !== 2) return [];
  const [a, b] = [...selected.value].sort((x, y) => x - y).map((v) => items.value.find((r) => r.version === v)?.snapshot || {});
  return [...new Set([...Object.keys(a), ...Object.keys(b)])]
    .filter((field) => JSON.stringify(a[field]) !== JSON.stringify(b[field]))
    .map((field) => ({ field, before: show(a[field]), after: show(b[field]) }));
});

function formatTime(iso) {
  try { return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return ''; }
}

async function restore(version) {
  const res = await store.rollbackProvider(props.provider.uuid, version);
  confirming.value = null;
  if (res.ok) {
    toast.success(`Proveedor restaurado a la version v${version}.`);
    await load();
  } else {
    const msg = res.error?.response?.data?.version;
    handleError(res.error, Array.isArray(msg) ? msg.join(' ') : (msg || 'No se pudo restaurar la version.'));
  }
}
</script>
