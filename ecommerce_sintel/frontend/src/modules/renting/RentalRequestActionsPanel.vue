<template>
  <div class="actions-panel">
    <div class="row g-3 mb-3">
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Solicitud</h6>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Equipo</dt>
            <dd class="col-7">{{ request.equipment_variant?.equipment_name }} ({{ request.equipment_variant?.sku }})</dd>
            <dt class="col-5 text-muted">Cliente</dt>
            <dd class="col-7">{{ request.contact_full_name }} — {{ request.contact_email }}</dd>
            <dt class="col-5 text-muted">Telefono</dt>
            <dd class="col-7">{{ request.contact_phone || '—' }}</dd>
            <dt class="col-5 text-muted">Fechas</dt>
            <dd class="col-7">{{ request.start_date }} — {{ request.end_date }}</dd>
            <dt v-if="request.rental_mode === 'hours'" class="col-5 text-muted">Horario</dt>
            <dd v-if="request.rental_mode === 'hours'" class="col-7">{{ request.delivery_time }} - {{ request.pickup_time }}</dd>
            <dt class="col-5 text-muted">Cantidad</dt>
            <dd class="col-7">{{ request.quantity }}</dd>
            <dt class="col-5 text-muted">Total</dt>
            <dd class="col-7 fw-bold">{{ money(request.grand_total) }}</dd>
            <dt v-if="request.refund_required" class="col-5 text-muted">Reembolso</dt>
            <dd v-if="request.refund_required" class="col-7 text-danger fw-bold">Requerido</dd>
          </dl>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Ubicacion del proyecto</h6>
          <p class="small mb-1">{{ request.location_address }}</p>
          <p class="small text-muted mb-0">{{ request.location_city }}, {{ request.location_department }}</p>
          <p v-if="request.operational_notes" class="small text-muted mt-2 mb-0">{{ request.operational_notes }}</p>
        </div>
      </div>
    </div>

    <div class="detail-card">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="fw-bold mb-0">Acciones</h6>
        <button type="button" class="btn btn-sm btn-light border" @click="emit('collapse')">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <div v-if="hasAnyAction" class="d-flex flex-wrap gap-2 mb-3">
        <button v-if="canApprove" type="button" class="btn btn-success" :disabled="actionLoading" @click="approve">
          <i class="bi bi-check-circle me-1"></i>Aprobar
        </button>
        <button v-if="canReject" type="button" class="btn btn-outline-danger" @click="openAction = openAction === 'reject' ? null : 'reject'">
          Rechazar
        </button>
        <button v-if="canMarkDelivered" type="button" class="btn btn-primary" :disabled="actionLoading" @click="markDelivered">
          <i class="bi bi-truck me-1"></i>Marcar entregado
        </button>
        <button v-if="canMarkReturned" type="button" class="btn btn-success" :disabled="actionLoading" @click="markReturned">
          <i class="bi bi-box-arrow-in-down me-1"></i>Marcar devuelto
        </button>
        <button v-if="canReleasePeriod" type="button" class="btn btn-outline-warning" @click="openAction = openAction === 'release' ? null : 'release'">
          Liberar agenda
        </button>
        <button v-if="canExtend" type="button" class="btn btn-outline-primary" @click="openAction = openAction === 'extend' ? null : 'extend'">
          Extender renta
        </button>
        <button v-if="canRegisterInspection" type="button" class="btn btn-outline-secondary" @click="openAction = openAction === 'inspection' ? null : 'inspection'">
          Registrar inspeccion de devolucion
        </button>
      </div>
      <p v-else-if="!request.return_inspection" class="text-muted small mb-0">No hay acciones disponibles para el estado actual ({{ request.display_status || request.status }}).</p>

      <div v-if="request.return_inspection" class="alert mb-3" :class="request.return_inspection.has_damage ? 'alert-danger' : 'alert-success'">
        <strong>Inspeccion de devolucion:</strong> {{ request.return_inspection.has_damage ? 'Con daño' : 'Sin daño' }}
        <span v-if="request.return_inspection.condition_notes"> — {{ request.return_inspection.condition_notes }}</span>
        <span v-if="request.return_inspection.resulting_block_uuid" class="d-block small mt-1">
          Equipo bloqueado automaticamente por daño (ver pestaña Bloqueos del equipo).
        </span>
      </div>

      <div v-if="canReject && openAction === 'reject'" class="action-form">
        <textarea v-model="reasonText" class="form-control mb-2" rows="2" placeholder="Motivo del rechazo (opcional)..."></textarea>
        <button type="button" class="btn btn-danger btn-sm" :disabled="actionLoading" @click="reject">Confirmar rechazo</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>
      <div v-if="canReleasePeriod && openAction === 'release'" class="action-form">
        <textarea v-model="reasonText" class="form-control mb-2" rows="2" placeholder="Motivo (unidad danada, reprogramacion, etc.)..."></textarea>
        <button type="button" class="btn btn-warning btn-sm" :disabled="actionLoading" @click="releasePeriod">Confirmar liberacion</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>
      <div v-if="canExtend && openAction === 'extend'" class="action-form">
        <label class="form-label small text-muted">Nueva fecha de fin</label>
        <input v-model="newEndDate" type="date" class="form-control form-control-sm mb-2" :min="minExtendDate" />
        <textarea v-model="reasonText" class="form-control mb-2" rows="2" placeholder="Motivo (opcional)..."></textarea>
        <p class="small text-muted mb-2">No genera cobro automatico -- la diferencia se gestiona manualmente con el cliente.</p>
        <button type="button" class="btn btn-primary btn-sm" :disabled="actionLoading || !newEndDate" @click="extend">Confirmar extension</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>
      <div v-if="canRegisterInspection && openAction === 'inspection'" class="action-form">
        <div class="form-check mb-2">
          <input v-model="hasDamage" type="checkbox" class="form-check-input" id="inspection-has-damage" />
          <label class="form-check-label" for="inspection-has-damage">El equipo presenta daño</label>
        </div>
        <textarea v-model="conditionNotesText" class="form-control mb-2" rows="2" placeholder="Estado del equipo (opcional)..."></textarea>
        <textarea v-model="missingAccessoriesText" class="form-control mb-2" rows="2" placeholder="Accesorios faltantes (opcional)..."></textarea>
        <p v-if="hasDamage" class="small text-warning mb-2">
          <i class="bi bi-exclamation-triangle me-1"></i>Esto bloqueara el equipo automaticamente por daño.
        </p>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="actionLoading" @click="registerInspection">Confirmar inspeccion</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { formatCOP } from '@/utils/money';
import { useToast } from '@/composables/useToast';
import { useRentingRequestsAdminStore } from '@/store/rentingAdmin/requests';

const props = defineProps({
  request: { type: Object, required: true },
});
const emit = defineEmits(['changed', 'collapse']);

const toast = useToast();
const store = useRentingRequestsAdminStore();

const openAction = ref(null);
const reasonText = ref('');
const newEndDate = ref('');
const hasDamage = ref(false);
const conditionNotesText = ref('');
const missingAccessoriesText = ref('');
const actionLoading = ref(false);

// Espeja RentalRequestCommands en renting/services/commands.py -- evita ofrecer
// una accion que el backend va a rechazar con 400 por estar en el estado equivocado.
const canApprove = computed(() => props.request.status === 'pending_validation');
const canReject = computed(() => props.request.status === 'pending_validation');
const canMarkDelivered = computed(() => ['paid', 'confirmed'].includes(props.request.status));
const canMarkReturned = computed(() => props.request.status === 'in_operation');
const canReleasePeriod = computed(() => ['paid', 'confirmed', 'in_operation'].includes(props.request.status));
// extend_period() solo admite modo dias -- ver renting/services/commands.py
const canExtend = computed(() =>
  ['paid', 'confirmed', 'in_operation'].includes(props.request.status) && props.request.rental_mode === 'days'
);
const minExtendDate = computed(() => {
  if (!props.request.end_date) return undefined;
  const next = new Date(props.request.end_date);
  next.setDate(next.getDate() + 1);
  return next.toISOString().slice(0, 10);
});
// return_inspection() es opcional/aparte: no gatea mark-returned, solo exige finished
const canRegisterInspection = computed(() => props.request.status === 'finished' && !props.request.return_inspection);
const hasAnyAction = computed(() =>
  canApprove.value || canReject.value || canMarkDelivered.value || canMarkReturned.value ||
  canReleasePeriod.value || canExtend.value || canRegisterInspection.value
);

function money(value) {
  return formatCOP(value, { withSymbol: true });
}

function resetForms() {
  openAction.value = null;
  reasonText.value = '';
  newEndDate.value = '';
  hasDamage.value = false;
  conditionNotesText.value = '';
  missingAccessoriesText.value = '';
}

async function approve() {
  actionLoading.value = true;
  const result = await store.approveRentalRequest(props.request.uuid);
  actionLoading.value = false;
  if (result.ok) { toast.success('Solicitud aprobada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function reject() {
  actionLoading.value = true;
  const result = await store.rejectRentalRequest(props.request.uuid, reasonText.value);
  actionLoading.value = false;
  if (result.ok) { toast.success('Solicitud rechazada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function markDelivered() {
  actionLoading.value = true;
  const result = await store.markDelivered(props.request.uuid);
  actionLoading.value = false;
  if (result.ok) { toast.success('Marcado como entregado.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function markReturned() {
  actionLoading.value = true;
  const result = await store.markReturned(props.request.uuid);
  actionLoading.value = false;
  if (result.ok) { toast.success('Marcado como devuelto.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function releasePeriod() {
  actionLoading.value = true;
  const result = await store.releaseRentalPeriod(props.request.uuid, reasonText.value);
  actionLoading.value = false;
  if (result.ok) { toast.success('Agenda liberada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function extend() {
  actionLoading.value = true;
  const result = await store.extendRentalPeriod(props.request.uuid, newEndDate.value, reasonText.value);
  actionLoading.value = false;
  if (result.ok) { toast.success('Renta extendida.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function registerInspection() {
  actionLoading.value = true;
  const result = await store.registerReturnInspection(props.request.uuid, {
    hasDamage: hasDamage.value,
    conditionNotes: conditionNotesText.value,
    missingAccessories: missingAccessoriesText.value,
  });
  actionLoading.value = false;
  if (result.ok) { toast.success('Inspeccion registrada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}
</script>

<style scoped>
.detail-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; height: 100%; }
.action-form { max-width: 480px; margin-top: 12px; }
</style>
