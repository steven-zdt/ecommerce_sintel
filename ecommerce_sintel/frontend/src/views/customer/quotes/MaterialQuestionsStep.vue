<template>
  <div>
    <h1 class="step-title">Información de la Instalación</h1>
    <p class="step-subtitle">Cuéntanos dónde y cómo se realizará el proyecto.</p>
    <p class="step-subtitle step-subtitle-secondary">
      Con esta información —distancias, ubicación y tipo de proyecto— nuestro equipo determina
      los materiales y recursos necesarios; no hace falta que nos indiques el detalle técnico.
    </p>

    <div v-if="!modules.length" class="text-muted">Esta plantilla no requiere información de instalación.</div>

    <div v-for="module in modules" :key="module.uuid" class="booking-card mb-3">
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
      <p v-if="distanceError" class="text-danger small mt-2">{{ distanceError }}</p>
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

function isFileType(type) {
  return FILE_TYPES.includes(type);
}

function isWideType(type) {
  return ['TEXT', 'TEXTAREA', 'ADDRESS', 'GPS', 'MULTISELECT', 'CHECKBOX', 'TABLE', 'DYNAMIC_LIST'].includes(type);
}

function onUpdate(moduleUuid, question, value) {
  if (isFileType(question.question_type)) {
    props.wizard.files[props.wizard.fileKeyFor(moduleUuid, question.key)] = value;
  } else {
    props.wizard.setAnswer(moduleUuid, question.key, value);
  }
}

// Validacion cruzada: la distancia del equipo mas cercano no puede superar
// la del mas lejano. No es una regla generica del motor de preguntas
// (QuoteQuestion no modela "depende del VALOR de otra pregunta", solo
// visibilidad) -- se resuelve aqui, acotada a estas 2 keys.
const distanceError = computed(() => {
  for (const module of modules.value) {
    const near = props.wizard.answerFor(module.uuid, 'nearest_equipment_distance');
    const far = props.wizard.answerFor(module.uuid, 'farthest_equipment_distance');
    if (near !== null && near !== undefined && near !== '' && far !== null && far !== undefined && far !== '' && Number(near) > Number(far)) {
      return 'La distancia del equipo mas cercano no puede ser mayor que la del mas lejano.';
    }
  }
  return '';
});

const isValid = computed(() => props.wizard.validateModuleType('MATERIALS') && !distanceError.value);

defineExpose({ isValid });
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 0.4rem; }
.step-subtitle-secondary { font-size: 0.86rem; margin-bottom: 2rem; }
.booking-card { background: #fff; border: 1px solid #e8e7ee; border-radius: 20px; padding: 1.4rem; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 0; }
.wide { grid-column: 1 / -1; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; } .wide { grid-column: auto; } }
</style>
