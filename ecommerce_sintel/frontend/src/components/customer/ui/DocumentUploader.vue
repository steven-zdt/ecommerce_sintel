<template>
  <div class="doc-uploader">
    <div class="doc-form">
      <select v-model="docType" class="form-select form-select-sm">
        <option value="">Tipo de documento</option>
        <option
          v-for="opt in docTypeOptions"
          :key="opt.value"
          :value="opt.value"
        >{{ opt.label }}</option>
      </select>

      <label class="file-label" :class="{ 'file-label--filled': file }">
        <i class="bi bi-upload"></i>
        {{ file ? file.name : 'Seleccionar archivo' }}
        <input type="file" class="file-input" @change="onFileChange" accept="image/*,.pdf" />
      </label>

      <button
        class="btn btn-primary btn-sm"
        :disabled="!docType || !file || uploading"
        @click="upload"
      >
        <span v-if="uploading" class="spinner-border spinner-border-sm me-1"></span>
        Subir
      </button>
    </div>

    <p v-if="successMsg" class="success-msg">{{ successMsg }}</p>
    <p v-if="errorMsg"   class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import useApi from '@/composables/useApi';

const props  = defineProps({
  ticketUuid:    { type: String, required: true },
  operationType: { type: String, default: '' },
});
const emit = defineEmits(['uploaded']);

const api        = useApi();
const docType    = ref('');
const file       = ref(null);
const uploading  = ref(false);
const successMsg = ref('');
const errorMsg   = ref('');

const ALL_DOC_TYPES = [
  { value: 'ID_CARD',          label: 'Cedula de identidad' },
  { value: 'RENTAL_CONTRACT',  label: 'Contrato de alquiler' },
  { value: 'SERVICE_CONTRACT', label: 'Contrato de servicios' },
  { value: 'INVOICE',          label: 'Factura' },
  { value: 'OTHER',            label: 'Otro' },
];

const ALLOWED_BY_TYPE = {
  RENTAL:        ['ID_CARD', 'OTHER'],
  SERVICE:       ['ID_CARD', 'OTHER'],
  SHOP_DELIVERY: ['OTHER'],
};

const docTypeOptions = computed(() => {
  const allowed = ALLOWED_BY_TYPE[props.operationType] ?? ALL_DOC_TYPES.map(d => d.value);
  return ALL_DOC_TYPES.filter(d => allowed.includes(d.value));
});

function onFileChange(e) {
  file.value       = e.target.files[0] ?? null;
  successMsg.value = '';
  errorMsg.value   = '';
}

async function upload() {
  if (!docType.value || !file.value) return;
  uploading.value  = true;
  successMsg.value = '';
  errorMsg.value   = '';

  const form = new FormData();
  form.append('doc_type', docType.value);
  form.append('file', file.value);

  try {
    await api.post(`operations/my/${props.ticketUuid}/upload-document/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    successMsg.value = 'Documento subido. Pendiente de revision.';
    docType.value    = '';
    file.value       = null;
    emit('uploaded');
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || 'Error al subir el documento.';
  } finally {
    uploading.value = false;
  }
}
</script>

<style scoped>
.doc-uploader { margin-bottom: 16px; }

.doc-form {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}

.form-select { max-width: 200px; }

.file-label {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px dashed #d1d5db; border-radius: 8px;
  padding: 6px 14px; font-size: 0.825rem; color: #6b7280;
  cursor: pointer; background: #f9fafb; transition: border-color .15s;
  flex: 1; min-width: 160px;
}
.file-label--filled { border-color: #3b82f6; color: #1d4ed8; }
.file-label:hover   { border-color: #3b82f6; }
.file-input { display: none; }

.success-msg { color: #16a34a; font-size: 0.825rem; margin: 8px 0 0; }
.error-msg   { color: #dc2626; font-size: 0.825rem; margin: 8px 0 0; }
</style>
