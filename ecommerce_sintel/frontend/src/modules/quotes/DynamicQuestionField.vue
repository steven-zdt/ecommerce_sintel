<template>
  <div>
    <label class="form-label small">{{ question.label }} <span v-if="question.is_required" class="text-danger">*</span></label>
    <div v-if="question.description" class="form-text small mb-1">{{ question.description }}</div>
    <div v-if="question.help_text" class="form-text small mb-1">{{ question.help_text }}</div>

    <input
      v-if="['TEXT', 'ADDRESS', 'GPS'].includes(question.question_type)"
      :value="modelValue" @input="$emit('update:modelValue', $event.target.value)"
      type="text" class="form-control form-control-sm" :placeholder="question.placeholder"
      :pattern="question.validation_regex || undefined"
    />
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

    <div v-else-if="['IMAGE', 'FILE', 'SIGNATURE'].includes(question.question_type)">
      <input
        type="file" class="form-control form-control-sm"
        :accept="question.question_type === 'FILE' ? undefined : 'image/*'"
        @change="$emit('update:modelValue', $event.target.files[0] || null)"
      />
      <div v-if="modelValue" class="text-muted small mt-1"><i class="bi bi-paperclip me-1"></i>{{ modelValue.name }}</div>
      <div v-if="question.question_type === 'SIGNATURE'" class="form-text small">Sube una foto o captura de tu firma.</div>
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
