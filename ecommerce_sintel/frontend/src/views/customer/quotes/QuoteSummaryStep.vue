<template>
  <div>
    <template v-if="!wizard.createdQuotation.value">
      <h1 class="step-title">Revisa tu solicitud</h1>
      <p class="step-subtitle">Verifica tus respuestas — un asesor las usará para preparar tu cotización.</p>

      <div class="booking-card mb-3">
        <span class="soft-badge">Plantilla</span>
        <p class="mt-2 mb-0 fw-semibold">{{ wizard.selectedTemplate.value?.name }}</p>
      </div>

      <div class="booking-card mb-3">
        <span class="soft-badge">Solicitante</span>
        <p class="mt-2 mb-0">{{ wizard.applicant.client_name }} · {{ wizard.applicant.client_email }}</p>
      </div>

      <div class="booking-card mb-3" v-for="group in groups" :key="group.type" v-show="group.rows.length">
        <span class="soft-badge">{{ group.label }}</span>
        <div v-for="row in group.rows" :key="row.key" class="row-line">
          <span>{{ row.label }}</span>
          <span class="text-muted">{{ row.display }}</span>
        </div>
      </div>

      <button class="btn-submit" :disabled="wizard.submitting.value" @click="handleSubmit">
        <span v-if="wizard.submitting.value" class="spinner-border spinner-border-sm me-2"></span>
        Enviar solicitud
      </button>
      <p v-if="wizard.error.value" class="text-danger small mt-2">{{ wizard.error.value }}</p>
    </template>

    <template v-else>
      <div class="success-box">
        <i class="bi bi-check-circle-fill"></i>
        <h1 class="step-title">¡Listo! Tu solicitud fue recibida</h1>
        <p class="step-subtitle">
          Un asesor comercial revisará tu requerimiento y te enviará la cotización a
          <strong>{{ wizard.applicant.client_email }}</strong>.
        </p>
        <p class="text-muted small">Referencia: <code>{{ wizard.createdQuotation.value.uuid }}</code></p>
        <div class="d-flex gap-2 justify-content-center flex-wrap mt-3">
          <RouterLink to="/cotizar/personalizada" class="btn btn-primary btn-lg px-4" @click="wizard.clear()">
            Nueva solicitud
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

const props = defineProps({ wizard: { type: Object, required: true } });

const GROUP_LABELS = { EQUIPMENT: 'Equipos', MATERIALS: 'Materiales', LABOR: 'Mano de Obra' };
const FILE_TYPES = ['IMAGE', 'FILE', 'SIGNATURE'];

const groups = computed(() => Object.entries(GROUP_LABELS).map(([type, label]) => {
  const modules = props.wizard.modulesByType(type);
  const rows = [];
  for (const module of modules) {
    for (const q of module.questions) {
      if (FILE_TYPES.includes(q.question_type)) {
        const file = props.wizard.files[props.wizard.fileKeyFor(module.uuid, q.key)];
        if (file) rows.push({ key: `${module.uuid}-${q.key}`, label: q.label, display: file.name });
        continue;
      }
      const value = props.wizard.answerFor(module.uuid, q.key);
      if (value === undefined || value === null || value === '') continue;
      rows.push({ key: `${module.uuid}-${q.key}`, label: q.label, display: Array.isArray(value) ? value.join(', ') : String(value) });
    }
  }
  return { type, label, rows };
}));

async function handleSubmit() {
  await props.wizard.submitQuotation();
}
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 2rem; }
.booking-card { background: #fff; border: 1px solid #e8e7ee; border-radius: 18px; padding: 1.2rem 1.4rem; }
.soft-badge { display: inline-block; background: #f3e8ff; color: #6b21a8; border-radius: 999px; padding: 0.3rem 0.7rem; font-size: 0.72rem; font-weight: 750; text-transform: uppercase; }
.row-line { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; }
.row-line:last-child { border-bottom: none; }
.btn-submit {
  width: 100%; border: 0; border-radius: 999px; background: #6d28d9; color: #fff;
  padding: 1rem; font-weight: 750; margin-top: 1.4rem; cursor: pointer;
}
.btn-submit:disabled { opacity: 0.6; }
.success-box { text-align: center; padding: 3rem 1rem; }
.success-box i { font-size: 3.5rem; color: #16a34a; margin-bottom: 1rem; display: block; }
</style>
