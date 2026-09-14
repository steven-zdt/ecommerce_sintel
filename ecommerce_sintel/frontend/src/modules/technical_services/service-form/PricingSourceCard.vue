<template>
  <div class="border rounded-3 p-3 mb-3 bg-white">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h6 class="fw-semibold mb-0">Fuente del precio</h6>
      <span v-if="variant.is_manual_pricing" class="badge bg-primary-subtle text-primary border border-primary-subtle">
        <i class="bi bi-hand-index-thumb me-1"></i>Manual
      </span>
      <span v-else class="badge bg-secondary-subtle text-secondary border">
        <i class="bi bi-cpu me-1"></i>Automático
      </span>
    </div>

    <div class="d-flex flex-column gap-2 mb-3">
      <div class="form-check" v-for="opt in PRICING_SOURCE_OPTIONS" :key="opt.value">
        <input
          :id="`ps-${variant.uuid}-${opt.value}`"
          class="form-check-input"
          type="radio"
          :value="opt.value"
          v-model="form.pricing_source"
        >
        <label class="form-check-label small" :for="`ps-${variant.uuid}-${opt.value}`">{{ opt.label }}</label>
      </div>
    </div>

    <div v-if="form.pricing_source === 'MANUAL_PROJECT'" class="mb-3">
      <label class="form-label small fw-semibold mb-1">Precio total del proyecto</label>
      <input type="number" min="0" step="1000" class="form-control form-control-sm" v-model.number="form.project_price">
    </div>

    <div v-else-if="form.pricing_source === 'MANUAL_GENERAL'" class="mb-3">
      <label class="form-label small fw-semibold mb-1">Precio general</label>
      <input type="number" min="0" step="1000" class="form-control form-control-sm" v-model.number="form.unit_price">
    </div>

    <div v-else-if="form.pricing_source === 'MANUAL_HOURLY'" class="mb-3">
      <label class="form-label small fw-semibold mb-1">Tarifa manual por hora</label>
      <input type="number" min="0" step="1000" class="form-control form-control-sm" v-model.number="form.unit_price">
    </div>

    <div v-else class="alert alert-light border small mb-3 py-2">
      <i class="bi bi-info-circle me-1"></i>
      Se calcula segun SMLV colombiano (LaborCostCalculator) + reglas de costo activas.
      Ver el desglose completo abajo, en "Cálculo de Costos".
    </div>

    <div class="mb-3">
      <label class="form-label small fw-semibold mb-1">Motivo del cambio (opcional)</label>
      <textarea
        class="form-control form-control-sm"
        rows="2"
        v-model="form.reason"
        placeholder="Ej: trabajo en altura, dificultad especial..."
      ></textarea>
    </div>

    <div class="d-flex justify-content-between align-items-center pt-2 border-top">
      <span v-if="isDirty" class="text-warning small">
        <i class="bi bi-exclamation-circle me-1"></i>Cambios sin guardar
      </span>
      <span v-else class="text-success small">
        <i class="bi bi-check-circle me-1"></i>Configuración guardada
      </span>
      <button type="button" class="btn btn-primary btn-sm" :disabled="saving || !isDirty" @click="save">
        <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
        Guardar precio
      </button>
    </div>
  </div>
</template>

<script setup>
/**
 * Plan "Manual Pricing Engine" (2026-08-13) FASE 9 -- unico componente
 * dedicado a cambiar ServiceVariant.pricing_source, montado en CostosTab.vue
 * arriba de CostCalculationPanel.vue (ese sigue siendo el que muestra el
 * desglose real calculado por el backend, para AUTOMATIC y MANUAL_* por
 * igual -- ver FASE 4, mismo contrato). No se construye aqui una vista previa
 * calculada en el cliente (violaria "frontend no calcula reglas comerciales",
 * FASE 13 del plan) -- al guardar, CostosTab.vue vuelve a pedir la cotizacion
 * real al backend para el panel de abajo.
 */
import { reactive, computed, ref, watch } from 'vue';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  variant: { type: Object, required: true },
  serviceUuid: { type: String, required: true },
});
const emit = defineEmits(['saved']);

const store = useTechnicalServicesStore();
const { handleError } = useErrorHandler();
const toast = useToast();

const PRICING_SOURCE_OPTIONS = [
  { value: 'AUTOMATIC', label: 'Automático' },
  { value: 'MANUAL_PROJECT', label: 'Manual — Proyecto completo' },
  { value: 'MANUAL_GENERAL', label: 'Manual — Precio general' },
  { value: 'MANUAL_HOURLY', label: 'Manual — Por horas' },
];

function buildFormFromVariant(variant) {
  return {
    pricing_source: variant?.pricing_source || 'AUTOMATIC',
    unit_price: variant?.manual_unit_price != null ? Number(variant.manual_unit_price) : null,
    project_price: variant?.manual_project_price != null ? Number(variant.manual_project_price) : null,
    reason: '',
  };
}

const form = reactive(buildFormFromVariant(props.variant));
const saving = ref(false);

watch(() => props.variant?.uuid, () => Object.assign(form, buildFormFromVariant(props.variant)));
watch(() => props.variant?.pricing_source, () => Object.assign(form, buildFormFromVariant(props.variant)));

const isDirty = computed(() => {
  const current = props.variant || {};
  const currentUnit = current.manual_unit_price != null ? Number(current.manual_unit_price) : null;
  const currentProject = current.manual_project_price != null ? Number(current.manual_project_price) : null;
  return (
    form.pricing_source !== (current.pricing_source || 'AUTOMATIC')
    || (form.unit_price || null) !== currentUnit
    || (form.project_price || null) !== currentProject
  );
});

async function save() {
  saving.value = true;
  try {
    const payload = { pricing_source: form.pricing_source, reason: form.reason || '' };
    if (form.pricing_source === 'MANUAL_PROJECT') {
      payload.project_price = form.project_price;
    } else if (form.pricing_source === 'MANUAL_GENERAL' || form.pricing_source === 'MANUAL_HOURLY') {
      payload.unit_price = form.unit_price;
    }

    const result = await store.setVariantPricing(props.variant.uuid, payload, props.serviceUuid);
    if (result.ok) {
      toast.success('Precio actualizado.');
      form.reason = '';
      emit('saved', result.data);
    } else {
      handleError({ response: { data: { detail: result.error } } }, 'Error al guardar el precio.');
    }
  } finally {
    saving.value = false;
  }
}
</script>
