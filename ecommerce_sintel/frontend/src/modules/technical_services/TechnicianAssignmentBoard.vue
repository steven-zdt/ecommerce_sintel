<template>
  <div class="assignment-board">

    <!-- Cabecera -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h4 class="fw-bold mb-0">Asignación de Técnicos</h4>
        <p class="text-muted small mb-0">{{ totalCount }} orden{{ totalCount !== 1 ? 'es' : '' }} de servicio</p>
      </div>
    </div>

    <!-- Filtros -->
    <div class="row g-2 mb-3">
      <div class="col-md-3">
        <div class="input-group">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input v-model="search" class="form-control border-start-0 ps-0" placeholder="Buscar orden, cliente o servicio..." />
        </div>
      </div>
      <div class="col-md-2">
        <select v-model="filters.priority" class="form-select" @change="loadPage()">
          <option value="">Toda prioridad</option>
          <option v-for="(meta, code) in priorities" :key="code" :value="code">{{ meta.label }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.category" class="form-select" @change="loadPage()">
          <option value="">Toda categoria</option>
          <option v-for="cat in categories" :key="cat.slug" :value="cat.slug">{{ cat.name }}</option>
        </select>
      </div>
      <div class="col-md-2">
        <select v-model="filters.has_technician" class="form-select" @change="loadPage()">
          <option value="">Con/sin técnico</option>
          <option value="true">Con técnico</option>
          <option value="false">Sin técnico</option>
        </select>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Orden</th>
              <th>Cliente</th>
              <th>Servicio</th>
              <th>Prioridad</th>
              <th>Estado</th>
              <th>Técnico</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando ordenes de servicio...</div>
              </td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="7" class="text-center py-5 text-muted">
                <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                No hay ordenes de servicio que coincidan con los filtros.
              </td>
            </tr>
            <tr v-else v-for="order in items" :key="order.uuid">
              <td>
                <div class="fw-semibold smaller">{{ order.tracking_number || order.uuid.slice(0, 8) }}</div>
                <div class="text-muted smaller">{{ formatDate(order.created_at) }}</div>
              </td>
              <td>
                <div class="smaller">{{ order.client_name }}</div>
                <div class="text-muted smaller">{{ order.client_email }}</div>
              </td>
              <td class="smaller">
                <div>{{ order.service_name || '—' }}</div>
                <div class="text-muted">{{ order.category_name || '—' }}</div>
              </td>
              <td>
                <select
                  class="form-select form-select-sm badge-select"
                  :class="enums.cssClass('service-priorities', order.priority)"
                  :value="order.priority"
                  @change="changePriority(order, $event.target.value)"
                >
                  <option v-for="(meta, code) in priorities" :key="code" :value="code">{{ meta.label }}</option>
                </select>
              </td>
              <td>
                <span class="badge" :class="enums.cssClass('service-order-statuses', order.current_status)">
                  {{ enums.label('service-order-statuses', order.current_status, order.current_status || '—') }}
                </span>
              </td>
              <td>
                <template v-if="order.technician">
                  <div class="smaller fw-semibold">{{ order.technician.full_name }}</div>
                  <span class="badge rounded-pill smaller" :class="order.technician.is_available ? 'bg-success' : 'bg-secondary'">
                    {{ order.technician.is_available ? 'Disponible' : 'Ocupado' }}
                  </span>
                </template>
                <span v-else class="text-muted smaller">Sin asignar</span>
              </td>
              <td class="text-end">
                <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                  <button class="btn btn-light border-end" title="Asignar/Reasignar" @click="openAssignModal(order)">
                    <i class="bi bi-person-plus text-primary"></i>
                  </button>
                  <button class="btn btn-light border-end" title="Ver agenda" :disabled="!order.technician" @click="openAgendaModal(order)">
                    <i class="bi bi-calendar3 text-info"></i>
                  </button>
                  <button class="btn btn-light border-end" title="Ver historial" @click="openHistoryModal(order)">
                    <i class="bi bi-clock-history text-secondary"></i>
                  </button>
                  <button
                    class="btn btn-light"
                    title="Cancelar asignación"
                    :disabled="!order.technician || actionLoading"
                    @click="unassign(order)"
                  >
                    <i class="bi bi-person-x text-danger"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div class="card-footer bg-white border-0 d-flex justify-content-between align-items-center py-3 px-4">
        <div class="text-muted smaller">{{ totalCount }} registros encontrados</div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-light border" :disabled="!prevPage || loading" @click="loadPage(prevPage)">
            <i class="bi bi-chevron-left"></i>
          </button>
          <button class="btn btn-sm btn-light border" :disabled="!nextPage || loading" @click="loadPage(nextPage)">
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Asignar/Reasignar tecnico -->
    <div v-if="assignModal.order" class="sintel-modal-backdrop" @click.self="closeAssignModal">
      <div class="sintel-modal">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="fw-bold mb-0">Asignar técnico</h5>
          <button class="btn-close" @click="closeAssignModal"></button>
        </div>
        <p class="text-muted smaller">Orden {{ assignModal.order.tracking_number || assignModal.order.uuid.slice(0, 8) }} — {{ assignModal.order.service_name }}</p>

        <div class="d-flex justify-content-end mb-2">
          <button class="btn btn-sm btn-outline-primary" :disabled="assignModal.loading" @click="autoAssign">
            <i class="bi bi-magic me-1"></i> Asignación automática
          </button>
        </div>

        <div v-if="assignModal.loadingCandidates" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="assignModal.candidates.length === 0" class="text-center text-muted py-4 smaller">
          No hay técnicos disponibles y calificados para esta orden.
        </div>
        <ul v-else class="list-group">
          <li
            v-for="tech in assignModal.candidates"
            :key="tech.uuid"
            class="list-group-item d-flex justify-content-between align-items-center"
          >
            <div>
              <div class="fw-semibold smaller">{{ tech.full_name }}</div>
              <div class="text-muted smaller">
                {{ tech.email }}
                <i class="bi bi-star-fill text-warning ms-1"></i> {{ tech.average_rating ?? '—' }}
              </div>
            </div>
            <button class="btn btn-sm btn-primary" :disabled="assignModal.loading" @click="confirmAssign(tech)">
              Asignar
            </button>
          </li>
        </ul>
      </div>
    </div>

    <!-- Modal: Agenda del tecnico -->
    <div v-if="agendaModal.order" class="sintel-modal-backdrop" @click.self="closeAgendaModal">
      <div class="sintel-modal">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="fw-bold mb-0">Agenda de {{ agendaModal.order.technician?.full_name }}</h5>
          <button class="btn-close" @click="closeAgendaModal"></button>
        </div>
        <div v-if="agendaModal.loading" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="agendaModal.slots.length === 0" class="text-center text-muted py-4 smaller">
          Este profesional no tiene slots de disponibilidad registrados.
        </div>
        <ul v-else class="list-group">
          <li v-for="slot in agendaModal.slots" :key="slot.id" class="list-group-item d-flex justify-content-between align-items-center">
            <span class="smaller">{{ slot.date }} · {{ slot.start_time }}–{{ slot.end_time }}</span>
            <span class="badge" :class="agendaStatusClass(slot.status)">{{ slot.status }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Modal: Historial de la orden -->
    <div v-if="historyModal.order" class="sintel-modal-backdrop" @click.self="closeHistoryModal">
      <div class="sintel-modal">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="fw-bold mb-0">Historial de la orden</h5>
          <button class="btn-close" @click="closeHistoryModal"></button>
        </div>
        <div v-if="historyModal.loading" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <ul v-else class="list-group">
          <li v-for="(event, i) in historyModal.timeline" :key="i" class="list-group-item">
            <div class="d-flex justify-content-between">
              <span class="badge" :class="enums.cssClass('service-order-statuses', event.status)">
                {{ enums.label('service-order-statuses', event.status, event.status) }}
              </span>
              <span class="text-muted smaller">{{ formatDate(event.created_at) }}</span>
            </div>
            <div class="smaller mt-1">{{ event.notes || '—' }}</div>
            <div class="text-muted smaller">{{ event.created_by_email || 'Sistema' }}</div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useEnums } from '@/composables/useEnums';

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const enums = useEnums();

const items = ref([]);
const loading = ref(true);
const actionLoading = ref(false);
const priorities = ref({});
const categories = ref([]);

const search = ref('');
const totalCount = ref(0);
const nextPage = ref(null);
const prevPage = ref(null);

const filters = reactive({
  priority: '',
  category: '',
  has_technician: '',
});

async function loadPage(url = null) {
  loading.value = true;
  try {
    const endpoint = url || buildEndpoint();
    const { data } = await api.get(endpoint);
    if (data.results !== undefined) {
      items.value = data.results;
      totalCount.value = data.count;
      nextPage.value = data.next ? extractPath(data.next) : null;
      prevPage.value = data.previous ? extractPath(data.previous) : null;
    } else {
      items.value = data;
      totalCount.value = data.length;
      nextPage.value = null;
      prevPage.value = null;
    }
  } catch (err) {
    console.error('Error al cargar ordenes de servicio:', err);
    toast.error('No se pudieron cargar las ordenes de servicio');
  } finally {
    loading.value = false;
  }
}

function buildEndpoint() {
  const params = new URLSearchParams();
  if (search.value) params.append('search', search.value);
  if (filters.priority) params.append('priority', filters.priority);
  if (filters.category) params.append('category', filters.category);
  if (filters.has_technician) params.append('has_technician', filters.has_technician);
  return `orders/service-orders/assignment-queue/?${params.toString()}`;
}

function extractPath(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

let debounceTimer = null;
watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadPage(), 400);
});

const formatDate = (d) =>
  d ? new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

// ── Cambiar prioridad ────────────────────────────────────────────────────
async function changePriority(order, priority) {
  try {
    await api.post(`orders/service-orders/${order.uuid}/change-priority/`, { priority });
    order.priority = priority;
    toast.success('Prioridad actualizada');
  } catch (err) {
    handleError(err, 'No se pudo cambiar la prioridad');
  }
}

// ── Cancelar asignación ──────────────────────────────────────────────────
async function unassign(order) {
  actionLoading.value = true;
  try {
    await api.post(`orders/service-orders/${order.uuid}/unassign-technician/`);
    toast.success('Asignación cancelada');
    await loadPage();
  } catch (err) {
    handleError(err, 'No se pudo cancelar la asignación');
  } finally {
    actionLoading.value = false;
  }
}

// ── Modal de asignación ──────────────────────────────────────────────────
const assignModal = reactive({ order: null, candidates: [], loading: false, loadingCandidates: false });

async function openAssignModal(order) {
  assignModal.order = order;
  assignModal.candidates = [];
  assignModal.loadingCandidates = true;
  try {
    const { data } = await api.get(`orders/service-orders/${order.uuid}/available-technicians/`);
    assignModal.candidates = data;
  } catch (err) {
    toast.error('No se pudieron cargar los técnicos disponibles');
  } finally {
    assignModal.loadingCandidates = false;
  }
}
function closeAssignModal() {
  assignModal.order = null;
}
async function confirmAssign(tech) {
  assignModal.loading = true;
  try {
    await api.post(`orders/service-orders/${assignModal.order.uuid}/assign-technician/`, {
      technician_uuid: tech.uuid,
    });
    toast.success(`${tech.full_name} asignado correctamente`);
    closeAssignModal();
    await loadPage();
  } catch (err) {
    handleError(err, 'No se pudo asignar el técnico');
  } finally {
    assignModal.loading = false;
  }
}
async function autoAssign() {
  assignModal.loading = true;
  try {
    await api.post(`orders/service-orders/${assignModal.order.uuid}/auto-assign/`);
    toast.success('Técnico asignado automáticamente');
    closeAssignModal();
    await loadPage();
  } catch (err) {
    handleError(err, 'No se pudo asignar automáticamente');
  } finally {
    assignModal.loading = false;
  }
}

// ── Modal de agenda ──────────────────────────────────────────────────────
const agendaModal = reactive({ order: null, slots: [], loading: false });

async function openAgendaModal(order) {
  if (!order.technician?.profile_uuid) return;
  agendaModal.order = order;
  agendaModal.slots = [];
  agendaModal.loading = true;
  try {
    const { data } = await api.get(`auth/admin/professionals/${order.technician.profile_uuid}/schedule/`);
    agendaModal.slots = data;
  } catch (err) {
    toast.error('No se pudo cargar la agenda del técnico');
  } finally {
    agendaModal.loading = false;
  }
}
function closeAgendaModal() {
  agendaModal.order = null;
}
function agendaStatusClass(status) {
  const map = {
    AVAILABLE: 'bg-success-subtle text-success',
    BOOKED: 'bg-primary-subtle text-primary',
    BLOCKED: 'bg-secondary-subtle text-secondary',
    VACATION: 'bg-warning-subtle text-warning',
  };
  return map[status] || 'bg-secondary-subtle text-secondary';
}

// ── Modal de historial ───────────────────────────────────────────────────
const historyModal = reactive({ order: null, timeline: [], loading: false });

async function openHistoryModal(order) {
  historyModal.order = order;
  historyModal.timeline = [];
  historyModal.loading = true;
  try {
    const { data } = await api.get(`orders/service-orders/${order.uuid}/`);
    historyModal.timeline = data.timeline || [];
  } catch (err) {
    toast.error('No se pudo cargar el historial de la orden');
  } finally {
    historyModal.loading = false;
  }
}
function closeHistoryModal() {
  historyModal.order = null;
}

onMounted(async () => {
  const [servicePriorities] = await Promise.all([
    enums.ensure('service-priorities'),
    enums.ensure('service-order-statuses'),
  ]);
  priorities.value = servicePriorities;
  loadPage();
  try {
    const { data } = await api.get('services/categories/');
    categories.value = data.results !== undefined ? data.results : data;
  } catch (err) {
    console.error('Error al cargar categorias:', err);
  }
});
</script>

<style scoped>
.smaller { font-size: 0.8rem; }
.badge-select { max-width: 130px; font-size: 0.75rem; font-weight: 700; border-width: 1.5px; }
.sintel-modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1050;
}
.sintel-modal {
  background: #fff; border-radius: 12px; padding: 1.5rem;
  width: 100%; max-width: 480px; max-height: 80vh; overflow-y: auto;
}
</style>
