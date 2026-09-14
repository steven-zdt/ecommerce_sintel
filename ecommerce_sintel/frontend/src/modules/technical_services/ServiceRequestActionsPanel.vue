<template>
  <div class="actions-panel">
    <div class="row g-3 mb-3">
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Cliente</h6>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Nombre</dt>
            <dd class="col-7">{{ request.customer?.name }}</dd>
            <dt class="col-5 text-muted">Email</dt>
            <dd class="col-7">{{ request.customer?.email }}</dd>
            <dt class="col-5 text-muted">Direccion</dt>
            <dd class="col-7">{{ request.customer?.address || '—' }}</dd>
          </dl>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Servicio</h6>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Servicio</dt>
            <dd class="col-7">{{ request.service?.name }} ({{ request.service?.category }})</dd>
            <dt class="col-5 text-muted">Variante</dt>
            <dd class="col-7">{{ request.variant?.sku }}</dd>
            <dt class="col-5 text-muted">Precio</dt>
            <dd class="col-7 fw-bold">{{ money(request.variant?.price) }}</dd>
          </dl>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Pago</h6>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Metodo</dt>
            <dd class="col-7">{{ request.payment?.method }}</dd>
            <dt class="col-5 text-muted">Estado orden</dt>
            <dd class="col-7">{{ request.payment?.order_status }}</dd>
            <dt class="col-5 text-muted">Total</dt>
            <dd class="col-7 fw-bold">{{ money(request.commercial?.total_amount) }}</dd>
          </dl>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="detail-card">
          <h6 class="fw-bold mb-3">Solicitud</h6>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Prioridad</dt>
            <dd class="col-7">
              <span class="badge" :class="enums.cssClass('service-priorities', request.commercial?.priority)">
                {{ enums.label('service-priorities', request.commercial?.priority, request.commercial?.priority) }}
              </span>
            </dd>
            <dt class="col-5 text-muted">Fecha preferida</dt>
            <dd class="col-7">{{ request.schedule?.preferred_date || '—' }} {{ request.schedule?.preferred_time || '' }}</dd>
            <dt class="col-5 text-muted">Creada</dt>
            <dd class="col-7">{{ formatDate(request.created_at) }}</dd>
          </dl>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-lg-6">
        <div class="detail-card">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="fw-bold mb-0">Operacion</h6>
            <RouterLink
              :to="{ name: 'service-operations', query: { search: request.order_id } }"
              class="btn btn-sm btn-outline-secondary"
            >
              Ver operacion <i class="bi bi-box-arrow-up-right ms-1"></i>
            </RouterLink>
          </div>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Estado</dt>
            <dd class="col-7"><OperationStatusBadge v-if="request.operation" :status="request.operation.status" /></dd>
            <dt class="col-5 text-muted">Tecnico</dt>
            <dd class="col-7">
              {{ request.technician?.name || 'Sin asignar' }}
              <span v-if="request.technician?.diverges" class="badge bg-warning-subtle text-warning ms-1" title="El sistema legacy tiene otro tecnico asignado">
                <i class="bi bi-exclamation-triangle"></i> Diverge
              </span>
            </dd>
            <dt class="col-5 text-muted">Programada</dt>
            <dd class="col-7">{{ request.schedule?.scheduled_date || '—' }} {{ request.schedule?.scheduled_time || '' }}</dd>
          </dl>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="detail-card">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="fw-bold mb-0">Orden</h6>
            <RouterLink :to="{ name: 'order-detail', params: { uuid: request.order_id } }" class="btn btn-sm btn-outline-secondary">
              Ver orden <i class="bi bi-box-arrow-up-right ms-1"></i>
            </RouterLink>
          </div>
          <dl class="row small mb-0">
            <dt class="col-5 text-muted">Estado solicitud</dt>
            <dd class="col-7">
              <span class="badge" :class="enums.cssClass('service-order-statuses', request.request_status)">
                {{ enums.label('service-order-statuses', request.request_status, request.request_status) }}
              </span>
            </dd>
            <dt class="col-5 text-muted">Tracking</dt>
            <dd class="col-7">{{ request.tracking_number || '—' }}</dd>
          </dl>
        </div>
      </div>
    </div>

    <div class="detail-card mb-3">
      <h6 class="fw-bold mb-3">Timeline</h6>
      <StatusTimeline mode="events" :events="timelineEvents" empty-message="Sin eventos registrados." />
    </div>

    <div class="detail-card">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="fw-bold mb-0">Acciones</h6>
        <button type="button" class="btn btn-sm btn-light border" @click="emit('collapse')">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <p v-if="isInExecutionOrClosed" class="text-muted small mb-0">
        Esta solicitud ya esta en ejecucion o cerrada -- las acciones de esta etapa
        (visita, cierre, incidentes) se gestionan desde
        <RouterLink :to="{ name: 'service-operations', query: { search: request.order_id } }">Operaciones</RouterLink>.
      </p>
      <template v-else>
        <div v-if="hasAnyAction" class="d-flex flex-wrap gap-2 mb-3">
          <button v-if="canPlan" type="button" class="btn btn-primary" @click="openAction = openAction === 'plan' ? null : 'plan'">
            <i class="bi bi-calendar-check me-1"></i>Planificar
          </button>
          <button v-if="canAssign" type="button" class="btn btn-success" @click="openAssign">
            <i class="bi bi-person-check me-1"></i>{{ request.technician?.uuid ? 'Cambiar tecnico' : 'Asignar tecnico' }}
          </button>
          <button v-if="canSchedule" type="button" class="btn btn-outline-primary" @click="openAction = openAction === 'schedule' ? null : 'schedule'">
            Reprogramar
          </button>
          <button v-if="canNotify" type="button" class="btn btn-outline-secondary" :disabled="actionLoading" @click="notify">
            <i class="bi bi-bell me-1"></i>Notificar cliente
          </button>
          <button v-if="canCancel" type="button" class="btn btn-outline-danger" @click="openAction = openAction === 'cancel' ? null : 'cancel'">
            Cancelar
          </button>
        </div>
        <p v-else class="text-muted small mb-0">No hay acciones disponibles para el estado actual.</p>
      </template>

      <div v-if="canPlan && openAction === 'plan'" class="action-form">
        <label class="form-label small text-muted">Fecha</label>
        <input v-model="planDate" type="date" class="form-control form-control-sm mb-2" />
        <label class="form-label small text-muted">Hora</label>
        <input v-model="planTime" type="time" class="form-control form-control-sm mb-2" />
        <label class="form-label small text-muted">Duracion estimada (minutos, opcional)</label>
        <input v-model.number="planDuration" type="number" min="1" class="form-control form-control-sm mb-2" />
        <textarea v-model="planNotes" class="form-control mb-2" rows="2" placeholder="Notas (opcional)..."></textarea>
        <button type="button" class="btn btn-primary btn-sm" :disabled="actionLoading || !planDate || !planTime" @click="plan">Confirmar planificacion</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>

      <div v-if="canAssign && openAction === 'assign'" class="action-form">
        <div v-if="loadingCandidates" class="small text-muted">Cargando tecnicos disponibles...</div>
        <template v-else>
          <label class="form-label small text-muted">Tecnico</label>
          <select v-model="selectedTechnicianUuid" class="form-select form-select-sm mb-2">
            <option value="" disabled>Selecciona un tecnico...</option>
            <option v-for="c in candidates" :key="c.uuid" :value="c.uuid">
              {{ c.full_name }}{{ c.has_conflict ? ' (conflicto de horario)' : '' }}
            </option>
          </select>
          <p v-if="!candidates.length" class="small text-muted">No hay tecnicos candidatos disponibles.</p>
        </template>
        <button type="button" class="btn btn-success btn-sm" :disabled="actionLoading || !selectedTechnicianUuid" @click="assign">Confirmar asignacion</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>

      <div v-if="canSchedule && openAction === 'schedule'" class="action-form">
        <label class="form-label small text-muted">Nueva fecha</label>
        <input v-model="scheduleDate" type="date" class="form-control form-control-sm mb-2" />
        <label class="form-label small text-muted">Nueva hora</label>
        <input v-model="scheduleTime" type="time" class="form-control form-control-sm mb-2" />
        <button type="button" class="btn btn-primary btn-sm" :disabled="actionLoading || !scheduleDate || !scheduleTime" @click="schedule">Confirmar reprogramacion</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>

      <div v-if="canCancel && openAction === 'cancel'" class="action-form">
        <textarea v-model="cancelReason" class="form-control mb-2" rows="2" placeholder="Motivo de la cancelacion (opcional)..."></textarea>
        <button type="button" class="btn btn-danger btn-sm" :disabled="actionLoading" @click="cancel">Confirmar cancelacion</button>
        <button type="button" class="btn btn-light btn-sm ms-2" @click="openAction = null">Cancelar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { formatCOP } from '@/utils/money';
import { useEnums } from '@/composables/useEnums';
import { useToast } from '@/composables/useToast';
import { useServiceRequestsAdminStore } from '@/store/technicalServicesAdmin/requests';
import useApi from '@/composables/useApi';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';
import OperationStatusBadge from '@/components/customer/services/OperationStatusBadge.vue';

const props = defineProps({
  request: { type: Object, required: true },
});
const emit = defineEmits(['changed', 'collapse']);

const enums = useEnums();
const toast = useToast();
const store = useServiceRequestsAdminStore();
const api = useApi();

const openAction = ref(null);
const actionLoading = ref(false);
const planDate = ref('');
const planTime = ref('');
const planDuration = ref(null);
const planNotes = ref('');
const scheduleDate = ref('');
const scheduleTime = ref('');
const cancelReason = ref('');
const selectedTechnicianUuid = ref('');
const candidates = ref([]);
const loadingCandidates = ref(false);

// Espeja ServiceOperationCommands (technical_services/services/operations.py) --
// evita ofrecer una accion que el backend va a rechazar por estar en el estado
// equivocado. Estados de ejecucion/cierre (READY_TO_VISIT en adelante) no tienen
// accion aqui a proposito -- se gestionan en el board de Operaciones existente
// (FASE 12 del plan "Fachada Administrativa Unificada": la fachada enlaza, no duplica).
const EXECUTION_STATES = ['READY_TO_VISIT', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED'];
const opStatus = computed(() => props.request.operation?.status);
const isInExecutionOrClosed = computed(() => EXECUTION_STATES.includes(opStatus.value));

const canPlan = computed(() => ['READY_FOR_PLANNING', 'PLANNED'].includes(opStatus.value));
// Migracion "autoridad unica de tecnico" FASE 2 (2026-08-14): assign_technician()
// ya permite pre-asignar tecnico antes de planear (sin fecha, sin slot reservado
// todavia -- se completa al planear). READY_FOR_PLANNING se habilita aqui para
// que la fachada ofrezca la misma capacidad que el backend ya soporta.
const canAssign = computed(() => ['READY_FOR_PLANNING', 'PLANNED', 'TECHNICIAN_ASSIGNED'].includes(opStatus.value));
const canSchedule = computed(() => !!opStatus.value && !isInExecutionOrClosed.value && opStatus.value !== 'CANCELLED');
const canNotify = computed(() => opStatus.value === 'TECHNICIAN_ASSIGNED');
const canCancel = computed(() => !!opStatus.value && !isInExecutionOrClosed.value && opStatus.value !== 'CANCELLED');
const hasAnyAction = computed(() => canPlan.value || canAssign.value || canSchedule.value || canNotify.value || canCancel.value);

const timelineEvents = computed(() =>
  (props.request.timeline || []).map((ev, idx) => ({
    key: `${ev.source}-${idx}`,
    label: ev.source === 'order'
      ? `Solicitud: ${enums.label('service-order-statuses', ev.status, ev.status)}`
      : ev.status,
    description: ev.actor ? `por ${ev.actor}` : '',
    date: ev.created_at,
    color: ev.source === 'order' ? '#0f766e' : '#2563eb',
    icon: ev.source === 'order' ? 'bi-receipt' : 'bi-gear',
  }))
);

function money(value) {
  return value != null ? formatCOP(value, { withSymbol: true }) : '—';
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

function resetForms() {
  openAction.value = null;
  planDate.value = ''; planTime.value = ''; planDuration.value = null; planNotes.value = '';
  scheduleDate.value = ''; scheduleTime.value = ''; cancelReason.value = '';
  selectedTechnicianUuid.value = ''; candidates.value = [];
}

async function openAssign() {
  openAction.value = openAction.value === 'assign' ? null : 'assign';
  if (openAction.value !== 'assign' || !props.request.operation) return;
  loadingCandidates.value = true;
  try {
    // Reusa el endpoint ya existente de ServiceOperationViewSet (FASE 10 del
    // plan: "no crear nuevo selector de tecnicos") en vez de duplicar la
    // logica de ProfessionalAvailability/TechnicianAvailabilityEngine aqui.
    const { data } = await api.get(`service-operations/${props.request.operation.uuid}/available-technicians/`);
    candidates.value = data;
  } catch {
    candidates.value = [];
  } finally {
    loadingCandidates.value = false;
  }
}

async function plan() {
  actionLoading.value = true;
  const result = await store.planRequest(props.request.order_id, {
    scheduledDate: planDate.value, scheduledTime: planTime.value,
    estimatedDurationMinutes: planDuration.value || null, notes: planNotes.value,
  });
  actionLoading.value = false;
  if (result.ok) { toast.success('Solicitud planificada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function assign() {
  actionLoading.value = true;
  const result = await store.assignTechnician(props.request.order_id, selectedTechnicianUuid.value);
  actionLoading.value = false;
  if (result.ok) { toast.success('Tecnico asignado.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function schedule() {
  actionLoading.value = true;
  const result = await store.scheduleRequest(props.request.order_id, {
    scheduledDate: scheduleDate.value, scheduledTime: scheduleTime.value,
  });
  actionLoading.value = false;
  if (result.ok) { toast.success('Solicitud reprogramada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function notify() {
  actionLoading.value = true;
  const result = await store.notifyCustomer(props.request.order_id);
  actionLoading.value = false;
  if (result.ok) { toast.success('Cliente notificado.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}

async function cancel() {
  actionLoading.value = true;
  const result = await store.cancelRequest(props.request.order_id, cancelReason.value);
  actionLoading.value = false;
  if (result.ok) { toast.success('Solicitud cancelada.'); resetForms(); emit('changed'); }
  else toast.error(result.error);
}
</script>

<style scoped>
.detail-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; height: 100%; }
.action-form { max-width: 480px; margin-top: 12px; }
</style>
