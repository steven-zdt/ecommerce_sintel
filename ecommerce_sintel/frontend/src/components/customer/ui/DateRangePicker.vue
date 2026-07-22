<template>
  <div class="date-range-picker">
    <div class="row g-3">
      <div class="col-6">
        <label class="form-label small fw-bold">
          <i class="bi bi-calendar-event me-1 text-primary"></i>Fecha inicio <span class="text-danger">*</span>
        </label>
        <input
          v-model="startDate"
          type="date"
          class="form-control"
          :min="today"
          @change="onStartDateChange"
        >
      </div>
      <div class="col-6">
        <label class="form-label small fw-bold">
          <i class="bi bi-calendar-check me-1 text-primary"></i>Fecha fin <span class="text-danger">*</span>
        </label>
        <input
          v-model="endDate"
          type="date"
          class="form-control"
          :min="minimumEndDate"
          @change="onEndDateChange"
        >
      </div>
    </div>

    <!-- Resumen del alquiler -->
    <div v-if="summary" class="rental-summary mt-3">
      <div class="d-flex align-items-center gap-2 mb-2">
        <i class="bi bi-info-circle text-primary"></i>
        <span class="small fw-bold">Resumen del alquiler</span>
      </div>
      <div class="d-flex justify-content-between small text-muted mb-1">
        <span>Duración</span>
        <span class="fw-bold text-dark">{{ summary.days }} día(s)</span>
      </div>
      <div v-if="pricePerDay" class="d-flex justify-content-between small text-muted mb-1">
        <span>Precio por día</span>
        <span>${{ fmt(pricePerDay) }}</span>
      </div>
      <div v-if="pricePerHour" class="d-flex justify-content-between small text-muted mb-1">
        <span>Precio por hora</span>
        <span>${{ fmt(pricePerHour) }}</span>
      </div>
      <hr class="my-2">
      <div class="d-flex justify-content-between fw-bold">
        <span>Total estimado</span>
        <span class="text-primary">${{ fmt(summary.total) }}</span>
      </div>
    </div>

    <p v-if="error" class="text-danger small mt-2">
      <i class="bi bi-exclamation-circle me-1"></i>{{ error }}
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  modelValue: { type: Object, default: () => ({ startDate: '', endDate: '' }) },
  pricePerDay: { type: [String, Number], default: null },
  pricePerHour: { type: [String, Number], default: null },
});

const emit = defineEmits(['update:modelValue', 'range-selected']);

// No usar toISOString(): trabaja en UTC y en Colombia puede bloquear el día
// actual a partir de las 19:00. Los límites del input deben ser fechas locales.
function toLocalDateInput(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const today = toLocalDateInput(new Date());
const startDate = ref(props.modelValue?.startDate || '');
const endDate = ref(props.modelValue?.endDate || '');
const error = ref('');

const minimumEndDate = computed(() => {
  if (!startDate.value) return today;
  const nextDay = new Date(`${startDate.value}T12:00:00`);
  nextDay.setDate(nextDay.getDate() + 1);
  return toLocalDateInput(nextDay);
});

const summary = computed(() => {
  if (!startDate.value || !endDate.value) return null;
  const start = new Date(startDate.value);
  const end = new Date(endDate.value);
  const days = Math.max(1, Math.ceil((end - start) / (1000 * 60 * 60 * 24)));
  let total = 0;
  if (props.pricePerDay) total = days * parseFloat(props.pricePerDay);
  return { days, total };
});

function emitRange() {
  const val = { startDate: startDate.value, endDate: endDate.value };
  emit('update:modelValue', val);
  if (summary.value) emit('range-selected', { ...summary.value });
}

function onStartDateChange() {
  error.value = '';
  // Al cambiar el inicio, no bloquear el calendario. Si el fin anterior ya no
  // sirve, se limpia para que el usuario pueda escoger uno nuevo.
  if (endDate.value && endDate.value < minimumEndDate.value) {
    endDate.value = '';
  }
  emitRange();
}

function onEndDateChange() {
  error.value = '';
  if (startDate.value && endDate.value && endDate.value <= startDate.value) {
    error.value = 'La fecha de fin debe ser posterior a la de inicio.';
    endDate.value = '';
    emitRange();
    return;
  }
  emitRange();
}

watch(() => props.modelValue, (v) => {
  if (v) {
    startDate.value = v.startDate || '';
    endDate.value = v.endDate || '';
  }
}, { deep: true });

const fmt = (val) => new Intl.NumberFormat('es-CO').format(parseFloat(val) || 0);
</script>

<style scoped>
.rental-summary {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 14px;
}
</style>
