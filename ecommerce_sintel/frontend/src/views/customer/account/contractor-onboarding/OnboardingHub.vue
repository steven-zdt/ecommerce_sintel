<template>
  <div>
    <CustomerPageHeader
      title="Solicitar cuenta como Asociado de Negocio"
      :subtitle="`Convierte tu cuenta en un Asociado de Negocio de ${brandName} y ofrece tus servicios profesionales en el marketplace.`"
    />

    <CustomerSkeleton v-if="loading" :count="3" height="120px" />
    <template v-else>
      <CustomerSection title="Estado actual" icon="bi-flag">
        <CustomerDetailRow label="Estado de la solicitud" icon="bi-hourglass-split">
          <span class="badge" :class="hubStatusClass">{{ hubStatusLabel }}</span>
        </CustomerDetailRow>
        <CustomerDetailRow v-if="verification?.requested_user_type" label="Tipo solicitado" icon="bi-briefcase">
          {{ typeLabelOf(verification.requested_user_type) }}
        </CustomerDetailRow>
      </CustomerSection>

      <CustomerSection title="Progreso" icon="bi-bar-chart-steps">
        <StatusTimeline mode="steps" :steps="hubSteps" :active-index="hubActiveIndex" accent-color="#7c3aed" />
      </CustomerSection>

      <CustomerSection title="Requisitos y Documentacion" icon="bi-file-earmark-check">
        <p class="text-muted small mb-3">Estos son los 5 documentos que se solicitan para verificar tu identidad y experiencia.</p>
        <div class="doc-req-list">
          <div v-for="doc in REQUIRED_DOCS" :key="doc.type" class="doc-req-row">
            <i class="bi" :class="isDocUploaded(doc.type) ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
            <span>{{ doc.label }}</span>
            <span v-if="isDocUploaded(doc.type)" class="badge bg-success-subtle text-success ms-auto">Enviado</span>
            <span v-else class="badge bg-secondary-subtle text-secondary ms-auto">Pendiente</span>
          </div>
        </div>
      </CustomerSection>

      <CustomerSection v-if="verification?.admin_message" title="Observaciones del administrador" icon="bi-chat-square-text">
        <p class="small mb-0">{{ verification.admin_message }}</p>
      </CustomerSection>

      <CustomerSection title="Pasos pendientes" icon="bi-list-check">
        <ul class="pending-steps mb-0">
          <li v-for="(step, i) in pendingSteps" :key="i">{{ step }}</li>
        </ul>
        <p v-if="!pendingSteps.length" class="text-success small mb-0">
          <i class="bi bi-check-circle-fill me-1"></i>No tienes pasos pendientes por ahora.
        </p>
      </CustomerSection>

      <div class="d-flex justify-content-end mt-4">
        <CustomerButton v-if="hubPrimaryAction" variant="primary" size="md" @click="hubPrimaryAction.handler">
          {{ hubPrimaryAction.label }}
        </CustomerButton>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAppConfigStore } from '@/store/appConfig';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerSection from '@/components/customer/account/CustomerSection.vue';
import CustomerDetailRow from '@/components/customer/account/CustomerDetailRow.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

const props = defineProps({
  loading: { type: Boolean, default: false },
  verification: { type: Object, default: null },
  isAlreadyProfessional: { type: Boolean, required: true },
  upgradeAlreadyRequested: { type: Boolean, required: true },
});
const emit = defineEmits(['start']);

const router = useRouter();
// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado.
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'la plataforma');

const REQUIRED_DOCS = [
  { type: 'CEDULA_FRONTAL', label: 'Cedula - frente' },
  { type: 'CEDULA_REVERSO', label: 'Cedula - reverso' },
  { type: 'RUT', label: 'RUT' },
  { type: 'HOJA_VIDA', label: 'Hoja de vida' },
  { type: 'DIPLOMA', label: 'Diploma o certificado' },
];

function isDocUploaded(docType) {
  return !!props.verification?.documents?.some(d => d.doc_type === docType && d.status !== 'REJECTED');
}

const TYPE_LABELS = { TECHNICIAN: 'Tecnico', PROFESSIONAL: 'Profesional', SPECIALIST: 'Especialista', CONTRACTOR: 'Contratista' };
function typeLabelOf(t) { return TYPE_LABELS[t] || t || ''; }

const hubSteps = [
  { key: 'request', label: 'Solicitud enviada', icon: 'bi-send' },
  { key: 'documents', label: 'Documentos', icon: 'bi-file-earmark-text' },
  { key: 'review', label: 'En revision', icon: 'bi-hourglass-split' },
  { key: 'approved', label: 'Aprobado', icon: 'bi-patch-check' },
];

const hubActiveIndex = computed(() => {
  if (props.isAlreadyProfessional) return 3;
  if (!props.upgradeAlreadyRequested) return 0;
  const status = props.verification?.status;
  if (status === 'APPROVED') return 3;
  if (status === 'UNDER_REVIEW') return 2;
  const allUploaded = REQUIRED_DOCS.every(d => isDocUploaded(d.type));
  return allUploaded ? 2 : 1;
});

const hubStatusLabel = computed(() => {
  if (props.isAlreadyProfessional) return 'Ya eres Asociado de Negocio';
  if (!props.upgradeAlreadyRequested) return 'Aun no has iniciado tu solicitud';
  const status = props.verification?.status;
  if (status === 'APPROVED') return 'Aprobado';
  if (status === 'UNDER_REVIEW') return 'En revision';
  if (status === 'REJECTED') return 'Rechazado - revisa las observaciones';
  if (status === 'BLOCKED') return 'Bloqueado';
  return 'Pendiente de documentacion';
});

const hubStatusClass = computed(() => {
  if (props.isAlreadyProfessional || props.verification?.status === 'APPROVED') return 'bg-success-subtle text-success';
  if (props.verification?.status === 'REJECTED' || props.verification?.status === 'BLOCKED') return 'bg-danger-subtle text-danger';
  if (props.upgradeAlreadyRequested) return 'bg-warning-subtle text-warning';
  return 'bg-secondary-subtle text-secondary';
});

const pendingSteps = computed(() => {
  if (props.isAlreadyProfessional) return [];
  if (!props.upgradeAlreadyRequested) return ['Inicia tu solicitud completando tu informacion profesional.'];
  const steps = [];
  const missing = REQUIRED_DOCS.filter(d => !isDocUploaded(d.type));
  if (missing.length) steps.push(`Sube ${missing.length} documento(s) pendiente(s): ${missing.map(d => d.label).join(', ')}.`);
  if (!missing.length && props.verification?.status !== 'UNDER_REVIEW' && props.verification?.status !== 'APPROVED') {
    steps.push('Envia tu documentacion a revision desde Verificacion de identidad.');
  }
  if (props.verification?.status === 'UNDER_REVIEW') steps.push('Espera la revision de nuestro equipo.');
  return steps;
});

const hubPrimaryAction = computed(() => {
  if (props.isAlreadyProfessional) {
    return { label: 'Editar mi perfil profesional', handler: () => emit('start') };
  }
  if (!props.upgradeAlreadyRequested) {
    return { label: 'Iniciar solicitud', handler: () => emit('start') };
  }
  const allUploaded = REQUIRED_DOCS.every(d => isDocUploaded(d.type));
  if (!allUploaded) {
    return { label: 'Continuar solicitud', handler: () => emit('start') };
  }
  if (props.verification?.status !== 'APPROVED') {
    return { label: 'Ir a subir documentos', handler: () => router.push({ name: 'kyc-verification' }) };
  }
  return null;
});
</script>
