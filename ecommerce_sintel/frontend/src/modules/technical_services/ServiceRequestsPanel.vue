<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-4">
      <div>
        <h4 class="fw-bold mb-0">Solicitudes de Servicio</h4>
        <p class="text-muted small mb-0">{{ store.totalRequests }} solicitud{{ store.totalRequests !== 1 ? 'es' : '' }} en total</p>
      </div>
    </div>

    <!-- KPIs -- lectura agregada de ServiceOperationSelector.dashboard_metrics()
         (ya existente, usado tambien por ServiceOperationBoard.vue) -- no se crea
         ningun modelo ni endpoint de estadisticas nuevo (FASE 18 del plan). -->
    <div class="row g-2 mb-3">
      <div v-for="kpi in kpiCards" :key="kpi.label" class="col-6 col-md-3 col-lg">
        <div class="kpi-card">
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-label">{{ kpi.label }}</div>
        </div>
      </div>
    </div>

    <!-- Filtros -->
    <div class="row g-2 mb-3">
      <div class="col-md-3">
        <select v-model="filters.status" class="form-select" @change="loadPage()">
          <option value="">Estado operacion: todos</option>
          <option v-for="opt in operationStatusOptions" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.priority" class="form-select" @change="loadPage()">
          <option value="">Prioridad: todas</option>
          <option v-for="opt in priorityOptions" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.has_technician" class="form-select" @change="loadPage()">
          <option value="">Tecnico: cualquiera</option>
          <option value="false">Sin tecnico asignado</option>
          <option value="true">Con tecnico asignado</option>
        </select>
      </div>
      <div class="col-md-3">
        <input v-model="filters.search" type="text" class="form-control" placeholder="Buscar cliente, servicio, tracking..." @input="onSearchInput" />
      </div>
    </div>

    <!-- Tabla -->
    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3">Solicitud</th>
              <th class="py-3">Cliente</th>
              <th class="py-3">Servicio</th>
              <th class="py-3">Pago</th>
              <th class="py-3">Estado solicitud</th>
              <th class="py-3">Estado operacion</th>
              <th class="py-3">Tecnico</th>
              <th class="py-3">Programada</th>
              <th class="py-3">Prioridad</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="10" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando solicitudes...</span>
              </td>
            </tr>
            <tr v-else-if="!store.requests.length">
              <td colspan="10" class="text-center py-5 text-muted">
                <i class="bi bi-inbox fs-2 d-block mb-2"></i>
                Sin registros.
              </td>
            </tr>
            <template v-for="item in store.requests" :key="item.request_id">
              <tr>
                <td class="px-4">
                  <div class="fw-semibold text-dark smaller">{{ item.tracking_number || item.request_id.slice(0, 8) }}</div>
                  <div class="text-muted smaller">{{ formatDate(item.created_at) }}</div>
                </td>
                <td>
                  <div class="fw-semibold">{{ item.customer?.name }}</div>
                  <div class="text-muted smaller">{{ item.customer?.email }}</div>
                </td>
                <td>
                  <div class="fw-semibold">{{ item.service?.name }}</div>
                  <div class="text-muted smaller">{{ item.variant?.sku }}</div>
                </td>
                <td class="small">
                  <div>{{ item.payment?.method }}</div>
                  <div class="text-muted smaller">{{ money(item.commercial?.total_amount) }}</div>
                </td>
                <td>
                  <span class="badge" :class="enums.cssClass('service-order-statuses', item.request_status)">
                    {{ enums.label('service-order-statuses', item.request_status, item.request_status) }}
                  </span>
                </td>
                <td>
                  <OperationStatusBadge v-if="item.operation" :status="item.operation.status" />
                  <span v-else class="text-muted smaller">—</span>
                </td>
                <td class="small">
                  {{ item.technician?.name || 'Sin asignar' }}
                  <i v-if="item.technician?.diverges" class="bi bi-exclamation-triangle text-warning ms-1" title="Diverge del sistema legacy"></i>
                </td>
                <td class="small">
                  <template v-if="item.schedule?.scheduled_date">{{ item.schedule.scheduled_date }} {{ item.schedule.scheduled_time }}</template>
                  <span v-else class="text-muted">Sin programar</span>
                </td>
                <td>
                  <span class="badge" :class="enums.cssClass('service-priorities', item.commercial?.priority)">
                    {{ enums.label('service-priorities', item.commercial?.priority, item.commercial?.priority) }}
                  </span>
                </td>
                <td class="text-end px-4">
                  <button class="btn btn-sm btn-outline-primary" @click="toggle(item.request_id)">
                    {{ expandedUuid === item.request_id ? 'Ocultar' : 'Gestionar' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedUuid === item.request_id">
                <td colspan="10" class="p-0 bg-light">
                  <div class="p-3">
                    <ServiceRequestActionsPanel :request="item" @changed="onChanged" @collapse="expandedUuid = null" />
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Paginacion -->
      <div class="card-footer bg-white border-0 d-flex justify-content-between align-items-center py-3 px-4">
        <div class="text-muted smaller">{{ store.totalRequests }} registros encontrados</div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-light border" :disabled="!prevPage || store.loading" @click="loadPage(prevPage)">
            <i class="bi bi-chevron-left"></i>
          </button>
          <button class="btn btn-sm btn-light border" :disabled="!nextPage || store.loading" @click="loadPage(nextPage)">
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { formatCOP } from '@/utils/money';
import { useEnums } from '@/composables/useEnums';
import useApi from '@/composables/useApi';
import { useServiceRequestsAdminStore } from '@/store/technicalServicesAdmin/requests';
import ServiceRequestActionsPanel from './ServiceRequestActionsPanel.vue';
import OperationStatusBadge from '@/components/customer/services/OperationStatusBadge.vue';

const enums = useEnums();
const store = useServiceRequestsAdminStore();
const api = useApi();

const expandedUuid = ref(null);
const nextPage = ref(null);
const prevPage = ref(null);
const currentPageUrl = ref(null);
let searchDebounce = null;

const kpiCards = ref([]);
async function loadKpis() {
  try {
    const { data } = await api.get('service-operations/dashboard/');
    kpiCards.value = [
      { label: 'Nuevas hoy', value: data.new_today },
      { label: 'Pendientes de planeacion', value: data.pending_planning },
      { label: 'Sin tecnico', value: data.without_technician },
      { label: 'Programadas hoy', value: data.scheduled_today },
      { label: 'En curso', value: data.in_progress },
      { label: 'Atrasadas', value: data.delayed },
      { label: 'Canceladas', value: data.cancelled },
    ];
  } catch {
    kpiCards.value = [];
  }
}

const filters = reactive({ status: '', priority: '', has_technician: '', search: '' });

// useEnums() no expone el mapa de valores de forma reactiva (solo
// label()/cssClass() por clave puntual) -- mismo motivo por el que
// RentingRequestList.vue tampoco deriva las opciones de su <select> de
// filtro del catalogo, solo el badge de render. Las claves de aqui
// espejan ServiceOperation.STATUS_CHOICES / OrderServiceDetail.PRIORITY_CHOICES
// (technical_services/models.py) -- el label mostrado si sale de
// enums.label(), no se hardcodea el texto.
const OPERATION_STATUS_KEYS = [
  'READY_FOR_PLANNING', 'PLANNED', 'TECHNICIAN_ASSIGNED', 'CUSTOMER_NOTIFIED',
  'READY_TO_VISIT', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'CANCELLED',
];
const PRIORITY_KEYS = ['low', 'medium', 'high', 'critical'];

// Poblados en onMounted, despues de enums.ensure() -- construirlos antes
// (ej. en un computed sin dependencia reactiva) los dejaria mostrando la
// clave cruda para siempre, porque enums.label() no es reactivo a la
// resolucion async de ensure() (mismo motivo por el que BaseStatusBadge.vue
// usa un ref `loaded` local en vez de confiar en reactividad implicita).
const operationStatusOptions = ref([]);
const priorityOptions = ref([]);

function money(value) {
  return value != null ? formatCOP(value, { withSymbol: true }) : '—';
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

function extractPath(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

async function loadPage(url = null) {
  currentPageUrl.value = url;
  const params = url ? Object.fromEntries(new URLSearchParams(url.split('?')[1] || '')) : buildParams();
  const payload = await store.fetchRequests(params);
  if (payload) {
    nextPage.value = payload.next ? extractPath(payload.next) : null;
    prevPage.value = payload.previous ? extractPath(payload.previous) : null;
  }
}

function buildParams() {
  const params = {};
  if (filters.status) params.status = filters.status;
  if (filters.priority) params.priority = filters.priority;
  if (filters.has_technician) params.has_technician = filters.has_technician;
  if (filters.search) params.search = filters.search;
  return params;
}

function onSearchInput() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => loadPage(), 400);
}

function toggle(uuid) {
  expandedUuid.value = expandedUuid.value === uuid ? null : uuid;
}

function onChanged() {
  expandedUuid.value = null;
  loadPage(currentPageUrl.value);
  loadKpis();
}

onMounted(async () => {
  await Promise.all([
    enums.ensure('service-operation-statuses'),
    enums.ensure('service-order-statuses'),
    enums.ensure('service-priorities'),
  ]);
  operationStatusOptions.value = OPERATION_STATUS_KEYS.map((key) => ({
    key, label: enums.label('service-operation-statuses', key, key),
  }));
  priorityOptions.value = PRIORITY_KEYS.map((key) => ({
    key, label: enums.label('service-priorities', key, key),
  }));
  loadPage();
  loadKpis();
});
</script>

<style scoped>
.smaller { font-size: 0.75rem; }
.kpi-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
  padding: .75rem 1rem; text-align: center;
}
.kpi-value { font-size: 1.35rem; font-weight: 700; color: #111827; line-height: 1.1; }
.kpi-label { font-size: .72rem; color: #6b7280; margin-top: .2rem; }
</style>
