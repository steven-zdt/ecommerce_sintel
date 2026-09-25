<template>
  <div class="card mb-3">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="mb-0">Historial de configuracion (chat de soporte)</h6>
        <button class="btn btn-sm btn-outline-secondary" :disabled="loading" @click="load">
          <span v-if="loading" class="spinner-border spinner-border-sm"></span>
          <template v-else>{{ loaded ? 'Actualizar' : 'Ver historial' }}</template>
        </button>
      </div>
      <p class="text-muted small mb-2">
        Cada cambio de primario, fallback o proveedor crea una version. Restaurar una version es un cambio nuevo; no borra el historial.
        Las API keys nunca se guardan en el historial ni se restauran.
      </p>

      <div v-if="loaded && !items.length" class="text-muted small">Sin versiones registradas todavia.</div>

      <div v-if="items.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Version</th><th>Accion</th><th>Primario</th><th>Fallbacks</th><th>Por</th><th>Fecha</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="rev in items" :key="rev.version">
              <td>
                v{{ rev.version }}
                <span v-if="rev.version === currentVersion" class="badge bg-success ms-1">actual</span>
              </td>
              <td class="small">{{ rev.action }}</td>
              <td class="small">{{ label(rev, rev.snapshot.primary_model_uuid) }}</td>
              <td class="small">{{ (rev.snapshot.fallback_model_uuids || []).map((u) => label(rev, u)).join(' > ') || '-' }}</td>
              <td class="small">{{ rev.changed_by || '-' }}</td>
              <td class="small">{{ formatTime(rev.created_at) }}</td>
              <td class="text-end">
                <template v-if="rev.version !== currentVersion">
                  <button
                    v-if="confirmingVersion !== rev.version"
                    class="btn btn-sm btn-outline-primary py-0" :disabled="store.actionLoading"
                    @click="confirmingVersion = rev.version"
                  >Restaurar</button>
                  <span v-else class="d-inline-flex gap-1">
                    <button class="btn btn-sm btn-primary py-0" :disabled="store.actionLoading" @click="restore(rev.version)">Confirmar</button>
                    <button class="btn btn-sm btn-outline-secondary py-0" @click="confirmingVersion = null">Cancelar</button>
                  </span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useAIProviderAdminStore } from '@/store/aiProviderAdmin';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const store = useAIProviderAdminStore();
const toast = useToast();
const { handleError } = useErrorHandler();

const items = ref([]);
const loading = ref(false);
const loaded = ref(false);
const confirmingVersion = ref(null);

const currentVersion = computed(() => store.channelConfig?.config_version);

async function load() {
  loading.value = true;
  const res = await store.fetchChannelHistory();
  loading.value = false;
  if (res.ok) {
    items.value = res.data;
    loaded.value = true;
  } else {
    handleError(res.error, 'No se pudo cargar el historial.');
  }
}

function label(rev, modelUuid) {
  if (!modelUuid) return '-';
  return rev.snapshot.labels?.[modelUuid] || modelUuid;
}

function formatTime(iso) {
  try { return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return ''; }
}

async function restore(version) {
  const res = await store.rollbackChannel(version);
  confirmingVersion.value = null;
  if (res.ok) {
    toast.success(`Configuracion restaurada a la version v${version}.`);
    await load();
  } else {
    const msg = res.error?.response?.data?.version;
    handleError(res.error, Array.isArray(msg) ? msg.join(' ') : (msg || 'No se pudo restaurar la version.'));
  }
}
</script>
