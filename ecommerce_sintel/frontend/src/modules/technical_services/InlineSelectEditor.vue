<template>
  <div class="inline-editor-wrapper" @click.stop="!isEditing && startEditing()">
    <!-- Display Mode -->
    <div v-if="!isEditing" class="display-mode">
      <slot :value="modelValue" :display-text="currentText">
        <span class="badge bg-light text-dark border fw-medium editable-value">
          {{ currentText || 'No asignado' }}
        </span>
      </slot>
      <i class="bi bi-pencil-fill edit-icon"></i>
    </div>

    <!-- Edit Mode -->
    <div v-else ref="editorRef" class="edit-mode">
      <div class="input-group input-group-sm">
        <select
          ref="inputRef"
          class="form-select form-select-sm"
          v-model="internalValue"
          @change="save(internalValue)"
        >
          <option v-if="placeholder" :value="null">{{ placeholder }}</option>
          <option v-for="option in options" :key="option.value" :value="option.value">
            {{ option.text }}
          </option>
        </select>
        <button class="btn btn-outline-secondary" type="button" @click="cancel" :disabled="loading">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
      <div v-if="error" class="text-danger small mt-1">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useInlineEditor } from './useInlineEditor';

type SelectOption = { value: string | number; text: string };

const props = defineProps<{
  modelValue: string | number | null;
  options: SelectOption[];
  placeholder?: string;
  onSave: (value: any) => Promise<void>;
}>();

const internalValue = ref(props.modelValue);

const { isEditing, loading, error, editorRef, inputRef, startEditing, save, cancel } = useInlineEditor(props.onSave);

const currentText = computed(() => {
  const selectedOption = props.options.find(opt => opt.value === props.modelValue);
  return selectedOption?.text;
});

watch(() => props.modelValue, (newValue) => {
  internalValue.value = newValue;
});

watch(isEditing, (editing) => {
  if (editing) internalValue.value = props.modelValue;
});
</script>

<style scoped src="./inline-editor.css"></style>