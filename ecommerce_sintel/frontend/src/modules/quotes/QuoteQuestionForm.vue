<template>
  <div class="p-3">
    <form @submit.prevent="handleSubmit" class="d-flex flex-column gap-3">
      <div>
        <label class="form-label small fw-semibold">Etiqueta *</label>
        <input v-model="form.label" type="text" class="form-control" required placeholder="Cantidad de cámaras" />
      </div>

      <div>
        <label class="form-label small fw-semibold">Descripción</label>
        <textarea v-model="form.description" class="form-control" rows="2" placeholder="Explicación larga (opcional)"></textarea>
      </div>

      <div class="row g-2">
        <div class="col-6">
          <label class="form-label small fw-semibold">Tipo de pregunta *</label>
          <select v-model="form.question_type" class="form-select">
            <option v-for="t in questionTypes" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">
            Clave (key)
            <i class="bi bi-info-circle text-muted" title="Identificador unico dentro del modulo"></i>
          </label>
          <input v-model="form.key" type="text" class="form-control" placeholder="camera_count (auto)" />
        </div>
      </div>

      <div class="row g-2">
        <div class="col-6">
          <label class="form-label small fw-semibold">Texto de ayuda</label>
          <input v-model="form.help_text" type="text" class="form-control" />
        </div>
        <div class="col-3">
          <label class="form-label small fw-semibold">Unidad</label>
          <input v-model="form.unit" type="text" class="form-control" placeholder="metros" />
        </div>
        <div class="col-3">
          <label class="form-label small fw-semibold">Grupo</label>
          <input v-model="form.group" type="text" class="form-control" placeholder="Datos del sitio" />
        </div>
      </div>

      <div class="row g-2">
        <div class="col-6">
          <label class="form-label small fw-semibold">Placeholder</label>
          <input v-model="form.placeholder" type="text" class="form-control" />
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor por defecto</label>
          <input v-model="form.default_value" type="text" class="form-control" />
        </div>
      </div>

      <div class="row g-2" v-if="isNumericType">
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor mínimo</label>
          <input v-model="form.min_value" type="number" step="0.01" class="form-control" />
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor máximo</label>
          <input v-model="form.max_value" type="number" step="0.01" class="form-control" />
        </div>
      </div>

      <div v-if="isValidatedType">
        <label class="form-label small fw-semibold">
          Patrón de validación (regex)
          <i class="bi bi-info-circle text-muted" title="Opcional, ej. para NIT/CC/Email/Telefono"></i>
        </label>
        <input v-model="form.validation_regex" type="text" class="form-control" placeholder="^[0-9]{6,10}$" />
      </div>

      <div v-if="form.question_type === 'TABLE'">
        <label class="form-label small fw-semibold">Columnas de la tabla</label>
        <div v-for="(col, i) in form.table_columns" :key="i" class="d-flex gap-2 mb-2">
          <input v-model="form.table_columns[i]" class="form-control form-control-sm" placeholder="Nombre de columna" />
          <button type="button" class="btn btn-sm btn-light border text-danger" @click="form.table_columns.splice(i, 1)"><i class="bi bi-trash"></i></button>
        </div>
        <button type="button" class="btn btn-sm btn-light border" @click="form.table_columns.push('')">
          <i class="bi bi-plus-lg me-1"></i>Agregar columna
        </button>
      </div>

      <div class="d-flex gap-4 flex-wrap">
        <div class="form-check form-switch">
          <input v-model="form.is_required" class="form-check-input" type="checkbox" role="switch" id="qRequired" />
          <label class="form-check-label small" for="qRequired">Obligatoria</label>
        </div>
        <div class="form-check form-switch">
          <input v-model="form.is_visible" class="form-check-input" type="checkbox" role="switch" id="qVisible" />
          <label class="form-check-label small" for="qVisible">Visible al cliente</label>
        </div>
        <div class="form-check form-switch">
          <input v-model="form.is_active" class="form-check-input" type="checkbox" role="switch" id="qActive" />
          <label class="form-check-label small" for="qActive">Activa</label>
        </div>
        <div v-if="isOptionType" class="form-check form-switch">
          <input v-model="form.allow_other" class="form-check-input" type="checkbox" role="switch" id="qAllowOther" />
          <label class="form-check-label small" for="qAllowOther">Permitir "Otro" (texto libre)</label>
        </div>
      </div>

      <!-- Visibilidad condicional (Fase F) -- solo muestra/oculta, nunca calcula precio/mano de obra. -->
      <div class="border-top pt-3">
        <label class="form-label small fw-semibold">
          Depende de <i class="bi bi-info-circle text-muted" title="Esta pregunta solo se muestra si la respuesta de la pregunta elegida coincide con los valores seleccionados abajo"></i>
        </label>
        <select
          v-model="form.depends_on_question" class="form-select form-select-sm"
          @change="form.depends_on_values = []"
        >
          <option value="">Ninguna — siempre visible</option>
          <option v-for="sq in siblingQuestions" :key="sq.uuid" :value="sq.uuid">{{ sq.label }}</option>
        </select>

        <div v-if="form.depends_on_question && parentQuestion" class="mt-2">
          <label class="form-label small text-muted">Mostrar cuando la respuesta sea:</label>

          <select v-if="parentQuestion.question_type === 'BOOLEAN'" v-model="booleanTrigger" class="form-select form-select-sm">
            <option value="true">Sí</option>
            <option value="false">No</option>
          </select>

          <div v-else-if="PARENT_OPTION_TYPES.includes(parentQuestion.question_type)" class="d-flex flex-wrap gap-3">
            <div v-for="opt in parentQuestion.options" :key="opt.uuid" class="form-check">
              <input
                :id="`trigger-${opt.uuid}`" class="form-check-input" type="checkbox"
                :value="opt.value" v-model="form.depends_on_values"
              />
              <label class="form-check-label small" :for="`trigger-${opt.uuid}`">{{ opt.label }}</label>
            </div>
          </div>

          <input
            v-else v-model="freeTextTrigger" type="text" class="form-control form-control-sm"
            placeholder="Valor exacto que activa esta pregunta"
          />
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-2">
        <button type="button" class="btn btn-light border" @click="$emit('cancel')">Cerrar</button>
        <button type="submit" class="btn btn-primary" :disabled="store.actionLoading">
          <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          {{ questionUuid ? 'Guardar cambios' : 'Crear pregunta' }}
        </button>
      </div>
    </form>

    <!-- Gestor de opciones (solo visible si el tipo lo requiere y la pregunta ya existe) -->
    <div v-if="isOptionType" class="mt-4 pt-3 border-top">
      <h6 class="fw-semibold small text-uppercase text-muted mb-2">Opciones</h6>
      <p v-if="!questionUuid" class="text-muted small">Guarda la pregunta primero para agregar opciones.</p>
      <template v-else>
        <div v-for="opt in currentOptions" :key="opt.uuid" class="d-flex align-items-center gap-2 mb-2">
          <input :value="opt.label" @change="handleOptionUpdate(opt, { label: $event.target.value })" class="form-control form-control-sm" placeholder="Texto" />
          <input :value="opt.value" @change="handleOptionUpdate(opt, { value: $event.target.value })" class="form-control form-control-sm" placeholder="Valor" />
          <button class="btn btn-sm btn-light border text-danger" @click="handleOptionDelete(opt)"><i class="bi bi-trash"></i></button>
        </div>
        <div class="d-flex gap-2">
          <input v-model="newOption.label" class="form-control form-control-sm" placeholder="Texto (ej. Sí)" />
          <input v-model="newOption.value" class="form-control form-control-sm" placeholder="Valor (ej. yes)" />
          <button class="btn btn-sm btn-success" @click="handleOptionCreate"><i class="bi bi-plus-lg"></i></button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
  moduleUuid: { type: String, required: true },
  templateUuid: { type: String, required: true },
});
const emit = defineEmits(['success', 'cancel']);

const store = useQuoteTemplateBuilderStore();
const toast = useToast();

const questionTypes = [
  'TEXT', 'TEXTAREA', 'NUMBER', 'DECIMAL', 'CURRENCY', 'BOOLEAN', 'DATE', 'TIME',
  'SELECT', 'MULTISELECT', 'RADIO', 'CHECKBOX',
  'IMAGE', 'FILE', 'SIGNATURE', 'GPS', 'ADDRESS',
  'EMAIL', 'PHONE', 'NIT', 'CC', 'COLOR', 'SLIDER', 'TABLE', 'DYNAMIC_LIST', 'AUTOCOMPLETE',
];
const OPTION_TYPES = ['SELECT', 'MULTISELECT', 'RADIO', 'CHECKBOX', 'AUTOCOMPLETE'];
const NUMERIC_TYPES = ['NUMBER', 'DECIMAL', 'CURRENCY', 'SLIDER'];
const VALIDATED_TYPES = ['TEXT', 'EMAIL', 'PHONE', 'NIT', 'CC'];
// Tipos de la pregunta PADRE para los que se ofrecen sus propias opciones
// como valores disparadores, en vez de un input de texto libre.
const PARENT_OPTION_TYPES = ['SELECT', 'MULTISELECT', 'RADIO', 'CHECKBOX', 'AUTOCOMPLETE'];

const questionUuid = ref(props.mode === 'edit' ? props.item?.uuid : null);

const blank = () => ({
  key: '', question_type: 'TEXT', label: '', description: '', help_text: '', placeholder: '',
  is_required: false, is_visible: true, is_active: true, default_value: '', unit: '', group: '',
  min_value: null, max_value: null, validation_regex: '', table_columns: [], allow_other: false,
  depends_on_question: '', depends_on_values: [],
});

const form = ref(blank());

// Modulo actual (del arbol ya cargado en el store) -- fuente de las
// preguntas "hermanas" candidatas a depends_on_question (Fase F).
const currentModule = computed(() => {
  if (!store.currentTemplate) return null;
  return (store.currentTemplate.modules || []).find((m) => m.uuid === props.moduleUuid);
});
const siblingQuestions = computed(() => {
  if (!currentModule.value) return [];
  return currentModule.value.questions.filter((q) => q.uuid !== questionUuid.value);
});
const parentQuestion = computed(() => {
  if (!form.value.depends_on_question) return null;
  return siblingQuestions.value.find((q) => q.uuid === form.value.depends_on_question) || null;
});

onMounted(() => {
  if (props.mode === 'edit' && props.item) {
    // El backend expone depends_on_question_key (no uuid) en lectura -- se
    // resuelve al uuid de la pregunta hermana correspondiente para poder
    // preseleccionarla en el <select>.
    const depUuid = props.item.depends_on_question_key
      ? (currentModule.value?.questions.find((q) => q.key === props.item.depends_on_question_key)?.uuid || '')
      : '';
    form.value = {
      key: props.item.key || '',
      question_type: props.item.question_type || 'TEXT',
      label: props.item.label || '',
      description: props.item.description || '',
      help_text: props.item.help_text || '',
      placeholder: props.item.placeholder || '',
      is_required: props.item.is_required || false,
      is_visible: props.item.is_visible ?? true,
      is_active: props.item.is_active ?? true,
      default_value: props.item.default_value || '',
      unit: props.item.unit || '',
      group: props.item.group || '',
      min_value: props.item.min_value,
      max_value: props.item.max_value,
      validation_regex: props.item.validation_regex || '',
      table_columns: [...(props.item.table_columns || [])],
      allow_other: props.item.allow_other || false,
      depends_on_question: depUuid,
      depends_on_values: [...(props.item.depends_on_values || [])],
    };
  }
});

const isNumericType = computed(() => NUMERIC_TYPES.includes(form.value.question_type));
const isOptionType = computed(() => OPTION_TYPES.includes(form.value.question_type));
const isValidatedType = computed(() => VALIDATED_TYPES.includes(form.value.question_type));

const booleanTrigger = computed({
  get: () => form.value.depends_on_values[0] ?? 'true',
  set: (v) => { form.value.depends_on_values = [v]; },
});
const freeTextTrigger = computed({
  get: () => form.value.depends_on_values[0] ?? '',
  set: (v) => { form.value.depends_on_values = v ? [v] : []; },
});

// Refleja las opciones actuales desde el arbol de la plantilla en el store
const currentOptions = computed(() => {
  if (!questionUuid.value || !store.currentTemplate) return [];
  for (const module of store.currentTemplate.modules || []) {
    const q = module.questions.find((q) => q.uuid === questionUuid.value);
    if (q) return q.options || [];
  }
  return [];
});

const newOption = ref({ label: '', value: '' });

async function handleSubmit() {
  if (!form.value.label) {
    toast.error('La etiqueta es obligatoria.');
    return;
  }
  const payload = { ...form.value };
  if (!isNumericType.value) {
    payload.min_value = null;
    payload.max_value = null;
  }
  // El SlugRelatedField del backend espera un uuid valido o null -- nunca
  // '' (intentaria buscar una pregunta con uuid='').
  if (!payload.depends_on_question) {
    payload.depends_on_question = null;
    payload.depends_on_values = [];
  }

  const result = questionUuid.value
    ? await store.updateQuestion(questionUuid.value, props.templateUuid, payload)
    : await store.createQuestion(props.moduleUuid, props.templateUuid, payload);

  if (result.ok) {
    toast.success(questionUuid.value ? 'Pregunta actualizada.' : 'Pregunta creada.');
    questionUuid.value = result.data.uuid;
    if (!isOptionType.value) {
      emit('success');
    }
  } else {
    toast.error(result.error || 'Error al guardar la pregunta.');
  }
}

async function handleOptionCreate() {
  if (!newOption.value.label || !newOption.value.value) {
    toast.error('Texto y valor son obligatorios.');
    return;
  }
  const { ok, error } = await store.createOption(questionUuid.value, props.templateUuid, newOption.value);
  if (ok) {
    newOption.value = { label: '', value: '' };
  } else {
    toast.error(error || 'Error al crear la opción.');
  }
}

async function handleOptionUpdate(option, payload) {
  const { ok, error } = await store.updateOption(option.uuid, props.templateUuid, payload);
  if (!ok) toast.error(error || 'Error al actualizar la opción.');
}

async function handleOptionDelete(option) {
  const { ok, error } = await store.deleteOption(option.uuid, props.templateUuid);
  if (!ok) toast.error(error || 'Error al eliminar la opción.');
}
</script>
