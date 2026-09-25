<template>
  <div class="border rounded p-2 mt-2 bg-body-tertiary">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <strong class="small">Parametros y capacidades — {{ model.display_name || model.model_id }}</strong>
      <button type="button" class="btn-close btn-sm" aria-label="Cerrar" @click="$emit('close')"></button>
    </div>

    <h6 class="text-uppercase text-muted small mb-1">Generacion</h6>
    <div class="row g-2 mb-2">
      <div class="col-6 col-md-3">
        <label class="form-label small mb-0">Temperature</label>
        <input v-model.number="form.temperature" type="number" step="0.05" min="0" max="2" class="form-control form-control-sm" placeholder="default" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label small mb-0">Top P</label>
        <input v-model.number="form.top_p" type="number" step="0.05" min="0" max="1" class="form-control form-control-sm" placeholder="default" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label small mb-0">Max tokens</label>
        <input v-model.number="form.max_tokens" type="number" min="1" class="form-control form-control-sm" placeholder="default" />
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label small mb-0">Contexto (informativo)</label>
        <input v-model.number="form.context_window" type="number" min="1" class="form-control form-control-sm" placeholder="-" />
      </div>
    </div>
    <small class="text-muted d-block mb-2">Vacio = valor por defecto del proveedor. Los overrides del canal (si existen) tienen prioridad.</small>

    <div class="d-flex justify-content-between align-items-center mb-1">
      <h6 class="text-uppercase text-muted small mb-0">Capacidades</h6>
      <button type="button" class="btn btn-sm btn-outline-secondary py-0" :disabled="store.actionLoading" @click="detect">
        Detectar capacidades
      </button>
    </div>
    <div class="row g-2 mb-2">
      <div class="col-6 col-md-4" v-for="cap in CAPABILITIES" :key="cap.key">
        <label class="form-label small mb-0">{{ cap.label }}</label>
        <select v-model="caps[cap.key]" class="form-select form-select-sm">
          <option :value="null">Desconocido</option>
          <option :value="true">Si</option>
          <option :value="false">No</option>
        </select>
      </div>
    </div>
    <small class="text-muted d-block mb-2">
      "Detectar" pregunta al proveedor; lo que no declara queda en Desconocido. Un modelo con tool calling = No no se puede usar como primario del chat.
      <span v-if="model.capabilities_checked_at">Ultima deteccion: {{ formatTime(model.capabilities_checked_at) }}.</span>
    </small>

    <div class="d-flex justify-content-end gap-2">
      <button type="button" class="btn btn-sm btn-outline-secondary" @click="$emit('close')">Cerrar</button>
      <button type="button" class="btn btn-sm btn-primary" :disabled="store.actionLoading" @click="save">Guardar</button>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue';
import { useAIProviderAdminStore } from '@/store/aiProviderAdmin';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  provider: { type: Object, required: true },
  model: { type: Object, required: true },
});
defineEmits(['close']);

const store = useAIProviderAdminStore();
const toast = useToast();
const { handleError } = useErrorHandler();

const CAPABILITIES = [
  { key: 'tool_calling', label: 'Tool calling' },
  { key: 'streaming', label: 'Streaming' },
  { key: 'structured_output', label: 'Salida estructurada' },
  { key: 'vision', label: 'Vision' },
  { key: 'reasoning', label: 'Razonamiento' },
  { key: 'json_mode', label: 'JSON mode' },
];

const form = reactive({ temperature: null, top_p: null, max_tokens: null, context_window: null });
const caps = reactive({});

watch(() => props.model, (m) => {
  form.temperature = m.temperature ?? null;
  form.top_p = m.top_p ?? null;
  form.max_tokens = m.max_tokens ?? null;
  form.context_window = m.context_window ?? null;
  CAPABILITIES.forEach(({ key }) => { caps[key] = (m.capabilities || {})[key] ?? null; });
}, { immediate: true, deep: true });

function formatTime(iso) {
  try { return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return ''; }
}

// Un campo numerico vaciado en el input llega como '' (v-model.number): se normaliza a null = "usar el default".
const clean = (v) => (v === '' || v === undefined ? null : v);

async function save() {
  const res = await store.updateModelSettings(props.provider.uuid, props.model.uuid, {
    temperature: clean(form.temperature), top_p: clean(form.top_p), max_tokens: clean(form.max_tokens),
    context_window: clean(form.context_window), capabilities: { ...caps },
  });
  if (res.ok) toast.success('Parametros del modelo guardados.');
  else handleError(res.error, 'No se pudieron guardar los parametros del modelo.');
}

async function detect() {
  const res = await store.detectCapabilities(props.provider.uuid, props.model.uuid);
  if (!res.ok) return handleError(res.error, 'No se pudieron detectar las capacidades.');
  const known = Object.values(res.data.capabilities || {}).filter((v) => v !== null).length;
  toast[known ? 'success' : 'info'](known
    ? 'Capacidades detectadas.'
    : 'El proveedor no declara capacidades para este modelo: ajustalas a mano si las conoces.');
}
</script>
