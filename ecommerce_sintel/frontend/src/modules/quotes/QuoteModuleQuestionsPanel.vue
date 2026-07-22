<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h6 class="fw-semibold mb-0">{{ moduleTypeLabel }} y preguntas</h6>
      <button class="btn btn-primary btn-sm" @click="isCreating = !isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nuevo {{ moduleTypeLabel.replace(/s$/, '') }}
      </button>
    </div>

    <div v-if="isCreating" class="card border-0 shadow-sm mb-3 p-3">
      <div class="row g-2 align-items-end">
        <div :class="moduleType === 'EQUIPMENT' ? 'col-5' : 'col-10'">
          <label class="form-label small">Nombre</label>
          <input v-model="newModule.name" class="form-control form-control-sm" :placeholder="namePlaceholder" />
        </div>
        <template v-if="moduleType === 'EQUIPMENT'">
          <div class="col-3">
            <label class="form-label small">Unidad</label>
            <input v-model="newModule.unit" class="form-control form-control-sm" placeholder="unidad" />
          </div>
          <div class="col-1">
            <label class="form-label small">Mín.</label>
            <input v-model.number="newModule.min_quantity" type="number" class="form-control form-control-sm" />
          </div>
          <div class="col-1">
            <label class="form-label small">Máx.</label>
            <input v-model.number="newModule.max_quantity" type="number" class="form-control form-control-sm" />
          </div>
        </template>
        <div class="col-2 d-flex gap-2">
          <button class="btn btn-sm btn-success flex-grow-1" @click="handleCreate"><i class="bi bi-check-lg"></i></button>
          <button class="btn btn-sm btn-light border" @click="isCreating = false"><i class="bi bi-x-lg"></i></button>
        </div>
      </div>
    </div>

    <div v-if="!modules.length" class="text-center text-muted py-5">
      <i class="bi bi-collection fs-2 d-block mb-2"></i>
      Sin {{ moduleTypeLabel.toLowerCase() }}. Crea el primero para empezar a agregar preguntas.
    </div>

    <div v-for="(module, idx) in modules" :key="module.uuid" class="card border-0 shadow-sm mb-3">
      <div class="card-header bg-white d-flex align-items-center gap-2">
        <div class="d-flex flex-column me-1">
          <button class="btn btn-sm btn-light border py-0 px-1" :disabled="idx === 0" @click="handleReorder(module, 'up')"><i class="bi bi-caret-up-fill small"></i></button>
          <button class="btn btn-sm btn-light border py-0 px-1 mt-1" :disabled="idx === modules.length - 1" @click="handleReorder(module, 'down')"><i class="bi bi-caret-down-fill small"></i></button>
        </div>
        <InlineTextEditor
          :model-value="module.name"
          :on-save="(value) => handleModuleSave(module, { name: value })"
        />
        <span v-if="module.equipment_type" class="badge bg-light text-secondary border rounded-pill">
          {{ module.equipment_type.name }}
        </span>
        <span v-if="module.is_required" class="badge bg-warning-subtle text-warning border">Obligatorio</span>
        <span class="badge bg-secondary-subtle text-secondary rounded-pill ms-auto">{{ module.questions.length }} pregunta(s)</span>
        <button class="btn btn-sm btn-outline-primary" @click="openQuestionCreate(module)">
          <i class="bi bi-plus-lg me-1"></i>Pregunta
        </button>
        <button class="btn btn-sm btn-light border" title="Importar pregunta de otra plantilla" @click="openImportPicker(module)">
          <i class="bi bi-box-arrow-in-down"></i>
        </button>
        <button class="btn btn-sm btn-light border" title="Duplicar" @click="handleDuplicate(module)">
          <i class="bi bi-files"></i>
        </button>
        <button class="btn btn-sm btn-light border text-danger" @click="pendingDelete = module">
          <i class="bi bi-trash"></i>
        </button>
      </div>

      <div v-if="pendingDelete?.uuid === module.uuid" class="bg-danger-subtle p-3 d-flex align-items-center gap-3">
        <i class="bi bi-exclamation-triangle-fill text-danger"></i>
        <span class="small">¿Eliminar <strong>{{ module.name }}</strong> y todas sus preguntas?</span>
        <div class="ms-auto d-flex gap-2">
          <button class="btn btn-sm btn-danger" @click="handleModuleDelete(module)">Confirmar</button>
          <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
        </div>
      </div>

      <div class="card-body p-0" v-else>
        <table class="table table-sm mb-0">
          <tbody>
            <tr v-if="!module.questions.length">
              <td class="text-muted small text-center py-3">Sin preguntas.</td>
            </tr>
            <tr v-for="q in module.questions" :key="q.uuid">
              <td class="ps-3" style="width: 40%">
                <div class="fw-medium small">{{ q.label }}</div>
                <code class="text-muted" style="font-size: .7rem">{{ q.key }}</code>
              </td>
              <td><span class="badge bg-secondary-subtle text-secondary">{{ q.question_type_display }}</span></td>
              <td>
                <span v-if="q.is_required" class="badge bg-warning-subtle text-warning border">Obligatoria</span>
                <span v-if="!q.is_visible" class="badge bg-light text-secondary border ms-1">Oculta</span>
                <span v-if="q.depends_on_question_key" class="badge bg-info-subtle text-info border ms-1" :title="`Depende de: ${q.depends_on_question_key}`">
                  <i class="bi bi-diagram-3 me-1"></i>Condicional
                </span>
              </td>
              <td class="text-end pe-3">
                <button class="btn btn-sm btn-light border" @click="openQuestionEdit(module, q)"><i class="bi bi-pencil text-primary"></i></button>
                <button class="btn btn-sm btn-light border ms-1" @click="handleQuestionDelete(q)"><i class="bi bi-trash text-danger"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <SintelOffcanvas
      v-model="showQuestionForm"
      :title="questionMode === 'create' ? 'Nueva Pregunta' : 'Editar Pregunta'"
      width="480px"
    >
      <QuoteQuestionForm
        v-if="showQuestionForm"
        :item="selectedQuestion"
        :mode="questionMode"
        :module-uuid="selectedModuleUuid"
        :template-uuid="templateUuid"
        @success="closeQuestionForm"
        @cancel="closeQuestionForm"
      />
    </SintelOffcanvas>

    <!-- Biblioteca de preguntas reutilizable (Fase C): buscar una pregunta
         en OTRA plantilla/modulo y copiarla (no compartirla por referencia)
         al modulo actual. -->
    <SintelOffcanvas v-model="showImportPicker" title="Importar pregunta" width="420px">
      <div v-if="showImportPicker" class="d-flex flex-column gap-3">
        <div>
          <label class="form-label small fw-semibold">Plantilla de origen</label>
          <select v-model="importSourceTemplateUuid" class="form-select form-select-sm" @change="handleImportTemplateChange">
            <option value="">-- Selecciona --</option>
            <option v-for="t in store.templates" :key="t.uuid" :value="t.uuid">{{ t.name }}</option>
          </select>
        </div>

        <div v-if="importSourceModules.length">
          <label class="form-label small fw-semibold">Módulo</label>
          <select v-model="importSourceModuleUuid" class="form-select form-select-sm">
            <option value="">-- Selecciona --</option>
            <option v-for="m in importSourceModules" :key="m.uuid" :value="m.uuid">{{ m.name }} ({{ LABELS[m.module_type] }})</option>
          </select>
        </div>

        <div v-if="importSourceQuestions.length" class="d-flex flex-column gap-2">
          <label class="form-label small fw-semibold mb-0">Pregunta</label>
          <div
            v-for="q in importSourceQuestions" :key="q.uuid"
            class="d-flex align-items-center justify-content-between border rounded p-2"
          >
            <div>
              <div class="small fw-medium">{{ q.label }}</div>
              <code class="text-muted" style="font-size:.7rem">{{ q.key }}</code>
            </div>
            <button class="btn btn-sm btn-primary" :disabled="store.actionLoading" @click="handleImportQuestion(q)">
              <i class="bi bi-box-arrow-in-down me-1"></i>Copiar aqui
            </button>
          </div>
        </div>
        <p v-else-if="importSourceModuleUuid" class="text-muted small">Este módulo no tiene preguntas.</p>
      </div>
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useToast } from '@/composables/useToast';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import InlineTextEditor from '@/modules/technical_services/InlineTextEditor.vue';
import QuoteQuestionForm from './QuoteQuestionForm.vue';

const props = defineProps({
  templateUuid: { type: String, required: true },
  moduleType: { type: String, required: true }, // EQUIPMENT | MATERIALS | LABOR
});

const store = useQuoteTemplateBuilderStore();
const toast = useToast();

const LABELS = { EQUIPMENT: 'Equipos', MATERIALS: 'Materiales', LABOR: 'Mano de Obra' };
const PLACEHOLDERS = {
  EQUIPMENT: 'Camara IP Domo Exterior',
  MATERIALS: 'Cableado estructurado',
  LABOR: 'Condiciones de instalación',
};
const moduleTypeLabel = computed(() => LABELS[props.moduleType] || props.moduleType);
const namePlaceholder = computed(() => PLACEHOLDERS[props.moduleType] || '');

const modules = computed(() => (store.currentTemplate?.modules || []).filter((m) => m.module_type === props.moduleType));

const isCreating = ref(false);
const newModule = ref({ name: '', unit: 'unidad', min_quantity: null, max_quantity: null });
const pendingDelete = ref(null);

const showQuestionForm = ref(false);
const questionMode = ref('create');
const selectedQuestion = ref(null);
const selectedModuleUuid = ref(null);

// Biblioteca de preguntas reutilizable (Fase C)
const showImportPicker = ref(false);
const importTargetModule = ref(null);
const importSourceTemplateUuid = ref('');
const importSourceModuleUuid = ref('');
const importSourceTemplateDetail = ref(null);

const importSourceModules = computed(() => importSourceTemplateDetail.value?.modules || []);
const importSourceQuestions = computed(() => {
  const module = importSourceModules.value.find((m) => m.uuid === importSourceModuleUuid.value);
  return module?.questions || [];
});

function openImportPicker(module) {
  importTargetModule.value = module;
  importSourceTemplateUuid.value = '';
  importSourceModuleUuid.value = '';
  importSourceTemplateDetail.value = null;
  showImportPicker.value = true;
  if (!store.templates.length) store.fetchTemplates();
}

async function handleImportTemplateChange() {
  importSourceModuleUuid.value = '';
  importSourceTemplateDetail.value = importSourceTemplateUuid.value
    ? await store.fetchTemplateDetailReadOnly(importSourceTemplateUuid.value)
    : null;
}

async function handleImportQuestion(question) {
  const { ok, error } = await store.duplicateQuestionToModule(
    question.uuid, importTargetModule.value.uuid, props.templateUuid,
  );
  if (ok) {
    toast.success(`"${question.label}" importada.`);
    showImportPicker.value = false;
  } else {
    toast.error(error || 'Error al importar la pregunta.');
  }
}

async function handleCreate() {
  if (!newModule.value.name) {
    toast.error('El nombre es obligatorio.');
    return;
  }
  const payload = { module_type: props.moduleType, name: newModule.value.name };
  if (props.moduleType === 'EQUIPMENT') {
    Object.assign(payload, {
      unit: newModule.value.unit,
      min_quantity: newModule.value.min_quantity,
      max_quantity: newModule.value.max_quantity,
    });
  }
  const { ok, error } = await store.createModule(props.templateUuid, payload);
  if (ok) {
    toast.success(`${moduleTypeLabel.value.replace(/s$/, '')} creado.`);
    newModule.value = { name: '', unit: 'unidad', min_quantity: null, max_quantity: null };
    isCreating.value = false;
  } else {
    toast.error(error || 'Error al crear.');
  }
}

async function handleModuleSave(module, payload) {
  const { ok, error } = await store.updateModule(module.uuid, props.templateUuid, payload);
  if (!ok) {
    toast.error(error || 'Error al actualizar.');
    throw new Error(error);
  }
}

async function handleModuleDelete(module) {
  const { ok, error } = await store.deleteModule(module.uuid, props.templateUuid);
  if (ok) {
    toast.success(`"${module.name}" eliminado.`);
  } else {
    toast.error(error || 'Error al eliminar.');
  }
  pendingDelete.value = null;
}

async function handleDuplicate(module) {
  const { ok, error } = await store.duplicateModule(module.uuid, props.templateUuid);
  if (ok) toast.success('Duplicado correctamente.');
  else toast.error(error || 'Error al duplicar.');
}

async function handleReorder(module, direction) {
  const { ok, error } = await store.reorderModule(module.uuid, props.templateUuid, direction);
  if (!ok) toast.error(error || 'Error al mover.');
}

function openQuestionCreate(module) {
  selectedModuleUuid.value = module.uuid;
  selectedQuestion.value = null;
  questionMode.value = 'create';
  showQuestionForm.value = true;
}

function openQuestionEdit(module, question) {
  selectedModuleUuid.value = module.uuid;
  selectedQuestion.value = question;
  questionMode.value = 'edit';
  showQuestionForm.value = true;
}

function closeQuestionForm() {
  showQuestionForm.value = false;
}

async function handleQuestionDelete(question) {
  const { ok, error } = await store.deleteQuestion(question.uuid, props.templateUuid);
  if (ok) {
    toast.success(`Pregunta "${question.label}" eliminada.`);
  } else {
    toast.error(error || 'Error al eliminar la pregunta.');
  }
}
</script>
