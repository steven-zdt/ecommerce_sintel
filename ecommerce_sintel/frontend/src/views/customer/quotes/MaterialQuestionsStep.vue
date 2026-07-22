<template>
  <div>
    <h1 class="step-title">Materiales</h1>
    <p class="step-subtitle">Cuéntanos qué materiales necesitas — nosotros calculamos el resto.</p>

    <div v-if="!modules.length" class="text-muted">Esta plantilla no requiere información de materiales.</div>

    <div v-for="module in modules" :key="module.uuid" class="booking-card mb-3">
      <h2><i class="bi bi-box-seam me-2"></i>{{ module.name }}</h2>
      <p v-if="module.description" class="text-muted small">{{ module.description }}</p>

      <div class="form-grid">
        <div
          v-for="q in module.questions" v-show="wizard.isQuestionVisible(module.uuid, q)"
          :key="q.uuid" :class="{ wide: isWideType(q.question_type) }"
        >
          <DynamicQuestionField
            :question="q"
            :model-value="isFileType(q.question_type) ? wizard.files[wizard.fileKeyFor(module.uuid, q.key)] : wizard.answerFor(module.uuid, q.key)"
            @update:model-value="(v) => onUpdate(module.uuid, q, v)"
          />
        </div>
      </div>
    </div>

    <p v-if="!isValid" class="text-danger small mt-2">Completa las preguntas obligatorias (*) para continuar.</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import DynamicQuestionField from '@/modules/quotes/DynamicQuestionField.vue';

const props = defineProps({ wizard: { type: Object, required: true } });

const FILE_TYPES = ['IMAGE', 'FILE', 'SIGNATURE'];
const modules = computed(() => props.wizard.modulesByType('MATERIALS'));
const isValid = computed(() => props.wizard.validateModuleType('MATERIALS'));

function isFileType(type) {
  return FILE_TYPES.includes(type);
}

function isWideType(type) {
  return ['TEXT', 'TEXTAREA', 'ADDRESS', 'MULTISELECT', 'CHECKBOX', 'TABLE', 'DYNAMIC_LIST'].includes(type);
}

function onUpdate(moduleUuid, question, value) {
  if (isFileType(question.question_type)) {
    props.wizard.files[props.wizard.fileKeyFor(moduleUuid, question.key)] = value;
  } else {
    props.wizard.setAnswer(moduleUuid, question.key, value);
  }
}

defineExpose({ isValid });
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 2rem; }
.booking-card { background: #fff; border: 1px solid #e8e7ee; border-radius: 20px; padding: 1.4rem; }
.booking-card h2 { font-size: 1.05rem; font-weight: 780; margin-bottom: 0.2rem; }
.booking-card h2 i { color: #7c3aed; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 1rem; }
.wide { grid-column: 1 / -1; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; } .wide { grid-column: auto; } }
</style>
