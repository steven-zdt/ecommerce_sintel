<template>
  <div>
    <p class="text-muted small mb-3">{{ config.hintText }}</p>

    <div class="card border-0 bg-light p-3 mb-3 rounded-3">
      <div class="row g-2">
        <div class="col-12">
          <label class="form-label small">Archivo <span class="text-danger">*</span></label>
          <input ref="fileInputRef" type="file" class="form-control form-control-sm" @change="onFileChange">
        </div>
        <div class="col-6">
          <label class="form-label small">Titulo <span class="text-danger">*</span></label>
          <input v-model="form.title" type="text" class="form-control form-control-sm" :placeholder="config.titlePlaceholder">
        </div>
        <div class="col-6">
          <label class="form-label small">Tipo</label>
          <select v-model="form.document_type" class="form-select form-select-sm">
            <option v-for="opt in config.documentTypes" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <template v-if="config.hasVersionLanguage">
          <div class="col-4">
            <label class="form-label small">Version</label>
            <input v-model="form.version" type="text" class="form-control form-control-sm" placeholder="Ej: v2.1">
          </div>
          <div class="col-4">
            <label class="form-label small">Idioma</label>
            <input v-model="form.language" type="text" class="form-control form-control-sm" placeholder="es">
          </div>
        </template>
        <div :class="config.hasVersionLanguage ? 'col-4' : 'col-12'" class="d-flex align-items-end pb-1">
          <div class="form-check form-switch">
            <input v-model="form.is_public" class="form-check-input" type="checkbox" :id="config.checkboxId">
            <label class="form-check-label small" :for="config.checkboxId">Visible al cliente</label>
          </div>
        </div>
        <div class="col-12">
          <label class="form-label small">Descripcion</label>
          <textarea v-model="form.description" class="form-control form-control-sm" rows="2"></textarea>
        </div>
      </div>
      <button type="button" class="btn btn-sm btn-primary mt-3" @click="upload" :disabled="uploading || !form.file || !form.title.trim()">
        <span v-if="uploading" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-cloud-upload me-1"></i> Subir documento
      </button>
    </div>

    <div v-if="documents.length" class="d-flex flex-column gap-2">
      <div
        v-for="(doc, idx) in documents"
        :key="doc.uuid"
        class="d-flex align-items-center gap-2 p-2 rounded-3 border"
        :class="doc.is_active ? 'bg-white' : 'bg-light opacity-60'"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <span class="text-muted" title="Arrastrar"><i class="bi bi-grip-vertical"></i></span>
        <i class="bi bi-file-earmark-text text-primary fs-5"></i>
        <div class="flex-grow-1 min-w-0">
          <div class="fw-semibold small text-truncate">{{ doc.title }}</div>
          <div class="text-muted" style="font-size:.72rem">
            {{ doc.document_type_display }}
            <span v-if="config.hasVersionLanguage && doc.version"> · v{{ doc.version }}</span>
            <span> · {{ doc.downloads }} descargas</span>
            <span v-if="!doc.is_public" class="text-warning"> · Oculto al cliente</span>
          </div>
        </div>
        <a :href="doc.file" target="_blank" class="btn btn-sm btn-light" title="Ver/descargar"><i class="bi bi-download"></i></a>
        <button type="button" class="btn btn-link p-0" :title="doc.is_active ? 'Desactivar' : 'Activar'" @click="toggleActive(doc)">
          <i :class="doc.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"></i>
        </button>
        <button type="button" class="btn btn-sm btn-light" title="Eliminar" @click="remove(doc)"><i class="bi bi-trash text-danger"></i></button>
      </div>
    </div>
    <div v-else class="text-center py-4 text-muted">
      <i class="bi bi-file-earmark-arrow-up fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin documentos registrados.</p>
    </div>
  </div>
</template>

<script setup>
// Generalizado 2026-08-05 (Sprint 5, auditoria transversal) -- ver
// SpecificationsManager.vue (mismo directorio) para el detalle del patron. Este
// caso tiene una diferencia real de schema entre dominios (no solo cosmetica):
// Renting agrega PLANO/FIRMWARE/DRIVER a la lista de tipos, y Services NO tiene
// los campos version/language en absoluto (ServiceDocument no los expone) -- se
// modela con `hasVersionLanguage` en vez de asumir que los 3 dominios comparten
// el mismo shape.
import { ref, computed, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const ENTITY_CONFIG = {
  product: {
    entityParam: 'product',
    endpoint: 'dashboard/product-documents/',
    hintText: 'Manuales, fichas tecnicas, guias, certificados y catalogos. Formatos permitidos: PDF, DOCX, ZIP, XLSX, PPTX (max 50MB).',
    titlePlaceholder: 'Ej: Ficha tecnica',
    hasVersionLanguage: true,
    checkboxId: 'prodDocPublic',
    documentTypes: [
      { value: 'MANUAL', label: 'Manual' },
      { value: 'FICHA_TECNICA', label: 'Ficha tecnica' },
      { value: 'GUIA', label: 'Guia' },
      { value: 'CERTIFICADO', label: 'Certificado' },
      { value: 'CATALOGO', label: 'Catalogo' },
      { value: 'OTRO', label: 'Otro' },
    ],
  },
  equipment: {
    entityParam: 'equipment',
    endpoint: 'dashboard/rental-documents/',
    hintText: 'Manuales, fichas tecnicas, guias, certificados, planos, catalogos, firmware y drivers. Formatos permitidos: PDF, DOCX, ZIP, DWG, DXF, XLSX, PPTX (max 50MB).',
    titlePlaceholder: 'Ej: Manual de operacion',
    hasVersionLanguage: true,
    checkboxId: 'docPublic',
    documentTypes: [
      { value: 'MANUAL', label: 'Manual' },
      { value: 'FICHA_TECNICA', label: 'Ficha tecnica' },
      { value: 'GUIA', label: 'Guia' },
      { value: 'CERTIFICADO', label: 'Certificado' },
      { value: 'PLANO', label: 'Plano' },
      { value: 'CATALOGO', label: 'Catalogo' },
      { value: 'FIRMWARE', label: 'Firmware' },
      { value: 'DRIVER', label: 'Driver' },
      { value: 'OTRO', label: 'Otro' },
    ],
  },
  service: {
    entityParam: 'service',
    endpoint: 'dashboard/service-documents/',
    hintText: 'Manuales, fichas tecnicas, certificados, normativas y catalogos. Formatos permitidos: PDF, DOCX, ZIP, XLSX, PPTX (max 50MB).',
    titlePlaceholder: 'Ej: Ficha tecnica',
    hasVersionLanguage: false,
    checkboxId: 'svcDocPublic',
    documentTypes: [
      { value: 'MANUAL', label: 'Manual' },
      { value: 'FICHA_TECNICA', label: 'Ficha tecnica' },
      { value: 'CERTIFICADO', label: 'Certificado' },
      { value: 'NORMATIVA', label: 'Normativa' },
      { value: 'CATALOGO', label: 'Catalogo' },
      { value: 'OTRO', label: 'Otro' },
    ],
  },
};

const props = defineProps({
  entityType: { type: String, default: 'product', validator: (v) => ['product', 'equipment', 'service'].includes(v) },
  entityUuid: { type: String, required: true },
});

const config = computed(() => ENTITY_CONFIG[props.entityType]);

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const documents = ref([]);
const fileInputRef = ref(null);
const uploading = ref(false);
const dragIndex = ref(null);

function emptyForm() {
  const base = { file: null, title: '', document_type: 'MANUAL', description: '', is_public: true };
  return config.value.hasVersionLanguage ? { ...base, version: '', language: 'es' } : base;
}
const form = ref(emptyForm());

function onFileChange(e) {
  form.value.file = e.target.files[0] || null;
}

async function fetchDocuments() {
  if (!props.entityUuid) return;
  try {
    const res = await api.get(`${config.value.endpoint}?${config.value.entityParam}=${props.entityUuid}`);
    documents.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudieron cargar los documentos');
  }
}

async function upload() {
  if (!form.value.file) return toast.error('Selecciona un archivo');
  if (!form.value.title.trim()) return toast.error('El titulo es requerido');
  uploading.value = true;
  try {
    const fd = new FormData();
    fd.append(config.value.entityParam, props.entityUuid);
    fd.append('file', form.value.file);
    fd.append('title', form.value.title);
    fd.append('document_type', form.value.document_type);
    if (config.value.hasVersionLanguage) {
      fd.append('version', form.value.version || '');
      fd.append('language', form.value.language || 'es');
    }
    fd.append('description', form.value.description || '');
    fd.append('is_public', form.value.is_public ? 'true' : 'false');
    await api.post(config.value.endpoint, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    form.value = emptyForm();
    if (fileInputRef.value) fileInputRef.value.value = '';
    await fetchDocuments();
    toast.success('Documento subido');
  } catch (e) {
    handleError(e, 'Error al subir el documento');
  } finally {
    uploading.value = false;
  }
}

async function remove(doc) {
  try {
    await api.delete(`${config.value.endpoint}${doc.uuid}/`);
    await fetchDocuments();
    toast.success('Documento eliminado');
  } catch {
    toast.error('No se pudo eliminar el documento');
  }
}

async function toggleActive(doc) {
  try {
    await api.post(`${config.value.endpoint}${doc.uuid}/toggle-active/`);
    await fetchDocuments();
  } catch {
    toast.error('No se pudo cambiar el estado');
  }
}

function handleDragStart(index) { dragIndex.value = index; }
async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...documents.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  documents.value = reordered;
  try {
    await api.post(`${config.value.endpoint}reorder/`, {
      [config.value.entityParam]: props.entityUuid,
      ordered_uuids: reordered.map((d) => d.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchDocuments();
  }
}

watch(() => props.entityUuid, fetchDocuments, { immediate: true });

defineExpose({ fetchDocuments });
</script>
