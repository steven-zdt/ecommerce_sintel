<template>
  <div>
    <template v-if="!wizard.createdQuotation.value">
      <h1 class="step-title">Revisa tu solicitud</h1>
      <p class="step-subtitle">Verifica los ítems y tus datos antes de enviar.</p>

      <div class="booking-card mb-3">
        <span class="soft-badge">Solicitante</span>
        <p class="mt-2 mb-0 fw-semibold">{{ wizard.applicant.client_name }} · {{ wizard.applicant.client_email }}</p>
        <p class="text-muted small mb-0">Válida hasta {{ wizard.applicant.valid_until }}</p>
      </div>

      <div class="booking-card mb-3">
        <span class="soft-badge">Selección ({{ wizard.cart.length }})</span>
        <div v-for="c in wizard.cart" :key="c.key" class="row-line">
          <span>{{ c.name }} <span class="text-muted">x{{ c.quantity }}</span></span>
          <span class="text-muted">${{ fmt(c.unitPrice * c.quantity) }}</span>
        </div>
        <div class="row-line fw-bold">
          <span>Total estimado</span>
          <span>${{ fmt(wizard.cartTotal.value) }}</span>
        </div>
      </div>

      <button class="btn-submit" :disabled="wizard.submitting.value" @click="handleSubmit">
        <span v-if="wizard.submitting.value" class="spinner-border spinner-border-sm me-2"></span>
        Solicitar cotización
      </button>
      <p v-if="wizard.error.value" class="text-danger small mt-2">{{ wizard.error.value }}</p>
    </template>

    <template v-else>
      <div class="success-box">
        <i class="bi bi-check-circle-fill"></i>
        <h1 class="step-title">¡Listo! Tu cotización fue generada</h1>
        <p class="step-subtitle">
          Total: <strong>${{ fmt(wizard.createdQuotation.value.total_amount) }}</strong> ·
          enviada a <strong>{{ wizard.createdQuotation.value.client_email }}</strong>.
        </p>
        <p class="text-muted small">Referencia: <code>{{ wizard.createdQuotation.value.uuid }}</code></p>
        <div class="d-flex gap-2 justify-content-center flex-wrap mt-3">
          <a :href="pdfUrl" target="_blank" class="btn btn-success btn-lg px-4">
            <i class="bi bi-file-earmark-pdf me-1"></i>Descargar PDF
          </a>
          <RouterLink to="/cotizar/catalogo" class="btn btn-outline-secondary btn-lg px-4" @click="wizard.clear()">
            Nueva cotización
          </RouterLink>
          <RouterLink to="/" class="btn btn-outline-secondary btn-lg px-4">
            Volver al inicio
          </RouterLink>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import useApi from '@/composables/useApi';
import { formatCOP } from '@/utils/money';

const props = defineProps({ wizard: { type: Object, required: true } });

const api = useApi();
const pdfUrl = computed(() => `${api.defaults.baseURL}quotes/quotations/${props.wizard.createdQuotation.value?.uuid}/download_pdf/`);

async function handleSubmit() {
  await props.wizard.submitQuotation();
}

const fmt = (val) => formatCOP(val);
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 2rem; }
.booking-card { background: #fff; border: 1px solid #e8e7ee; border-radius: 18px; padding: 1.2rem 1.4rem; }
.soft-badge { display: inline-block; background: #dcfce7; color: #15803d; border-radius: 999px; padding: 0.3rem 0.7rem; font-size: 0.72rem; font-weight: 750; text-transform: uppercase; }
.row-line { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; }
.row-line:last-child { border-bottom: none; }
.btn-submit {
  width: 100%; border: 0; border-radius: 999px; background: #16a34a; color: #fff;
  padding: 1rem; font-weight: 750; margin-top: 1.4rem; cursor: pointer;
}
.btn-submit:disabled { opacity: 0.6; }
.success-box { text-align: center; padding: 3rem 1rem; }
.success-box i { font-size: 3.5rem; color: #16a34a; margin-bottom: 1rem; display: block; }
</style>
