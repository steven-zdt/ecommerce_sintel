<template>
  <div>
    <h1 class="step-title">Equipos</h1>
    <p class="step-subtitle">Cuéntanos qué equipos necesitas — nosotros calculamos el resto.</p>

    <div v-if="!modules.length" class="text-muted">Esta plantilla no requiere información de equipos.</div>

    <!-- Preguntas con group=DOCUMENT_GROUP (ver quotes/migrations/
         0032_optimize_installation_flow.py) -- banner para adjuntar un
         documento de requerimientos existente, sin ocultar el resto del
         formulario. -->
    <div v-for="module in modules" :key="`doc-${module.uuid}`">
      <div v-if="documentQuestions(module).length" class="document-card mb-3">
        <div class="document-banner">
          <h2><i class="bi bi-file-earmark-text me-2"></i>¿Ya tienes un documento con los requerimientos?</h2>
          <p>
            Si ya tienes un documento con las especificaciones técnicas, pliego de condiciones,
            lista de requerimientos o cualquier información relacionada con la instalación, puedes
            adjuntarlo aquí. Nuestro equipo utilizará esta información para complementar el
            análisis de tu solicitud.
          </p>
        </div>
        <div class="form-grid">
          <div
            v-for="q in documentQuestions(module)" v-show="wizard.isQuestionVisible(module.uuid, q)"
            :key="q.uuid" :class="{ wide: isWideType(q.question_type) }"
          >
            <DynamicQuestionField
              :question="q"
              :model-value="isFileType(q.question_type) ? wizard.files[wizard.fileKeyFor(module.uuid, q.key)] : wizard.answerFor(module.uuid, q.key)"
              @update:model-value="(v) => onUpdate(module.uuid, q, v)"
            />
          </div>
          <p v-if="hasAttachedDocuments(module)" class="text-success small mb-0 wide">
            <i class="bi bi-check-circle-fill me-1"></i>Perfecto. Hemos recibido tu documento.
            Puedes continuar respondiendo las siguientes preguntas para complementar la información
            o enviar la solicitud cuando consideres que está completa.
          </p>
        </div>
      </div>
    </div>

    <div v-for="module in modules" :key="module.uuid" class="booking-card mb-3">
      <h2><i class="bi bi-hdd-stack me-2"></i>{{ module.name }}</h2>
      <p v-if="module.description" class="text-muted small">{{ module.description }}</p>

      <div class="form-grid">
        <div
          v-for="q in equipmentQuestions(module)" v-show="wizard.isQuestionVisible(module.uuid, q)"
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
const DOCUMENT_GROUP = 'Documentacion Adjunta';
const modules = computed(() => props.wizard.modulesByType('EQUIPMENT'));
const isValid = computed(() => props.wizard.validateModuleType('EQUIPMENT'));

function documentQuestions(module) {
  return module.questions.filter((q) => q.group === DOCUMENT_GROUP);
}
function equipmentQuestions(module) {
  return module.questions.filter((q) => q.group !== DOCUMENT_GROUP);
}

function hasAttachedDocuments(module) {
  const files = props.wizard.files[props.wizard.fileKeyFor(module.uuid, 'requirement_documents')];
  return Array.isArray(files) ? files.length > 0 : !!files;
}

function isFileType(type) {
  return FILE_TYPES.includes(type);
}

function isWideType(type) {
  return ['TEXT', 'TEXTAREA', 'ADDRESS', 'FILE', 'MULTISELECT', 'CHECKBOX', 'TABLE', 'DYNAMIC_LIST'].includes(type);
}

function onUpdate(moduleUuid, question, value) {
  if (isFileType(question.question_type)) {
    const key = props.wizard.fileKeyFor(moduleUuid, question.key);
    const isEmpty = value === undefined || value === null || (Array.isArray(value) && value.length === 0);
    if (isEmpty) {
      delete props.wizard.files[key];
    } else {
      props.wizard.files[key] = value;
    }
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
.document-card { background: #fff; border: 1.5px solid #ddd6fe; border-radius: 20px; overflow: hidden; }
.document-banner { background: #f5f3ff; padding: 1.2rem 1.4rem; border-bottom: 1.5px solid #ddd6fe; }
.document-banner h2 { font-size: 1.05rem; font-weight: 780; color: #5b21b6; margin-bottom: 0.3rem; }
.document-banner h2 i { color: #7c3aed; }
.document-banner p { color: #6d5b91; font-size: 0.86rem; margin: 0; }
.document-card .form-grid { padding: 1.4rem; margin-top: 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 1rem; }
.wide { grid-column: 1 / -1; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; } .wide { grid-column: auto; } }
</style>
