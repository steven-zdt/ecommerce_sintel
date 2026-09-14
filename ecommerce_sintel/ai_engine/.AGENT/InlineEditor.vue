<template>
  <div class="inline-editor" @click.stop="!isEditing && startEditing()">
    <div v-if="!isEditing" class="d-flex align-items-center gap-2">
      <slot name="display" :value="modelValue">
        <span class="editable-value">{{ displayValue || 'No asignado' }}</span>
      </slot>
      <i class="bi bi-pencil-fill edit-icon text-muted small"></i>
    </div>

    <div v-else ref="editorRef">
      <div class="input-group input-group-sm">
        <slot name="editor" :value="internalValue" :update="onInput">
          <!-- Default text input -->
          <input
            v-if="type === 'text' || type === 'number'"
            ref="inputRef"
            :type="type"
            class="form-control form-control-sm"
            v-model="internalValue"
            @keydown.enter.prevent="save"
            @keydown.esc.prevent="cancel"
          />
          <!-- Default select input -->
          <select
            v-if="type === 'select'"
            ref="inputRef"
            class="form-select form-select-sm"
            v-model="internalValue"
            @change="save"
          >
            <option v-for="option in options" :key="option.value" :value="option.value">
              {{ option.text }}
            </option>
          </select>
        </slot>

        <button class="btn btn-outline-secondary" type="button" @click="save" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          <i v-else class="bi bi-check-lg"></i>
        </button>
        <button class="btn btn-outline-secondary" type="button" @click="cancel" :disabled="loading">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
      <div v-if="error" class="text-danger small mt-1">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue';
import { onClickOutside } from '@vueuse/core';

const props = defineProps({
  modelValue: {
    required: true,
  },
  type: {
    type: String,
    default: 'text', // text, number, select
  },
  options: { // For select type
    type: Array,
    default: () => [], // [{ value: 'val', text: 'Display' }]
  },
  displayValue: { // Optional, for complex values like objects
    type: String,
    default: '',
  },
});

const emit = defineEmits(['update:modelValue', 'save']);

const isEditing = ref(false);
const internalValue = ref(props.modelValue);
const loading = ref(false);
const error = ref('');

const editorRef = ref(null);
const inputRef = ref(null);

onClickOutside(editorRef, () => {
  if (isEditing.value) {
    cancel();
  }
});

const startEditing = async () => {
  internalValue.value = props.modelValue;
  isEditing.value = true;
  await nextTick();
  inputRef.value?.focus();
  inputRef.value?.select();
};

const save = async () => {
  loading.value = true;
  error.value = '';
  try {
    await emit('save', internalValue.value);
    isEditing.value = false;
  } catch (e) {
    error.value = e.message || 'Error al guardar.';
  } finally {
    loading.value = false;
  }
};

const cancel = () => {
  isEditing.value = false;
  error.value = '';
};

const onInput = (val) => {
  internalValue.value = val;
};

watch(() => props.modelValue, (newVal) => {
  if (!isEditing.value) {
    internalValue.value = newVal;
  }
});
</script>

<style scoped>
.inline-editor { cursor: pointer; padding: 4px; border-radius: 4px; transition: background-color 0.2s; min-height: 38px; }
.inline-editor:hover .edit-icon { opacity: 1; }
.editable-value { transition: color 0.2s; }
.inline-editor:hover .editable-value { color: var(--bs-primary); }
.edit-icon { opacity: 0; transition: opacity 0.2s; }
</style>