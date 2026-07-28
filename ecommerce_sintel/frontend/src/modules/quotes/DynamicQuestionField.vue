<template>
  <div>
    <label class="form-label small">{{ question.label }} <span v-if="question.is_required" class="text-danger">*</span></label>
    <div v-if="question.description" class="form-text small mb-1">{{ question.description }}</div>
    <div v-if="question.help_text" class="form-text small mb-1">{{ question.help_text }}</div>

    <input
      v-if="['TEXT', 'ADDRESS'].includes(question.question_type)"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="text" class="form-control form-control-sm" :placeholder="question.placeholder"
      :pattern="question.validation_regex || undefined"
    />

    <div v-else-if="question.question_type === 'GPS'">
      <button
        type="button" class="btn btn-outline-primary btn-sm"
        :disabled="gpsLoading" @click="shareLocation"
      >
        <span v-if="gpsLoading" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-geo-alt me-1"></i>
        {{ gpsCoords ? 'Actualizar ubicacion' : 'Compartir ubicacion' }}
      </button>
      <div v-if="gpsCoords" class="text-success small mt-1">
        <i class="bi bi-check-circle-fill me-1"></i>Ubicacion compartida ({{ gpsCoords.lat.toFixed(5) }}, {{ gpsCoords.lng.toFixed(5) }})
      </div>
      <div v-else-if="modelValue === 'DENIED'" class="text-danger small mt-1">
        No pudimos obtener tu ubicacion. Puedes ingresar la direccion manualmente.
      </div>
    </div>
    <input
      v-else-if="question.question_type === 'EMAIL'"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="email" class="form-control form-control-sm" :placeholder="question.placeholder"
    />
    <input
      v-else-if="question.question_type === 'PHONE'"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="tel" class="form-control form-control-sm" :placeholder="question.placeholder"
    />
    <input
      v-else-if="['NIT', 'CC'].includes(question.question_type)"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="text" class="form-control form-control-sm" :placeholder="question.placeholder"
      :pattern="question.validation_regex || undefined"
    />
    <textarea
      v-else-if="question.question_type === 'TEXTAREA'"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      class="form-control form-control-sm" rows="3" :placeholder="question.placeholder"
    ></textarea>

    <div v-else-if="['NUMBER', 'DECIMAL', 'CURRENCY'].includes(question.question_type)" class="input-group input-group-sm">
      <span v-if="question.question_type === 'CURRENCY'" class="input-group-text">$</span>
      <input
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value === '' ? null : Number($event.target.value))"
        type="number" :step="question.question_type === 'DECIMAL' ? '0.01' : '1'" class="form-control"
        :min="question.min_value ?? undefined" :max="question.max_value ?? undefined"
      />
      <span v-if="question.unit" class="input-group-text">{{ question.unit }}</span>
    </div>

    <div v-else-if="question.question_type === 'SLIDER'">
      <input
        :value="modelValue ?? question.min_value ?? 0"
        @input="$emit('update:modelValue', Number($event.target.value))"
        type="range" class="form-range"
        :min="question.min_value ?? 0" :max="question.max_value ?? 100"
      />
      <div class="text-muted small text-center">{{ modelValue ?? question.min_value ?? 0 }} {{ question.unit }}</div>
    </div>

    <input
      v-else-if="question.question_type === 'DATE'"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="date" class="form-control form-control-sm"
    />
    <input
      v-else-if="question.question_type === 'TIME'"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="time" class="form-control form-control-sm"
    />
    <input
      v-else-if="question.question_type === 'COLOR'"
      :value="modelValue || '#000000'" @input="$emit('update:modelValue', $event.target.value)"
      type="color" class="form-control form-control-sm form-control-color"
    />

    <div v-else-if="question.question_type === 'BOOLEAN'" class="form-check form-switch">
      <input
        :checked="!!modelValue" @change="$emit('update:modelValue', $event.target.checked)"
        class="form-check-input" type="checkbox" role="switch"
      />
    </div>

    <div v-else-if="['SELECT', 'RADIO'].includes(question.question_type)">
      <select
        :value="selectValue" @change="onSelectChange($event.target.value)"
        class="form-select form-select-sm"
      >
        <option value="">-- Selecciona --</option>
        <option v-for="opt in question.options" :key="opt.uuid" :value="opt.value">{{ opt.label }}</option>
        <option v-if="question.allow_other" :value="OTHER_VALUE">Otro (especificar)</option>
      </select>
      <input
        v-if="question.allow_other && otherMode"
        :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
        type="text" class="form-control form-control-sm mt-2"
        placeholder="Especifica..."
      />
    </div>

    <div v-else-if="question.question_type === 'AUTOCOMPLETE'">
      <input
        :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
        type="text" class="form-control form-control-sm" :list="`ac-${question.uuid}`"
        :placeholder="question.placeholder"
      />
      <datalist :id="`ac-${question.uuid}`">
        <option v-for="opt in question.options" :key="opt.uuid" :value="opt.value">{{ opt.label }}</option>
      </datalist>
    </div>

    <div v-else-if="['MULTISELECT', 'CHECKBOX'].includes(question.question_type)" class="d-flex flex-wrap gap-2">
      <div v-for="opt in question.options" :key="opt.uuid" class="form-check form-check-inline">
        <input
          class="form-check-input" type="checkbox" :id="`opt-${opt.uuid}`"
          :checked="(modelValue || []).includes(opt.value)"
          @change="toggleMultiValue(opt.value, $event.target.checked)"
        />
        <label class="form-check-label small" :for="`opt-${opt.uuid}`">{{ opt.label }}</label>
      </div>
    </div>

    <div v-else-if="['IMAGE', 'SIGNATURE'].includes(question.question_type)">
      <input
        type="file" class="form-control form-control-sm"
        accept="image/*"
        @change="$emit('update:modelValue', $event.target.files[0] || null)"
      />
      <div v-if="modelValue" class="text-muted small mt-1"><i class="bi bi-paperclip me-1"></i>{{ modelValue.name }}</div>
      <div v-if="question.question_type === 'SIGNATURE'" class="form-text small">Sube una foto o captura de tu firma.</div>
    </div>

    <div v-else-if="question.question_type === 'FILE'">
      <input
        type="file" class="form-control form-control-sm" multiple
        :accept="FILE_ACCEPT"
        @change="onFilesSelected"
      />
      <div class="form-text small">PDF, DOC, DOCX, XLS, XLSX o TXT — máximo 20&nbsp;MB por archivo.</div>
      <ul v-if="fileList.length" class="list-unstyled mt-2 mb-0">
        <li v-for="(f, i) in fileList" :key="i" class="d-flex align-items-center justify-content-between small border rounded px-2 py-1 mb-1">
          <span><i class="bi bi-paperclip me-1"></i>{{ f.name }} <span class="text-muted">({{ formatFileSize(f.size) }})</span></span>
          <button type="button" class="btn btn-sm btn-link text-danger p-0" @click="removeFile(i)"><i class="bi bi-x-lg"></i></button>
        </li>
      </ul>
      <div v-if="fileErrors.length" class="text-danger small mt-1">
        <div v-for="(err, i) in fileErrors" :key="i">{{ err }}</div>
      </div>
    </div>

    <div v-else-if="question.question_type === 'DYNAMIC_LIST'">
      <div v-for="(row, i) in listValue" :key="i" class="d-flex gap-2 mb-2">
        <input :value="row" @input="updateListRow(i, $event.target.value)" class="form-control form-control-sm" />
        <button type="button" class="btn btn-sm btn-light border text-danger" @click="removeListRow(i)"><i class="bi bi-trash"></i></button>
      </div>
      <button type="button" class="btn btn-sm btn-light border" @click="addListRow"><i class="bi bi-plus-lg me-1"></i>Agregar</button>
    </div>

    <div v-else-if="question.question_type === 'TABLE'">
      <table class="table table-sm">
        <thead>
          <tr>
            <th v-for="(col, i) in question.table_columns" :key="i" class="small">{{ col }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in tableValue" :key="ri">
            <td v-for="(col, ci) in question.table_columns" :key="ci">
              <input :value="row[ci]" @input="updateTableCell(ri, ci, $event.target.value)" class="form-control form-control-sm" />
            </td>
            <td>
              <button type="button" class="btn btn-sm btn-light border text-danger" @click="removeTableRow(ri)"><i class="bi bi-trash"></i></button>
            </td>
          </tr>
        </tbody>
      </table>
      <button type="button" class="btn btn-sm btn-light border" @click="addTableRow"><i class="bi bi-plus-lg me-1"></i>Agregar fila</button>
    </div>

    <input
      v-else
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="text" class="form-control form-control-sm"
      :placeholder="`(${question.question_type_display || question.question_type})`"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  question: { type: Object, required: true },
  modelValue: { default: null },
});
const emit = defineEmits(['update:modelValue']);

const OTHER_VALUE = '__OTHER__';

const knownValues = computed(() => (props.question.options || []).map((o) => o.value));
const otherMode = ref(
  props.question.allow_other &&
    !!props.modelValue &&
    !knownValues.value.includes(props.modelValue),
);
const selectValue = computed(() => (otherMode.value ? OTHER_VALUE : (props.modelValue ?? '')));

// GPS -- modelValue es {lat,lng,accuracy} en exito, o el string sentinela
// 'DENIED' si el navegador nego/no tiene el permiso (activa la pregunta
// ADDRESS de respaldo via depends_on_values, ver quotes/migrations
// 0028_seed_installation_info_questions.py y quoteVisibility.js).
const gpsLoading = ref(false);
const gpsCoords = computed(() => (
  props.modelValue && typeof props.modelValue === 'object' ? props.modelValue : null
));

function shareLocation() {
  if (!navigator.geolocation) {
    emit('update:modelValue', 'DENIED');
    return;
  }
  gpsLoading.value = true;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      gpsLoading.value = false;
      emit('update:modelValue', {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      });
    },
    () => {
      gpsLoading.value = false;
      emit('update:modelValue', 'DENIED');
    },
    { enableHighAccuracy: true, timeout: 10000 },
  );
}

// FILE (multi-archivo) -- ver requirement_documents, Fase 5 de la
// simplificacion del wizard (2026-07-23). modelValue es un array de File;
// la misma politica de extension/tamaño se re-valida en el backend
// (validate_file, quotes/services/commands.py) -- esto es solo UX temprana.
const FILE_ALLOWED_EXT = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'];
const FILE_ACCEPT = FILE_ALLOWED_EXT.join(',');
const FILE_MAX_SIZE = 20 * 1024 * 1024;
const fileErrors = ref([]);
const fileList = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []));

function onFilesSelected(event) {
  const picked = Array.from(event.target.files || []);
  event.target.value = '';
  const errors = [];
  const accepted = [];
  for (const f of picked) {
    const ext = `.${f.name.split('.').pop().toLowerCase()}`;
    if (!FILE_ALLOWED_EXT.includes(ext)) {
      errors.push(`${f.name}: formato no permitido.`);
    } else if (f.size > FILE_MAX_SIZE) {
      errors.push(`${f.name}: supera el limite de 20 MB.`);
    } else {
      accepted.push(f);
    }
  }
  fileErrors.value = errors;
  if (accepted.length) {
    emit('update:modelValue', [...fileList.value, ...accepted]);
  }
}

function removeFile(index) {
  const next = fileList.value.filter((_, i) => i !== index);
  emit('update:modelValue', next.length ? next : undefined);
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function onSelectChange(value) {
  if (value === OTHER_VALUE) {
    otherMode.value = true;
    emit('update:modelValue', '');
  } else {
    otherMode.value = false;
    emit('update:modelValue', value);
  }
}

function toggleMultiValue(value, checked) {
  const current = props.modelValue || [];
  emit('update:modelValue', checked ? [...current, value] : current.filter((v) => v !== value));
}

// DYNAMIC_LIST — array of strings
const listValue = computed(() => props.modelValue || []);

function addListRow() {
  emit('update:modelValue', [...listValue.value, '']);
}
function updateListRow(i, value) {
  const next = [...listValue.value];
  next[i] = value;
  emit('update:modelValue', next);
}
function removeListRow(i) {
  emit('update:modelValue', listValue.value.filter((_, idx) => idx !== i));
}

// TABLE — array of row-arrays, one entry per table_columns
const tableValue = computed(() => props.modelValue || []);

function blankRow() {
  return (props.question.table_columns || []).map(() => '');
}
function addTableRow() {
  emit('update:modelValue', [...tableValue.value, blankRow()]);
}
function updateTableCell(ri, ci, value) {
  const next = tableValue.value.map((row) => [...row]);
  next[ri][ci] = value;
  emit('update:modelValue', next);
}
function removeTableRow(ri) {
  emit('update:modelValue', tableValue.value.filter((_, idx) => idx !== ri));
}
</script>
