<template>
  <div class="product-list-module">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Productos</h4>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-primary" @click="openCreate">
          <i class="bi bi-plus-lg me-1"></i> Nuevo Producto
        </button>
      </div>
    </div>

    <!-- Filtros y Búsqueda -->
    <div class="card shadow-sm border-0 mb-4">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-6">
            <div class="input-group">
              <span class="input-group-text bg-white border-end-0">
                <i class="bi bi-search text-muted"></i>
              </span>
              <input 
                v-model="filters.search" 
                type="text" 
                class="form-control border-start-0 ps-0" 
                placeholder="Buscar por nombre, SKU o descripción..."
                @input="onSearch"
              >
            </div>
          </div>
          <div class="col-md-3">
            <select v-model="filters.is_active" class="form-select" @change="fetchProducts">
              <option :value="null">Todos los estados</option>
              <option :value="true">Activos</option>
              <option :value="false">Inactivos</option>
            </select>
          </div>
          <div class="col-md-3">
            <select v-model="filters.is_featured" class="form-select" @change="fetchProducts">
              <option :value="null">Destacado: Todos</option>
              <option :value="true">Solo Destacados</option>
              <option :value="false">No Destacados</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabla de Productos -->
    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Producto</th>
              <th>Categoría</th>
              <th>Precio (V. Defecto)</th>
              <th>Stock Total</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando catálogo...</div>
              </td>
            </tr>
            <tr v-else-if="products.length === 0">
              <td colspan="6" class="text-center py-5 text-muted">
                No se encontraron productos con estos criterios.
              </td>
            </tr>
            <template v-for="product in products" :key="product.uuid">
              <!-- Confirmación Inline -->
              <tr v-if="pendingDelete?.uuid === product.uuid" class="bg-danger-subtle">
                <td colspan="6" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">
                      ¿Seguro que deseas desactivar <strong>{{ product.name }}</strong>? Esta acción es reversible.
                    </span>
                    <div class="ms-auto d-flex gap-2">
                      <button 
                        class="btn btn-sm btn-danger" 
                        @click="executeDelete(product)"
                        :disabled="actionLoading"
                      >
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <!-- Fila Normal -->
              <tr v-else>
                <td>
                  <div class="fw-bold">{{ product.name }}</div>
                  <div class="text-muted smaller">SKU: {{ product.sku || 'Sin SKU' }}</div>
                </td>
                <td>
                  <select
                    v-model="product.category_uuid"
                    class="form-select form-select-sm inline-control"
                    :disabled="savingCell === `${product.uuid}:category`"
                    @change="patchProductInline(product, { category: product.category_uuid }, 'category')"
                  >
                    <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
                  </select>
                </td>
                <td>
                  <div v-if="product.variants && product.variants.length" class="input-group input-group-sm inline-money">
                    <span class="input-group-text">$</span>
                    <input
                      v-model.number="product._inline_price"
                      type="number"
                      min="0.01"
                      step="0.01"
                      class="form-control"
                      :disabled="savingCell === `${product.uuid}:price`"
                      @blur="patchProductInline(product, { price: product._inline_price }, 'price')"
                      @keydown.enter.prevent="$event.target.blur()"
                    >
                  </div>
                  <span v-else class="text-muted small italic">Sin variantes</span>
                </td>
                <td>
                  <input
                    v-model.number="product._inline_stock"
                    type="number"
                    min="0"
                    class="form-control form-control-sm inline-stock"
                    :disabled="savingCell === `${product.uuid}:stock`"
                    @blur="patchProductInline(product, { stock: product._inline_stock }, 'stock')"
                    @keydown.enter.prevent="$event.target.blur()"
                  >
                </td>
                <td>
                  <div class="d-flex align-items-center gap-3">
                    <div class="form-check form-switch m-0" title="Destacado">
                      <input
                        v-model="product.is_featured"
                        class="form-check-input"
                        type="checkbox"
                        :disabled="savingCell === `${product.uuid}:featured`"
                        @change="patchProductInline(product, { is_featured: product.is_featured }, 'featured')"
                      >
                    </div>
                    <div class="form-check form-switch m-0" title="Activo">
                      <input
                        v-model="product.is_active"
                        class="form-check-input"
                        type="checkbox"
                        :disabled="savingCell === `${product.uuid}:active`"
                        @change="patchProductInline(product, { is_active: product.is_active }, 'active')"
                      >
                    </div>
                  </div>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button type="button" class="btn btn-light border-end" @click="openEdit(product)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button type="button" class="btn btn-light" @click="pendingDelete = product" title="Desactivar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Paginación Simple -->
      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted smaller">
          Mostrando {{ products.length }} de {{ totalCount }} registros
        </span>
        <nav v-if="totalPages > 1">
          <ul class="pagination pagination-sm m-0">
            <li class="page-item" :class="{ disabled: !pagination.previous }">
              <button class="page-link" @click="changePage(currentPage - 1)">Ant.</button>
            </li>
            <li class="page-item" :class="{ disabled: !pagination.next }">
              <button class="page-link" @click="changePage(currentPage + 1)">Sig.</button>
            </li>
          </ul>
        </nav>
      </div>
    </div>

    <!-- Offcanvas para Crear/Editar -->
    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nuevo Producto' : 'Editar Producto'"
      :subtitle="mode === 'create' ? 'Completa los datos básicos del producto' : `Modificando: ${selected?.name}`"
      width="820px"
    >
      <ProductForm
        :item="selected"
        :mode="mode"
        @success="onFormSuccess"
        @cancel="close"
        @item-saved="fetchProducts"
      />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useShopAdminStore } from '@/store/shopAdmin';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import ProductForm from './ProductForm.vue';

const toast = useToast();
const { handleError } = useErrorHandler();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();
const store = useShopAdminStore();
const {
  products, productsTotalCount: totalCount, productsTotalPages: totalPages,
  productsPagination: pagination, productsLoading: loading,
  productCategories: categories,
  actionLoading,
} = storeToRefs(store);

const savingCell = ref('');
const currentPage = ref(1);
const pendingDelete = ref(null);

const filters = reactive({
  search: '',
  is_active: null,
  is_featured: null,
});

const decorateProduct = (product) => {
  const def = product.variants?.find(v => v.is_default) || product.variants?.[0];
  return {
    ...product,
    _inline_price: def ? Number(def.price) : null,
    _inline_stock: Number(product.stock || 0),
  };
};

const fetchProducts = async () => {
  await store.fetchProducts({
    page: currentPage.value,
    search: filters.search || undefined,
    is_active: filters.is_active !== null ? filters.is_active : undefined,
    is_featured: filters.is_featured !== null ? filters.is_featured : undefined,
  });
  products.value = products.value.map(decorateProduct);
};

const fetchCategories = () => store.fetchProductCategories();

const patchProductInline = async (product, payload, field) => {
  const key = `${product.uuid}:${field}`;
  savingCell.value = key;
  const res = await store.patchProductInline(product.uuid, payload);
  if (res.ok) {
    Object.assign(product, decorateProduct(res.data));
    toast.success('Producto actualizado');
  } else {
    handleError(res.error, 'No se pudo guardar el cambio');
    await fetchProducts();
  }
  savingCell.value = '';
};

const executeDelete = async (product) => {
  const res = await store.deleteProduct(product.uuid);
  if (res.ok) {
    toast.success(`Producto "${product.name}" eliminado`);
    await fetchProducts();
  } else {
    toast.error('No se pudo desactivar el producto');
  }
  pendingDelete.value = null;
};

const onFormSuccess = () => {
  close();
  fetchProducts();
};

const onSearch = () => {
  currentPage.value = 1;
  fetchProducts();
};

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    fetchProducts();
  }
};

onMounted(async () => {
  await Promise.all([fetchCategories(), fetchProducts()]);
});
</script>

<style scoped>
.smaller { font-size: 0.85rem; }
.bg-success-soft { background-color: rgba(25, 135, 84, 0.1); }
.bg-danger-soft { background-color: rgba(220, 53, 69, 0.1); }
.inline-control { min-width: 150px; }
.inline-money { width: 150px; }
.inline-stock { width: 96px; }
</style>
