<template>
  <div class="kyc-verification-panel">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-start mb-3 flex-wrap gap-2">
      <div>
        <h4 class="fw-bold mb-1">{{ verification.primer_nombre }} {{ verification.primer_apellido }}</h4>
        <div class="text-muted small">{{ verification.email }}</div>
      </div>
      <div class="text-end">
        <span class="badge fs-6" :class="enums.cssClass('kyc-verification-statuses', verification.status)">
          {{ enums.label('kyc-verification-statuses', verification.status, verification.status) }}
        </span>
        <div v-if="verification.requested_user_type" class="badge bg-primary-subtle text-primary border border-primary-subtle mt-1 d-block">
          Solicita convertirse en: {{ enums.label('user-types', verification.requested_user_type, verification.requested_user_type) }}
        </div>
        <div class="text-muted smaller mt-1" v-if="verification.submitted_at">
          Enviado a revision: {{ formatDate(verification.submitted_at) }}
        </div>
      </div>
    </div>

    <div class="row g-3">
      <!-- Identidad / documento -->
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Identidad</h6>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Nombre completo</dt>
            <dd class="col-7">{{ fullName }}</dd>
            <dt class="col-5 text-muted">Sexo</dt>
            <dd class="col-7">{{ verification.sexo || '—' }}</dd>
            <dt class="col-5 text-muted">Nacionalidad</dt>
            <dd class="col-7">{{ verification.nacionalidad || '—' }}</dd>
            <dt class="col-5 text-muted">Fecha de nacimiento</dt>
            <dd class="col-7">{{ verification.fecha_nacimiento || '—' }}</dd>
            <dt class="col-5 text-muted">Telefono</dt>
            <dd class="col-7">{{ verification.phone_number || '—' }}</dd>
            <dt class="col-5 text-muted">Direccion</dt>
            <dd class="col-7">{{ addressLine }}</dd>
            <dt class="col-5 text-muted">Documento</dt>
            <dd class="col-7">{{ verification.document_type }} {{ verification.document }}</dd>
            <dt class="col-5 text-muted">Expedicion</dt>
            <dd class="col-7">{{ verification.fecha_expedicion_documento || '—' }} — {{ verification.lugar_expedicion_documento || '—' }}</dd>
          </dl>
        </div>
      </div>

      <!-- Documentos -->
      <div class="col-lg-6">
        <div class="detail-card">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="fw-bold mb-0">Documentos</h6>
            <RouterLink
              v-if="!reviewable"
              :to="{ name: 'kyc-admin-detail', params: { uuid: verification.uuid } }"
              class="small"
            >
              Revisar en Validaciones <i class="bi bi-box-arrow-up-right"></i>
            </RouterLink>
          </div>
          <div v-for="doc in verification.documents" :key="doc.uuid" class="doc-row">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <span class="fw-semibold small">{{ docTypeLabel(doc.doc_type) }}</span>
                <span class="badge ms-2" :class="enums.cssClass('kyc-document-statuses', doc.status)">
                  {{ enums.label('kyc-document-statuses', doc.status, doc.status) }}
                </span>
              </div>
              <div class="d-flex gap-1">
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="viewDocument(doc)">
                  <i class="bi bi-eye"></i>
                </button>
                <template v-if="reviewable">
                  <button v-if="doc.status !== 'APPROVED'" type="button" class="btn btn-sm btn-outline-success"
                    :disabled="reviewingDocUuid === doc.uuid" @click="reviewDocument(doc, true)">
                    <i class="bi bi-check-lg"></i>
                  </button>
                  <button v-if="doc.status !== 'REJECTED'" type="button" class="btn btn-sm btn-outline-danger"
                    :disabled="reviewingDocUuid === doc.uuid" @click="toggleDocReject(doc)">
                    <i class="bi bi-x-lg"></i>
                  </button>
                </template>
              </div>
            </div>
            <div v-if="doc.rejection_reason" class="small text-danger mt-1">{{ doc.rejection_reason }}</div>
            <div v-if="reviewable && docRejectOpenUuid === doc.uuid" class="mt-2">
              <textarea v-model="docRejectReason" class="form-control form-control-sm mb-2" rows="2"
                placeholder="Motivo del rechazo..."></textarea>
              <button type="button" class="btn btn-sm btn-danger me-2" :disabled="reviewingDocUuid === doc.uuid"
                @click="reviewDocument(doc, false)">Confirmar rechazo</button>
              <button type="button" class="btn btn-sm btn-light" @click="docRejectOpenUuid = null">Cancelar</button>
            </div>
          </div>
          <div v-if="!verification.documents.length" class="text-muted small">Sin documentos subidos aun.</div>
        </div>
      </div>
    </div>

    <!-- Timeline -->
    <div class="detail-card mt-3">
      <h6 class="fw-bold mb-3">Historial</h6>
      <ul class="timeline-list list-unstyled small mb-0">
        <li v-for="event in verification.timeline_events" :key="event.uuid" class="mb-2">
          <span class="fw-semibold">{{ eventLabel(event.event_type) }}</span>
          <span class="text-muted"> — {{ formatDate(event.created_at) }}</span>
          <span v-if="event.actor_email" class="text-muted"> ({{ event.actor_email }})</span>
          <div v-if="event.description" class="text-muted">{{ event.description }}</div>
        </li>
        <li v-if="!verification.timeline_events?.length" class="text-muted">Sin eventos registrados.</li>
      </ul>
    </div>

    <!-- Acciones de nivel verificacion -->
    <div class="detail-card mt-3">
      <h6 class="fw-bold mb-3">{{ reviewable ? 'Acciones' : 'Dar de alta' }}</h6>
      <p v-if="!reviewable" class="small text-muted">
        La revision documento por documento se hace desde
        <RouterLink :to="{ name: 'kyc-admin-detail', params: { uuid: verification.uuid } }">Validaciones</RouterLink>.
        Aqui solo se valida que los documentos esten aprobados y se activa el acceso del usuario.
      </p>

      <div v-if="hasAnyAction" class="d-flex flex-wrap gap-2 mb-3">
        <button v-if="canApprove" type="button" class="btn btn-success" :disabled="actionLoading" @click="approve">
          <i class="bi bi-check-circle me-1"></i>Aprobar verificacion completa
        </button>
        <button v-if="canForceApprove" type="button" class="btn btn-outline-primary" @click="openAction = openAction === 'force' ? null : 'force'">
          <i class="bi bi-lightning-charge me-1"></i>Aprobacion manual
        </button>
        <template v-if="reviewable">
          <button v-if="canReject" type="button" class="btn btn-outline-danger" @click="openAction = openAction === 'reject' ? null : 'reject'">
            Rechazar
          </button>
          <button v-if="canRequestInfo" type="button" class="btn btn-outline-warning" @click="openAction = openAction === 'info' ? null : 'info'">
            Solicitar informacion
          </button>
          <button v-if="canBlock" type="button" class="btn btn-outline-dark" @click="openAction = openAction === 'block' ? null : 'block'">
            Bloquear
          </button>
        </template>
      </div>
      <p v-else class="text-muted small mb-0">{{ noActionsMessage }}</p>

      <div v-if="canForceApprove && openAction === 'force'" class="action-form">
        <p class="small text-primary">
          <i class="bi bi-exclamation-triangle me-1"></i>
          Esto activa el acceso del usuario de inmediato, sin exigir que cada documento este
          individualmente revisado. Quedara registrado como una aprobacion manual.
        </p>
        <textarea v-model="noteText" class="form-control mb-2" rows="2" placeholder="Nota (opcional)..."></textarea>
        <button type="button" class="btn btn-primary btn-sm" :disabled="actionLoading" @click="forceApprove">
          Confirmar aprobacion manual
        </button>
      </div>
      <div v-if="reviewable && canReject && openAction === 'reject'" class="action-form">
        <textarea v-model="reasonText" class="form-control mb-2" rows="2" placeholder="Motivo del rechazo..."></textarea>
        <button type="button" class="btn btn-danger btn-sm" :disabled="actionLoading" @click="reject">Confirmar rechazo</button>
      </div>
      <div v-if="reviewable && canRequestInfo && openAction === 'info'" class="action-form">
        <textarea v-model="messageText" class="form-control mb-2" rows="2" placeholder="Que informacion necesitas del solicitante..."></textarea>
        <button type="button" class="btn btn-warning btn-sm" :disabled="actionLoading" @click="requestInfo">Enviar solicitud</button>
      </div>
      <div v-if="reviewable && canBlock && openAction === 'block'" class="action-form">
        <textarea v-model="reasonText" class="form-control mb-2" rows="2" placeholder="Motivo del bloqueo..."></textarea>
        <button type="button" class="btn btn-dark btn-sm" :disabled="actionLoading" @click="block">Confirmar bloqueo</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';

const props = defineProps({
  verification: { type: Object, required: true },
  reviewable: { type: Boolean, default: true },
});
const emit = defineEmits(['changed']);

const api = useApi();
const toast = useToast();
const enums = useEnums();
enums.ensure('user-types');

const DOC_TYPE_LABELS = {
  CEDULA_FRONTAL: 'Cedula (frontal)',
  CEDULA_REVERSO: 'Cedula (reverso)',
  RUT: 'RUT',
  HOJA_VIDA: 'Hoja de vida / CV',
  DIPLOMA: 'Diploma',
  CERTIFICACION: 'Certificacion',
  ANTECEDENTES_POLICIA: 'Antecedentes de Policia',
  ANTECEDENTES_CONTRALORIA: 'Antecedentes de Contraloria',
  ANTECEDENTES_PROCURADURIA: 'Antecedentes de Procuraduria',
  OTRO: 'Otro',
};

const EVENT_LABELS = {
  CREATED: 'Verificacion creada', SUBMITTED_FOR_REVIEW: 'Enviado a revision',
  APPROVED: 'Aprobado', REJECTED: 'Rechazado', INFO_REQUESTED: 'Informacion solicitada',
  BLOCKED: 'Bloqueado', DOC_UPLOADED: 'Documento subido', DOC_DELETED: 'Documento eliminado',
  DOC_OPENED: 'Documento abierto por admin', DOC_APPROVED: 'Documento aprobado',
  DOC_REJECTED: 'Documento rechazado', NOTE: 'Nota',
};

const reviewingDocUuid = ref(null);
const docRejectOpenUuid = ref(null);
const docRejectReason = ref('');
const openAction = ref(null);
const reasonText = ref('');
const messageText = ref('');
const noteText = ref('');
const actionLoading = ref(false);

const fullName = computed(() => {
  const v = props.verification;
  return [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido].filter(Boolean).join(' ');
});
const addressLine = computed(() => {
  const v = props.verification;
  return [v.direccion, v.ciudad, v.pais].filter(Boolean).join(', ') || '—';
});

// Espeja kyc/services/config.py::ALLOWED_TRANSITIONS + los chequeos de
// precondicion en KycCommands -- evita ofrecer una accion que el backend
// va a rechazar con 400 por estar en el estado equivocado.
const canApprove = computed(() => props.verification.status === 'UNDER_REVIEW');
const canForceApprove = computed(() => ['PENDING', 'UNDER_REVIEW', 'REJECTED'].includes(props.verification.status));
const canReject = computed(() => props.verification.status === 'UNDER_REVIEW');
const canRequestInfo = computed(() => props.verification.status === 'UNDER_REVIEW');
const canBlock = computed(() => ['PENDING', 'UNDER_REVIEW', 'APPROVED'].includes(props.verification.status));
const hasAnyAction = computed(() => {
  if (canApprove.value || canForceApprove.value) return true;
  if (props.reviewable && (canReject.value || canRequestInfo.value || canBlock.value)) return true;
  return false;
});
const noActionsMessage = computed(() => {
  const status = props.verification.status;
  if (status === 'BLOCKED') return 'La verificacion esta bloqueada (estado terminal, sin acciones disponibles).';
  if (status === 'APPROVED' && !props.reviewable) return 'El usuario ya esta aprobado; su acceso ya esta activo.';
  return `No hay acciones disponibles para el estado actual (${status}).`;
});

function docTypeLabel(type) { return DOC_TYPE_LABELS[type] || type; }
function eventLabel(type) { return EVENT_LABELS[type] || type; }
function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
}

function resetForms() {
  openAction.value = null;
  reasonText.value = '';
  messageText.value = '';
  noteText.value = '';
  docRejectOpenUuid.value = null;
  docRejectReason.value = '';
}

async function viewDocument(doc) {
  try {
    const res = await api.get(`auth/documents/${doc.uuid}/download/`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (e) {
    toast.error('No se pudo abrir el documento.');
  }
}

function toggleDocReject(doc) {
  docRejectOpenUuid.value = docRejectOpenUuid.value === doc.uuid ? null : doc.uuid;
  docRejectReason.value = '';
}

async function reviewDocument(doc, approved) {
  reviewingDocUuid.value = doc.uuid;
  try {
    await api.post(`auth/admin/verifications/${props.verification.uuid}/documents/${doc.uuid}/review/`, {
      approved, reason: approved ? '' : docRejectReason.value,
    });
    toast.success('Documento revisado.');
    docRejectOpenUuid.value = null;
    emit('changed');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'No se pudo revisar el documento.');
  } finally {
    reviewingDocUuid.value = null;
  }
}

async function approve() {
  actionLoading.value = true;
  try {
    await api.post(`auth/admin/verifications/${props.verification.uuid}/approve/`);
    toast.success('Verificacion aprobada.');
    resetForms();
    emit('changed');
  } catch (e) {
    toast.error(e.response?.data?.documents || e.response?.data?.detail || 'No se pudo aprobar.');
  } finally {
    actionLoading.value = false;
  }
}

async function forceApprove() {
  if (!confirm('¿Aprobar manualmente? Esto activa el acceso del usuario de inmediato sin revisar cada documento.')) return;
  actionLoading.value = true;
  try {
    await api.post(`auth/admin/verifications/${props.verification.uuid}/force-approve/`, { note: noteText.value });
    toast.success('Usuario aprobado manualmente. Su acceso ya esta activo.');
    resetForms();
    emit('changed');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'No se pudo aprobar manualmente.');
  } finally {
    actionLoading.value = false;
  }
}

async function reject() {
  actionLoading.value = true;
  try {
    await api.post(`auth/admin/verifications/${props.verification.uuid}/reject/`, { reason: reasonText.value });
    toast.success('Verificacion rechazada.');
    resetForms();
    emit('changed');
  } catch (e) {
    toast.error(e.response?.data?.reason?.[0] || e.response?.data?.detail || 'No se pudo rechazar.');
  } finally {
    actionLoading.value = false;
  }
}

async function requestInfo() {
  actionLoading.value = true;
  try {
    await api.post(`auth/admin/verifications/${props.verification.uuid}/request-info/`, { message: messageText.value });
    toast.success('Solicitud de informacion enviada.');
    resetForms();
    emit('changed');
  } catch (e) {
    toast.error(e.response?.data?.message?.[0] || e.response?.data?.detail || 'No se pudo enviar la solicitud.');
  } finally {
    actionLoading.value = false;
  }
}

async function block() {
  actionLoading.value = true;
  try {
    await api.post(`auth/admin/verifications/${props.verification.uuid}/block/`, { reason: reasonText.value });
    toast.success('Verificacion bloqueada.');
    resetForms();
    emit('changed');
  } catch (e) {
    toast.error(e.response?.data?.reason?.[0] || e.response?.data?.detail || 'No se pudo bloquear.');
  } finally {
    actionLoading.value = false;
  }
}
</script>

<style scoped>
.detail-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  height: 100%;
}
.doc-row { padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.doc-row:last-child { border-bottom: none; }
.action-form { max-width: 480px; margin-top: 8px; }
.smaller { font-size: 0.8rem; }
</style>
