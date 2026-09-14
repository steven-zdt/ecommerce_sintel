<template>
  <form @submit.prevent="submit">
    <div class="row g-3">
      <div class="col-md-8">
        <label class="form-label small fw-semibold">Nombre administrativo</label>
        <input v-model="form.name" type="text" class="form-control" maxlength="255" required
               placeholder="Ej. Meta Business Verification">
      </div>
      <div class="col-md-4">
        <label class="form-label small fw-semibold">Prioridad</label>
        <input v-model.number="form.priority" type="number" min="0" class="form-control">
      </div>

      <div class="col-md-6">
        <label class="form-label small fw-semibold">Proveedor</label>
        <select v-model="form.provider" class="form-select" required>
          <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="col-md-6">
        <label class="form-label small fw-semibold">Tipo</label>
        <select v-model="form.tag_type" class="form-select" required>
          <option v-for="opt in tagTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>

      <div class="col-12">
        <label class="form-label small fw-semibold">Descripcion</label>
        <textarea v-model="form.description" class="form-control" rows="2"
                  placeholder="Para que sirve esta metaetiqueta (uso interno del panel)."></textarea>
      </div>

      <div class="col-12">
        <ul class="nav nav-pills nav-fill mb-2" style="font-size:.8rem">
          <li class="nav-item">
            <button type="button" class="nav-link" :class="{ active: editorMode === 'simple' }" @click="editorMode = 'simple'">
              <i class="bi bi-input-cursor-text me-1"></i>Simple (name / content)
            </button>
          </li>
          <li class="nav-item">
            <button type="button" class="nav-link" :class="{ active: editorMode === 'advanced' }" @click="editorMode = 'advanced'">
              <i class="bi bi-code-slash me-1"></i>HTML avanzado
            </button>
          </li>
        </ul>
      </div>

      <template v-if="editorMode === 'simple'">
        <div class="col-md-6">
          <label class="form-label small fw-semibold">meta name</label>
          <input v-model="form.meta_name" type="text" class="form-control" maxlength="255"
                 placeholder="facebook-domain-verification">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">meta content</label>
          <input v-model="form.meta_content" type="text" class="form-control" maxlength="500"
                 placeholder="0c6qg0sg1qsfxhoth3srzf53i62neb">
        </div>
      </template>
      <template v-else>
        <div class="col-12">
          <label class="form-label small fw-semibold">HTML (solo etiquetas &lt;meta&gt;)</label>
          <textarea v-model="form.html_snippet" class="form-control font-monospace" rows="3"
                    placeholder='<meta name="..." content="...">'></textarea>
          <div class="form-text">Se sanitiza al guardar: scripts, atributos <code>on*</code> y otras etiquetas se rechazan.</div>
        </div>
      </template>

      <div class="col-12">
        <label class="form-label small fw-semibold">Vista previa (aproximada)</label>
        <pre class="preview-box mb-0">{{ localPreview }}</pre>
      </div>

      <div class="col-md-6">
        <label class="form-label small fw-semibold">Pagina destino</label>
        <input v-model="form.target_page" type="text" class="form-control" maxlength="255"
               placeholder="/tienda (vacio = todas las paginas)">
      </div>
      <div class="col-md-6">
        <label class="form-label small fw-semibold">Entorno</label>
        <select v-model="form.environment" class="form-select">
          <option v-for="opt in environmentOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>

      <div class="col-12">
        <div class="form-check form-switch">
          <input v-model="form.is_active" class="form-check-input" type="checkbox" id="seoTagActive">
          <label class="form-check-label small" for="seoTagActive">Activa (se renderiza en el sitio)</label>
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-end gap-2 mt-4 pt-3 border-top">
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="emit('cancel')">Cancelar</button>
      <button type="submit" class="btn btn-primary btn-sm" :disabled="saving">
        <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
        {{ mode === 'create' ? 'Crear metaetiqueta' : 'Guardar cambios' }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  item: { type: Object, default: () => ({}) },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const saving = ref(false);
const editorMode = ref('simple');

const providerOptions = [
  { value: 'meta', label: 'Meta Business Suite' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'google_search_console', label: 'Google Search Console' },
  { value: 'google_tag_manager', label: 'Google Tag Manager' },
  { value: 'google_analytics', label: 'Google Analytics' },
  { value: 'bing', label: 'Microsoft Bing' },
  { value: 'pinterest', label: 'Pinterest' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'apple', label: 'Apple' },
  { value: 'cloudflare', label: 'Cloudflare' },
  { value: 'custom', label: 'Personalizado' },
];

const tagTypeOptions = [
  { value: 'domain_verification', label: 'Verificacion de dominio' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'pixel', label: 'Pixel de conversion' },
  { value: 'seo', label: 'SEO' },
  { value: 'social', label: 'Redes sociales' },
  { value: 'custom', label: 'Personalizado' },
];

const environmentOptions = [
  { value: 'all', label: 'Todos los entornos' },
  { value: 'development', label: 'Development' },
  { value: 'testing', label: 'Testing' },
  { value: 'staging', label: 'Staging' },
  { value: 'production', label: 'Production' },
];

const emptyForm = () => ({
  name: '', provider: 'custom', tag_type: 'custom', description: '',
  meta_name: '', meta_content: '', html_snippet: '',
  priority: 0, is_active: true, target_page: '', environment: 'all',
});

const form = reactive(emptyForm());

watch(() => props.item, (item) => {
  const base = emptyForm();
  Object.assign(form, base, item || {});
  editorMode.value = form.html_snippet ? 'advanced' : 'simple';
}, { immediate: true });

const localPreview = computed(() => {
  if (editorMode.value === 'advanced' && form.html_snippet) return form.html_snippet;
  if (form.meta_name && form.meta_content) {
    return `<meta name="${form.meta_name}" content="${form.meta_content}">`;
  }
  return '(completa meta name/content o el HTML avanzado para ver la vista previa)';
});

async function submit() {
  saving.value = true;
  try {
    const payload = { ...form };
    if (editorMode.value === 'simple') {
      payload.html_snippet = '';
    } else {
      payload.meta_name = '';
      payload.meta_content = '';
    }

    if (props.mode === 'create') {
      await api.post('dashboard/seo/meta-tags/', payload);
      toast.success('Metaetiqueta creada.');
    } else {
      await api.patch(`dashboard/seo/meta-tags/${props.item.uuid}/`, payload);
      toast.success('Metaetiqueta actualizada.');
    }
    emit('success');
  } catch (err) {
    handleError(err, 'No se pudo guardar la metaetiqueta.');
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.preview-box {
  background: #0f172a; color: #e2e8f0; border-radius: 8px;
  padding: .75rem 1rem; font-size: .8rem; white-space: pre-wrap; word-break: break-all;
}
</style>
