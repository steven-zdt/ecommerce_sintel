<template>
  <div class="professionals-module">

    <!-- Cabecera -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h4 class="fw-bold mb-0">Profesionales del Marketplace</h4>
        <p class="text-muted small mb-0">{{ totalCount }} profesional{{ totalCount !== 1 ? 'es' : '' }} registrado{{ totalCount !== 1 ? 's' : '' }}</p>
      </div>
    </div>

    <!-- KPI cards -->
    <div class="row g-3 mb-3">
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value">{{ metrics.total ?? '—' }}</div>
          <div class="kpi-label">Total profesionales</div>
        </div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-success">{{ metrics.active_count ?? '—' }}</div>
          <div class="kpi-label">Activos ({{ metrics.inactive_count ?? 0 }} inactivos)</div>
        </div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-primary">{{ metrics.available_count ?? '—' }}</div>
          <div class="kpi-label">Disponibles ({{ metrics.unavailable_count ?? 0 }} ocupados)</div>
        </div>
      </div>
      <div class="col-6 col-lg-3">
        <div class="kpi-card">
          <div class="kpi-value text-warning">
            <i class="bi bi-star-fill smaller"></i> {{ metrics.average_rating ?? '—' }}
          </div>
          <div class="kpi-label">Calificación promedio</div>
        </div>
      </div>
    </div>

    <!-- Filtros -->
    <div class="row g-2 mb-3">
      <div class="col-md-4">
        <div class="input-group">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input
            v-model="search"
            class="form-control border-start-0 ps-0"
            placeholder="Buscar por nombre o email..."
          />
        </div>
      </div>
      <div class="col-md-3">
        <select v-model="filters.user_type" class="form-select" @change="loadPage()">
          <option value="">Todos los tipos</option>
          <option v-for="(meta, code) in serviceProviderTypes" :key="code" :value="code">{{ meta.label }}</option>
        </select>
      </div>
      <div class="col-md-2">
        <select v-model="filters.is_active" class="form-select" @change="loadPage()">
          <option value="">Activo/Inactivo</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.is_available" class="form-select" @change="loadPage()">
          <option value="">Disponibilidad</option>
          <option value="true">Disponibles</option>
          <option value="false">Ocupados</option>
        </select>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Profesional</th>
              <th>Tipo</th>
              <th>Ciudad</th>
              <th>Tarifa/hr</th>
              <th>Rating</th>
              <th>Servicios</th>
              <th>Disponibilidad</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando profesionales...</div>
              </td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="8" class="text-center py-5 text-muted">
                <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                No hay profesionales que coincidan con los filtros.
              </td>
            </tr>
            <tr v-else v-for="pro in items" :key="pro.uuid" :class="{ 'opacity-60': !pro.is_active }">
              <td>
                <div class="fw-semibold">{{ pro.full_name }}</div>
                <div class="text-muted smaller">{{ pro.email }}</div>
              </td>
              <td>
                <span class="badge" :class="enums.cssClass('user-types', pro.user_type)">
                  {{ enums.label('user-types', pro.user_type, pro.user_type) }}
                </span>
              </td>
              <td class="text-muted small">{{ pro.city || '—' }}</td>
              <td class="text-muted small">{{ pro.hourly_rate ? `${pro.hourly_rate} ${pro.currency}` : '—' }}</td>
              <td>
                <i class="bi bi-star-fill text-warning smaller"></i>
                {{ pro.average_rating }} <span class="text-muted smaller">({{ pro.total_reviews }})</span>
              </td>
              <td class="text-muted small">{{ pro.total_services_completed }}</td>
              <td>
                <button
                  class="btn btn-sm"
                  :class="pro.is_available ? 'btn-outline-success' : 'btn-outline-secondary'"
                  :disabled="togglingUuid === pro.uuid"
                  @click="toggleAvailability(pro)"
                >
                  <span v-if="togglingUuid === pro.uuid" class="spinner-border spinner-border-sm me-1"></span>
                  {{ pro.is_available ? 'Disponible' : 'Ocupado' }}
                </button>
              </td>
              <td>
                <span :class="['badge rounded-pill', pro.is_active ? 'bg-success' : 'bg-secondary']">
                  {{ pro.is_active ? 'Activo' : 'Inactivo' }}
                </span>
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
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';

const api = useApi();
const toast = useToast();
const enums = useEnums();

const items = ref([]);
const loading = ref(true);
const togglingUuid = ref(null);
const metrics = ref({});
const serviceProviderTypes = ref({});

const search = ref('');
const totalCount = ref(0);
const nextPage = ref(null);
const prevPage = ref(null);

const filters = reactive({
  user_type: '',
  is_active: '',
  is_available: '',
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
    console.error('Error al cargar profesionales:', err);
    toast.error('No se pudieron cargar los profesionales');
  } finally {
    loading.value = false;
  }
}

async function loadMetrics() {
  try {
    const { data } = await api.get('auth/admin/professionals/metrics/');
    metrics.value = data;
  } catch (err) {
    console.error('Error al cargar métricas de profesionales:', err);
  }
}

function buildEndpoint() {
  const params = new URLSearchParams();
  if (search.value) params.append('search', search.value);
  if (filters.user_type) params.append('user_type', filters.user_type);
  if (filters.is_active) params.append('is_active', filters.is_active);
  if (filters.is_available) params.append('is_available', filters.is_available);
  return `auth/admin/professionals/?${params.toString()}`;
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

const toggleAvailability = async (pro) => {
  togglingUuid.value = pro.uuid;
  try {
    const { data } = await api.patch(`auth/admin/professionals/${pro.uuid}/toggle-availability/`, {
      is_available: !pro.is_available,
    });
    pro.is_available = data.is_available;
    toast.success(`${pro.full_name} ahora está ${data.is_available ? 'disponible' : 'ocupado'}`);
    await loadMetrics();
  } catch (err) {
    toast.error(err.response?.data?.detail || 'No se pudo cambiar la disponibilidad');
  } finally {
    togglingUuid.value = null;
  }
};

onMounted(async () => {
  const allUserTypes = await enums.ensure('user-types');
  serviceProviderTypes.value = Object.fromEntries(
    Object.entries(allUserTypes).filter(([code]) =>
      ['TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR'].includes(code)
    )
  );
  loadPage();
  loadMetrics();
});
</script>

<style scoped>
.smaller { font-size: 0.8rem; }
.opacity-60 { opacity: 0.6; }
.kpi-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 12px;
  padding: 1rem 1.25rem;
}
.kpi-value { font-size: 1.6rem; font-weight: 800; line-height: 1; }
.kpi-label { font-size: 0.78rem; color: #6b7280; margin-top: 0.35rem; }
</style>
