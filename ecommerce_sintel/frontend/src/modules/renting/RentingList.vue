<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-4">
      <h4 class="fw-bold mb-0">Renta de Equipos</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Equipo
      </button>
    </div>

    <!-- Filtros -->
    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="input-group">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input
            v-model="search"
            class="form-control border-start-0 ps-0"
            placeholder="Buscar equipos..."
          />
        </div>
      </div>
      <div class="col-md-3">
        <select v-model="filters.category" class="form-select" @change="loadPage()">
          <option value="">Todas las categorías</option>
          <option v-for="cat in categories" :key="cat.uuid" :value="cat.slug">
            {{ cat.name }}
          </option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.brand" class="form-select" @change="loadPage()">
          <option value="">Todas las marcas</option>
          <option v-for="brd in brands" :key="brd.uuid" :value="brd.slug">
            {{ brd.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 35%">Equipo</th>
              <th class="py-3">Categoría</th>
              <th class="py-3">Marca</th>
              <th class="py-3 text-center">Stock</th>
              <th class="py-3">Precio / Día</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando equipos...</span>
              </td>
            </tr>
            <tr v-else-if="!items.length">
              <td colspan="6" class="text-center py-5 text-muted">
                <i class="bi bi-truck fs-2 d-block mb-2"></i>
                Sin registros.
              </td>
            </tr>
            <template v-for="item in items" :key="item.uuid">
              <tr v-if="pendingDelete?.uuid === item.uuid" class="bg-danger-subtle">
                <td colspan="6" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar equipo <strong>{{ item.name }}</strong>? Esta acción es permanente.</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(item)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4">
                  <div class="d-flex align-items-center">
                    <div
                      class="rounded-3 bg-light d-flex align-items-center justify-content-center me-3"
                      style="width: 45px; height: 45px;"
                    >
                      <img
                        v-if="item.images && item.images.length"
                        :src="item.images.find(img => img.is_primary)?.image || item.images[0].image"
                        class="rounded-3"
                        style="width: 100%; height: 100%; object-fit: cover;"
                      />
                      <i v-else class="bi bi-gear-wide-connected text-muted"></i>
                    </div>
                    <div>
                      <div class="fw-semibold text-dark">{{ item.name }}</div>
                      <div class="text-muted smaller" v-if="item.variants?.length">
                        {{ item.variants[0].sku }}
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  <span class="badge bg-light text-secondary border rounded-pill fw-medium">
                    {{ item.category?.name }}
                  </span>
                </td>
                <td>
                  <span class="badge bg-dark-subtle text-dark border rounded-pill fw-medium">
                    {{ item.brand?.name || '—' }}
                  </span>
                </td>
                <td class="text-center">
                  <span
                    class="badge rounded-pill fw-bold"
                    :class="item.variants?.[0]?.stock > 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'"
                  >
                    {{ item.variants?.[0]?.stock || 0 }} und
                  </span>
                </td>
                <td>
                  <div class="fw-bold text-dark">
                    {{ item.variants?.length ? formatCurrency(item.variants[0].rental_price_per_day) : 'N/A' }}
                  </div>
                  <div v-if="item.variants?.length" class="text-muted smaller">
                    {{ formatCurrency(item.variants[0].rental_price_per_hour) }} / hora
                  </div>
                </td>
                <td class="text-end px-4">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button
                      class="btn btn-light border-end"
                      @click="router.push({ name: 'equipment-detail', params: { uuid: item.uuid } })"
                      title="Ver Detalle"
                    >
                      <i class="bi bi-eye text-info"></i>
                    </button>
                    <button class="btn btn-light border-end" @click="openEdit(item)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = item" title="Eliminar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
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

    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nuevo Equipo' : 'Gestionar Equipo'"
      :subtitle="mode === 'create' ? 'Registrar equipo para renta' : selected?.name"
      width="820px"
    >
      <RentingForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { formatCOP } from '@/utils/money';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import RentingForm from './RentingForm.vue';

const router = useRouter();
const api = useApi();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const items = ref([]);
const categories = ref([]);
const brands = ref([]);
const loading = ref(true);
const actionLoading = ref(false);
const search = ref('');
const totalCount = ref(0);
const nextPage = ref(null);
const prevPage = ref(null);
const pendingDelete = ref(null);

const filters = reactive({ category: '', brand: '' });

async function loadFilters() {
  try {
    const [catRes, brdRes] = await Promise.all([
      api.get('dashboard/renting-categories/'),
      api.get('dashboard/renting-brands/')
    ]);
    categories.value = catRes.data.results || catRes.data;
    brands.value = brdRes.data.results || brdRes.data;
  } catch (err) {
    console.error('Error cargando filtros:', err);
  }
}

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
    }
  } catch (err) {
    toast.error('Error cargando los equipos.');
  } finally {
    loading.value = false;
  }
}

async function executeDelete(item) {
  actionLoading.value = true;
  try {
    await api.delete(`dashboard/equipment/${item.uuid}/`);
    toast.success(`Equipo "${item.name}" eliminado`);
    await loadPage();
  } catch (err) {
    toast.error('No se pudo eliminar el equipo');
  } finally {
    actionLoading.value = false;
    pendingDelete.value = null;
  }
}

function buildEndpoint() {
  const params = new URLSearchParams();
  if (search.value) params.append('search', search.value);
  if (filters.category) params.append('category__slug', filters.category);
  if (filters.brand) params.append('brand__slug', filters.brand);
  return `dashboard/equipment/?${params.toString()}`;
}

function extractPath(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

function formatCurrency(value) {
  if (!value) return 'N/A';
  return formatCOP(value, { withSymbol: true });
}

const onFormSuccess = () => { close(); loadFilters(); loadPage(); };

let debounceTimer = null;
watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadPage(), 400);
});

onMounted(() => {
  loadFilters();
  loadPage();
});
</script>

<style scoped>
.smaller { font-size: 0.75rem; }
</style>
