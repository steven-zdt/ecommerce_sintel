<template>
  <div>
    <!-- Cabecera -->
    <div class="d-flex align-items-center justify-content-between mb-4">
      <h4 class="fw-bold mb-0">Servicios Técnicos</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Servicio
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
            placeholder="Buscar servicios..."
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
        <select v-model="filters.level" class="form-select" @change="loadPage()">
          <option value="">Todos los niveles</option>
          <option v-for="lvl in levels" :key="lvl.uuid" :value="lvl.slug">
            {{ lvl.name }}
          </option>
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-center">
        <div class="form-check form-switch ms-1">
          <input
            class="form-check-input"
            type="checkbox"
            id="featuredSwitch"
            v-model="filters.is_featured"
            @change="loadPage()"
          />
          <label class="form-check-label small" for="featuredSwitch">Destacados</label>
        </div>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 20%">Servicio</th>
              <th class="py-3" style="width: 15%">Descripción corta</th>
              <th class="py-3">Categoría</th>
              <th class="py-3">Nivel</th>
              <th class="py-3">Precio</th>
              <th class="py-3">Duración</th>
              <th class="py-3">Complejidad</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <!-- Cargando -->
            <tr v-if="loading">
              <td colspan="9" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando servicios...</span>
              </td>
            </tr>
            <!-- Vacío -->
            <tr v-else-if="!items.length">
              <td colspan="9" class="text-center py-5 text-muted">
                <i class="bi bi-tools fs-2 d-block mb-2"></i>
                Sin registros.
              </td>
            </tr>
            <!-- Filas -->
            <template v-for="item in items" :key="item.uuid">
              <!-- Confirmación de borrado inline -->
              <tr v-if="pendingDelete?.uuid === item.uuid" class="bg-danger-subtle">
                <td colspan="9" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">
                      ¿Eliminar <strong>{{ item.name }}</strong>? Esta acción es permanente.
                    </span>
                    <div class="ms-auto d-flex gap-2">
                      <button
                        class="btn btn-sm btn-danger"
                        @click="executeDelete(item)"
                        :disabled="actionLoading"
                      >
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">
                        Cancelar
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
              <!-- Fila normal -->
              <tr v-else>
                <td class="px-4">
                  <div class="d-flex align-items-center">
                    <!-- Thumbnail / icono fallback -->
                    <div
                      class="rounded-3 bg-light d-flex align-items-center justify-content-center me-3 flex-shrink-0"
                      style="width: 45px; height: 45px;"
                    >
                      <img
                        v-if="item.images && item.images.length"
                        :src="item.images.find(img => img.is_primary)?.image || item.images[0].image"
                        class="rounded-3"
                        style="width: 100%; height: 100%; object-fit: cover;"
                        :alt="item.name"
                      />
                      <i v-else class="bi bi-tools text-muted"></i>
                    </div>
                    <div class="flex-grow-1">
                      <InlineTextEditor
                        :model-value="item.name"
                        :on-save="(value) => handleSave(item, { name: value })"
                      />
                      <span class="badge bg-secondary-subtle text-secondary rounded-pill smaller mt-1">
                        {{ item.variants?.length || 0 }} variante(s)
                      </span>
                    </div>
                  </div>
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="item.description"
                    :on-save="(value) => handleSave(item, { description: value })"
                  >
                    <template #default="{ value }">
                      <span class="editable-value text-truncate d-inline-block" style="max-width: 160px;">
                        {{ value || 'Sin descripción' }}
                      </span>
                    </template>
                  </InlineTextEditor>
                </td>
                <td>
                  <InlineSelectEditor
                    :model-value="item.category_uuid"
                    :options="categoryOptions"
                    placeholder="-- Sin categoría --"
                    :on-save="(value) => handleSave(item, { category: value })"
                  />
                </td>
                <td>
                  <InlineSelectEditor
                    :model-value="item.level_uuid"
                    :options="levelOptions"
                    placeholder="-- Sin nivel --"
                    :on-save="(value) => handleSave(item, { level: value })"
                  />
                </td>
                <td>
                  <InlineTextEditor
                    v-if="defaultVariant(item)?.pricing_strategy === 'FIXED'"
                    type="number"
                    :model-value="defaultVariant(item)?.fixed_price"
                    :on-save="(value) => handleVariantSave(item, { fixed_price: value })"
                  >
                    <template #default="{ value }">
                      <span class="editable-value fw-semibold">{{ formatCurrency(value) }}</span>
                    </template>
                  </InlineTextEditor>
                  <span v-else-if="defaultVariant(item)" class="badge bg-light text-secondary border" title="Calculado según horas y complejidad">
                    {{ formatCurrency(defaultVariant(item)?.calculated_price) }}
                  </span>
                  <span v-else class="text-muted small">Sin variante</span>
                </td>
                <td>
                  <InlineTextEditor
                    v-if="defaultVariant(item)"
                    type="number"
                    :model-value="defaultVariant(item)?.estimated_hours"
                    :on-save="(value) => handleVariantSave(item, { estimated_hours: value })"
                  >
                    <template #default="{ value }">
                      <span class="editable-value">{{ value }} h</span>
                    </template>
                  </InlineTextEditor>
                  <span v-else class="text-muted small">N/A</span>
                </td>
                <td>
                  <InlineTextEditor
                    v-if="defaultVariant(item)"
                    type="number"
                    :model-value="defaultVariant(item)?.complexity_factor"
                    :on-save="(value) => handleVariantSave(item, { complexity_factor: value })"
                  />
                  <span v-else class="text-muted small">N/A</span>
                </td>
                <td>
                  <div class="d-flex flex-column gap-1 align-items-center">
                    <div class="d-flex align-items-center gap-1" title="Activo">
                      <i class="bi bi-power small text-muted"></i>
                      <InlineSwitch
                        :model-value="item.is_active"
                        :on-save="(value) => handleSave(item, { is_active: value })"
                      />
                    </div>
                    <div class="d-flex align-items-center gap-1" title="Destacado">
                      <i class="bi bi-star small text-muted"></i>
                      <InlineSwitch
                        :model-value="item.is_featured"
                        :on-save="(value) => handleSave(item, { is_featured: value })"
                      />
                    </div>
                    <div class="d-flex align-items-center gap-1" title="Comprable">
                      <i class="bi bi-cart small text-muted"></i>
                      <InlineSwitch
                        :model-value="item.is_purchasable"
                        :on-save="(value) => handleSave(item, { is_purchasable: value })"
                      />
                    </div>
                  </div>
                </td>
                <td class="text-end px-4">
                  <TableRowActions
                    :item="item"
                    :actions="rowActions"
                    @edit="openEdit"
                    @detail="openDetailPanel"
                    @variants="openVariantsPanel"
                    @duplicate="handleDuplicate"
                    @delete="pendingDelete = $event"
                  />
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
          <button
            class="btn btn-sm btn-light border"
            :disabled="!prevPage || loading"
            @click="loadPage(prevPage)"
          >
            <i class="bi bi-chevron-left"></i>
          </button>
          <button
            class="btn btn-sm btn-light border"
            :disabled="!nextPage || loading"
            @click="loadPage(nextPage)"
          >
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Offcanvas Crear/Editar -->
    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nuevo Servicio' : 'Editar Servicio'"
      :subtitle="mode === 'create' ? 'Completa los datos del servicio técnico' : `Modificando: ${selected?.name}`"
      width="820px"
    >
      <ServiceForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>

    <!-- Offcanvas Detalle -->
    <SintelOffcanvas
      v-model="showDetail"
      :title="detailItem?.name || 'Detalle del Servicio'"
      width="580px"
    >
      <ServiceDetail v-if="detailItem" :service="detailItem" />
    </SintelOffcanvas>

    <!-- Offcanvas Administrar variantes -->
    <SintelOffcanvas
      v-model="showVariantsPanel"
      :title="variantsServiceItem ? `Variantes de ${variantsServiceItem.name}` : 'Variantes'"
      width="720px"
    >
      <ServiceVariantsPanel v-if="variantsServiceItem" :service="variantsServiceItem" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, reactive } from 'vue';
import { storeToRefs } from 'pinia';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useTechnicalServicesCatalogStore } from '@/store/technicalServicesAdmin/catalog';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import ServiceDetail from './ServiceDetail.vue';
import ServiceForm from './ServiceForm.vue';
import ServiceVariantsPanel from './ServiceVariantsPanel.vue';
import InlineTextEditor from './InlineTextEditor.vue';
import InlineSelectEditor from './InlineSelectEditor.vue';
import InlineSwitch from './InlineSwitch.vue';
import TableRowActions from './TableRowActions.vue';

const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const store = useTechnicalServicesStore();
const catalogStore = useTechnicalServicesCatalogStore();
const { services: items, loading, actionLoading } = storeToRefs(store);
const { categories, levels } = storeToRefs(catalogStore);

// ── Detalle ──────────────────────────────────────────────────────────────────
const showDetail = ref(false);
const detailItem = ref(null);
const openDetailPanel = (item) => { detailItem.value = item; showDetail.value = true; };

// ── Variantes ────────────────────────────────────────────────────────────────
const showVariantsPanel = ref(false);
const variantsServiceItem = ref(null);
const openVariantsPanel = (item) => { variantsServiceItem.value = item; showVariantsPanel.value = true; };

// ── Estado ───────────────────────────────────────────────────────────────────
const search      = ref('');
const totalCount  = ref(0);
const nextPage    = ref(null);
const prevPage    = ref(null);
const pendingDelete = ref(null);

const filters = reactive({ category: '', level: '', is_featured: false });

// ── Edición inline ───────────────────────────────────────────────────────────
const categoryOptions = computed(() => categories.value.map((c) => ({ value: c.uuid, text: c.name })));
const levelOptions = computed(() => levels.value.map((l) => ({ value: l.uuid, text: l.name })));

const defaultVariant = (item) =>
  item.variants?.find((v) => v.is_default) || item.variants?.[0] || null;

const handleSave = async (item, payload) => {
  const { ok, error } = await store.updateService(item.uuid, payload);
  if (ok) {
    toast.success(`Servicio "${item.name}" actualizado.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    await loadPage();
    throw new Error(error);
  }
};

const handleVariantSave = async (item, payload) => {
  const variant = defaultVariant(item);
  if (!variant) return;
  const { ok, error } = await store.updateVariant(variant.uuid, item.uuid, payload);
  if (ok) {
    toast.success(`Variante de "${item.name}" actualizada.`);
    // updateVariant solo refresca store.variants, no el array anidado
    // services[].variants — se recarga la pagina para reflejar el cambio.
    await loadPage();
  } else {
    toast.error(error || 'Error al actualizar variante.');
    throw new Error(error);
  }
};

const handleDuplicate = async (item) => {
  const { ok, error } = await store.duplicateService(item.uuid);
  if (ok) {
    toast.success(`Servicio duplicado como borrador.`);
  } else {
    toast.error(error || 'Error al duplicar.');
  }
};

const rowActions = [
  { key: 'edit', label: 'Editar', icon: 'bi bi-pencil' },
  { key: 'detail', label: 'Ver detalle', icon: 'bi bi-eye' },
  { key: 'variants', label: 'Administrar variantes', icon: 'bi bi-list-ul' },
  { key: 'duplicate', label: 'Duplicar', icon: 'bi bi-copy' },
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

// ── Filtros (dashboard para categorías; público para niveles) ─────────────────
async function loadFilters() {
  try {
    await Promise.all([
      catalogStore.fetchCategories(),
      catalogStore.fetchLevels(),
    ]);
  } catch (err) {
    console.error('Error cargando filtros:', err);
  }
}

// ── Carga de datos ────────────────────────────────────────────────────────────
async function loadPage(url = null) {
  try {
    let params = {};
    if (url) {
      params = getParamsFromUrl(url);
    } else {
      if (search.value)         params.search = search.value;
      if (filters.category)     params.category__slug = filters.category;
      if (filters.level)        params.level__slug = filters.level;
      if (filters.is_featured)  params.is_featured = 'true';
    }

    const data = await store.fetchServices(params);
    if (data) {
      totalCount.value = data.count !== undefined ? data.count : data.length;
      nextPage.value   = data.next     ? extractPath(data.next)     : null;
      prevPage.value   = data.previous ? extractPath(data.previous) : null;
    }
  } catch (err) {
    toast.error('Error cargando los servicios.');
  }
}

function getParamsFromUrl(urlOrPath) {
  if (!urlOrPath) return {};
  const params = {};
  const queryString = urlOrPath.includes('?') ? urlOrPath.split('?')[1] : urlOrPath;
  const searchParams = new URLSearchParams(queryString);
  for (const [key, value] of searchParams.entries()) {
    params[key] = value;
  }
  return params;
}

function extractPath(fullUrl) {
  const match = fullUrl?.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

// ── Eliminación ───────────────────────────────────────────────────────────────
async function executeDelete(item) {
  const res = await store.deleteService(item.uuid);
  if (res.ok) {
    toast.success(`Servicio "${item.name}" eliminado`);
    await loadPage();
  } else {
    toast.error(res.error || 'No se pudo eliminar el servicio');
  }
  pendingDelete.value = null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatCurrency(value) {
  if (!value) return 'N/A';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(value);
}

// ── Eventos ───────────────────────────────────────────────────────────────────
const onFormSuccess = () => { close(); loadFilters(); loadPage(); };

let debounceTimer = null;
watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadPage(), 400);
});

onMounted(() => { loadFilters(); loadPage(); });
</script>

<style scoped>
.smaller { font-size: 0.75rem; }
</style>
