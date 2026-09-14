<template>
  <div class="op-card">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h6 class="fw-bold mb-0"><i class="bi bi-cash-coin me-1"></i>Precio comercial</h6>
      <span class="badge" :class="statusBadgeClass">{{ quotation?.price_status_display || 'Estimado' }}</span>
    </div>

    <div class="op-row"><span class="text-muted small">Fuente</span><span>{{ sourceLabel }}</span></div>
    <div v-if="quotation?.unit_price_snapshot" class="op-row">
      <span class="text-muted small">Tarifa</span><span>${{ fmt(quotation.unit_price_snapshot) }}</span>
    </div>
    <div v-if="quotation?.project_price_snapshot" class="op-row">
      <span class="text-muted small">Precio proyecto</span><span>${{ fmt(quotation.project_price_snapshot) }}</span>
    </div>
    <div class="op-row"><span class="text-muted small">Total de la orden</span><span class="fw-bold">${{ fmt(order?.total_amount) }}</span></div>
    <div v-if="quotation?.confirmed_total" class="op-row">
      <span class="text-muted small">Total confirmado/ajustado</span>
      <span class="fw-bold text-primary">${{ fmt(quotation.confirmed_total) }}</span>
    </div>

    <div v-if="!isLocked && !isEditing" class="d-flex gap-2 mt-2">
      <button class="btn btn-sm btn-outline-secondary" :disabled="saving" @click="$emit('confirm')">
        <i class="bi bi-check2 me-1"></i>Confirmar precio
      </button>
      <button class="btn btn-sm btn-outline-primary" :disabled="saving" @click="startEdit">
        <i class="bi bi-pencil me-1"></i>Editar precio
      </button>
    </div>

    <div v-if="isEditing" class="mt-3 p-3 rounded bg-white border">
      <label class="form-label small fw-semibold mb-1">Nuevo total (COP)</label>
      <input v-model.number="newTotal" type="number" min="0" step="1000" class="form-control form-control-sm mb-2">
      <label class="form-label small fw-semibold mb-1">Motivo del cambio (obligatorio)</label>
      <textarea
        v-model="reason" class="form-control form-control-sm mb-2" rows="2"
        placeholder="Ej: trabajo en altura, dificultad especial..."
      ></textarea>
      <div class="d-flex gap-2 justify-content-end">
        <button class="btn btn-sm btn-light border" :disabled="saving" @click="cancelEdit">Cancelar</button>
        <button class="btn btn-sm btn-primary" :disabled="!canSaveOverride || saving" @click="submitOverride">
          Guardar
        </button>
      </div>
    </div>

    <div v-if="isLocked" class="small text-muted mt-2">
      <i class="bi bi-lock me-1"></i>Precio bloqueado, no se puede modificar.
    </div>
  </div>
</template>

<script setup>
/**
 * Plan "Manual Pricing Engine" (2026-08-13) FASE 16/18/19 -- bloque "PRECIO
 * COMERCIAL" del detalle de operacion en /panel/servicios/operaciones.
 * Emite `confirm`/`override` en vez de llamar la API directamente -- el padre
 * (ServiceOperationBoard.vue) ya centraliza todas las mutaciones de operacion
 * via su helper execute(), mismo patron que TechnicianSelector/ScheduleModal.
 * `override` NUNCA cambia Order.total_amount (ver OrderPricingCommands en el
 * backend) -- este componente solo manda la intencion, no decide el alcance.
 */
import { computed, ref } from 'vue';
import { formatCOP } from '@/utils/money';

const props = defineProps({
  operation: { type: Object, required: true },
  saving: { type: Boolean, default: false },
});
const emit = defineEmits(['confirm', 'override']);

const order = computed(() => props.operation.order || {});
const quotation = computed(() => order.value.quotation || null);
const isLocked = computed(() => quotation.value?.price_status === 'LOCKED');

const SOURCE_LABELS = {
  AUTOMATIC: 'Automático',
  MANUAL_PROJECT: 'Manual — Proyecto completo',
  MANUAL_GENERAL: 'Manual — Precio general',
  MANUAL_HOURLY: 'Manual — Por horas',
};
const sourceLabel = computed(() => {
  const source = quotation.value?.pricing_source_snapshot;
  return SOURCE_LABELS[source] || source || 'Sin definir';
});

const statusBadgeClass = computed(() => {
  const map = {
    ESTIMATED: 'bg-secondary-subtle text-secondary',
    CONFIRMED: 'bg-success-subtle text-success',
    OVERRIDDEN: 'bg-primary-subtle text-primary',
    LOCKED: 'bg-dark-subtle text-dark',
  };
  return map[quotation.value?.price_status] || 'bg-secondary-subtle text-secondary';
});

function fmt(v) {
  return formatCOP(Math.round(parseFloat(v) || 0));
}

const isEditing = ref(false);
const newTotal = ref(null);
const reason = ref('');

function startEdit() {
  newTotal.value = Math.round(parseFloat(quotation.value?.confirmed_total || order.value.total_amount) || 0);
  reason.value = '';
  isEditing.value = true;
}

function cancelEdit() {
  isEditing.value = false;
  reason.value = '';
}

const canSaveOverride = computed(
  () => newTotal.value !== null && newTotal.value >= 0 && reason.value.trim().length > 0,
);

function submitOverride() {
  emit('override', { new_total: newTotal.value, reason: reason.value.trim() });
  isEditing.value = false;
}
</script>

<style scoped>
.op-card { background: #f9fafb; border-radius: 10px; padding: 12px 16px; }
.op-row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid #eef0f2; }
.op-row:last-child { border-bottom: none; }
</style>
