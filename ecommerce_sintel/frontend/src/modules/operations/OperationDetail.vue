<template>
  <div class="op-detail p-4">
    <RouterLink to="/panel/operaciones" class="back-link mb-3 d-inline-block">
      <i class="bi bi-arrow-left"></i> Volver
    </RouterLink>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <template v-else-if="ticket">
      <div class="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-3">
        <div>
          <h2 class="mb-1">{{ ticket.ticket_number }}</h2>
          <span class="badge" :class="enums.cssClass('operation-statuses', ticket.status, 'text-bg-secondary')">{{ enums.label('operation-statuses', ticket.status, ticket.status) }}</span>
        </div>
        <div class="action-group d-flex gap-2 flex-wrap">
          <!-- Asignar -->
          <button
            v-if="['CREATED','DOCS_PENDING','READY_TO_ASSIGN','ASSIGNED'].includes(ticket.status)"
            class="btn btn-outline-primary btn-sm"
            @click="openAssign"
          >Asignar</button>
          <!-- Auto-asignar -->
          <button class="btn btn-outline-secondary btn-sm" :disabled="actioning" @click="autoAssign">
            Auto-asignar
          </button>
          <button v-if="ticket.status === 'ASSIGNED'" class="btn btn-outline-secondary btn-sm" @click="showSchedule = true">
            Programar
          </button>
          <!-- Transicion -->
          <div class="d-flex gap-1">
            <select v-model="nextStatus" class="form-select form-select-sm">
              <option value="">Cambiar estado...</option>
              <option v-for="s in allowedStatuses" :key="s.v" :value="s.v">{{ s.l }}</option>
            </select>
            <button class="btn btn-primary btn-sm" :disabled="!nextStatus || actioning" @click="transition">
              Actualizar
            </button>
          </div>
        </div>
      </div>

      <!-- Detalles -->
      <div class="row g-3 mb-4">
        <div class="col-md-6">
          <div class="detail-card">
            <p class="dc-label">Tipo</p>
            <p class="dc-val">{{ ticket.operation_type }}</p>
          </div>
        </div>
        <div class="col-md-6">
          <div class="detail-card">
            <p class="dc-label">Ubicacion</p>
            <p class="dc-val">{{ ticket.location_address || '—' }}</p>
            <p class="dc-sub">{{ ticket.location_city }}</p>
          </div>
        </div>
        <div class="col-12" v-if="sourceOrder">
          <div class="detail-card">
            <p class="dc-label">Orden asociada</p>
            <p class="dc-val">#{{ sourceOrder.uuid?.slice(0, 8) }}</p>
            <p class="dc-sub">Estado: {{ orderStatusLabel }}</p>
            <p class="dc-sub">Pago: {{ sourceOrder.payment_method || 'N/A' }}</p>
            <p class="dc-sub">Fecha: {{ formatDate(sourceOrder.created_at) }}</p>
            <p class="dc-sub mt-2">{{ orderAddressLine }}</p>
            <p class="dc-sub small text-muted">{{ orderAddressCity }}</p>
          </div>
        </div>
        <div class="col-md-6" v-if="ticket.scheduled_date">
          <div class="detail-card">
            <p class="dc-label">Fecha programada</p>
            <p class="dc-val">{{ ticket.scheduled_date }}</p>
            <p class="dc-sub" v-if="ticket.scheduled_time_start">
              {{ ticket.scheduled_time_start }} – {{ ticket.scheduled_time_end }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="!ticket.assignments?.length" class="text-muted small">Sin asignaciones aun.</div>
      <div v-for="a in ticket.assignments" :key="a.uuid" class="assignment-row">
        <i class="bi bi-person-badge"></i>
        <span>{{ a.assignee_name || a.assignee_email }}</span>
        <span class="badge text-bg-light ms-2">{{ a.role }}</span>
        <span class="badge ms-2" :class="a.status === 'ACTIVE' ? 'text-bg-success' : 'text-bg-secondary'">
          {{ a.status }}
        </span>
      </div>

      <!-- Timeline -->
      <div class="section mb-4">
        <h4 class="section-title">Historial</h4>
        <TrackingTimeline :events="ticket.tracking_events" />
      </div>

      <!-- Documentos -->
      <div class="section mb-4">
        <h4 class="section-title">Documentos</h4>
        <div v-if="!ticket.documents?.length" class="text-muted small">Sin documentos.</div>
        <div v-for="doc in ticket.documents" :key="doc.uuid" class="doc-row d-flex align-items-center gap-2 py-2">
          <i class="bi bi-file-earmark"></i>
          <span>{{ doc.doc_type }}</span>
          <span class="badge" :class="docBadge(doc.status)">{{ doc.status }}</span>
          <div class="ms-auto d-flex gap-1" v-if="doc.status === 'PENDING'">
            <button class="btn btn-success btn-sm" @click="reviewDoc(doc.uuid, true)">Aprobar</button>
            <button class="btn btn-danger btn-sm" @click="reviewDoc(doc.uuid, false)">Rechazar</button>
          </div>
        </div>
      </div>

      <!-- Modal asignar (simple inline) -->
      <div v-if="showAssign" class="assign-modal">
        <div class="assign-modal__box">
          <h5>Asignar recurso</h5>
          <select v-model="assignForm.assignee_id" class="form-select mb-3" :disabled="staffLoading" @change="selectStaffRole">
            <option value="">Selecciona personal disponible</option>
            <option v-for="person in availableStaff" :key="person.uuid" :value="person.id">
              {{ person.name }} · {{ person.role }}
            </option>
          </select>
          <p v-if="!staffLoading && !availableStaff.length" class="text-muted small">No hay personal disponible.</p>
          <div class="d-flex gap-2">
            <button class="btn btn-primary btn-sm" @click="assign">Asignar</button>
            <button class="btn btn-outline-secondary btn-sm" @click="showAssign = false">Cancelar</button>
          </div>
        </div>
      </div>

      <div v-if="showSchedule" class="assign-modal">
        <div class="assign-modal__box">
          <h5>Programar operacion</h5>
          <input v-model="scheduleForm.scheduled_date" type="date" class="form-control mb-2" />
          <div class="d-flex gap-2 mb-3">
            <input v-model="scheduleForm.scheduled_time_start" type="time" class="form-control" />
            <input v-model="scheduleForm.scheduled_time_end" type="time" class="form-control" />
          </div>
          <div class="d-flex gap-2">
            <button class="btn btn-primary btn-sm" :disabled="actioning" @click="schedule">Programar</button>
            <button class="btn btn-outline-secondary btn-sm" @click="showSchedule = false">Cancelar</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';
import TrackingTimeline from '@/components/customer/ui/TrackingTimeline.vue';

const route   = useRoute();
const api     = useApi();
const toast   = useToast();
const enums   = useEnums();
const uuid    = route.params.uuid;

const ticket     = ref(null);
const loading    = ref(true);
const actioning  = ref(false);
const showAssign = ref(false);
const showSchedule = ref(false);
const staffLoading = ref(false);
const availableStaff = ref([]);
const nextStatus = ref('');

const assignForm = reactive({ assignee_id: '', role: 'TECHNICIAN' });
const scheduleForm = reactive({ scheduled_date: '', scheduled_time_start: '', scheduled_time_end: '' });

async function openAssign() {
  showAssign.value = true;
  staffLoading.value = true;
  try {
    const { data } = await api.get(`dashboard/operations/${uuid}/available-staff/`);
    availableStaff.value = data;
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'No fue posible cargar el personal.');
  } finally {
    staffLoading.value = false;
  }
}

function selectStaffRole() {
  const person = availableStaff.value.find(item => item.id === Number(assignForm.assignee_id));
  if (person) assignForm.role = person.role;
}

async function fetchTicket() {
  loading.value = true;
  try {
    const { data } = await api.get(`dashboard/operations/${uuid}/`);
    ticket.value   = data;
  } finally { loading.value = false; }
}

const sourceOrder = computed(() => ticket.value?.source_order || null);
const orderStatusLabel = computed(() => sourceOrder.value?.status || 'N/D');
const orderAddressLine = computed(() => {
  const address = sourceOrder.value?.shipping_address;
  if (!address) return 'Dirección no disponible';
  return `${address.address_line_1 || ''}${address.address_line_2 ? ', ' + address.address_line_2 : ''}`.trim();
});
const orderAddressCity = computed(() => {
  const address = sourceOrder.value?.shipping_address;
  if (!address) return '';
  return [address.city, address.state, address.country].filter(Boolean).join(', ');
});

const formatDate = (value) => {
  if (!value) return 'N/D';
  return new Date(value).toLocaleString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

onMounted(() => { fetchTicket(); enums.ensure('operation-statuses'); });

async function transition() {
  if (!nextStatus.value) return;
  actioning.value = true;
  try {
    await api.post(`dashboard/operations/${uuid}/transition/`, { status: nextStatus.value });
    toast.success('Estado actualizado.');
    nextStatus.value = '';
    await fetchTicket();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error.');
  } finally { actioning.value = false; }
}

async function schedule() {
  if (!scheduleForm.scheduled_date || !scheduleForm.scheduled_time_start || !scheduleForm.scheduled_time_end) return;
  actioning.value = true;
  try {
    await api.post(`dashboard/operations/${uuid}/schedule/`, { ...scheduleForm });
    toast.success('Operacion programada.');
    showSchedule.value = false;
    await fetchTicket();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'No fue posible programar la operacion.');
  } finally {
    actioning.value = false;
  }
}

async function autoAssign() {
  actioning.value = true;
  try {
    await api.post(`dashboard/operations/${uuid}/auto-assign/`);
    toast.success('Auto-asignacion completada.');
    await fetchTicket();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error.');
  } finally { actioning.value = false; }
}

async function assign() {
  if (!assignForm.assignee_id) return;
  actioning.value = true;
  try {
    await api.post(`dashboard/operations/${uuid}/assign/`, { ...assignForm });
    toast.success('Recurso asignado.');
    showAssign.value = false;
    await fetchTicket();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error.');
  } finally { actioning.value = false; }
}

async function reviewDoc(docUuid, approved) {
  try {
    await api.post(`dashboard/operations/${uuid}/documents/${docUuid}/review/`, { approved });
    toast.success(approved ? 'Documento aprobado.' : 'Documento rechazado.');
    await fetchTicket();
  } catch (e) {
    toast.error('Error al revisar el documento.');
  }
}



const DOC_BADGE = {
  APPROVED: 'text-bg-success', REJECTED: 'text-bg-danger', PENDING: 'text-bg-warning',
};
const docBadge = (s) => DOC_BADGE[s] ?? 'text-bg-light';

const ALL_STATUSES = [
  { v: 'DOCS_PENDING',    l: 'Docs. pendientes' },
  { v: 'READY_TO_ASSIGN', l: 'Listo para asignar' },
  { v: 'ASSIGNED',        l: 'Asignado' },
  { v: 'SCHEDULED',       l: 'Programado' },
  { v: 'EN_ROUTE',        l: 'En camino' },
  { v: 'IN_PROGRESS',     l: 'En progreso' },
  { v: 'COMPLETED',       l: 'Completado' },
  { v: 'CANCELLED',       l: 'Cancelado' },
];

const ALLOWED = {
  CREATED:        ['DOCS_PENDING', 'READY_TO_ASSIGN', 'CANCELLED'],
  DOCS_PENDING:   ['READY_TO_ASSIGN', 'CANCELLED'],
  READY_TO_ASSIGN:['ASSIGNED', 'CANCELLED'],
  ASSIGNED:       ['SCHEDULED', 'READY_TO_ASSIGN', 'CANCELLED'],
  SCHEDULED:      ['EN_ROUTE', 'CANCELLED'],
  EN_ROUTE:       ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS:    ['COMPLETED', 'CANCELLED'],
};

const allowedStatuses = computed(() => {
  if (!ticket.value) return ALL_STATUSES;
  const allowed = ALLOWED[ticket.value?.status] ?? [];
  return ALL_STATUSES.filter(s => allowed.includes(s.v));
});
</script>

<style scoped>
.op-detail { background: #fff; min-height: 80vh; }
.back-link { color: #3b82f6; text-decoration: none; font-size: 0.875rem; }
.section { padding: 16px 0; border-top: 1px solid #f3f4f6; }
.section-title { font-size: 1rem; font-weight: 600; color: #374151; margin: 0 0 12px; }
.detail-card { background: #f9fafb; border-radius: 8px; padding: 14px; }
.dc-label { font-size: 0.72rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; margin: 0 0 4px; }
.dc-val   { font-size: 0.925rem; font-weight: 600; color: #111827; margin: 0; }
.dc-sub   { font-size: 0.8rem; color: #6b7280; margin: 0; }
.assignment-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; font-size: 0.875rem; }
.action-group select { max-width: 180px; }

.assign-modal {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
}
.assign-modal__box {
  background: #fff; border-radius: 16px; padding: 28px; width: 340px;
  box-shadow: 0 20px 60px rgba(0,0,0,.2);
}
.assign-modal__box h5 { margin: 0 0 20px; font-weight: 700; }
</style>
