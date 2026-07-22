<template>
  <!-- Modal Backdrop -->
  <div class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.4);">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content border-0 shadow-lg">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fw-bold">Nueva Regla de Costo de Alquiler</h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        <div class="modal-body pt-3">
          <form @submit.prevent="save" id="cost-rule-form">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label small fw-semibold">Nombre <span class="text-danger">*</span></label>
                <input v-model="form.name" type="text" class="form-control" :class="{'is-invalid': errors.name}" placeholder="Ej: IVA 19%, Seguro Básico..." />
                <div class="invalid-feedback">{{ errors.name }}</div>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">Contexto <span class="text-danger">*</span></label>
                <select v-model="form.context" class="form-select">
                  <option value="TAX">IVA / Impuesto</option>
                  <option value="DISCOUNT">Descuento</option>
                  <option value="DEPOSIT">Depósito</option>
                  <option value="INSURANCE">Seguro</option>
                  <option value="SURCHARGE">Recargo</option>
                </select>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">Tipo de Costo <span class="text-danger">*</span></label>
                <select v-model="form.cost_type" class="form-select">
                  <option value="PERCENTAGE">Porcentaje (%)</option>
                  <option value="FIXED">Valor Fijo ($)</option>
                </select>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">
                  Valor <span class="text-danger">*</span>
                  <span class="text-muted fw-normal">({{ form.cost_type === 'PERCENTAGE' ? '%' : '$' }})</span>
                </label>
                <input
                  v-model.number="form.value"
                  type="number"
                  step="0.0001"
                  min="0"
                  class="form-control"
                  :class="{'is-invalid': errors.value}"
                  placeholder="19.0000"
                />
                <div class="invalid-feedback">{{ errors.value }}</div>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">Descripción</label>
                <input v-model="form.description" type="text" class="form-control" placeholder="Descripción opcional..." />
              </div>
            </div>
            <div v-if="globalError" class="alert alert-danger mt-3 py-2 small">{{ globalError }}</div>
          </form>
        </div>
        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-light border" @click="$emit('close')">Cancelar</button>
          <button type="submit" form="cost-rule-form" class="btn btn-primary" :disabled="store.actionLoading">
            <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
            Crear Regla
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRentingPricingAdminStore } from '@/store/rentingAdmin/pricing';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});
const emit = defineEmits(['success', 'close']);
const store = useRentingPricingAdminStore();

const form = reactive({
  name: '',
  context: 'TAX',
  cost_type: 'PERCENTAGE',
  value: null,
  description: '',
});

const errors = reactive({ name: null, value: null });
const globalError = ref(null);

function validate() {
  errors.name = null;
  errors.value = null;
  if (!form.name?.trim()) { errors.name = 'El nombre es requerido.'; return false; }
  if (!form.value && form.value !== 0) { errors.value = 'El valor es requerido.'; return false; }
  if (Number(form.value) < 0) { errors.value = 'El valor debe ser positivo.'; return false; }
  return true;
}

async function save() {
  globalError.value = null;
  if (!validate()) return;
  const result = await store.createCostRule({
    ...form,
    value: String(form.value),
    equipment: props.equipmentUuid,
  });
  if (result.ok) {
    emit('success', result.data);
  } else {
    globalError.value = result.error;
  }
}
</script>
