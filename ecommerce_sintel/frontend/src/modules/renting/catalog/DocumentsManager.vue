<template>
  <div>
    <p class="text-muted small mb-3">
      Manuales, fichas tecnicas, guias, certificados, planos, catalogos, firmware y drivers.
      Formatos permitidos: PDF, DOCX, ZIP, DWG, DXF, XLSX, PPTX (max 50MB).
    </p>

    <div class="card border-0 bg-light p-3 mb-3 rounded-3">
      <div class="row g-2">
        <div class="col-12">
          <label class="form-label small">Archivo <span class="text-danger">*</span></label>
          <input ref="fileInputRef" type="file" class="form-control form-control-sm" @change="onFileChange">
        </div>
        <div class="col-6">
          <label class="form-label small">Titulo <span class="text-danger">*</span></label>
          <input v-model="form.title" type="text" class="form-control form-control-sm" placeholder="Ej: Manual de operacion">
        </div>
        <div class="col-6">
          <label class="form-label small">Tipo</label>
          <select v-model="form.document_type" class="form-select form-select-sm">
            <option v-for="opt in documentTypes" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="col-4">
          <label class="form-label small">Version</label>
          <input v-model="form.version" type="text" class="form-control form-control-sm" placeholder="Ej: v2.1">
        </div>
        <div class="col-4">
          <label class="form-label small">Idioma</label>
          <input v-model="form.language" type="text" class="form-control form-control-sm" placeholder="es">
        </div>
        <div class="col-4 d-flex align-items-end pb-1">
          <div class="form-check form-switch">
            <input v-model="form.is_public" class="form-check-input" type="checkbox" id="docPublic">
            <label class="form-check-label small" for="docPublic">Visible al cliente</label>
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
            <span v-if="doc.version"> · v{{ doc.version }}</span>
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
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const ENDPOINT = 'dashboard/rental-documents/';

const documentTypes = [
  { value: 'MANUAL', label: 'Manual' },
  { value: 'FICHA_TECNICA', label: 'Ficha tecnica' },
  { value: 'GUIA', label: 'Guia' },
  { value: 'CERTIFICADO', label: 'Certificado' },
  { value: 'PLANO', label: 'Plano' },
  { value: 'CATALOGO', label: 'Catalogo' },
  { value: 'FIRMWARE', label: 'Firmware' },
  { value: 'DRIVER', label: 'Driver' },
  { value: 'OTRO', label: 'Otro' },
];

const documents = ref([]);
const fileInputRef = ref(null);
const uploading = ref(false);
const dragIndex = ref(null);

function emptyForm() {
  return { file: null, title: '', document_type: 'MANUAL', version: '', language: 'es', description: '', is_public: true };
}
const form = ref(emptyForm());

function onFileChange(e) {
  form.value.file = e.target.files[0] || null;
}

async function fetchDocuments() {
  if (!props.equipmentUuid) return;
  try {
    const res = await api.get(`${ENDPOINT}?equipment=${props.equipmentUuid}`);
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
    fd.append('equipment', props.equipmentUuid);
    fd.append('file', form.value.file);
    fd.append('title', form.value.title);
    fd.append('document_type', form.value.document_type);
    fd.append('version', form.value.version || '');
    fd.append('language', form.value.language || 'es');
    fd.append('description', form.value.description || '');
    fd.append('is_public', form.value.is_public ? 'true' : 'false');
    await api.post(ENDPOINT, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
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
    await api.delete(`${ENDPOINT}${doc.uuid}/`);
    await fetchDocuments();
    toast.success('Documento eliminado');
  } catch {
    toast.error('No se pudo eliminar el documento');
  }
}

async function toggleActive(doc) {
  try {
    await api.post(`${ENDPOINT}${doc.uuid}/toggle-active/`);
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
    await api.post(`${ENDPOINT}reorder/`, {
      equipment: props.equipmentUuid,
      ordered_uuids: reordered.map((d) => d.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchDocuments();
  }
}

watch(() => props.equipmentUuid, fetchDocuments, { immediate: true });

defineExpose({ fetchDocuments });
</script>
