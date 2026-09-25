<template>
  <form @submit.prevent="handleSubmit">
    <!-- BASICO -->
    <h6 class="text-uppercase text-muted small mb-2">Basico</h6>
    <div class="mb-3">
      <label class="form-label">Nombre</label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Ej. LM Studio (Windows)" />
    </div>

    <div class="mb-3">
      <label class="form-label">Tipo de proveedor</label>
      <select v-model="form.kind" class="form-select" required>
        <option value="ollama-nativo">Ollama (nativo)</option>
        <option value="openai-compatible">OpenAI-compatible (LM Studio, vLLM, OpenAI, DeepSeek...)</option>
        <option value="anthropic">Anthropic (Claude)</option>
        <option value="gemini">Google Gemini</option>
        <option value="generic-rest">REST generico (solo registro y prueba)</option>
        <option value="custom">Personalizado (solo registro y prueba)</option>
      </select>
      <small v-if="!isRunnable" class="text-warning d-block mt-1">
        Este tipo se puede registrar y probar, pero todavia no se puede usar como modelo primario del chat.
      </small>
    </div>

    <div class="mb-3 form-check form-switch">
      <input v-model="form.is_active" type="checkbox" class="form-check-input" id="ai-provider-active" />
      <label class="form-check-label" for="ai-provider-active">Activo</label>
    </div>

    <!-- CONEXION -->
    <h6 class="text-uppercase text-muted small mt-4 mb-2">Conexion</h6>
    <div class="mb-3" v-if="showUrl">
      <label class="form-label">URL base <span v-if="urlOptional" class="text-muted small">(opcional)</span></label>
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

    <div class="mb-3" v-if="usesEndpointPath">
      <label class="form-label">Ruta de descubrimiento de modelos <span class="text-muted small">(opcional)</span></label>
      <input v-model="form.endpoint_path" type="text" class="form-control" placeholder="/models" />
    </div>

    <!-- AUTENTICACION -->
    <h6 class="text-uppercase text-muted small mt-4 mb-2">Autenticacion</h6>
    <div class="mb-3" v-if="showAuthType">
      <label class="form-label">Tipo de autenticacion</label>
      <select v-model="form.auth_type" class="form-select">
        <option value="bearer">Authorization: Bearer &lt;key&gt;</option>
        <option value="header">Cabecera personalizada</option>
        <option value="none">Sin autenticacion</option>
      </select>
    </div>
    <div class="mb-3" v-if="showAuthType && form.auth_type === 'header'">
      <label class="form-label">Nombre de la cabecera</label>
      <input v-model="form.api_key_header" type="text" class="form-control" placeholder="x-api-key" />
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
      <small class="text-muted">Se guarda cifrada y nunca se vuelve a mostrar.</small>
    </div>

    <!-- TIEMPOS -->
    <h6 class="text-uppercase text-muted small mt-4 mb-2">Tiempos</h6>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label">Conexion (s)</label>
        <input v-model.number="form.connect_timeout" type="number" min="1" max="60" class="form-control" />
      </div>
      <div class="col-6">
        <label class="form-label">Total (s)</label>
        <input v-model.number="form.timeout" type="number" min="5" max="300" class="form-control" />
      </div>
    </div>

    <!-- SEGURIDAD -->
    <h6 class="text-uppercase text-muted small mt-4 mb-2">Seguridad</h6>
    <div class="mb-3 form-check form-switch" v-if="showUrl">
      <input v-model="form.verify_tls" type="checkbox" class="form-check-input" id="ai-provider-tls" />
      <label class="form-check-label" for="ai-provider-tls">Verificar certificado TLS</label>
      <small v-if="!form.verify_tls" class="text-warning d-block">Desactivar solo para certificados autofirmados de una red de confianza.</small>
    </div>
    <small class="text-muted d-block mb-3">
      El servidor rechaza destinos peligrosos (metadatos de nube, link-local, API de Docker, URLs con usuario/clave) y no sigue redirecciones.
    </small>

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
  auth_type: 'bearer', api_key_header: '', endpoint_path: '', verify_tls: true, connect_timeout: 5, timeout: 90,
});

watch(() => props.item, (item) => {
  form.name = item?.name || '';
  form.kind = item?.kind || 'ollama-nativo';
  form.base_url = item?.base_url || '';
  form.api_key = '';
  form.is_active = item?.is_active ?? true;
  form.display_order = item?.display_order ?? 0;
  form.auth_type = item?.auth_type || 'bearer';
  form.api_key_header = item?.api_key_header || '';
  form.endpoint_path = item?.endpoint_path || '';
  form.verify_tls = item?.verify_tls ?? true;
  form.connect_timeout = item?.connect_timeout ?? 5;
  form.timeout = item?.timeout ?? 90;
}, { immediate: true });

const RUNNABLE = ['ollama-nativo', 'openai-compatible', 'anthropic', 'gemini'];
const isRunnable = computed(() => RUNNABLE.includes(form.kind));
// Anthropic tiene URL fija; Gemini la admite opcional (por defecto la API oficial); el resto la exige.
const showUrl = computed(() => form.kind !== 'anthropic');
const urlOptional = computed(() => form.kind === 'gemini');
const usesEndpointPath = computed(() => ['openai-compatible', 'generic-rest', 'custom'].includes(form.kind));
const showAuthType = computed(() => ['openai-compatible', 'generic-rest', 'custom', 'ollama-nativo'].includes(form.kind));

// LM Studio/Ollama muestran http://localhost:PUERTO (vista desde tu equipo); dentro de Docker eso apunta al contenedor. Aviso en vivo.
const isLoopbackUrl = computed(() => {
  try {
    const host = new URL(form.base_url).hostname.replace(/^\[|\]$/g, '').toLowerCase();
    return ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(host);
  } catch { return false; }
});

const urlPlaceholder = computed(() => {
  if (form.kind === 'ollama-nativo') return 'http://sintel_ollama:11434';
  if (form.kind === 'gemini') return 'https://generativelanguage.googleapis.com';
  return 'http://host.docker.internal:1234/v1';
});

function handleSubmit() {
  const payload = { ...form };
  if (form.kind === 'anthropic' || (form.kind === 'gemini' && !form.base_url)) delete payload.base_url;
  if (!showAuthType.value) { delete payload.auth_type; delete payload.api_key_header; }
  if (!usesEndpointPath.value) delete payload.endpoint_path;
  emit('success', payload);
}
</script>
