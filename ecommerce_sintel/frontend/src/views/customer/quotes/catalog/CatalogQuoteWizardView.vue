<template>
  <div class="qw-root">
    <div class="qw-bg-glow qw-glow-1"></div>
    <div class="qw-bg-glow qw-glow-2"></div>

    <div class="container py-5" style="max-width:1080px; position:relative">
      <div class="qw-header">
        <div class="qw-header-icon">
          <i class="bi bi-bag-check"></i>
        </div>
        <nav class="qw-breadcrumb">
          <RouterLink to="/" class="qw-bc-link">Inicio</RouterLink>
          <span class="qw-bc-sep">/</span>
          <RouterLink to="/cotizar" class="qw-bc-link">Cotizar</RouterLink>
          <span class="qw-bc-sep">/</span>
          <span class="qw-bc-current">Catálogo</span>
        </nav>
        <h1 class="qw-title">Cotización de Catálogo</h1>
        <p class="qw-sub">Elige productos, equipos en renta y servicios — ve el precio al instante.</p>
      </div>

      <div v-if="!wizard.createdQuotation.value" class="qw-stepper">
        <template v-for="(label, i) in wizard.steps" :key="i">
          <div class="qw-step" :class="{ 'qw-step-active': wizard.step.value === i, 'qw-step-done': wizard.step.value > i }">
            <div class="qw-step-circle">
              <i v-if="wizard.step.value > i" class="bi bi-check-lg"></i>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <span class="qw-step-label d-none d-sm-block">{{ label }}</span>
          </div>
          <div v-if="i < wizard.steps.length - 1" class="qw-step-line"></div>
        </template>
      </div>

      <div class="qw-card">
        <CatalogBrowseStep v-if="wizard.step.value === STEP_BROWSE" :wizard="wizard" />
        <CatalogApplicantStep v-else-if="wizard.step.value === STEP_APPLICANT" :wizard="wizard" />
        <CatalogSummaryStep v-else :wizard="wizard" />

        <div v-if="!wizard.createdQuotation.value" class="qw-nav">
          <button v-if="wizard.step.value > 0" class="btn-back" @click="goBack">
            <i class="bi bi-arrow-left me-1"></i>Atrás
          </button>
          <span v-else></span>
          <button
            v-if="wizard.step.value < wizard.steps.length - 1"
            class="btn-next" :disabled="!canAdvance" @click="goNext"
          >
            Continuar<i class="bi bi-arrow-right ms-1"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useCatalogQuoteWizard } from '@/composables/useCatalogQuoteWizard';
import CatalogBrowseStep from './CatalogBrowseStep.vue';
import CatalogApplicantStep from './CatalogApplicantStep.vue';
import CatalogSummaryStep from './CatalogSummaryStep.vue';

const STEP_BROWSE = 0;
const STEP_APPLICANT = 1;

const route = useRoute();
const wizard = useCatalogQuoteWizard();

const canAdvance = computed(() => {
  if (wizard.step.value === STEP_BROWSE) return wizard.cart.length > 0;
  if (wizard.step.value === STEP_APPLICANT) return wizard.validateApplicant();
  return true;
});

function goNext() {
  if (!canAdvance.value) return;
  if (wizard.step.value < wizard.steps.length - 1) wizard.step.value += 1;
}

function goBack() {
  if (wizard.step.value > 0) wizard.step.value -= 1;
}

onMounted(async () => {
  await Promise.all([wizard.fetchProducts(), wizard.fetchEquipment(), wizard.fetchServices()]);

  // Deep-link desde ProductDetailView.vue / RentalDetailView.vue: preseleccionar
  // el item en el carrito para que el cliente no tenga que buscarlo de nuevo.
  const productUuid = route.query.product;
  const equipmentUuid = route.query.equipment;
  if (productUuid) {
    const product = wizard.findProductByUuid(productUuid);
    const variant = wizard.defaultVariant(product);
    if (product && variant) wizard.addProduct(product, variant, 1);
  }
  if (equipmentUuid) {
    const item = wizard.findEquipmentByUuid(equipmentUuid);
    const variant = wizard.defaultVariant(item);
    if (item && variant) {
      const start = new Date();
      const end = new Date();
      end.setDate(end.getDate() + 1);
      wizard.addEquipment(item, variant, start.toISOString().slice(0, 10), end.toISOString().slice(0, 10));
    }
  }
});
</script>

<style scoped>
.qw-root { position: relative; min-height: 100vh; overflow: hidden; background: #fafafa; }
.qw-bg-glow { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.25; pointer-events: none; }
.qw-glow-1 { width: 420px; height: 420px; background: #a78bfa; top: -120px; right: -100px; }
.qw-glow-2 { width: 380px; height: 380px; background: #7c3aed; bottom: -140px; left: -100px; }

.qw-header { text-align: center; margin-bottom: 2rem; }
.qw-header-icon {
  width: 56px; height: 56px; border-radius: 16px; background: #16a34a; color: #fff;
  display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;
}
.qw-breadcrumb { font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.6rem; }
.qw-bc-link { color: #94a3b8; text-decoration: none; }
.qw-bc-sep { margin: 0 0.4rem; }
.qw-bc-current { color: #16a34a; font-weight: 600; }
.qw-title { font-size: clamp(2rem, 5vw, 2.8rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.qw-sub { color: #64748b; }

.qw-stepper { display: flex; align-items: center; justify-content: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 0.4rem 0; }
.qw-step { display: flex; flex-direction: column; align-items: center; gap: 0.35rem; }
.qw-step-circle {
  width: 34px; height: 34px; border-radius: 50%; background: #fff; border: 2px solid #e2e8f0;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; color: #94a3b8;
}
.qw-step-active .qw-step-circle { border-color: #16a34a; color: #16a34a; }
.qw-step-done .qw-step-circle { background: #16a34a; border-color: #16a34a; color: #fff; }
.qw-step-label { font-size: 0.68rem; color: #94a3b8; font-weight: 600; }
.qw-step-active .qw-step-label, .qw-step-done .qw-step-label { color: #16a34a; }
.qw-step-line { width: 28px; height: 2px; background: #e2e8f0; margin: 0 0.3rem; }

.qw-card { background: #fff; border-radius: 24px; padding: 2rem; box-shadow: 0 10px 40px rgba(15, 23, 42, 0.06); }

.qw-nav { display: flex; justify-content: space-between; margin-top: 2rem; padding-top: 1.4rem; border-top: 1px solid #f1f5f9; }
.btn-back { background: none; border: 0; color: #64748b; font-weight: 650; cursor: pointer; padding: 0.7rem 1rem; }
.btn-next {
  border: 0; border-radius: 999px; background: #16a34a; color: #fff;
  padding: 0.8rem 1.6rem; font-weight: 750; cursor: pointer;
}
.btn-next:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
