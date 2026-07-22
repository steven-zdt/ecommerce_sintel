<template>
  <div class="form-check form-switch d-flex justify-content-center align-items-center" style="min-height: 38px;">
    <input
      class="form-check-input"
      type="checkbox"
      role="switch"
      :checked="modelValue"
      @change="handleChange"
      :disabled="loading"
    />
    <span v-if="loading" class="spinner-border spinner-border-sm text-primary ms-2"></span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useToast } from '@/composables/useToast';

const props = defineProps<{ modelValue: boolean; onSave: (value: boolean) => Promise<void>; }>();
const loading = ref(false);
const toast = useToast();

const handleChange = async (event: Event) => {
  loading.value = true;
  const target = event.target as HTMLInputElement;
  try {
    await props.onSave(target.checked);
  } catch (e: any) {
    toast.error(e.message || 'Error al actualizar');
    target.checked = !target.checked; // Revert on error
  } finally {
    loading.value = false;
  }
};
</script>