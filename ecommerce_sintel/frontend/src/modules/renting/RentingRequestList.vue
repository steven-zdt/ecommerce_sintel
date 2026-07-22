<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-4">
      <div>
        <h4 class="fw-bold mb-0">Solicitudes de Alquiler</h4>
        <p class="text-muted small mb-0">{{ store.totalRentalRequests }} solicitud{{ store.totalRentalRequests !== 1 ? 'es' : '' }} en total</p>
      </div>
    </div>

    <!-- Filtros -->
    <div class="row g-2 mb-3">
      <div class="col-md-4">
        <select v-model="filters.status" class="form-select" @change="loadPage()">
          <option value="">Todos los estados</option>
          <option value="pending_validation">Pendiente de aprobacion</option>
          <option value="pending_payment">Pendiente de pago</option>
          <option value="paid">Pagado</option>
          <option value="confirmed">Confirmado</option>
          <option value="in_operation">En operacion</option>
          <option value="finished">Finalizado</option>
          <option value="cancelled">Cancelado</option>
          <option value="payment_conflict">Conflicto de pago</option>
        </select>
      </div>
      <div class="col-md-4">
        <select v-model="filters.payment_method" class="form-select" @change="loadPage()">
          <option value="">Cualquier metodo de pago</option>
          <option value="WOMPI">Wompi</option>
          <option value="NEQUI">Nequi</option>
          <option value="COD">Contra entrega</option>
        </select>
      </div>
      <div class="col-md-4">
        <select v-model="filters.refund_required" class="form-select" @change="loadPage()">
          <option value="">Reembolso: cualquiera</option>
          <option value="true">Requiere reembolso</option>
          <option value="false">Sin reembolso pendiente</option>
        </select>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3">Equipo</th>
              <th class="py-3">Cliente</th>
              <th class="py-3">Fechas</th>
              <th class="py-3 text-center">Cantidad</th>
              <th class="py-3">Estado</th>
              <th class="py-3 text-end">Costo</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="7" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando solicitudes...</span>
              </td>
            </tr>
            <tr v-else-if="!store.rentalRequests.length">
              <td colspan="7" class="text-center py-5 text-muted">
                <i class="bi bi-clipboard-check fs-2 d-block mb-2"></i>
                Sin registros.
              </td>
            </tr>
            <template v-for="item in store.rentalRequests" :key="item.uuid">
              <tr>
                <td class="px-4">
                  <div class="fw-semibold text-dark">{{ item.equipment_variant?.equipment_name }}</div>
                  <div class="text-muted smaller">{{ item.equipment_variant?.sku }}</div>
                </td>
                <td>
                  <div class="fw-semibold">{{ item.contact_full_name }}</div>
                  <div class="text-muted smaller">{{ item.contact_email }}</div>
                </td>
                <td class="small">
                  <div>{{ item.start_date }} — {{ item.end_date }}</div>
                  <div v-if="item.rental_mode === 'hours'" class="text-muted smaller">{{ item.delivery_time }} - {{ item.pickup_time }}</div>
                </td>
                <td class="text-center">{{ item.quantity }}</td>
                <td>
                  <span class="badge" :class="enums.cssClass('rental-statuses', item.status)">
                    {{ item.display_status || enums.label('rental-statuses', item.status, item.status) }}
                  </span>
                  <span v-if="item.refund_required" class="badge bg-danger-subtle text-danger border border-danger-subtle ms-1">
                    Reembolso
                  </span>
                </td>
                <td class="text-end fw-bold">{{ money(item.grand_total) }}</td>
                <td class="text-end px-4">
                  <button class="btn btn-sm btn-outline-primary" @click="toggle(item.uuid)">
                    {{ expandedUuid === item.uuid ? 'Ocultar' : 'Gestionar' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedUuid === item.uuid">
                <td colspan="7" class="p-0 bg-light">
                  <div class="p-3">
                    <RentalRequestActionsPanel :request="item" @changed="onChanged" @collapse="expandedUuid = null" />
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Paginacion -->
      <div class="card-footer bg-white border-0 d-flex justify-content-between align-items-center py-3 px-4">
        <div class="text-muted smaller">{{ store.totalRentalRequests }} registros encontrados</div>
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
import { useEnums } from '@/composables/useEnums';
import { useRentingRequestsAdminStore } from '@/store/rentingAdmin/requests';
import RentalRequestActionsPanel from './RentalRequestActionsPanel.vue';

const enums = useEnums();
const store = useRentingRequestsAdminStore();

const expandedUuid = ref(null);
const nextPage = ref(null);
const prevPage = ref(null);
const currentPageUrl = ref(null);

const filters = reactive({ status: '', payment_method: '', refund_required: '' });

function money(value) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value || 0);
}

function extractPath(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

async function loadPage(url = null) {
  currentPageUrl.value = url;
  // `url` (cuando viene de la paginacion) es un path relativo con su propio
  // query string (ej. 'renting/rental-requests/?page=2&status=paid'); se
  // reextraen sus params para reusar la misma action del store en vez de
  // llamar a useApi() directo desde el componente.
  const params = url ? Object.fromEntries(new URLSearchParams(url.split('?')[1] || '')) : buildParams();
  const payload = await store.fetchRentalRequests(params);
  if (payload) {
    nextPage.value = payload.next ? extractPath(payload.next) : null;
    prevPage.value = payload.previous ? extractPath(payload.previous) : null;
  }
}

function buildParams() {
  const params = {};
  if (filters.status) params.status = filters.status;
  if (filters.payment_method) params.payment_method = filters.payment_method;
  if (filters.refund_required) params.refund_required = filters.refund_required;
  return params;
}

function toggle(uuid) {
  expandedUuid.value = expandedUuid.value === uuid ? null : uuid;
}

function onChanged() {
  expandedUuid.value = null;
  loadPage(currentPageUrl.value);
}

onMounted(async () => {
  await enums.ensure('rental-statuses');
  loadPage();
});
</script>

<style scoped>
.smaller { font-size: 0.75rem; }
</style>
