<template>
  <div class="shop-catalog">

    <!-- ── Hero premium ─────────────────────────────────────────────────────── -->
    <section class="catalog-hero">
      <div class="ch-glow ch-glow-1"></div>
      <div class="ch-glow ch-glow-2"></div>
      <div class="container-xl">
        <div class="ch-inner">
          <!-- Left: breadcrumb + title -->
          <div class="ch-left">
            <nav class="ch-breadcrumb" aria-label="breadcrumb">
              <RouterLink to="/" class="ch-bc-link">Inicio</RouterLink>
              <span class="ch-bc-sep">/</span>
              <span class="ch-bc-current">Tienda</span>
            </nav>
            <div class="d-flex align-items-center gap-3 mt-1">
              <h1 class="ch-title">Tienda</h1>
              <span v-if="totalCount && !loading" class="ch-count-badge">
                {{ totalCount.toLocaleString('es-CO') }} productos
              </span>
            </div>
            <p class="ch-sub">Encuentra el equipo que necesitas al mejor precio</p>
          </div>

          <!-- Right: search desktop -->
          <div class="ch-search-wrap d-none d-lg-flex">
            <i class="bi bi-search ch-search-icon"></i>
            <input
              v-model="filters.search"
              type="text"
              class="ch-search-input"
              placeholder="Buscar productos..."
              @input="onSearchInput"
            >
          </div>
        </div>
      </div>
    </section>

    <div id="shop-marketplace" class="container-xl py-4">

      <!-- ── Toolbar ─────────────────────────────────────────────────────────── -->
      <div class="toolbar mb-4">
        <!-- Search mobile -->
        <div class="tb-search d-lg-none">
          <i class="bi bi-search tb-search-icon"></i>
          <input
            v-model="filters.search"
            type="text"
            class="tb-search-input"
            placeholder="Buscar..."
            @input="onSearchInput"
          >
        </div>

        <div class="tb-right">
          <!-- Result count desktop -->
          <span v-if="totalCount && !loading" class="tb-count d-none d-lg-block">
            {{ totalCount.toLocaleString('es-CO') }} resultados
          </span>

          <!-- Sort -->
          <div class="tb-select-wrap">
            <i class="bi bi-sort-down tb-select-icon"></i>
            <select v-model="filters.ordering" class="tb-select" @change="fetchProducts">
              <option value="">Relevancia</option>
              <option value="name">Nombre A–Z</option>
              <option value="-name">Nombre Z–A</option>
              <option value="price">Precio menor</option>
              <option value="-price">Precio mayor</option>
            </select>
          </div>

          <!-- View toggle -->
          <div class="tb-view-toggle">
            <button
              class="tb-view-btn"
              :class="{ 'tb-view-btn-active': viewMode === 'grid' }"
              @click="viewMode = 'grid'"
              title="Vista cuadricula"
            >
              <i class="bi bi-grid-3x3-gap"></i>
            </button>
            <button
              class="tb-view-btn"
              :class="{ 'tb-view-btn-active': viewMode === 'list' }"
              @click="viewMode = 'list'"
              title="Vista lista"
            >
              <i class="bi bi-list-ul"></i>
            </button>
          </div>
        </div>
      </div>

      <div class="d-flex gap-4">

        <!-- ── Sidebar filtros ───────────────────────────────────────────────── -->
        <aside class="filter-aside d-none d-lg-block">
          <FilterPanel
            :categories="categories"
            :brands="brands"
            :show-price="true"
            :filters="filterState"
            @change="onFilterChange"
            @reset="onFilterReset"
          />
        </aside>

        <!-- ── Área de productos ─────────────────────────────────────────────── -->
        <div class="flex-grow-1 min-w-0">

          <!-- Loading skeleton -->
          <div v-if="loading" class="row g-3">
            <div
              v-for="i in 8"
              :key="i"
              :class="viewMode === 'list' ? 'col-12' : 'col-6 col-md-4 col-xl-3'"
            >
              <div class="sk-card" :class="viewMode === 'list' ? 'sk-card-list' : 'sk-card-grid'">
                <div class="sk-img shimmer"></div>
                <div class="sk-body">
                  <div class="sk-line shimmer sk-line-sm"></div>
                  <div class="sk-line shimmer sk-line-lg"></div>
                  <div class="sk-line shimmer sk-line-md mt-2"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Sin resultados -->
          <div v-else-if="products.length === 0" class="empty-state">
            <div class="es-icon-wrap">
              <i class="bi bi-search es-icon"></i>
            </div>
            <h3 class="es-title">Sin resultados</h3>
            <p class="es-sub">No encontramos productos con estos filtros.<br>Prueba con otros criterios.</p>
            <button class="es-btn" @click="resetFilters">
              <i class="bi bi-arrow-counterclockwise me-2"></i>Limpiar filtros
            </button>
          </div>

          <!-- Vista cuadricula -->
          <div v-else-if="viewMode === 'grid'" class="row g-3">
            <div
              v-for="product in products"
              :key="product.uuid"
              class="col-6 col-md-4 col-xl-3"
            >
              <ItemCard
                :item="product"
                type="product"
                @view="goToDetail"
                @add-to-cart="addToCart"
              />
            </div>
          </div>

          <!-- Vista lista -->
          <div v-else class="d-flex flex-column gap-2">
            <ProductHorizontalCard
              v-for="product in products"
              :key="product.uuid"
              :product="product"
              @view="goToDetail"
              @add-to-cart="addToCart"
            />
          </div>

          <!-- Paginación pill -->
          <div v-if="totalPages > 1" class="pagination-wrap">
            <button
              class="pg-btn pg-arrow"
              :disabled="currentPage === 1"
              @click="changePage(currentPage - 1)"
            >
              <i class="bi bi-chevron-left"></i>
            </button>

            <button
              v-for="p in visiblePages"
              :key="p"
              class="pg-btn"
              :class="{ 'pg-btn-active': p === currentPage }"
              @click="changePage(p)"
            >
              {{ p }}
            </button>

            <button
              class="pg-btn pg-arrow"
              :disabled="currentPage === totalPages"
              @click="changePage(currentPage + 1)"
            >
              <i class="bi bi-chevron-right"></i>
            </button>
          </div>

        </div>
      </div>
    </div>

    <!-- ── Filter FAB mobile ─────────────────────────────────────────────────── -->
    <button class="filter-fab d-lg-none" @click="showFilterMobile = true">
      <i class="bi bi-sliders2"></i>
      <span class="fab-label">Filtros</span>
      <span v-if="activeFilterCount > 0" class="fab-badge">{{ activeFilterCount }}</span>
    </button>

    <!-- ── Mobile offcanvas ──────────────────────────────────────────────────── -->
    <div
      v-if="showFilterMobile"
      class="offcanvas-backdrop fade show"
      @click="showFilterMobile = false"
    ></div>

    <div
      class="offcanvas offcanvas-start"
      :class="{ show: showFilterMobile }"
      style="visibility:visible; max-width:290px"
    >
      <div class="offcanvas-header mob-oc-header">
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-sliders2 text-primary"></i>
          <h6 class="mb-0 fw-bold">Filtros</h6>
        </div>
        <button class="btn-close" @click="showFilterMobile = false"></button>
      </div>
      <div class="offcanvas-body p-0">
        <FilterPanel
          :categories="categories"
          :brands="brands"
          :show-price="true"
          :filters="filterState"
          @change="(f) => { onFilterChange(f); showFilterMobile = false; }"
          @reset="() => { onFilterReset(); showFilterMobile = false; }"
        />
      </div>
    </div>

    <!-- ── Busquedas relacionadas ────────────────────────────────────────────── -->
    <section v-if="categories.length" class="related-search-section">
      <div class="container-xl">
        <div class="section-head compact">
          <div>
            <span class="section-kicker">Explora tambien</span>
            <h2>Busquedas relacionadas</h2>
          </div>
        </div>
        <div class="related-search-cloud">
          <button
            v-for="cat in categories"
            :key="cat.slug"
            type="button"
            class="related-search-chip"
            @click="searchByCategory(cat)"
          >
            <i class="bi bi-search"></i>
            {{ cat.name }}
          </button>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { shopService } from '@/services/shop/shopService';
import { useToast } from '@/composables/useToast';
import { useCartStore } from '@/store/cart';
import { useAuthStore } from '@/store/auth';
import ItemCard from '@/components/customer/ui/ItemCard.vue';
import FilterPanel from '@/components/customer/ui/FilterPanel.vue';
import ProductHorizontalCard from '@/components/shop/ProductHorizontalCard.vue';

const toast = useToast();
const cartStore = useCartStore();
const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const products = ref([]);
const categories = ref([]);
const brands = ref([]);
const totalCount = ref(0);
const totalPages = ref(0);
const currentPage = ref(1);
const showFilterMobile = ref(false);
const viewMode = ref('list');

const filters = reactive({
  search: route.query.q || '',
  ordering: '',
});

const filterState = reactive({
  categorySlug: route.query.categoria || '',
  brandSlug: route.query.marca || '',
  minPrice: '',
  maxPrice: '',
  isFeatured: null,
});

const activeFilterCount = computed(() => {
  let c = 0;
  if (filterState.categorySlug) c++;
  if (filterState.brandSlug) c++;
  if (filterState.minPrice) c++;
  if (filterState.maxPrice) c++;
  return c;
});

const visiblePages = computed(() => {
  const pages = [];
  const start = Math.max(1, currentPage.value - 2);
  const end = Math.min(totalPages.value, currentPage.value + 2);
  for (let i = start; i <= end; i++) pages.push(i);
  return pages;
});

async function fetchProducts() {
  loading.value = true;
  try {
    const params = {
      page: currentPage.value,
      search: filters.search || undefined,
      ordering: filters.ordering || undefined,
      is_active: true,
    };
    if (filterState.categorySlug) params['category__slug'] = filterState.categorySlug;
    if (filterState.brandSlug) params['brand__slug'] = filterState.brandSlug;
    if (filterState.minPrice) params['price__gte'] = filterState.minPrice;
    if (filterState.maxPrice) params['price__lte'] = filterState.maxPrice;
    if (filterState.isFeatured) params['is_featured'] = true;

    const data = await shopService.list(params);
    products.value = data.results || data;
    totalCount.value = data.count || products.value.length;
    totalPages.value = Math.ceil(totalCount.value / 24);
  } catch {
    toast.error('Error al cargar el catalogo');
  } finally {
    loading.value = false;
  }
}

async function fetchFilters() {
  const [catData, brandData] = await Promise.all([
    shopService.categories().catch(() => ({ results: [] })),
    shopService.brands().catch(() => ({ results: [] })),
  ]);
  categories.value = catData.results || catData || [];
  brands.value = brandData.results || brandData || [];
}

let searchTimer = null;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { currentPage.value = 1; fetchProducts(); }, 400);
}

function onFilterChange(f) {
  Object.assign(filterState, f);
  currentPage.value = 1;
  fetchProducts();
}

function onFilterReset() {
  Object.assign(filterState, { categorySlug: '', brandSlug: '', minPrice: '', maxPrice: '', isFeatured: null });
  filters.search = '';
  currentPage.value = 1;
  fetchProducts();
}

function resetFilters() { onFilterReset(); }

function searchByCategory(cat) {
  onFilterChange({ categorySlug: cat.slug, brandSlug: filterState.brandSlug });
  document.getElementById('shop-marketplace')?.scrollIntoView({ behavior: 'smooth' });
}

function changePage(p) {
  if (p >= 1 && p <= totalPages.value) {
    currentPage.value = p;
    fetchProducts();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function goToDetail(product) {
  router.push({ name: 'product-detail', params: { uuid: product.uuid } });
}

async function addToCart(product) {
  if (!authStore.isAuthenticated) {
    toast.info('Inicia sesion para agregar al carrito');
    router.push('/login');
    return;
  }
  const variant = product.variants?.find(v => v.is_default) || product.variants?.[0];
  if (!variant) { toast.error('Sin variante disponible'); return; }
  try {
    await cartStore.addItem(variant.uuid, 1);
    toast.success(`"${product.name}" agregado al carrito`);
  } catch {
    toast.error('No se pudo agregar al carrito');
  }
}

watch(() => route.query.q, (q) => {
  if (q !== undefined) {
    filters.search = q || '';
    currentPage.value = 1;
    fetchProducts();
  }
});

onMounted(() => {
  fetchFilters();
  fetchProducts();
});
</script>

<style scoped>
/* ── Catalog hero ───────────────────────────────────────────────────────────── */
.catalog-hero {
  position: relative;
  background: linear-gradient(135deg, #0d1526 0%, #1e3a8a 55%, #2563eb 100%);
  overflow: hidden;
  padding: 2.5rem 0 2rem;
}
.ch-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  opacity: 0.35;
}
.ch-glow-1 {
  width: 420px; height: 420px;
  background: #3b82f6;
  top: -120px; right: -80px;
}
.ch-glow-2 {
  width: 300px; height: 300px;
  background: #06b6d4;
  bottom: -100px; left: 5%;
}
.ch-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  flex-wrap: wrap;
}
.ch-left { flex: 1; min-width: 0; }
.ch-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  margin-bottom: 0.35rem;
}
.ch-bc-link {
  color: rgba(255,255,255,.65);
  text-decoration: none;
  transition: color 0.18s;
}
.ch-bc-link:hover { color: #fff; }
.ch-bc-sep { color: rgba(255,255,255,.3); font-size: 0.7rem; }
.ch-bc-current { color: rgba(255,255,255,.8); }

.ch-title {
  font-size: clamp(1.7rem, 4vw, 2.5rem);
  font-weight: 900;
  color: #fff;
  letter-spacing: -0.03em;
  margin: 0;
  line-height: 1;
}
.ch-count-badge {
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(255,255,255,.12);
  backdrop-filter: blur(8px);
  color: rgba(255,255,255,.9);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  white-space: nowrap;
}
.ch-sub {
  font-size: 0.85rem;
  color: rgba(255,255,255,.55);
  margin: 0.5rem 0 0;
}

/* Search desktop in hero */
.ch-search-wrap {
  align-items: center;
  background: rgba(255,255,255,.1);
  backdrop-filter: blur(12px);
  border: 1.5px solid rgba(255,255,255,.2);
  border-radius: 14px;
  padding: 0.55rem 1rem;
  gap: 0.6rem;
  min-width: 280px;
  flex-shrink: 0;
}
.ch-search-icon { color: rgba(255,255,255,.55); font-size: 0.9rem; }
.ch-search-input {
  background: none;
  border: none;
  outline: none;
  color: #fff;
  font-size: 0.88rem;
  width: 100%;
}
.ch-search-input::placeholder { color: rgba(255,255,255,.4); }

/* ── Toolbar ────────────────────────────────────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
/* mobile search in toolbar */
.tb-search {
  flex: 1;
  max-width: 300px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.45rem 0.85rem;
}
.tb-search-icon { color: #94a3b8; font-size: 0.85rem; }
.tb-search-input {
  border: none;
  outline: none;
  background: none;
  font-size: 0.85rem;
  color: #0f172a;
  width: 100%;
}
.tb-search-input::placeholder { color: #94a3b8; }

.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.tb-count {
  font-size: 0.78rem;
  color: #94a3b8;
  white-space: nowrap;
}

/* Sort select */
.tb-select-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.tb-select-icon {
  position: absolute;
  left: 0.7rem;
  color: #64748b;
  font-size: 0.85rem;
  pointer-events: none;
}
.tb-select {
  appearance: none;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.42rem 1.6rem 0.42rem 2.1rem;
  font-size: 0.82rem;
  color: #0f172a;
  cursor: pointer;
  outline: none;
  transition: border-color 0.18s;
}
.tb-select:focus { border-color: #2563eb; }

/* View toggle */
.tb-view-toggle {
  display: flex;
  background: #f1f5f9;
  border-radius: 10px;
  padding: 2px;
  gap: 2px;
}
.tb-view-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #64748b;
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.18s, color 0.18s;
}
.tb-view-btn-active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}

/* ── Sidebar ────────────────────────────────────────────────────────────────── */
.filter-aside {
  width: 230px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid rgba(0,0,0,.07);
  border-radius: 20px;
  position: sticky;
  top: 90px;
  align-self: flex-start;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,.04);
}

/* ── Skeleton ───────────────────────────────────────────────────────────────── */
.shimmer {
  background: linear-gradient(90deg, #f0f4f8 25%, #e8ecf0 37%, #f0f4f8 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}
.sk-card {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid #f1f5f9;
}
.sk-card-grid .sk-img { height: 200px; }
.sk-card-list {
  display: flex;
  gap: 0;
}
.sk-card-list .sk-img {
  width: 140px;
  height: 120px;
  flex-shrink: 0;
  border-radius: 0;
}
.sk-body {
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex: 1;
}
.sk-line {
  height: 12px;
  border-radius: 6px;
}
.sk-line-sm { width: 45%; }
.sk-line-lg { width: 85%; height: 15px; }
.sk-line-md { width: 60%; }

/* ── Empty state ────────────────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 4rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.es-icon-wrap {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}
.es-icon { font-size: 2rem; color: #2563eb; }
.es-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.5rem;
}
.es-sub {
  font-size: 0.88rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 1.5rem;
}
.es-btn {
  display: inline-flex;
  align-items: center;
  font-size: 0.88rem;
  font-weight: 600;
  color: #2563eb;
  background: rgba(37,99,235,.08);
  border: 1.5px solid rgba(37,99,235,.22);
  border-radius: 9999px;
  padding: 0.55rem 1.4rem;
  cursor: pointer;
  transition: background 0.2s;
}
.es-btn:hover { background: rgba(37,99,235,.15); }

/* ── Pagination ─────────────────────────────────────────────────────────────── */
.pagination-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.4rem;
  margin-top: 2.5rem;
  padding-bottom: 1rem;
}
.pg-btn {
  width: 38px;
  height: 38px;
  border-radius: 9999px;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  color: #374151;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.18s, border-color 0.18s, color 0.18s;
}
.pg-btn:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #2563eb;
}
.pg-btn-active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
  box-shadow: 0 2px 10px rgba(37,99,235,.3);
}
.pg-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.pg-arrow { font-size: 0.75rem; }

/* ── Filter FAB ─────────────────────────────────────────────────────────────── */
.filter-fab {
  position: fixed;
  bottom: 80px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0 1rem;
  height: 46px;
  border-radius: 9999px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  border: none;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 4px 18px rgba(37,99,235,.45);
  z-index: 99;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.filter-fab:hover { transform: translateY(-2px); box-shadow: 0 6px 22px rgba(37,99,235,.5); }
.fab-label { font-size: 0.82rem; }
.fab-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #ef4444;
  color: #fff;
  font-size: 0.62rem;
  font-weight: 800;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
}

/* ── Busquedas relacionadas ─────────────────────────────────────────────────── */
.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.8rem 0 0.9rem;
}
.section-head.compact { margin-top: 0; }
.section-head h2 {
  color: #0f172a;
  font-weight: 850;
  letter-spacing: 0;
  margin: 0;
  font-size: 1.35rem;
}
.section-kicker {
  display: block;
  color: #1d4ed8;
  font-size: 0.72rem;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: 0.25rem;
}
.related-search-section {
  padding: 0.5rem 0 2.5rem;
}
.related-search-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.9rem;
}
.related-search-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 999px;
  padding: 0.5rem 1rem;
  font-size: 0.82rem;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.18s, border-color 0.18s, transform 0.18s;
}
.related-search-chip i { font-size: 0.78rem; color: #2563eb; }
.related-search-chip:hover {
  background: #dbeafe;
  border-color: #93c5fd;
  transform: translateY(-1px);
}

/* ── Mobile offcanvas header ────────────────────────────────────────────────── */
.mob-oc-header {
  background: linear-gradient(135deg, #f8fafc, #eff6ff);
  border-bottom: 1px solid #e2e8f0;
}

/* ── Utilities ──────────────────────────────────────────────────────────────── */
.min-w-0 { min-width: 0; }
</style>
