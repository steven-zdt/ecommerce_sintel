<template>
  <form @submit.prevent="submit">
    <div class="mb-3">
      <label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Ej: Operador, Instalación">
    </div>
    <div class="mb-3">
      <label class="form-label small fw-bold">Descripción</label>
      <textarea v-model="form.description" class="form-control" rows="2"></textarea>
    </div>
    <div class="mb-3">
      <label class="form-label small fw-bold">Precio por Hora <span class="text-danger">*</span></label>
      <input v-model="form.price_per_hour" type="number" step="0.01" min="0.01" class="form-control" required placeholder="0.00">
    </div>
    <div class="mb-4 form-check form-switch">
      <input v-model="form.is_active" class="form-check-input" type="checkbox" id="laborActive">
      <label class="form-check-label small" for="laborActive">Activo</label>
    </div>
    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? 'Crear' : 'Guardar' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const loading = ref(false);
const form = ref({ name: '', description: '', price_per_hour: '', is_active: true });

watch(() => props.item, (val) => {
  form.value = (val && props.mode === 'edit')
    ? { name: val.name, description: val.description || '', price_per_hour: val.price_per_hour, is_active: val.is_active }
    : { name: '', description: '', price_per_hour: '', is_active: true };
}, { immediate: true });

async function submit() {
  loading.value = true;
  try {
    if (props.mode === 'create') {
      await api.post('dashboard/rental-labor/', form.value);
      toast.success('Mano de obra creada');
    } else {
      await api.patch(`dashboard/rental-labor/${props.item.id}/`, form.value);
      toast.success('Mano de obra actualizada');
    }
    emit('success');
  } catch (e) {
    handleError(e, 'Error al guardar');
  } finally {
    loading.value = false;
  }
}
</script>
