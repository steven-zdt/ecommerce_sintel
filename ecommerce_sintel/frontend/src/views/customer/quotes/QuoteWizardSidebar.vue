<template>
  <aside class="qws-sidebar">
    <div class="qws-card">
      <div v-if="wizard.selectedTemplate.value" class="qws-template">
        <i class="bi bi-file-earmark-text-fill"></i>
        <span>{{ wizard.selectedTemplate.value.name }}</span>
      </div>

      <div class="qws-progress-track">
        <div class="qws-progress-fill" :style="{ width: `${progressPct}%` }"></div>
      </div>
      <div class="qws-progress-label">{{ progressPct }}%</div>

      <ul class="qws-checklist">
        <li v-for="item in checklist" :key="item.label" :class="{ 'qws-item-done': item.done, 'qws-item-active': item.active }">
          <i :class="['bi', item.done ? 'bi-check-circle-fill' : 'bi-circle']"></i>
          <span>{{ item.label }}</span>
        </li>
      </ul>

      <div v-if="wizard.selectedTemplate.value" class="qws-remaining">
        <i class="bi bi-list-check me-1"></i>
        <span v-if="remainingRequired > 0">{{ remainingRequired }} pregunta{{ remainingRequired === 1 ? '' : 's' }} obligatoria{{ remainingRequired === 1 ? '' : 's' }} restante{{ remainingRequired === 1 ? '' : 's' }}</span>
        <span v-else class="text-success fw-semibold">Todas las preguntas obligatorias respondidas</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';

/**
 * Resumen lateral permanente del wizard de cotizacion -- visible mientras
 * el cliente responde (Plantilla en adelante). Puramente de presentacion:
 * lee el mismo estado que ya expone useQuoteWizard.js, no agrega ninguna
 * llamada nueva ni cambia la logica de validacion/envio.
 * Ver PLAN_MAESTRO_QUOTES_UX.md, Fase B.
 */
const props = defineProps({ wizard: { type: Object, required: true } });

const STEP_DESTINATARIO = 0;
const STEP_TEMPLATE = 1;
const STEP_EQUIPMENT = 2;
const STEP_MATERIALS = 3;
const STEP_LABOR = 4;

const MODULE_TYPE_BY_STEP = {
  [STEP_EQUIPMENT]: 'EQUIPMENT',
  [STEP_MATERIALS]: 'MATERIALS',
  [STEP_LABOR]: 'LABOR',
};

const checklist = computed(() => {
  const currentStep = props.wizard.step.value;
  const labels = [
    { label: 'Destinatario', step: STEP_DESTINATARIO },
    { label: 'Plantilla', step: STEP_TEMPLATE },
    { label: 'Equipos', step: STEP_EQUIPMENT },
    { label: 'Materiales', step: STEP_MATERIALS },
    { label: 'Mano de obra', step: STEP_LABOR },
  ];
  return labels.map(({ label, step }) => ({
    label,
    active: currentStep === step,
    done: currentStep > step || (step === STEP_DESTINATARIO && props.wizard.validateApplicant())
      || (step === STEP_TEMPLATE && !!props.wizard.selectedTemplate.value)
      || (MODULE_TYPE_BY_STEP[step] && currentStep >= step && props.wizard.validateModuleType(MODULE_TYPE_BY_STEP[step])),
  }));
});

// Solo cuenta preguntas obligatorias que ademas esten visibles ahora mismo
// (Fase F: una pregunta oculta por una regla de visibilidad condicional no
// debe contar como "pendiente" ni bloquear el 100% de progreso).
function requiredQuestionsFor(moduleType) {
  return props.wizard.modulesByType(moduleType)
    .flatMap((m) => m.questions
      .filter((q) => q.is_required && props.wizard.isQuestionVisible(m.uuid, q))
      .map((q) => ({ moduleUuid: m.uuid, key: q.key })));
}

const remainingRequired = computed(() => {
  if (!props.wizard.selectedTemplate.value) return 0;
  const all = [
    ...requiredQuestionsFor('EQUIPMENT'),
    ...requiredQuestionsFor('MATERIALS'),
    ...requiredQuestionsFor('LABOR'),
  ];
  return all.filter(({ moduleUuid, key }) => {
    const v = props.wizard.answerFor(moduleUuid, key);
    return v === undefined || v === null || v === '';
  }).length;
});

const progressPct = computed(() => {
  if (!props.wizard.selectedTemplate.value) return 0;
  const total = requiredQuestionsFor('EQUIPMENT').length + requiredQuestionsFor('MATERIALS').length + requiredQuestionsFor('LABOR').length;
  if (total === 0) return 100;
  return Math.round(((total - remainingRequired.value) / total) * 100);
});
</script>

<style scoped>
.qws-sidebar { position: sticky; top: 90px; }
.qws-card { background: #fff; border-radius: 20px; padding: 1.4rem; box-shadow: 0 10px 40px rgba(15, 23, 42, 0.06); }

.qws-template {
  display: flex; align-items: center; gap: 0.5rem;
  font-weight: 700; font-size: 0.9rem; color: #1e1b4b;
  margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #f1f5f9;
}
.qws-template i { color: #7c3aed; }

.qws-progress-track { height: 8px; border-radius: 999px; background: #f1f5f9; overflow: hidden; }
.qws-progress-fill { height: 100%; background: #7c3aed; transition: width .25s ease; }
.qws-progress-label { font-size: 0.75rem; font-weight: 700; color: #7c3aed; margin: 0.35rem 0 1rem; text-align: right; }

.qws-checklist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.6rem; }
.qws-checklist li { display: flex; align-items: center; gap: 0.55rem; font-size: 0.85rem; color: #94a3b8; font-weight: 600; }
.qws-checklist li i { font-size: 0.95rem; }
.qws-item-done { color: #1e1b4b; }
.qws-item-done i { color: #16a34a; }
.qws-item-active { color: #7c3aed; }
.qws-item-active i { color: #7c3aed; }

.qws-remaining {
  margin-top: 1.1rem; padding-top: 1rem; border-top: 1px solid #f1f5f9;
  font-size: 0.8rem; color: #64748b;
}

@media (max-width: 991px) {
  .qws-sidebar { position: static; margin-bottom: 1.5rem; }
}
</style>
