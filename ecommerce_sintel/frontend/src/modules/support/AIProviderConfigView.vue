<template>
  <div class="ai-provider-config">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h4 class="mb-0">Proveedores de IA</h4>
        <p class="text-muted small mb-0">
          Configura los proveedores y modelos que usa el chatbot de soporte — sin tocar .env ni reiniciar Docker.
        </p>
      </div>
      <button class="btn btn-primary" @click="offcanvas.openCreate()">
        <i class="bi bi-plus-lg"></i> Nuevo proveedor
      </button>
    </div>

    <div v-if="store.loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <div v-else-if="store.channelConfig" class="card mb-3">
      <div class="card-body">
        <h6 class="mb-2">Configuracion activa (chat de soporte)</h6>
        <div class="row g-2 small mb-3">
          <div class="col-6 col-md-3">
            <div class="text-muted">Proveedor activo</div>
            <strong>{{ activeProvider?.name || 'LOCAL_MODEL_CHAIN (arranque)' }}</strong>
          </div>
          <div class="col-6 col-md-3">
            <div class="text-muted">Modelo activo</div>
            <strong>{{ store.channelConfig.primary_model?.display_name || store.channelConfig.primary_model?.model_id || '-' }}</strong>
          </div>
          <div class="col-6 col-md-2">
            <div class="text-muted">Estado</div>
            <strong v-if="!activeProvider">-</strong>
            <strong v-else-if="!store.channelConfig.enabled" class="text-muted">Canal apagado</strong>
            <strong v-else-if="activeProvider.last_test_ok === true" class="text-success">Conexion OK</strong>
            <strong v-else-if="activeProvider.last_test_ok === false" class="text-danger">Conexion fallo</strong>
            <strong v-else class="text-muted">Sin probar</strong>
          </div>
          <div class="col-6 col-md-2">
            <div class="text-muted">Latencia (ultima prueba)</div>
            <strong>{{ activeProvider?.last_test_latency_ms != null ? activeProvider.last_test_latency_ms + ' ms' : '-' }}</strong>
          </div>
          <div class="col-6 col-md-2">
            <div class="text-muted">Version de config</div>
            <strong>v{{ store.channelConfig.config_version }}</strong>
          </div>
        </div>

        <div v-if="pendingForce" class="alert alert-warning small d-flex justify-content-between align-items-center gap-2">
          <span>
            <strong>La validacion previa fallo</strong> para "{{ pendingForce.label }}": {{ pendingForce.message }}
            No se cambio el modelo primario.
          </span>
          <span class="d-flex gap-2 flex-shrink-0">
            <button class="btn btn-sm btn-outline-secondary" @click="pendingForce = null">Cancelar</button>
            <button class="btn btn-sm btn-warning" :disabled="store.actionLoading" @click="handleSetPrimary(pendingForce.model, true)">
              Activar de todas formas
            </button>
          </span>
        </div>

        <h6 class="mb-2">Cadena de fallback (chat de soporte)</h6>
        <p class="text-muted small mb-2">
          Si el modelo primario falla, se intenta con el siguiente de esta lista, en orden.
          Agrega modelos con el boton <i class="bi bi-arrow-down-circle"></i> de cada badge abajo.
        </p>
        <div v-if="fallbackChain.length" class="d-flex flex-column gap-1">
          <div
            v-for="(model, idx) in fallbackChain" :key="model.uuid"
            class="d-flex align-items-center gap-2 border rounded px-2 py-1"
          >
            <span class="badge bg-secondary">{{ idx + 1 }}</span>
            <span class="flex-grow-1 small">{{ model.display_name || model.model_id }}</span>
            <button type="button" class="btn btn-sm btn-outline-secondary py-0" :disabled="idx === 0" @click="moveFallback(idx, -1)">
              <i class="bi bi-arrow-up"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary py-0" :disabled="idx === fallbackChain.length - 1" @click="moveFallback(idx, 1)">
              <i class="bi bi-arrow-down"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger py-0" @click="removeFallback(idx)">&times;</button>
          </div>
        </div>
        <div v-else class="text-muted small">Sin fallback configurado — si el primario falla, el chat degrada directo al mensaje de "asistente no disponible".</div>
        <button
          class="btn btn-sm btn-primary mt-2" :disabled="store.actionLoading || !fallbackChainDirty"
          @click="handleSaveFallbackChain"
        >Guardar orden de fallback</button>
      </div>
    </div>

    <AIConfigHistory v-if="!store.loading && store.channelConfig" />

    <div v-if="!store.loading" class="row g-3">
      <div class="col-12" v-for="provider in store.providers" :key="provider.uuid">
        <div class="card">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <h6 class="mb-1">
                  {{ provider.name }}
                  <span
                    class="status-dot ms-1"
                    :class="provider.is_active ? 'online' : 'offline'"
                    :title="provider.is_active ? 'Activo' : 'Inactivo'"
                  ></span>
                </h6>
                <div class="text-muted small">
                  {{ provider.kind_display }}
                  <span v-if="provider.base_url"> · {{ provider.base_url }}</span>
                  <span v-if="provider.has_api_key"> · <i class="bi bi-key-fill"></i> API key configurada</span>
                </div>
                <div class="small mt-1" v-if="provider.last_tested_at">
                  <span :class="provider.last_test_ok ? 'text-success' : 'text-danger'">
                    <i :class="provider.last_test_ok ? 'bi bi-check-circle-fill' : 'bi bi-x-circle-fill'"></i>
                    {{ provider.last_test_ok ? 'Conexión OK' : 'Conexión falló' }}
                  </span>
                  <span class="text-muted">
                    ({{ formatTime(provider.last_tested_at) }}<span v-if="provider.last_test_latency_ms"> · {{ provider.last_test_latency_ms }}ms</span>)
                  </span>
                  <span v-if="!provider.last_test_ok && provider.last_test_error" class="text-danger d-block">
                    {{ provider.last_test_error }}
                  </span>
                </div>
              </div>
              <div class="d-flex gap-2">
                <button
                  class="btn btn-sm btn-outline-secondary" :disabled="testingUuid === provider.uuid"
                  @click="handleTestConnection(provider)"
                >
                  <span v-if="testingUuid === provider.uuid" class="spinner-border spinner-border-sm"></span>
                  <template v-else>Probar conexión</template>
                </button>
                <button class="btn btn-sm btn-outline-secondary" @click="handleDiscoverModels(provider)" :disabled="discoveringUuid === provider.uuid">
                  <span v-if="discoveringUuid === provider.uuid" class="spinner-border spinner-border-sm"></span>
                  <template v-else>Descubrir modelos</template>
                </button>
                <button class="btn btn-sm btn-outline-secondary" @click="offcanvas.openEdit(provider)">Editar</button>
                <button
                  v-if="confirmingDeleteUuid !== provider.uuid"
                  class="btn btn-sm btn-outline-danger" @click="confirmingDeleteUuid = provider.uuid"
                >Eliminar</button>
              </div>
            </div>

            <div v-if="confirmingDeleteUuid === provider.uuid" class="bg-danger-subtle rounded p-2 mt-2 d-flex justify-content-between align-items-center">
              <span class="small">¿Eliminar "{{ provider.name }}"? Esta accion no se puede deshacer.</span>
              <div class="d-flex gap-2">
                <button class="btn btn-sm btn-outline-secondary" @click="confirmingDeleteUuid = null">Cancelar</button>
                <button class="btn btn-sm btn-danger" @click="handleDelete(provider)">Confirmar</button>
              </div>
            </div>

            <!-- Modelos -->
            <div class="mt-3">
              <div class="d-flex flex-wrap gap-2 align-items-center">
                <span
                  v-for="model in provider.models" :key="model.uuid"
                  class="badge model-badge"
                  :class="isPrimary(model) ? 'bg-primary' : 'bg-secondary-subtle text-dark'"
                >
                  {{ model.display_name || model.model_id }}
                  <i v-if="isPrimary(model)" class="bi bi-star-fill ms-1" title="Modelo primario"></i>
                  <button type="button" class="btn-set-primary" @click="handleSetPrimary(model)" title="Usar como primario">
                    <i class="bi bi-check2"></i>
                  </button>
                  <button
                    v-if="!isPrimary(model) && !isInFallback(model)"
                    type="button" class="btn-set-primary" @click="addFallback(model)" title="Agregar a la cadena de fallback"
                  >
                    <i class="bi bi-arrow-down-circle"></i>
                  </button>
                  <button type="button" class="btn-remove-model" @click="handleDeleteModel(provider, model)" title="Eliminar modelo">
                    &times;
                  </button>
                </span>
                <span v-if="!provider.models.length" class="text-muted small">Sin modelos agregados.</span>
              </div>

              <div v-if="discovered[provider.uuid]" class="mt-2 p-2 border rounded">
                <div class="small text-muted mb-1">Modelos descubiertos en el proveedor real:</div>
                <div class="d-flex flex-wrap gap-2">
                  <button
                    v-for="d in discovered[provider.uuid]" :key="d.model_id"
                    type="button" class="btn btn-sm btn-outline-primary"
                    @click="handleAddModel(provider, d)"
                  >+ {{ d.display_name || d.model_id }}</button>
                  <span v-if="!discovered[provider.uuid].length" class="text-muted small">
                    Sin descubrimiento automatico disponible para este tipo de proveedor.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!store.providers.length" class="text-center text-muted py-5">
        Sin proveedores configurados todavia. El chatbot sigue usando la configuracion de arranque (LOCAL_MODEL_CHAIN).
      </div>
    </div>

    <SintelOffcanvas
      v-model="offcanvas.show.value"
      :title="offcanvas.mode.value === 'edit' ? 'Editar proveedor' : 'Nuevo proveedor'"
      :loading="store.actionLoading"
    >
      <AIProviderForm
        :item="offcanvas.selected.value" :mode="offcanvas.mode.value" :loading="store.actionLoading"
        @success="handleFormSubmit" @cancel="offcanvas.close()"
      />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useAIProviderAdminStore } from '@/store/aiProviderAdmin';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import AIProviderForm from './AIProviderForm.vue';
import AIConfigHistory from './AIConfigHistory.vue';

const store = useAIProviderAdminStore();
const offcanvas = useOffcanvas();
const toast = useToast();
const { handleError } = useErrorHandler();

const testingUuid = ref(null);
const discoveringUuid = ref(null);
const confirmingDeleteUuid = ref(null);
const discovered = reactive({});

const pendingForce = ref(null);
const activeProvider = computed(() => {
  const primary = store.channelConfig?.primary_model;
  if (!primary) return null;
  return store.providers.find((p) => (p.models || []).some((m) => m.uuid === primary.uuid)) || null;
});

const fallbackChain = ref([]);
const fallbackChainDirty = ref(false);

onMounted(() => store.fetchAll());

watch(() => store.channelConfig, (config) => {
  fallbackChain.value = (config?.fallbacks || []).map((f) => ({ uuid: f.uuid, model_id: f.model_id }));
  fallbackChainDirty.value = false;
}, { immediate: true });

function isPrimary(model) {
  return store.channelConfig?.primary_model?.uuid === model.uuid;
}

function isInFallback(model) {
  return fallbackChain.value.some((m) => m.uuid === model.uuid);
}

function addFallback(model) {
  fallbackChain.value.push({ uuid: model.uuid, model_id: model.model_id, display_name: model.display_name });
  fallbackChainDirty.value = true;
}

function removeFallback(idx) {
  fallbackChain.value.splice(idx, 1);
  fallbackChainDirty.value = true;
}

function moveFallback(idx, delta) {
  const target = idx + delta;
  if (target < 0 || target >= fallbackChain.value.length) return;
  const [item] = fallbackChain.value.splice(idx, 1);
  fallbackChain.value.splice(target, 0, item);
  fallbackChainDirty.value = true;
}

async function handleSaveFallbackChain() {
  const res = await store.setFallbackChain(fallbackChain.value.map((m) => m.uuid));
  if (res.ok) {
    toast.success('Cadena de fallback actualizada.');
    fallbackChainDirty.value = false;
  } else {
    handleError(res.error, 'No se pudo guardar la cadena de fallback.');
  }
}

function formatTime(iso) {
  try { return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return ''; }
}

async function handleFormSubmit(payload) {
  const res = offcanvas.mode.value === 'edit'
    ? await store.updateProvider(offcanvas.selected.value.uuid, payload)
    : await store.createProvider(payload);
  if (res.ok) {
    toast.success(offcanvas.mode.value === 'edit' ? 'Proveedor actualizado.' : 'Proveedor creado.');
    offcanvas.close();
  } else {
    handleError(res.error, 'No se pudo guardar el proveedor.');
  }
}

async function handleDelete(provider) {
  const res = await store.deleteProvider(provider.uuid);
  confirmingDeleteUuid.value = null;
  if (res.ok) toast.success('Proveedor eliminado.');
  else handleError(res.error, 'No se pudo eliminar el proveedor.');
}

async function handleTestConnection(provider) {
  testingUuid.value = provider.uuid;
  const res = await store.testConnection(provider.uuid);
  testingUuid.value = null;
  if (res.ok) {
    toast[res.data.last_test_ok ? 'success' : 'error'](
      res.data.last_test_ok ? 'Conexion exitosa.' : `Conexion fallo: ${res.data.last_test_error}`
    );
  } else {
    handleError(res.error, 'No se pudo probar la conexion.');
  }
}

async function handleDiscoverModels(provider) {
  discoveringUuid.value = provider.uuid;
  const res = await store.discoverModels(provider.uuid);
  discoveringUuid.value = null;
  if (res.ok) {
    discovered[provider.uuid] = res.data.discovered;
    if (!res.data.discovered.length) toast.info('El proveedor no devolvio modelos (o no soporta descubrimiento automatico).');
  } else {
    handleError(res.error, 'No se pudo consultar el proveedor.');
  }
}

async function handleAddModel(provider, discoveredModel) {
  const res = await store.addModel(provider.uuid, {
    model_id: discoveredModel.model_id, display_name: discoveredModel.display_name,
  });
  if (res.ok) toast.success(`Modelo "${discoveredModel.model_id}" agregado.`);
  else handleError(res.error, 'No se pudo agregar el modelo.');
}

async function handleDeleteModel(provider, model) {
  const res = await store.deleteModel(provider.uuid, model.uuid);
  if (res.ok) toast.success('Modelo eliminado.');
  else handleError(res.error, 'No se pudo eliminar el modelo.');
}

async function handleSetPrimary(model, force = false) {
  const res = await store.setPrimary(model.uuid, force);
  if (res.ok) {
    pendingForce.value = null;
    toast.success(`"${model.display_name || model.model_id}" es ahora el modelo primario del chat.`);
    return;
  }
  // 409 = la validacion previa (conectividad/modelo disponible) fallo y NO se cambio nada: pedir confirmacion para forzar.
  const report = res.error?.response?.status === 409 ? res.error.response.data?.report : null;
  if (report) {
    pendingForce.value = { model, label: model.display_name || model.model_id, message: report.message };
  } else {
    handleError(res.error, 'No se pudo actualizar el modelo primario.');
  }
}
</script>

<style scoped>
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-dot.online { background: #4ade80; }
.status-dot.offline { background: #9ca3af; }

.model-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  font-weight: 400;
  font-size: 12px;
}
.btn-set-primary, .btn-remove-model {
  background: none;
  border: none;
  color: inherit;
  padding: 0;
  line-height: 1;
  cursor: pointer;
  opacity: 0.75;
}
.btn-set-primary:hover, .btn-remove-model:hover { opacity: 1; }
</style>
