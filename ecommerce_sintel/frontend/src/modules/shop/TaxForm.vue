<template>
  <form @submit.prevent="submit">
    <div class="mb-3">
      <label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Ej: IVA 19%">
    </div>

    <div class="mb-3">
      <label class="form-label small fw-bold">Tipo <span class="text-danger">*</span></label>
      <select v-model="form.tax_type" class="form-select" required>
        <option value="percentage">Porcentaje (%)</option>
        <option value="fixed">Monto Fijo ($)</option>
      </select>
    </div>

    <div class="mb-3">
      <label class="form-label small fw-bold">
        Valor {{ form.tax_type === 'percentage' ? '(%)' : '($)' }} <span class="text-danger">*</span>
      </label>
      <div class="input-group">
        <span class="input-group-text">{{ form.tax_type === 'percentage' ? '%' : '$' }}</span>
        <input v-model="form.value" type="number" step="0.01" min="0" class="form-control" required placeholder="0.00">
      </div>
    </div>

    <div class="mb-4 form-check form-switch">
      <input v-model="form.is_active" class="form-check-input" type="checkbox" id="taxActive">
      <label class="form-check-label small" for="taxActive">Impuesto Activo</label>
    </div>

    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? 'Crear Impuesto' : 'Guardar Cambios' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useShopAdminStore } from '@/store/shopAdmin';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useShopAdminStore();
const { actionLoading: loading } = storeToRefs(store);

const emptyForm = () => ({ name: '', tax_type: 'percentage', value: '', is_active: true });
const form = ref(emptyForm());

watch(() => props.item, (val) => {
  if (val && props.mode === 'edit') {
    form.value = { name: val.name, tax_type: val.tax_type, value: val.value, is_active: val.is_active };
  } else {
    form.value = emptyForm();
  }
}, { immediate: true });

async function submit() {
  const res = props.mode === 'create'
    ? await store.createTax(form.value)
    : await store.updateTax(props.item.uuid, form.value);

  if (res.ok) {
    toast.success(props.mode === 'create' ? 'Impuesto creado' : 'Impuesto actualizado');
    emit('success');
  } else {
    handleError(res.error, 'Error al guardar');
  }
}
</script>
