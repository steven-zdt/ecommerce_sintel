<template>
  <form @submit.prevent="submit">
    <div class="mb-4">
      <label class="form-label small fw-bold">Nombre del Nivel <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Ej: Básico, Intermedio, Avanzado">
    </div>
    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? 'Crear Nivel' : 'Guardar Cambios' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useTechnicalServicesCatalogStore } from '@/store/technicalServicesAdmin/catalog';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const store = useTechnicalServicesCatalogStore();
const toast = useToast();
const loading = ref(false);
const form = ref({ name: '' });

watch(() => props.item, (val) => {
  form.value = { name: (val && props.mode === 'edit') ? val.name : '' };
}, { immediate: true });

async function submit() {
  loading.value = true;
  try {
    if (props.mode === 'create') {
      const res = await store.createLevel(form.value);
      if (!res.ok) {
        throw new Error(res.error);
      }
      toast.success('Nivel creado');
    } else {
      const res = await store.updateLevel(props.item.uuid, form.value);
      if (!res.ok) {
        throw new Error(res.error);
      }
      toast.success('Nivel actualizado');
    }
    emit('success');
  } catch (e) {
    toast.error(e.message || 'Error al guardar');
  } finally {
    loading.value = false;
  }
}
</script>
