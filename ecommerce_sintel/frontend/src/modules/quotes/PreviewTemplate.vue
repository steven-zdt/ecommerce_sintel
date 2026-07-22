<template>
  <div>
    <div class="alert alert-info d-flex align-items-center gap-2 small">
      <i class="bi bi-info-circle-fill"></i>
      Así verá el cliente el cuestionario en <code>/cotizar</code>. Es solo una vista previa —
      no se guarda ninguna respuesta ni se publica la plantilla.
    </div>

    <div v-if="!modules.length" class="text-muted small text-center py-5">
      Agrega equipos, materiales o mano de obra con preguntas para ver la vista previa.
    </div>

    <div v-for="group in groups" :key="group.type" v-show="group.modules.length" class="mb-4">
      <h6 class="text-uppercase small fw-semibold text-muted mb-3">{{ group.label }}</h6>
      <div v-for="module in group.modules" :key="module.uuid" class="card border-0 shadow-sm mb-3 p-3">
        <div class="fw-semibold mb-1">{{ module.name }}</div>
        <p v-if="module.description" class="text-muted small">{{ module.description }}</p>
        <div v-if="!module.questions.length" class="text-muted small">Sin preguntas.</div>
        <div v-for="q in module.questions" v-show="isVisible(q)" :key="q.uuid" class="mb-3">
          <DynamicQuestionField
            :question="q"
            :model-value="answers[q.key]"
            @update:model-value="(v) => (answers[q.key] = v)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { isQuestionVisible } from '@/utils/quoteVisibility';
import DynamicQuestionField from './DynamicQuestionField.vue';

defineProps({
  templateUuid: { type: String, required: true },
});

const store = useQuoteTemplateBuilderStore();
const answers = reactive({});

// Vista previa admin: mismo criterio de visibilidad condicional que el
// wizard publico (Fase F) para que el admin vea exactamente el efecto de
// depends_on_question/depends_on_values al configurar la plantilla.
function isVisible(question) {
  return isQuestionVisible(question, answers);
}

const GROUP_LABELS = { EQUIPMENT: 'Equipos', MATERIALS: 'Materiales', LABOR: 'Mano de Obra' };

const modules = computed(() => store.currentTemplate?.modules || []);
const groups = computed(() => Object.entries(GROUP_LABELS).map(([type, label]) => ({
  type, label, modules: modules.value.filter((m) => m.module_type === type),
})));
</script>
