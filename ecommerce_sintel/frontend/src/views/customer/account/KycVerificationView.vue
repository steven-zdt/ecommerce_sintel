<template>
  <div class="kyc-verification-page">
    <CustomerSkeleton v-if="loading" :count="3" height="90px" />

    <div v-else-if="verification" class="kyc-card">
      <h1 class="h4 fw-bold mb-1">Verificacion de identidad</h1>

      <!-- PENDING / REJECTED: subir documentos ------------------------------>
      <template v-if="verification.status === 'PENDING' || verification.status === 'REJECTED'">
        <p class="text-muted small mb-4">
          Tu cuenta fue creada. Para poder comprar y ofrecer servicios en {{ brandName }},
          sube los siguientes documentos y envialos a revision.
        </p>

        <div v-if="verification.status === 'REJECTED' && verification.admin_message"
          class="alert alert-danger small mb-4">
          <strong>Tu verificacion fue rechazada:</strong> {{ verification.admin_message }}
        </div>

        <KycDocumentUploadStep
          :documents="verification.documents"
          :verification-status="verification.status"
          @changed="reload"
        />

        <button type="button" class="btn btn-primary w-100 py-3 fw-bold mt-4"
          :disabled="!allRequiredUploaded || submitting" @click="submitForReview">
          <span v-if="submitting" class="spinner-border spinner-border-sm me-2"></span>
          {{ submitting ? 'Enviando...' : 'Enviar a revision' }}
        </button>
        <div v-if="!allRequiredUploaded" class="form-text text-center mt-2">
          Sube los 5 documentos obligatorios para poder enviar tu verificacion a revision.
        </div>
      </template>

      <!-- UNDER_REVIEW --------------------------------------------------->
      <template v-else-if="verification.status === 'UNDER_REVIEW'">
        <div class="text-center py-4">
          <i class="bi bi-hourglass-split display-4 text-warning"></i>
          <p class="mt-3 mb-0">
            Tu documentacion esta en revision. Te avisaremos por correo cuando
            nuestro equipo termine.
          </p>
        </div>
      </template>

      <!-- APPROVED ----------------------------------------------------->
      <template v-else-if="verification.status === 'APPROVED'">
        <div class="text-center py-4">
          <i class="bi bi-patch-check-fill display-4 text-success"></i>
          <p class="mt-3 mb-3">Tu cuenta ya esta verificada.</p>
          <RouterLink to="/mi-cuenta/perfil" class="btn btn-primary">Ir a mi perfil</RouterLink>
        </div>
      </template>

      <!-- BLOCKED -------------------------------------------------------->
      <template v-else-if="verification.status === 'BLOCKED'">
        <div class="text-center py-4">
          <i class="bi bi-slash-circle display-4 text-danger"></i>
          <p class="mt-3 mb-0">Tu cuenta ha sido bloqueada.</p>
          <p v-if="verification.admin_message" class="text-muted small">{{ verification.admin_message }}</p>
        </div>
      </template>

      <div v-if="isContractorType" class="text-center mt-4 pt-3 border-top">
        <p class="small text-muted mb-2">Ademas de tu verificacion de identidad, puedes completar tu solicitud de Asociado de Negocio:</p>
        <RouterLink :to="{ name: 'contractor-onboarding' }" class="btn btn-outline-primary btn-sm">
          Completar solicitud de Asociado de Negocio
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { kycService } from '@/services/kyc/kycService';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useAuthStore } from '@/store/auth';
import { useAppConfigStore } from '@/store/appConfig';
import KycDocumentUploadStep from '@/components/auth/kyc/KycDocumentUploadStep.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

const toast = useToast();
const { handleError } = useErrorHandler();
const authStore = useAuthStore();
// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado.
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'la plataforma');

const loading = ref(true);
const submitting = ref(false);
const verification = ref(null);

const REQUIRED_DOC_TYPES = ['CEDULA_FRONTAL', 'CEDULA_REVERSO', 'RUT', 'HOJA_VIDA', 'DIPLOMA'];

const allRequiredUploaded = computed(() => {
  if (!verification.value) return false;
  return REQUIRED_DOC_TYPES.every(type =>
    verification.value.documents.some(d => d.doc_type === type && d.status !== 'REJECTED')
  );
});

const isContractorType = computed(() => {
  const userType = authStore.user?.profile?.user_type;
  return ['PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR', 'TECHNICIAN'].includes(userType);
});

async function reload() {
  try {
    verification.value = await kycService.myVerification();
  } catch (e) {
    toast.error('No se pudo cargar tu estado de verificacion.');
  }
}

async function submitForReview() {
  submitting.value = true;
  try {
    await kycService.submitForReview();
    toast.success('Tu documentacion fue enviada a revision.');
    await reload();
  } catch (e) {
    handleError(e, 'No se pudo enviar a revision.');
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  await reload();
  loading.value = false;
});
</script>

<style scoped>
.kyc-verification-page {
  max-width: 700px;
  margin: 0 auto;
  padding: 32px 20px;
}
.kyc-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 28px;
}
</style>
