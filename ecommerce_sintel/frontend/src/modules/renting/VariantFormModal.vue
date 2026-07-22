<template>
  <!-- Modal Backdrop -->
  <div class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.4);">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content border-0 shadow-lg">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fw-bold">
            {{ mode === 'create' ? 'Nueva Variante' : 'Editar Variante' }}
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        <div class="modal-body pt-3">
          <form @submit.prevent="save" id="variant-form">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label small fw-semibold">SKU <span class="text-danger">*</span></label>
                <input v-model="form.sku" type="text" class="form-control" :class="{'is-invalid': errors.sku}" placeholder="Ej: GA110-STD" />
                <div class="invalid-feedback">{{ errors.sku }}</div>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">Precio / Día</label>
                <div class="input-group">
                  <span class="input-group-text">$</span>
                  <input v-model.number="form.rental_price_per_day" type="number" step="0.01" min="0.01" class="form-control" placeholder="150.00" />
                </div>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">Precio / Hora</label>
                <div class="input-group">
                  <span class="input-group-text">$</span>
                  <input v-model.number="form.rental_price_per_hour" type="number" step="0.01" min="0.01" class="form-control" placeholder="25.00" />
                </div>
              </div>
              <div class="col-sm-6">
                <label class="form-label small fw-semibold">Stock</label>
                <input v-model.number="form.stock" type="number" min="0" class="form-control" placeholder="0" />
              </div>
              <div class="col-sm-6 d-flex align-items-center pt-4">
                <div class="form-check form-switch ms-1">
                  <input class="form-check-input" type="checkbox" v-model="form.is_active" id="variant-active" />
                  <label class="form-check-label small fw-semibold" for="variant-active">Variante activa</label>
                </div>
              </div>
            </div>
            <div v-if="globalError" class="alert alert-danger mt-3 py-2 small">{{ globalError }}</div>
          </form>
        </div>
        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-light border" @click="$emit('close')">Cancelar</button>
          <button type="submit" form="variant-form" class="btn btn-primary" :disabled="store.actionLoading">
            <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
            {{ mode === 'create' ? 'Crear Variante' : 'Guardar Cambios' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
  variant: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'close']);

const store = useRentingCatalogAdminStore();

const form = reactive({
  sku: '',
  rental_price_per_day: null,
  rental_price_per_hour: null,
  stock: 0,
  is_active: true,
});

const errors = reactive({ sku: null });
const globalError = ref(null);

watch(() => props.variant, (v) => {
  if (v) Object.assign(form, {
    sku: v.sku,
    rental_price_per_day: v.rental_price_per_day,
    rental_price_per_hour: v.rental_price_per_hour,
    stock: v.stock,
    is_active: v.is_active,
  });
}, { immediate: true });

function validate() {
  errors.sku = null;
  if (!form.sku?.trim()) { errors.sku = 'El SKU es requerido.'; return false; }
  if (!form.rental_price_per_day && !form.rental_price_per_hour) {
    globalError.value = 'Debe ingresar al menos un precio (por día o por hora).';
    return false;
  }
  return true;
}

async function save() {
  globalError.value = null;
  if (!validate()) return;
  const payload = { ...form };
  let result;
  if (props.mode === 'create') {
    result = await store.createVariant(props.equipmentUuid, payload);
  } else {
    result = await store.updateVariant(props.equipmentUuid, props.variant.uuid, payload);
  }
  if (result.ok) {
    emit('success', result.data);
  } else {
    globalError.value = result.error;
  }
}
</script>
