<template>
  <div class="inline-editor-wrapper" @click.stop="!isEditing && startEditing()">
    <!-- Display Mode -->
    <div v-if="!isEditing" class="display-mode">
      <slot :value="modelValue">
        <span class="editable-value">{{ modelValue || 'No asignado' }}</span>
      </slot>
      <i class="bi bi-pencil-fill edit-icon"></i>
    </div>

    <!-- Edit Mode -->
    <div v-else ref="editorRef" class="edit-mode">
      <div class="input-group input-group-sm">
        <input
          ref="inputRef"
          :type="type"
          class="form-control form-control-sm"
          v-model="internalValue"
          @keydown.enter.prevent="save(internalValue)"
          @keydown.esc.prevent="cancel"
        />
        <button class="btn btn-outline-secondary" type="button" @click="save(internalValue)" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm" role="status"></span>
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

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useInlineEditor } from './useInlineEditor';

const props = defineProps<{
  modelValue: string | number;
  type?: 'text' | 'number' | 'email' | 'url';
  onSave: (value: any) => Promise<void>;
}>();

const internalValue = ref(props.modelValue);

const {
  isEditing, loading, error,
  editorRef, inputRef,
  startEditing, save, cancel
} = useInlineEditor(props.onSave);

watch(() => props.modelValue, (newValue) => {
  internalValue.value = newValue;
});

watch(isEditing, (editing) => {
  if (editing) {
    internalValue.value = props.modelValue;
  }
});
</script>

<style scoped src="./inline-editor.css"></style>