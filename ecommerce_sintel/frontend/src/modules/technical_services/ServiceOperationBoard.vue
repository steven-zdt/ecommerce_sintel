<template>
  <BaseOperationBoard
    title="Operaciones de Servicios Tecnicos"
    subtitle="Recepcion, planeacion, asignacion y ejecucion de visitas."
    :cards="cards"
    :loading="loading"
    @refresh="load"
  >
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white d-flex gap-2 py-3 flex-wrap">
        <input v-model="filters.search" class="form-control" style="max-width:260px" placeholder="Buscar orden o cliente" @keyup.enter="load">
        <select v-model="filters.status" class="form-select" style="max-width:220px" @change="load">
          <option value="">Todos los estados</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ s.replaceAll('_', ' ') }}</option>
        </select>
        <input v-model="filters.date_from" type="date" class="form-control" style="max-width:170px" @change="load">
        <input v-model="filters.date_to" type="date" class="form-control" style="max-width:170px" @change="load">
      </div>
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead><tr><th class="ps-4">Servicio</th><th>Cliente</th><th>Programado</th><th>Tecnico</th><th>Prioridad</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-if="loading"><td colspan="7" class="text-center py-5">Cargando...</td></tr>
            <tr v-else-if="!items.length"><td colspan="7" class="text-center py-5 text-muted">No hay operaciones de servicio.</td></tr>
            <tr v-for="op in items" :key="op.uuid">
              <td class="ps-4 fw-semibold">
                {{ op.order?.service_name }}
                <span v-if="!op.order?.is_paid" class="badge bg-warning-subtle text-warning ms-2">Pago pendiente</span>
                <span v-if="op.has_incident" class="badge bg-danger-subtle text-danger ms-2"><i class="bi bi-exclamation-triangle-fill"></i> Incidencia</span>
              </td>
              <td>{{ op.order?.user_name }}</td>
              <td>{{ formatSlot(op.scheduled_date, op.scheduled_time) }}</td>
              <td>{{ op.technician_name || 'Sin asignar' }}</td>
              <td><span class="badge bg-light text-dark border">{{ op.priority }}</span></td>
              <td><OperationStatusBadge :status="op.status" /></td>
              <td><button class="btn btn-sm btn-outline-primary" @click="selectOperation(op)">Gestionar</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selected" class="card border-0 shadow-sm mt-4 p-4">
      <div class="d-flex justify-content-between align-items-start mb-3">
        <h5 class="mb-0">Gestionar operacion</h5>
        <button class="btn-close" @click="selected = null"></button>
      </div>

      <OperationProgress :status="selected.status" class="mb-3" />
      <OperationSummary :operation="selected" class="mb-3" />

      <!-- Planear / reprogramar -->
      <div v-if="canPlan || canReschedule" class="mb-3">
        <button class="btn btn-outline-primary" @click="showSchedule = true">
          <i class="bi bi-calendar-plus me-2"></i>{{ canReschedule ? 'Reprogramar' : 'Planear visita' }}
        </button>
      </div>

      <!-- Asignar tecnico -->
      <div v-if="['PLANNED', 'TECHNICIAN_ASSIGNED'].includes(selected.status)" class="mb-3">
        <h6 class="fw-bold">Asignar profesional</h6>
        <TechnicianSelector
          :operation-uuid="selected.uuid"
          :assigning="saving"
          @assign="assignTechnician"
        />
        <div v-if="selected.status === 'TECHNICIAN_ASSIGNED'" class="d-flex gap-2 mt-2">
          <button class="btn btn-sm btn-outline-secondary" @click="openAgenda">
            <i class="bi bi-calendar-week me-1"></i>Ver agenda del tecnico
          </button>
          <button class="btn btn-sm btn-outline-danger" :disabled="saving" @click="unassignTechnician">
            <i class="bi bi-person-dash me-1"></i>Quitar asignacion
          </button>
        </div>
      </div>

      <!-- Notificar cliente -->
      <div v-if="selected.status === 'TECHNICIAN_ASSIGNED'" class="mb-3">
        <button class="btn btn-primary" :disabled="saving" @click="notifyClient">
          <i class="bi bi-envelope me-2"></i>Notificar al cliente
        </button>
      </div>

      <!-- Siguiente transicion -->
      <div v-if="nextAction" class="p-3 rounded bg-light d-flex align-items-center justify-content-between mb-3">
        <div><div class="small text-muted">Siguiente paso</div><div class="fw-semibold">{{ nextAction.label }}</div></div>
        <button class="btn btn-primary" :disabled="saving" @click="runTransition(nextAction)">
          <i :class="['bi', nextAction.icon, 'me-2']"></i>{{ nextAction.button }}
        </button>
      </div>

      <!-- Cancelar -->
      <div v-if="!['COMPLETED', 'CLOSED', 'CANCELLED'].includes(selected.status)" class="mb-3">
        <div class="input-group input-group-sm" style="max-width:480px">
          <input v-model="cancelReason" class="form-control" placeholder="Motivo de cancelacion">
          <button class="btn btn-outline-danger" :disabled="saving" @click="cancelOperation">Cancelar operacion</button>
        </div>
      </div>

      <!-- Incidencias -->
      <div class="p-3 rounded mb-3" :class="selected.has_incident ? 'bg-danger-subtle' : 'bg-light'">
        <h6 class="fw-bold mb-2"><i class="bi bi-exclamation-triangle me-1"></i>Incidencias</h6>
        <template v-if="selected.has_incident">
          <p class="mb-2">{{ selected.incident_notes }}</p>
          <button class="btn btn-sm btn-outline-success" :disabled="saving" @click="resolveIncident">Marcar como resuelta</button>
        </template>
        <template v-else-if="!['COMPLETED', 'CLOSED'].includes(selected.status)">
          <div class="input-group input-group-sm">
            <input v-model="incidentNotes" class="form-control" placeholder="Describe la novedad...">
            <button class="btn btn-danger" :disabled="!incidentNotes.trim() || saving" @click="reportIncident">Reportar</button>
          </div>
        </template>
      </div>

      <div>
        <h6 class="fw-bold">Timeline operativo</h6>
        <OperationTimeline :events="selected.timeline" />
      </div>
    </div>

    <ScheduleModal
      v-model="showSchedule"
      :is-reschedule="canReschedule"
      :saving="saving"
      :initial="selected || {}"
      @save="saveSchedule"
    />
    <TechnicianAgendaList
      v-model="showAgenda"
      :profile-uuid="selectedTechnicianProfileUuid"
    />
  </BaseOperationBoard>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import BaseOperationBoard from '@/components/shared/BaseOperationBoard.vue';
import OperationStatusBadge from '@/components/customer/services/OperationStatusBadge.vue';
import OperationProgress from '@/components/customer/services/OperationProgress.vue';
import OperationSummary from '@/components/customer/services/OperationSummary.vue';
import OperationTimeline from '@/components/customer/services/OperationTimeline.vue';
import TechnicianSelector from '@/components/customer/services/TechnicianSelector.vue';
import ScheduleModal from '@/components/customer/services/ScheduleModal.vue';
import TechnicianAgendaList from '@/components/customer/services/TechnicianAgendaList.vue';

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const items = ref([]);
const selected = ref(null);
const loading = ref(false);
const saving = ref(false);
const metrics = ref({});
const filters = reactive({ status: '', search: '', date_from: '', date_to: '' });
const incidentNotes = ref('');
const cancelReason = ref('');
const showSchedule = ref(false);
const showAgenda = ref(false);
const selectedTechnicianProfileUuid = ref('');

const STATUSES = [
  'READY_FOR_PLANNING', 'PLANNED', 'TECHNICIAN_ASSIGNED', 'CUSTOMER_NOTIFIED',
  'READY_TO_VISIT', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'CANCELLED',
];

const transitionActions = {
  CUSTOMER_NOTIFIED: { endpoint: 'ready-to-visit', label: 'Preparar la visita', button: 'Marcar lista para visita', icon: 'bi-calendar-check' },
  READY_TO_VISIT:    { endpoint: 'start', label: 'El tecnico inicia desplazamiento', button: 'Marcar en camino', icon: 'bi-truck' },
  ON_THE_WAY:        { endpoint: 'arrive', label: 'El tecnico llega al sitio', button: 'Marcar llegada', icon: 'bi-geo-alt' },
  ARRIVED:           { endpoint: 'start-service', label: 'Iniciar ejecucion del servicio', button: 'Iniciar servicio', icon: 'bi-play-circle' },
  IN_PROGRESS:       { endpoint: 'complete', label: 'Finalizar el servicio', button: 'Marcar completado', icon: 'bi-check-circle' },
  COMPLETED:         { endpoint: 'close', label: 'Cerrar la operacion', button: 'Cerrar operacion', icon: 'bi-lock' },
};

const nextAction = computed(() => transitionActions[selected.value?.status] || null);
const canPlan = computed(() => ['READY_FOR_PLANNING'].includes(selected.value?.status));
const canReschedule = computed(() => ['PLANNED', 'TECHNICIAN_ASSIGNED'].includes(selected.value?.status) && !!selected.value?.scheduled_date);

const cards = computed(() => [
  { label: 'Pendientes de planear', value: metrics.value.pending_planning ?? 0 },
  { label: 'Programados hoy', value: metrics.value.scheduled_today ?? 0 },
  { label: 'En ejecucion', value: metrics.value.in_progress ?? 0 },
  { label: 'Tecnicos ocupados', value: metrics.value.technicians_busy ?? 0 },
  { label: 'Tecnicos disponibles', value: metrics.value.technicians_available ?? 0 },
  { label: 'Atrasados', value: metrics.value.delayed ?? 0, danger: (metrics.value.delayed ?? 0) > 0 },
  { label: 'Tiempo promedio (h)', value: metrics.value.avg_completion_hours ?? '-' },
  { label: 'SLA cumplido', value: metrics.value.sla_percentage != null ? `${metrics.value.sla_percentage}%` : '-' },
]);

function formatSlot(date, time) {
  return date ? `${date} ${time?.slice(0, 5) || ''}` : 'Sin programar';
}

async function loadMetrics() {
  const { data } = await api.get('service-operations/dashboard/');
  metrics.value = data;
}

async function load() {
  loading.value = true;
  try {
    const [{ data }] = await Promise.all([
      api.get('service-operations/', { params: filters }),
      loadMetrics(),
    ]);
    items.value = data.results ?? data;
  } finally {
    loading.value = false;
  }
}

function selectOperation(op) {
  selected.value = op;
  incidentNotes.value = '';
  cancelReason.value = '';
  selectedTechnicianProfileUuid.value = '';
}

async function execute(action, successMessage) {
  saving.value = true;
  try {
    const { data } = await action();
    selected.value = data;
    toast.success(successMessage);
    await load();
  } catch (e) {
    handleError(e, 'No fue posible completar la accion.');
  } finally {
    saving.value = false;
  }
}

async function saveSchedule(form) {
  const endpoint = canReschedule.value ? 'reschedule' : 'plan';
  await execute(() => api.post(`service-operations/${selected.value.uuid}/${endpoint}/`, form), 'Programacion guardada.');
  showSchedule.value = false;
}

async function assignTechnician(technicianUuid) {
  await execute(
    () => api.post(`service-operations/${selected.value.uuid}/assign-technician/`, { technician_uuid: technicianUuid }),
    'Tecnico asignado y notificado.',
  );
}

async function unassignTechnician() {
  await execute(
    () => api.post(`service-operations/${selected.value.uuid}/unassign-technician/`),
    'Tecnico desasignado.',
  );
}

function openAgenda() {
  selectedTechnicianProfileUuid.value = selected.value?.technician_profile_uuid || '';
  showAgenda.value = true;
}

async function notifyClient() {
  await execute(() => api.post(`service-operations/${selected.value.uuid}/notify-client/`), 'Cliente notificado.');
}

async function runTransition(action) {
  await execute(() => api.post(`service-operations/${selected.value.uuid}/${action.endpoint}/`), 'Estado operativo actualizado.');
}

async function cancelOperation() {
  await execute(
    () => api.post(`service-operations/${selected.value.uuid}/cancel/`, { reason: cancelReason.value }),
    'Operacion cancelada.',
  );
  cancelReason.value = '';
}

async function reportIncident() {
  await execute(
    () => api.post(`service-operations/${selected.value.uuid}/report-incident/`, { notes: incidentNotes.value }),
    'Incidencia reportada.',
  );
  incidentNotes.value = '';
}

async function resolveIncident() {
  await execute(() => api.post(`service-operations/${selected.value.uuid}/resolve-incident/`), 'Incidencia resuelta.');
}

onMounted(load);
</script>
