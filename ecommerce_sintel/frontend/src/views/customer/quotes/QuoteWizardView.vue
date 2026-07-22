<template>
  <div class="qw-root">
    <div class="qw-bg-glow qw-glow-1"></div>
    <div class="qw-bg-glow qw-glow-2"></div>

    <div class="container py-5" style="max-width:1140px; position:relative">
      <div class="qw-header">
        <div class="qw-header-icon">
          <i class="bi bi-file-earmark-text"></i>
        </div>
        <nav class="qw-breadcrumb">
          <RouterLink to="/" class="qw-bc-link">Inicio</RouterLink>
          <span class="qw-bc-sep">/</span>
          <span class="qw-bc-current">Cotizar</span>
        </nav>
        <h1 class="qw-title">Solicitar Cotización</h1>
        <p class="qw-sub">Responde unas preguntas — un asesor te enviará la cotización con precios.</p>
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

      <div class="qw-layout" :class="{ 'qw-layout--solo': !showSidebar }">
        <div class="qw-card">
          <ApplicantStep v-if="wizard.step.value === STEP_DESTINATARIO" ref="stepRef" :wizard="wizard" />
          <TemplateSelectStep v-else-if="wizard.step.value === STEP_TEMPLATE" :wizard="wizard" @next="goNext" />
          <EquipmentQuestionsStep v-else-if="wizard.step.value === STEP_EQUIPMENT" ref="stepRef" :wizard="wizard" />
          <MaterialQuestionsStep v-else-if="wizard.step.value === STEP_MATERIALS" ref="stepRef" :wizard="wizard" />
          <LaborQuestionsStep v-else-if="wizard.step.value === STEP_LABOR" ref="stepRef" :wizard="wizard" />
          <QuoteSummaryStep v-else :wizard="wizard" />

          <div v-if="!wizard.createdQuotation.value" class="qw-nav">
            <button v-if="wizard.step.value > 0" class="btn-back" @click="goBack">
              <i class="bi bi-arrow-left me-1"></i>Atrás
            </button>
            <span v-else></span>
            <button
              v-if="wizard.step.value < wizard.steps.length - 1 && wizard.step.value !== STEP_TEMPLATE"
              class="btn-next" :disabled="!canAdvance" @click="goNext"
            >
              Continuar<i class="bi bi-arrow-right ms-1"></i>
            </button>
          </div>
        </div>

        <QuoteWizardSidebar v-if="showSidebar" :wizard="wizard" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuoteWizard } from '@/composables/useQuoteWizard';
import TemplateSelectStep from './TemplateSelectStep.vue';
import ApplicantStep from './ApplicantStep.vue';
import EquipmentQuestionsStep from './EquipmentQuestionsStep.vue';
import MaterialQuestionsStep from './MaterialQuestionsStep.vue';
import LaborQuestionsStep from './LaborQuestionsStep.vue';
import QuoteSummaryStep from './QuoteSummaryStep.vue';
import QuoteWizardSidebar from './QuoteWizardSidebar.vue';

const STEP_DESTINATARIO = 0;
const STEP_TEMPLATE = 1;
const STEP_EQUIPMENT = 2;
const STEP_MATERIALS = 3;
const STEP_LABOR = 4;

const wizard = useQuoteWizard();
const stepRef = ref(null);

const VALIDATED_STEPS = {
  [STEP_DESTINATARIO]: () => wizard.validateApplicant(),
  [STEP_EQUIPMENT]: () => wizard.validateModuleType('EQUIPMENT'),
  [STEP_MATERIALS]: () => wizard.validateModuleType('MATERIALS'),
  [STEP_LABOR]: () => wizard.validateModuleType('LABOR'),
};

const canAdvance = computed(() => {
  const validator = VALIDATED_STEPS[wizard.step.value];
  if (!validator) return true;
  return stepRef.value?.isValid ?? validator();
});

// Resumen lateral: visible desde que se elige la Plantilla (step >= 1) hasta
// antes de enviar la solicitud -- en Destinatario (step 0) no hay progreso
// de plantilla/preguntas que mostrar todavia. Ver PLAN_MAESTRO_QUOTES_UX.md
// Fase B.
const showSidebar = computed(() => wizard.step.value >= STEP_TEMPLATE && !wizard.createdQuotation.value);

function goNext() {
  if (!canAdvance.value) return;
  if (wizard.step.value < wizard.steps.length - 1) wizard.step.value += 1;
}

function goBack() {
  if (wizard.step.value > 0) wizard.step.value -= 1;
}

onMounted(async () => {
  const savedTemplateUuid = wizard.restore();
  if (savedTemplateUuid) {
    await wizard.selectTemplate(savedTemplateUuid);
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
  width: 56px; height: 56px; border-radius: 16px; background: #6d28d9; color: #fff;
  display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;
}
.qw-breadcrumb { font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.6rem; }
.qw-bc-link { color: #94a3b8; text-decoration: none; }
.qw-bc-sep { margin: 0 0.4rem; }
.qw-bc-current { color: #6d28d9; font-weight: 600; }
.qw-title { font-size: clamp(2rem, 5vw, 2.8rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.qw-sub { color: #64748b; }

.qw-stepper { display: flex; align-items: center; justify-content: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 0.4rem 0; }
.qw-step { display: flex; flex-direction: column; align-items: center; gap: 0.35rem; }
.qw-step-circle {
  width: 34px; height: 34px; border-radius: 50%; background: #fff; border: 2px solid #e2e8f0;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; color: #94a3b8;
}
.qw-step-active .qw-step-circle { border-color: #7c3aed; color: #7c3aed; }
.qw-step-done .qw-step-circle { background: #7c3aed; border-color: #7c3aed; color: #fff; }
.qw-step-label { font-size: 0.68rem; color: #94a3b8; font-weight: 600; }
.qw-step-active .qw-step-label, .qw-step-done .qw-step-label { color: #6d28d9; }
.qw-step-line { width: 28px; height: 2px; background: #e2e8f0; margin: 0 0.3rem; }

.qw-layout { display: grid; grid-template-columns: 1fr 300px; gap: 2rem; align-items: start; }
.qw-layout--solo { grid-template-columns: 1fr; max-width: 880px; margin: 0 auto; }
.qw-card { background: #fff; border-radius: 24px; padding: 2rem; box-shadow: 0 10px 40px rgba(15, 23, 42, 0.06); min-width: 0; }

@media (max-width: 991px) {
  .qw-layout { grid-template-columns: 1fr; }
}

.qw-nav { display: flex; justify-content: space-between; margin-top: 2rem; padding-top: 1.4rem; border-top: 1px solid #f1f5f9; }
.btn-back { background: none; border: 0; color: #64748b; font-weight: 650; cursor: pointer; padding: 0.7rem 1rem; }
.btn-next {
  border: 0; border-radius: 999px; background: #6d28d9; color: #fff;
  padding: 0.8rem 1.6rem; font-weight: 750; cursor: pointer;
}
.btn-next:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
