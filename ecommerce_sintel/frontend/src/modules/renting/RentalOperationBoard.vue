<template>
  <BaseOperationBoard
    title="Operaciones de Renting"
    subtitle="Programacion, entrega y recogida de alquileres."
    :cards="cards"
    :loading="loading"
    @refresh="load"
  >
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white d-flex gap-2 py-3">
        <input v-model="filters.search" class="form-control" placeholder="Buscar equipo" @keyup.enter="load">
        <select v-model="filters.status" class="form-select" @change="load"><option value="">Todos los estados</option><option v-for="s in statuses" :key="s" :value="s">{{ s.replaceAll('_', ' ') }}</option></select>
      </div>
      <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead><tr><th class="ps-4">Equipo</th><th>Cliente</th><th>Entrega</th><th>Recogida</th><th>Transportista</th><th>Estado</th><th></th></tr></thead><tbody>
        <tr v-if="loading"><td colspan="7" class="text-center py-5">Cargando...</td></tr>
        <tr v-else-if="!items.length"><td colspan="7" class="text-center py-5 text-muted">No hay operaciones de renting.</td></tr>
        <tr v-for="op in items" :key="op.uuid"><td class="ps-4 fw-semibold">{{ op.equipment_name }}<span v-if="op.priority === 'HIGH'" class="badge bg-warning-subtle text-warning ms-2">Alta prioridad</span><span v-if="op.has_incident" class="badge bg-danger-subtle text-danger ms-2"><i class="bi bi-exclamation-triangle-fill"></i> Incidencia</span></td><td>{{ op.customer_name }}</td><td>{{ formatSlot(op.delivery_date, op.delivery_time) }}</td><td>{{ formatSlot(op.pickup_date, op.pickup_time) }}</td><td>{{ op.dispatcher_name || 'Sin asignar' }}</td><td><span class="badge bg-primary-subtle text-primary">{{ op.status_display }}</span></td><td><button class="btn btn-sm btn-outline-primary" @click="selectOperation(op)">Gestionar</button></td></tr>
      </tbody></table></div>
    </div>
    <div v-if="selected" class="card border-0 shadow-sm mt-4 p-4">
      <div class="d-flex justify-content-between"><h5>Gestionar {{ selected.equipment_name }}</h5><button class="btn-close" @click="selected = null"></button></div>
      <div v-if="canSchedule" class="row g-2 mt-1">
        <div class="col-md-3"><label class="form-label">Fecha entrega</label><input v-model="schedule.delivery_date" type="date" class="form-control"></div>
        <div class="col-md-3"><label class="form-label">Hora entrega</label><input v-model="schedule.delivery_time" type="time" class="form-control"></div>
        <div class="col-md-3"><label class="form-label">Fecha recogida</label><input v-model="schedule.pickup_date" type="date" class="form-control"></div>
        <div class="col-md-3"><label class="form-label">Hora recogida</label><input v-model="schedule.pickup_time" type="time" class="form-control"></div>
        <div class="col-md-4"><label class="form-label">Prioridad</label><select v-model="schedule.priority" class="form-select"><option value="LOW">Baja</option><option value="HIGH">Alta</option></select></div>
        <div class="col-md-8"><label class="form-label">Tiempo estimado (minutos)</label><input v-model.number="schedule.estimated_duration_minutes" type="number" min="1" class="form-control"></div>
        <div class="col-md-6"><input v-model="schedule.route" class="form-control" placeholder="Ruta"></div><div class="col-md-6"><input v-model="schedule.notes" class="form-control" placeholder="Observaciones e instrucciones"></div>
        <div class="col-12"><button class="btn btn-primary" @click="saveSchedule">Guardar programacion</button></div>
      </div>
      <template v-if="selected.status === 'SCHEDULED'"><hr><div class="row g-2"><div class="col-md-5"><select v-model="assignment.dispatcher_uuid" class="form-select"><option value="">Seleccionar transportista</option><option v-for="d in availableDispatchers" :key="d.uuid" :value="d.uuid">{{ d.email }} · {{ d.vehicle_plate || 'sin placa' }}</option></select></div><div class="col-md-4"><input v-model="assignment.vehicle" class="form-control" placeholder="Vehiculo / placa"></div><div class="col-md-3"><button class="btn btn-success w-100" :disabled="!assignment.dispatcher_uuid || saving" @click="assign">Asignar y notificar</button></div></div></template>
      <div v-if="nextAction" class="mt-4 p-3 rounded bg-light d-flex align-items-center justify-content-between"><div><div class="small text-muted">Siguiente paso</div><div class="fw-semibold">{{ nextAction.label }}</div></div><button class="btn btn-primary" :disabled="saving" @click="runTransition(nextAction)"><i :class="['bi', nextAction.icon, 'me-2']"></i>{{ nextAction.button }}</button></div>
      <div class="mt-4 p-3 rounded" :class="selected.has_incident ? 'bg-danger-subtle' : 'bg-light'">
        <h6 class="fw-bold mb-2"><i class="bi bi-exclamation-triangle me-1"></i>Incidencias</h6>
        <template v-if="selected.has_incident">
          <p class="mb-2">{{ selected.incident_notes }}</p>
          <button class="btn btn-sm btn-outline-success" :disabled="saving" @click="resolveIncident">Marcar como resuelta</button>
        </template>
        <template v-else-if="selected.status !== 'COMPLETED'">
          <div class="input-group input-group-sm">
            <input v-model="incidentNotes" class="form-control" placeholder="Describe la novedad (equipo danado, retraso, acceso denegado...)">
            <button class="btn btn-danger" :disabled="!incidentNotes.trim() || saving" @click="reportIncident">Reportar incidencia</button>
          </div>
        </template>
      </div>
      <div class="mt-4"><h6 class="fw-bold">Timeline operativo</h6><div v-if="!selected.timeline?.length" class="text-muted small">Sin eventos registrados.</div><div v-for="event in selected.timeline" :key="event.uuid" class="border-start border-primary ps-3 py-2"><div class="fw-semibold small">{{ event.description || event.event_type }}</div><div class="text-muted smaller">{{ new Date(event.created_at).toLocaleString('es-CO') }}<span v-if="event.actor_name"> · {{ event.actor_name }}</span></div></div></div>
    </div>
  </BaseOperationBoard>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import BaseOperationBoard from '@/components/shared/BaseOperationBoard.vue';
const api = useApi();
const toast = useToast();
const items = ref([]); const dispatchers = ref([]); const selected = ref(null); const loading = ref(false); const saving = ref(false); const filters = reactive({ status: '', search: '' });
const metrics = ref({});
const schedule = reactive({ delivery_date: '', delivery_time: '', pickup_date: '', pickup_time: '', route: '', notes: '', priority: 'LOW', estimated_duration_minutes: null });
const assignment = reactive({ dispatcher_uuid: '', vehicle: '' });
const incidentNotes = ref('');
const statuses = ['READY_FOR_SCHEDULING','SCHEDULED','TRANSPORT_ASSIGNED','READY_FOR_DELIVERY','DELIVERED','IN_OPERATION','READY_FOR_PICKUP','PICKED_UP','RETURN_INSPECTION','COMPLETED'];
const transitionActions = {
  TRANSPORT_ASSIGNED: { endpoint: 'dispatch', label: 'Preparar equipo para despacho', button: 'Marcar listo para entrega', icon: 'bi-box-seam' },
  READY_FOR_DELIVERY: { endpoint: 'deliver', label: 'Confirmar entrega al cliente', button: 'Equipo entregado', icon: 'bi-truck' },
  DELIVERED: { endpoint: 'start-operation', label: 'Iniciar periodo operativo', button: 'Iniciar operacion', icon: 'bi-play-circle' },
  IN_OPERATION: { endpoint: 'ready-pickup', label: 'Preparar recogida del equipo', button: 'Listo para recogida', icon: 'bi-calendar-check' },
  READY_FOR_PICKUP: { endpoint: 'pickup', label: 'Confirmar recogida', button: 'Equipo recogido', icon: 'bi-truck-flatbed' },
  PICKED_UP: { endpoint: 'inspect-return', label: 'Registrar ingreso a inspeccion', button: 'Iniciar inspeccion', icon: 'bi-clipboard2-check' },
  RETURN_INSPECTION: { endpoint: 'complete', label: 'Cerrar operacion de alquiler', button: 'Completar operacion', icon: 'bi-check-circle' },
};
const canSchedule = computed(() => ['READY_FOR_SCHEDULING', 'SCHEDULED'].includes(selected.value?.status));
const nextAction = computed(() => transitionActions[selected.value?.status] || null);
const availableDispatchers = computed(() => dispatchers.value.filter(d => d.is_active && d.is_available));
const cards = computed(() => [
  { label: 'Pendientes de programar', value: metrics.value.pending_scheduling ?? 0 },
  { label: 'Sin transportista', value: metrics.value.pending_dispatcher ?? 0 },
  { label: 'Entregas de hoy', value: metrics.value.deliveries_today ?? 0 },
  { label: 'Recogidas de hoy', value: metrics.value.pickups_today ?? 0 },
  { label: 'En operacion', value: metrics.value.in_operation ?? 0 },
  { label: 'Proximas a devolucion', value: metrics.value.upcoming_returns ?? 0 },
  { label: 'Retrasos', value: metrics.value.delayed ?? 0, danger: (metrics.value.delayed ?? 0) > 0 },
  { label: 'Incidencias', value: metrics.value.incidents ?? 0, danger: (metrics.value.incidents ?? 0) > 0 },
]);
const formatSlot = (date, time) => date ? `${date} ${time?.slice(0, 5) || ''}` : 'Sin programar';
async function loadMetrics() { const { data } = await api.get('renting/operations/dashboard/'); metrics.value = data; }
async function load() { loading.value = true; try { const [{ data }, dispatcherResponse] = await Promise.all([api.get('renting/operations/', { params: filters }), api.get('dashboard/dispatchers/'), loadMetrics()]); items.value = data.results ?? data; dispatchers.value = dispatcherResponse.data.results ?? dispatcherResponse.data; } finally { loading.value = false; } }
function selectOperation(op) { selected.value = op; incidentNotes.value = ''; Object.assign(schedule, { delivery_date: op.delivery_date || '', delivery_time: op.delivery_time?.slice(0, 5) || '', pickup_date: op.pickup_date || '', pickup_time: op.pickup_time?.slice(0, 5) || '', route: op.route || '', notes: op.notes || '', priority: op.priority || 'LOW', estimated_duration_minutes: op.estimated_duration_minutes || null }); Object.assign(assignment, { dispatcher_uuid: '', vehicle: op.assigned_vehicle || '' }); }
async function execute(action, successMessage) { saving.value = true; try { const { data } = await action(); selected.value = data; toast.success(successMessage); await load(); } catch (e) { toast.error(e?.response?.data?.detail || 'No fue posible completar la accion.'); } finally { saving.value = false; } }
async function saveSchedule() { await execute(() => api.post(`renting/operations/${selected.value.uuid}/schedule/`, schedule), 'Programacion guardada.'); }
async function assign() { await execute(() => api.post(`renting/operations/${selected.value.uuid}/assign-dispatcher/`, assignment), 'Transportista asignado y notificaciones encoladas.'); }
async function runTransition(action) { await execute(() => api.post(`renting/operations/${selected.value.uuid}/${action.endpoint}/`), 'Estado operativo actualizado.'); }
async function reportIncident() { await execute(() => api.post(`renting/operations/${selected.value.uuid}/report-incident/`, { notes: incidentNotes.value }), 'Incidencia reportada.'); incidentNotes.value = ''; }
async function resolveIncident() { await execute(() => api.post(`renting/operations/${selected.value.uuid}/resolve-incident/`), 'Incidencia resuelta.'); }
onMounted(load);
</script>
