<template>
  <div class="kyc-module">

    <!-- Cabecera -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h4 class="fw-bold mb-0">Validaciones KYC</h4>
        <p class="text-muted small mb-0">{{ totalCount }} solicitud{{ totalCount !== 1 ? 'es' : '' }} en total</p>
      </div>
    </div>

    <!-- KPI cards -->
    <div class="row g-3 mb-3">
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-warning">{{ kpi.by_status?.PENDING ?? '—' }}</div>
          <div class="kpi-label">Pendientes</div>
        </div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-primary">{{ kpi.by_status?.UNDER_REVIEW ?? '—' }}</div>
          <div class="kpi-label">En revision</div>
        </div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-success">{{ kpi.by_status?.APPROVED ?? '—' }}</div>
          <div class="kpi-label">Aprobados</div>
        </div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-danger">{{ kpi.by_status?.REJECTED ?? '—' }}</div>
          <div class="kpi-label">Rechazados</div>
        </div>
      </div>
    </div>

    <!-- Desglose por tipo solicitado + tiempo promedio de aprobacion -->
    <div v-if="hasTypeBreakdown || kpi.average_approval_seconds" class="row g-3 mb-3">
      <div class="col-lg-8">
        <div class="kpi-card d-flex flex-wrap gap-3">
          <div v-for="(count, type) in kpi.by_requested_type" :key="type" class="text-center px-2">
            <div class="fw-bold">{{ count }}</div>
            <div class="smaller text-muted">{{ enums.label('user-types', type, type) }}</div>
          </div>
          <div v-if="!hasTypeBreakdown" class="text-muted smaller">Sin solicitudes de upgrade todavia.</div>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="kpi-card">
          <div class="kpi-value">{{ averageApprovalLabel }}</div>
          <div class="kpi-label">Tiempo promedio de aprobacion</div>
        </div>
      </div>
    </div>

    <!-- Filtros -->
    <div class="row g-2 mb-3">
      <div class="col-md-5">
        <div class="input-group">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input v-model="search" class="form-control border-start-0 ps-0" placeholder="Buscar por email...">
        </div>
      </div>
      <div class="col-md-4">
        <select v-model="filters.status" class="form-select" @change="loadPage()">
          <option value="">Todos los estados</option>
          <option value="PENDING">Pendiente</option>
          <option value="UNDER_REVIEW">En revision</option>
          <option value="APPROVED">Aprobado</option>
          <option value="REJECTED">Rechazado</option>
          <option value="BLOCKED">Bloqueado</option>
          <option value="EXPIRED">Expirado</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.requested_user_type" class="form-select" @change="loadPage()">
          <option value="">Cualquier tipo solicitado</option>
          <option v-for="t in SERVICE_PROVIDER_VALUES" :key="t" :value="t">
            {{ enums.label('user-types', t, t) }}
          </option>
        </select>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Solicitante</th>
              <th>Documento</th>
              <th>Tipo solicitado</th>
              <th>Estado</th>
              <th>Fecha registro</th>
              <th>Enviado a revision</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando verificaciones...</div>
              </td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="7" class="text-center py-5 text-muted">
                <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                No hay verificaciones que coincidan con los filtros.
              </td>
            </tr>
            <tr v-else v-for="item in items" :key="item.uuid">
              <td>
                <div class="fw-semibold">{{ item.primer_nombre }} {{ item.primer_apellido }}</div>
                <div class="text-muted smaller">{{ item.email }}</div>
              </td>
              <td class="text-muted small">{{ item.document_type }} {{ item.document }}</td>
              <td>
                <span v-if="item.requested_user_type" class="badge bg-primary-subtle text-primary border border-primary-subtle">
                  {{ enums.label('user-types', item.requested_user_type, item.requested_user_type) }}
                </span>
                <span v-else class="text-muted smaller">—</span>
              </td>
              <td>
                <span class="badge" :class="enums.cssClass('kyc-verification-statuses', item.status)">
                  {{ enums.label('kyc-verification-statuses', item.status, item.status) }}
                </span>
              </td>
              <td class="text-muted small">{{ formatDate(item.created_at) }}</td>
              <td class="text-muted small">{{ item.submitted_at ? formatDate(item.submitted_at) : '—' }}</td>
              <td>
                <RouterLink :to="{ name: 'kyc-admin-detail', params: { uuid: item.uuid } }" class="btn btn-sm btn-outline-primary">
                  Ver
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginacion -->
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';
import { useKycAdminStore } from '@/store/kycAdmin';

const SERVICE_PROVIDER_VALUES = ['TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR'];

const toast = useToast();
const enums = useEnums();
const store = useKycAdminStore();
const {
  items, totalCount, nextPage, prevPage, kpi,
  listLoading: loading,
} = storeToRefs(store);

const search = ref('');
const filters = reactive({ status: '', requested_user_type: '' });

const hasTypeBreakdown = computed(() => Object.keys(kpi.value.by_requested_type || {}).length > 0);
const averageApprovalLabel = computed(() => {
  const seconds = kpi.value.average_approval_seconds;
  if (!seconds) return '—';
  const hours = seconds / 3600;
  if (hours < 24) return `${hours.toFixed(1)} h`;
  return `${(hours / 24).toFixed(1)} dias`;
});

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' });
}

async function loadPage(page = null) {
  await store.fetchList(buildParams(page));
  if (store.error) toast.error(store.error);
}

function loadKpis() {
  return store.fetchKpis();
}

function buildParams(page) {
  const params = {};
  if (search.value) params.search = search.value;
  if (filters.status) params.status = filters.status;
  if (filters.requested_user_type) params.requested_user_type = filters.requested_user_type;
  if (page) params.page = page;
  return params;
}

let debounceTimer = null;
watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadPage(), 400);
});

onMounted(async () => {
  await Promise.all([enums.ensure('kyc-verification-statuses'), enums.ensure('user-types')]);
  loadPage();
  loadKpis();
});
</script>

<style scoped>
.smaller { font-size: 0.8rem; }
.kpi-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 12px;
  padding: 1rem 1.25rem;
}
.kpi-value { font-size: 1.6rem; font-weight: 800; line-height: 1; }
.kpi-label { font-size: 0.78rem; color: #6b7280; margin-top: 0.35rem; }
</style>
