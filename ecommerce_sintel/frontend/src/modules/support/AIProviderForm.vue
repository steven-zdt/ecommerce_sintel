<template>
  <form @submit.prevent="handleSubmit">
    <div class="mb-3">
      <label class="form-label">Nombre</label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Ej. Ollama Windows" />
    </div>

    <div class="mb-3">
      <label class="form-label">Tipo de proveedor</label>
      <select v-model="form.kind" class="form-select" required>
        <option value="ollama-nativo">Ollama (nativo)</option>
        <option value="openai-compatible">OpenAI-compatible (LM Studio, vLLM, OpenAI, DeepSeek...)</option>
        <option value="anthropic">Anthropic (Claude)</option>
      </select>
    </div>

    <div class="mb-3" v-if="form.kind !== 'anthropic'">
      <label class="form-label">URL base</label>
      <input
        v-model="form.base_url" type="text" class="form-control"
        :placeholder="urlPlaceholder"
      />
      <small class="text-muted">
        Ollama en Windows: <code>http://host.docker.internal:11434</code> ·
        LM Studio en Windows: <code>http://host.docker.internal:1234/v1</code> ·
        Ollama en Docker: <code>http://sintel_ollama:11434</code>
      </small>
      <div v-if="isLoopbackUrl" class="text-danger small mt-1">
        <i class="bi bi-exclamation-triangle-fill"></i>
        <code>localhost</code> / <code>127.0.0.1</code> dentro de Docker es el propio contenedor, no tu equipo: aunque LM Studio muestre esa
        URL, aqui debes usar <code>http://host.docker.internal:PUERTO</code>. El servidor no permitira guardarla.
      </div>
    </div>

    <div class="mb-3">
      <label class="form-label">
        API Key
        <span v-if="isEdit && hasApiKey" class="text-muted small">(configurada — deja en blanco para no cambiarla)</span>
      </label>
      <input
        v-model="form.api_key" type="password" class="form-control"
        :placeholder="isEdit && hasApiKey ? 'sk-••••••••' : 'Opcional para motores locales'"
        autocomplete="new-password"
      />
    </div>

    <div class="mb-3 form-check form-switch">
      <input v-model="form.is_active" type="checkbox" class="form-check-input" id="ai-provider-active" />
      <label class="form-check-label" for="ai-provider-active">Activo</label>
    </div>

    <div class="d-flex justify-content-end gap-2 mt-4">
      <button type="button" class="btn btn-outline-secondary" @click="$emit('cancel')">Cancelar</button>
      <button type="submit" class="btn btn-primary" :disabled="loading">
        {{ isEdit ? 'Guardar cambios' : 'Crear proveedor' }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { computed, reactive, watch } from 'vue';

const props = defineProps({
  item: { type: Object, default: () => ({}) },
  mode: { type: String, default: 'create' },
  loading: { type: Boolean, default: false },
});
const emit = defineEmits(['success', 'cancel']);

const isEdit = computed(() => props.mode === 'edit');
const hasApiKey = computed(() => !!props.item?.has_api_key);

const form = reactive({
  name: '', kind: 'ollama-nativo', base_url: '', api_key: '', is_active: true, display_order: 0,
});

watch(() => props.item, (item) => {
  form.name = item?.name || '';
  form.kind = item?.kind || 'ollama-nativo';
  form.base_url = item?.base_url || '';
  form.api_key = '';
  form.is_active = item?.is_active ?? true;
  form.display_order = item?.display_order ?? 0;
}, { immediate: true });

// LM Studio/Ollama muestran http://localhost:PUERTO (vista desde tu equipo); dentro de Docker eso apunta al contenedor. Aviso en vivo.
const isLoopbackUrl = computed(() => {
  try {
    const host = new URL(form.base_url).hostname.replace(/^\[|\]$/g, '').toLowerCase();
    return ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(host);
  } catch { return false; }
});

const urlPlaceholder = computed(() =>
  form.kind === 'ollama-nativo' ? 'http://sintel_ollama:11434' : 'http://host.docker.internal:1234/v1'
);

function handleSubmit() {
  const payload = { ...form };
  if (form.kind === 'anthropic') delete payload.base_url;
  emit('success', payload);
}
</script>
