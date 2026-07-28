<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Transacciones de Pago</h4>
    </div>

    <!-- ── Feature flag (ADR-001 Fase 5/7) ──────────────────────────── -->
    <div class="card shadow-sm border-0 mb-3">
      <div class="card-body d-flex justify-content-between align-items-center py-2">
        <div>
          <p class="fw-semibold mb-0 small">Flujo de pago con tarjeta via API</p>
          <p class="text-muted mb-0" style="font-size:.78rem">
            Si se desactiva, el checkout solo ofrece PSE/Otros (Widget completo) -- reversion instantanea sin deploy.
          </p>
        </div>
        <div class="form-check form-switch m-0">
          <input
            class="form-check-input" type="checkbox" role="switch"
            :checked="cardApiFlowEnabled" :disabled="flagLoading"
            @change="toggleCardApiFlow($event.target.checked)"
          >
        </div>
      </div>
    </div>

    <!-- Plan hibrido Widget+API (auditoria 2026-07-22): kill-switch independiente
         para el Widget, simetrico al de arriba. -->
    <div class="card shadow-sm border-0 mb-3">
      <div class="card-body d-flex justify-content-between align-items-center py-2">
        <div>
          <p class="fw-semibold mb-0 small">Flujo de pago via Widget (PSE/Otros)</p>
          <p class="text-muted mb-0" style="font-size:.78rem">
            Si se desactiva, el checkout solo permite pagar con Tarjeta via API -- util ante una incidencia puntual del Widget de Wompi.
          </p>
        </div>
        <div class="form-check form-switch m-0">
          <input
            class="form-check-input" type="checkbox" role="switch"
            :checked="widgetFlowEnabled" :disabled="flagLoading"
            @change="toggleWidgetFlow($event.target.checked)"
          >
        </div>
      </div>
    </div>

    <ul class="nav nav-tabs mb-3">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'wompi' }" @click="switchTab('wompi')">
          Wompi
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'nequi' }" @click="switchTab('nequi')">
          Nequi
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'cod' }" @click="switchTab('cod')">
          Contraentrega (COD)
        </button>
      </li>
    </ul>

    <div class="d-flex gap-2 mb-3">
      <select v-model="statusFilter" class="form-select form-select-sm" style="max-width:220px" @change="fetchCurrent">
        <option value="">Todos los estados</option>
        <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <!-- ── Wompi ──────────────────────────────────────────────────── -->
    <div v-show="tab === 'wompi'" class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Fecha</th>
              <th>Wompi ID</th>
              <th>Orden / Alquiler</th>
              <th>Metodo</th>
              <th>Canal</th>
              <th>Monto</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="text-center py-5"><div class="spinner-border text-primary"></div></td>
            </tr>
            <tr v-else-if="wompiTx.length === 0">
              <td colspan="8" class="text-center py-5 text-muted">Sin transacciones.</td>
            </tr>
            <template v-for="t in wompiTx" :key="t.uuid">
              <tr>
                <td class="small text-muted">{{ formatDate(t.created_at) }}</td>
                <td><code class="small">{{ t.wompi_id || '-' }}</code></td>
                <td class="small">{{ t.order ? `Orden #${t.order}` : (t.rental_request ? `Alquiler #${t.rental_request}` : '-') }}</td>
                <td class="small">{{ t.payment_method_type || '-' }}</td>
                <td>
                  <span v-if="t.initiation_channel" class="badge bg-light text-dark border small">
                    {{ t.initiation_channel === 'CARD_API' ? 'Tarjeta (API)' : 'Widget' }}
                  </span>
                  <span v-else class="text-muted small">-</span>
                </td>
                <td>{{ fmtCOP(t.amount_in_cents / 100) }}</td>
                <td><span :class="['badge', statusClass(t.status)]">{{ t.status }}</span></td>
                <td class="d-flex gap-1">
                  <button
                    v-if="t.status === 'PENDING' && t.wompi_id"
                    class="btn btn-sm btn-outline-primary" :disabled="resyncingUuid === t.uuid"
                    @click="resyncTransaction(t)"
                  >
                    <span v-if="resyncingUuid === t.uuid" class="spinner-border spinner-border-sm"></span>
                    <template v-else>Reconciliar</template>
                  </button>
                  <button class="btn btn-sm btn-outline-secondary" @click="toggleHistory(t.uuid)">
                    {{ expandedUuid === t.uuid ? 'Ocultar' : 'Historial' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedUuid === t.uuid">
                <td colspan="8" class="bg-light">
                  <div v-if="historyLoading" class="text-center py-2">
                    <span class="spinner-border spinner-border-sm text-primary"></span>
                  </div>
                  <div v-else-if="transactionEvents.length === 0" class="text-muted small py-2">
                    Sin eventos registrados para esta transaccion.
                  </div>
                  <table v-else class="table table-sm mb-0">
                    <thead>
                      <tr class="small text-muted">
                        <th>Fecha</th><th>Origen</th><th>Transicion</th><th>Procesado</th><th>Detalle</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="ev in transactionEvents" :key="ev.uuid" class="small">
                        <td class="text-muted">{{ formatDate(ev.created_at) }}</td>
                        <td>{{ ev.source }}</td>
                        <td>{{ ev.previous_status || '—' }} → {{ ev.new_status || '—' }}</td>
                        <td>
                          <span :class="['badge', ev.processed ? 'bg-success' : 'bg-warning text-dark']">
                            {{ ev.processed ? 'si' : 'no' }}
                          </span>
                        </td>
                        <td class="text-muted">{{ ev.error_detail || '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted small">{{ wompiTx.length }} de {{ totalCount }} registros</span>
        <nav v-if="totalPages > 1">
          <ul class="pagination pagination-sm m-0">
            <li class="page-item"><button class="page-link" @click="changePage(currentPage - 1)">Ant.</button></li>
            <li class="page-item"><button class="page-link" @click="changePage(currentPage + 1)">Sig.</button></li>
          </ul>
        </nav>
      </div>
    </div>

    <!-- ── Nequi ──────────────────────────────────────────────────── -->
    <div v-show="tab === 'nequi'" class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Fecha</th>
              <th>Telefono</th>
              <th>Orden / Alquiler</th>
              <th>Monto</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="text-center py-5"><div class="spinner-border text-primary"></div></td>
            </tr>
            <tr v-else-if="nequiTx.length === 0">
              <td colspan="5" class="text-center py-5 text-muted">Sin transacciones.</td>
            </tr>
            <tr v-for="t in nequiTx" :key="t.uuid">
              <td class="small text-muted">{{ formatDate(t.created_at) }}</td>
              <td>{{ t.phone_number }}</td>
              <td class="small">{{ t.order ? `Orden #${t.order}` : (t.rental_request ? `Alquiler #${t.rental_request}` : '-') }}</td>
              <td>{{ fmtCOP(t.amount) }}</td>
              <td><span :class="['badge', statusClass(t.status)]">{{ t.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted small">{{ nequiTx.length }} de {{ totalCount }} registros</span>
        <nav v-if="totalPages > 1">
          <ul class="pagination pagination-sm m-0">
            <li class="page-item"><button class="page-link" @click="changePage(currentPage - 1)">Ant.</button></li>
            <li class="page-item"><button class="page-link" @click="changePage(currentPage + 1)">Sig.</button></li>
          </ul>
        </nav>
      </div>
    </div>

    <!-- ── COD ────────────────────────────────────────────────────── -->
    <div v-show="tab === 'cod'" class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Fecha</th>
              <th>Orden</th>
              <th>Entregado</th>
              <th>Notas</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="text-center py-5"><div class="spinner-border text-primary"></div></td>
            </tr>
            <tr v-else-if="codTx.length === 0">
              <td colspan="5" class="text-center py-5 text-muted">Sin transacciones.</td>
            </tr>
            <tr v-for="t in codTx" :key="t.uuid">
              <td class="small text-muted">{{ formatDate(t.created_at) }}</td>
              <td class="small">Orden #{{ t.order }}</td>
              <td class="small text-muted">{{ t.delivered_at ? formatDate(t.delivered_at) : '-' }}</td>
              <td class="small">{{ t.notes || '-' }}</td>
              <td><span :class="['badge', statusClass(t.status)]">{{ t.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted small">{{ codTx.length }} de {{ totalCount }} registros</span>
        <nav v-if="totalPages > 1">
          <ul class="pagination pagination-sm m-0">
            <li class="page-item"><button class="page-link" @click="changePage(currentPage - 1)">Ant.</button></li>
            <li class="page-item"><button class="page-link" @click="changePage(currentPage + 1)">Sig.</button></li>
          </ul>
        </nav>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { formatCOP } from '@/utils/money';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { usePaymentAdminStore } from '@/store/paymentAdmin';

const toast = useToast();
const { handleError } = useErrorHandler();
const store = usePaymentAdminStore();
const {
  wompiTx, nequiTx, codTx, totalCount, totalPages, loading,
  cardApiFlowEnabled, widgetFlowEnabled, flagLoading,
  transactionEvents, historyLoading,
} = storeToRefs(store);

const tab = ref('wompi');
const statusFilter = ref('');
const currentPage = ref(1);
const expandedUuid = ref('');
const resyncingUuid = ref('');

const STATUS_OPTIONS_BY_TAB = {
  wompi: ['PENDING', 'APPROVED', 'DECLINED', 'VOIDED', 'ERROR'],
  nequi: ['PENDING', 'APPROVED', 'REJECTED', 'ERROR'],
  cod:   ['CONFIRMED', 'DELIVERED', 'CANCELLED'],
};
const statusOptions = computed(() => STATUS_OPTIONS_BY_TAB[tab.value]);

function switchTab(t) {
  tab.value = t;
  statusFilter.value = '';
  currentPage.value = 1;
  fetchCurrent();
}

function fetchCurrent() {
  store.fetchTransactions(tab.value, currentPage.value, statusFilter.value);
}

async function toggleCardApiFlow(checked) {
  const res = await store.toggleCardApiFlow(checked);
  if (res.ok) {
    toast.success(checked ? 'Flujo de tarjeta via API activado' : 'Flujo de tarjeta via API desactivado');
  } else {
    handleError(res.error, 'No se pudo actualizar el flag');
  }
}

async function toggleWidgetFlow(checked) {
  const res = await store.toggleWidgetFlow(checked);
  if (res.ok) {
    toast.success(checked ? 'Flujo via Widget activado' : 'Flujo via Widget desactivado');
  } else {
    handleError(res.error, 'No se pudo actualizar el flag');
  }
}

async function resyncTransaction(t) {
  resyncingUuid.value = t.uuid;
  const res = await store.resyncTransaction(t.uuid);
  if (res.ok) {
    toast.success(`Estado actualizado: ${res.data.status}`);
  } else {
    handleError(res.error, 'No se pudo reconciliar la transaccion');
  }
  resyncingUuid.value = '';
}

function toggleHistory(uuid) {
  if (expandedUuid.value === uuid) {
    expandedUuid.value = '';
    return;
  }
  expandedUuid.value = uuid;
  store.fetchTransactionEvents(uuid);
}

function changePage(p) {
  if (p >= 1 && p <= totalPages.value) {
    currentPage.value = p;
    fetchCurrent();
  }
}

function statusClass(status) {
  if (['APPROVED', 'DELIVERED', 'CONFIRMED'].includes(status)) return 'bg-success';
  if (['DECLINED', 'REJECTED', 'ERROR', 'CANCELLED'].includes(status)) return 'bg-danger';
  if (status === 'VOIDED') return 'bg-secondary';
  return 'bg-warning text-dark';
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('es-CO');
}

function fmtCOP(n) {
  return formatCOP(n, { withSymbol: true });
}

onMounted(() => {
  fetchCurrent();
  store.fetchFeatureFlags();
});
</script>
