<template>
  <div class="kyc-upload">
    <h3 class="h6 fw-bold mb-3">Documentos obligatorios</h3>
    <div class="kyc-slot" v-for="slot in REQUIRED_SLOTS" :key="slot.doc_type">
      <div class="kyc-slot__info">
        <span class="fw-semibold small">{{ slot.label }}</span>
        <span v-if="findDoc(slot.doc_type)" class="badge ms-2" :class="statusBadgeClass(findDoc(slot.doc_type).status)">
          {{ statusLabel(findDoc(slot.doc_type).status) }}
        </span>
        <span v-else class="badge ms-2 bg-secondary-subtle text-secondary border border-secondary-subtle">Pendiente de subir</span>
        <div v-if="findDoc(slot.doc_type)?.rejection_reason" class="small text-danger mt-1">
          {{ findDoc(slot.doc_type).rejection_reason }}
        </div>
      </div>
      <div class="kyc-slot__action">
        <template v-if="findDoc(slot.doc_type)">
          <button type="button" class="btn btn-sm btn-outline-danger"
            :disabled="!canDelete || deletingUuid === findDoc(slot.doc_type).uuid"
            @click="deleteDoc(findDoc(slot.doc_type))">
            <span v-if="deletingUuid === findDoc(slot.doc_type).uuid" class="spinner-border spinner-border-sm"></span>
            <i v-else class="bi bi-trash"></i>
          </button>
        </template>
        <template v-else>
          <label class="btn btn-sm btn-outline-primary mb-0" :class="{ disabled: uploadingSlot === slot.doc_type }">
            <span v-if="uploadingSlot === slot.doc_type" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-upload me-1"></i>
            Subir
            <input type="file" class="d-none" :accept="slot.accept"
              :disabled="uploadingSlot === slot.doc_type"
              @change="onFileChange($event, slot.doc_type)">
          </label>
        </template>
      </div>
    </div>

    <button type="button" class="btn btn-link btn-sm px-0 mt-2" @click="showOptional = !showOptional">
      <i :class="['bi', showOptional ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
      Documentos opcionales (antecedentes, certificaciones)
    </button>

    <div v-if="showOptional" class="mt-2">
      <div class="kyc-slot" v-for="doc in optionalUploaded" :key="doc.uuid">
        <div class="kyc-slot__info">
          <span class="fw-semibold small">{{ optionalLabel(doc.doc_type) }}</span>
          <span class="badge ms-2" :class="statusBadgeClass(doc.status)">{{ statusLabel(doc.status) }}</span>
        </div>
        <div class="kyc-slot__action">
          <button type="button" class="btn btn-sm btn-outline-danger"
            :disabled="!canDelete || deletingUuid === doc.uuid" @click="deleteDoc(doc)">
            <span v-if="deletingUuid === doc.uuid" class="spinner-border spinner-border-sm"></span>
            <i v-else class="bi bi-trash"></i>
          </button>
        </div>
      </div>

      <div class="d-flex gap-2 align-items-center mt-2">
        <select v-model="optionalDocType" class="form-select form-select-sm" style="max-width: 220px">
          <option v-for="slot in OPTIONAL_SLOTS" :key="slot.doc_type" :value="slot.doc_type">{{ slot.label }}</option>
        </select>
        <label class="btn btn-sm btn-outline-secondary mb-0" :class="{ disabled: uploadingSlot === optionalDocType }">
          <span v-if="uploadingSlot === optionalDocType" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="bi bi-upload me-1"></i>
          Agregar
          <input type="file" class="d-none" :accept="optionalAccept"
            :disabled="uploadingSlot === optionalDocType"
            @change="onFileChange($event, optionalDocType)">
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { kycService } from '@/services/kyc/kycService';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  documents: { type: Array, default: () => [] },
  verificationStatus: { type: String, default: 'PENDING' },
});
const emit = defineEmits(['changed']);

const toast = useToast();
const { handleError } = useErrorHandler();

const REQUIRED_SLOTS = [
  { doc_type: 'CEDULA_FRONTAL', label: 'Cedula (frontal)', accept: '.pdf,.jpg,.jpeg' },
  { doc_type: 'CEDULA_REVERSO', label: 'Cedula (reverso)', accept: '.pdf,.jpg,.jpeg' },
  { doc_type: 'RUT', label: 'RUT', accept: '.pdf' },
  { doc_type: 'HOJA_VIDA', label: 'Hoja de vida / CV', accept: '.pdf' },
  { doc_type: 'DIPLOMA', label: 'Diploma', accept: '.pdf' },
];
const OPTIONAL_SLOTS = [
  { doc_type: 'CERTIFICACION', label: 'Certificacion', accept: '.pdf' },
  { doc_type: 'ANTECEDENTES_POLICIA', label: 'Antecedentes de Policia', accept: '.pdf' },
  { doc_type: 'ANTECEDENTES_CONTRALORIA', label: 'Antecedentes de Contraloria', accept: '.pdf' },
  { doc_type: 'ANTECEDENTES_PROCURADURIA', label: 'Antecedentes de Procuraduria', accept: '.pdf' },
];

const showOptional = ref(false);
const optionalDocType = ref(OPTIONAL_SLOTS[0].doc_type);
const uploadingSlot = ref(null);
const deletingUuid = ref(null);

const canDelete = computed(() => ['PENDING', 'REJECTED'].includes(props.verificationStatus));
const optionalAccept = computed(() => OPTIONAL_SLOTS.find(s => s.doc_type === optionalDocType.value)?.accept || '.pdf');
const optionalUploaded = computed(() => props.documents.filter(d => OPTIONAL_SLOTS.some(s => s.doc_type === d.doc_type)));

function findDoc(docType) {
  return props.documents.find(d => d.doc_type === docType);
}

function optionalLabel(docType) {
  return OPTIONAL_SLOTS.find(s => s.doc_type === docType)?.label || docType;
}

function statusLabel(status) {
  return { PENDING: 'Pendiente de revision', APPROVED: 'Aprobado', REJECTED: 'Rechazado' }[status] || status;
}

function statusBadgeClass(status) {
  return {
    PENDING: 'bg-warning-subtle text-warning border border-warning-subtle',
    APPROVED: 'bg-success-subtle text-success border border-success-subtle',
    REJECTED: 'bg-danger-subtle text-danger border border-danger-subtle',
  }[status] || 'bg-secondary-subtle text-secondary';
}

async function onFileChange(event, docType) {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;
  uploadingSlot.value = docType;
  try {
    const formData = new FormData();
    formData.append('doc_type', docType);
    formData.append('file', file);
    await kycService.uploadDocument(formData);
    toast.success('Documento subido.');
    emit('changed');
  } catch (e) {
    handleError(e, 'No se pudo subir el documento.');
  } finally {
    uploadingSlot.value = null;
  }
}

async function deleteDoc(doc) {
  deletingUuid.value = doc.uuid;
  try {
    await kycService.deleteDocument(doc.uuid);
    toast.success('Documento eliminado.');
    emit('changed');
  } catch (e) {
    handleError(e, 'No se pudo eliminar el documento.');
  } finally {
    deletingUuid.value = null;
  }
}
</script>

<style scoped>
.kyc-slot {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 10px 0; border-bottom: 1px solid #e5e7eb;
}
.kyc-slot:last-child { border-bottom: none; }
</style>
