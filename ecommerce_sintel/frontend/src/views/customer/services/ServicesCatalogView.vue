<template>
  <div class="services-catalog">

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
              <span class="ch-bc-current">Servicios</span>
            </nav>
            <div class="d-flex align-items-center gap-3 mt-1">
              <h1 class="ch-title">Servicios Tecnicos</h1>
              <span v-if="totalCount && !loading" class="ch-count-badge">
                {{ totalCount.toLocaleString('es-CO') }} servicios
              </span>
            </div>
            <p class="ch-sub">Compra soluciones profesionales con alcance, garantia y equipos certificados.</p>
            <div class="ch-actions">
              <a href="#services-marketplace" class="ch-cta-primary">
                <i class="bi bi-bag-check"></i>
                Comprar servicio
              </a>
              <RouterLink to="/registro-profesional" class="ch-cta-provider">
                <i class="bi bi-person-workspace"></i>
                Ofrecer servicios
              </RouterLink>
            </div>
            <div class="ch-trust-row">
              <span><i class="bi bi-shield-check"></i> Garantia incluida</span>
              <span><i class="bi bi-credit-card"></i> Pago seguro</span>
              <span><i class="bi bi-calendar-check"></i> Agenda flexible</span>
            </div>
          </div>

          <!-- Right: search desktop -->
          <div class="ch-search-wrap d-none d-lg-flex">
            <i class="bi bi-search ch-search-icon"></i>
            <input
              v-model="search"
              type="text"
              class="ch-search-input"
              placeholder="Buscar servicio tecnico..."
            >
            <button v-if="search" class="ch-search-clear" @click="clearSearch">
              <i class="bi bi-x"></i>
            </button>
          </div>
        </div>
      </div>
    </section>

    <section class="market-home">
      <div class="container-xl">
        <div class="mh-grid">
          <article
            v-for="category in marketplaceCategories"
            :key="category.title"
            class="mh-card"
          >
            <div class="mh-icon">
              <i :class="['bi', category.icon]"></i>
            </div>
            <div>
              <h2>{{ category.title }}</h2>
              <p>{{ category.copy }}</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <div id="services-marketplace" class="container-xl py-4">

      <!-- ── Toolbar ─────────────────────────────────────────────────────────── -->
      <div class="toolbar mb-4">
        <!-- Search mobile -->
        <div class="tb-search d-lg-none">
          <i class="bi bi-search tb-search-icon"></i>
          <input
            v-model="search"
            type="text"
            class="tb-search-input"
            placeholder="Buscar servicio..."
          >
          <button v-if="search" class="tb-search-clear" @click="clearSearch">
            <i class="bi bi-x"></i>
          </button>
        </div>

        <div class="tb-right">
          <!-- Result count desktop -->
          <span v-if="totalCount && !loading" class="tb-count d-none d-lg-block">
            {{ totalCount.toLocaleString('es-CO') }} servicios
          </span>

          <!-- Featured toggle -->
          <label class="tb-feat-toggle">
            <input v-model="filterFeatured" type="checkbox" @change="goPage(1)">
            <span class="tb-feat-track"></span>
            <span class="tb-feat-label d-none d-md-inline">Solo destacados</span>
          </label>

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
            :brands="levels"
            brand-label="Nivel"
            :show-price="false"
            :filters="filterState"
            @change="onFilterChange"
            @reset="onFilterReset"
          />
        </aside>

        <!-- ── Area de servicios ─────────────────────────────────────────────── -->
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
          <div v-else-if="services.length === 0" class="empty-state">
            <div class="es-icon-wrap">
              <i class="bi bi-tools es-icon"></i>
            </div>
            <h3 class="es-title">Sin servicios disponibles</h3>
            <p class="es-sub">No encontramos servicios con estos filtros.<br>Prueba con otros criterios.</p>
            <button class="es-btn" @click="onFilterReset">
              <i class="bi bi-arrow-counterclockwise me-2"></i>Limpiar filtros
            </button>
          </div>

          <!-- Vista cuadricula -->
          <div v-else-if="viewMode === 'grid'" class="row g-3">
            <div
              v-for="svc in services"
              :key="svc.uuid"
              class="col-6 col-md-4 col-xl-3"
            >
              <ServiceCard :service="svc" @view="goToDetail" @quote="goToQuote" />
            </div>
          </div>

          <!-- Vista lista -->
          <div v-else class="d-flex flex-column gap-2">
            <ServiceHorizontalCard
              v-for="svc in services"
              :key="svc.uuid"
              :service="svc"
              @view="goToDetail"
              @quote="goToQuote"
            />
          </div>

          <!-- Paginacion pill -->
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
          <i class="bi bi-sliders2" style="color:#d97706"></i>
          <h6 class="mb-0 fw-bold">Filtros</h6>
        </div>
        <button class="btn-close" @click="showFilterMobile = false"></button>
      </div>
      <div class="offcanvas-body p-0">
        <FilterPanel
          :categories="categories"
          :brands="levels"
          brand-label="Nivel"
          :show-price="false"
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
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { servicesService } from '@/services/technical_services/servicesService';
import { useToast } from '@/composables/useToast';
import ServiceCard from '@/components/customer/ui/ServiceCard.vue';
import FilterPanel from '@/components/customer/ui/FilterPanel.vue';
import ServiceHorizontalCard from '@/components/services/ServiceHorizontalCard.vue';

const toast  = useToast();
const router = useRouter();

const loading          = ref(true);
const services         = ref([]);
const categories       = ref([]);
const levels           = ref([]);
const totalCount       = ref(0);
const totalPages       = ref(0);
const currentPage      = ref(1);
const filterFeatured   = ref(false);
const showFilterMobile = ref(false);
const search           = ref('');
const viewMode         = ref('list');

const filterState = reactive({ categorySlug: '', brandSlug: '', minPrice: '', maxPrice: '', isFeatured: null });

const marketplaceCategories = [
  { icon: 'bi-camera-video', title: 'CCTV y seguridad', copy: 'Instalacion, puesta en marcha, analitica, mantenimiento y soporte.' },
  { icon: 'bi-router', title: 'Redes y conectividad', copy: 'Cableado, WiFi, switching, routing, segmentacion y pruebas certificadas.' },
  { icon: 'bi-door-open', title: 'Control de acceso', copy: 'Lectores, biometria, torniquetes, integracion y auditoria operativa.' },
  { icon: 'bi-hdd-network', title: 'Infraestructura TI', copy: 'Servidores, racks, UPS, respaldo, monitoreo y documentacion tecnica.' },
];

const industries = [
  { icon: 'bi-buildings', name: 'Empresas' },
  { icon: 'bi-hospital', name: 'Hospitales' },
  { icon: 'bi-bank', name: 'Bancos' },
  { icon: 'bi-house-gear', name: 'Conjuntos' },
  { icon: 'bi-building-check', name: 'Hoteles' },
];

const processSteps = ['Compra', 'Direccion', 'Fecha', 'Pago', 'Programacion', 'Visita', 'Pruebas', 'Garantia'];

const compatibleBrands = ['Hikvision', 'Dahua', 'Axis', 'Bosch', 'ZKTeco', 'Akuvox', 'Ubiquiti', 'Mikrotik', 'UniFi'];

const activeFilterCount = computed(() => {
  let c = 0;
  if (filterState.categorySlug) c++;
  if (filterState.brandSlug) c++;
  return c;
});

const visiblePages = computed(() => {
  const pages = [];
  const start = Math.max(1, currentPage.value - 2);
  const end   = Math.min(totalPages.value, currentPage.value + 2);
  for (let i = start; i <= end; i++) pages.push(i);
  return pages;
});

async function fetchServices() {
  loading.value = true;
  try {
    const params = { page: currentPage.value, is_active: true };
    if (filterState.categorySlug) params['category__slug'] = filterState.categorySlug;
    if (filterState.brandSlug)    params['level__slug']    = filterState.brandSlug;
    if (filterFeatured.value)     params['is_featured']    = true;
    if (search.value.trim())      params['search']         = search.value.trim();

    const data = await servicesService.list(params);
    services.value  = data.results || data || [];
    totalCount.value = data.count || services.value.length;
    totalPages.value = Math.ceil(totalCount.value / 25);
  } catch {
    toast.error('Error al cargar servicios');
  } finally {
    loading.value = false;
  }
}

async function fetchFilters() {
  const [catData, lvlData] = await Promise.all([
    servicesService.categories().catch(() => []),
    servicesService.levels().catch(() => []),
  ]);
  categories.value = catData.results || catData || [];
  levels.value     = lvlData.results || lvlData || [];
}

function onFilterChange(f) {
  Object.assign(filterState, f);
  goPage(1);
}

function onFilterReset() {
  Object.assign(filterState, { categorySlug: '', brandSlug: '', minPrice: '', maxPrice: '', isFeatured: null });
  filterFeatured.value = false;
  search.value = '';
  goPage(1);
}

function clearSearch() { search.value = ''; goPage(1); }

function searchByCategory(cat) {
  onFilterChange({ categorySlug: cat.slug, brandSlug: filterState.brandSlug });
  document.getElementById('services-marketplace')?.scrollIntoView({ behavior: 'smooth' });
}

function goPage(p) { currentPage.value = p; fetchServices(); }

function changePage(p) {
  if (p >= 1 && p <= totalPages.value) {
    currentPage.value = p;
    fetchServices();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function goToDetail(svc) {
  router.push({ name: 'service-detail', params: { uuid: svc.uuid } });
}

function goToQuote(svc) {
  router.push({ name: 'service-request', params: { uuid: svc.uuid } });
}

let debounceTimer = null;
watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => goPage(1), 380);
});

onMounted(() => { fetchFilters(); fetchServices(); });
</script>

<style scoped>
/* ── Catalog hero ───────────────────────────────────────────────────────────── */
.catalog-hero {
  position: relative;
  background: linear-gradient(135deg, #1c0a00 0%, #78350f 55%, #d97706 100%);
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
  background: #f59e0b;
  top: -120px; right: -80px;
}
.ch-glow-2 {
  width: 300px; height: 300px;
  background: #fbbf24;
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
  font-size: clamp(1.5rem, 3.5vw, 2.3rem);
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
.ch-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}
.ch-cta-primary,
.ch-cta-provider {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.1rem;
  border-radius: 9999px;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
  transition: background .15s ease, transform .15s ease;
}
.ch-cta-primary {
  background: #fff;
  color: #0f172a;
  border: 1.5px solid rgba(255,255,255,.7);
  box-shadow: 0 14px 30px rgba(15,23,42,.18);
}
.ch-cta-provider {
  background: rgba(255,255,255,.12);
  backdrop-filter: blur(8px);
  border: 1.5px solid rgba(255,255,255,.25);
  color: #fff;
}
.ch-cta-primary:hover {
  background: #f8fafc;
  color: #0f172a;
  transform: translateY(-1px);
}
.ch-cta-provider:hover {
  background: rgba(255,255,255,.2);
  color: #fff;
  transform: translateY(-1px);
}
.ch-trust-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1rem;
  color: rgba(255,255,255,.78);
  font-size: 0.76rem;
}
.ch-trust-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(15,23,42,.2);
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 999px;
  padding: 0.28rem 0.65rem;
}

/* ── Marketplace home ──────────────────────────────────────────────────────── */
.market-home {
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  border-bottom: 1px solid #e2e8f0;
  padding: 1.3rem 0 1.8rem;
}
.mh-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: -2.35rem;
  position: relative;
  z-index: 2;
}
.mh-card {
  min-height: 148px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  display: flex;
  gap: 0.85rem;
  box-shadow: 0 16px 34px rgba(15,23,42,.08);
}
.mh-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #ecfeff;
  color: #0e7490;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1.15rem;
}
.mh-card h2,
.section-head h2,
.technician-panel h2 {
  color: #0f172a;
  font-weight: 850;
  letter-spacing: 0;
  margin: 0;
}
.mh-card h2 {
  font-size: 0.98rem;
  line-height: 1.2;
}
.mh-card p,
.technician-panel p {
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.55;
  margin: 0.35rem 0 0;
}
.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.8rem 0 0.9rem;
}
.section-head.compact { margin-top: 0; }
.section-head h2 { font-size: 1.35rem; }
.section-kicker {
  display: block;
  color: #0f766e;
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: 0.25rem;
}
.section-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: #0f766e;
  text-decoration: none;
  font-size: 0.86rem;
  font-weight: 750;
  white-space: nowrap;
}
.industry-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.75rem;
}
.industry-card {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 58px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 14px;
  padding: 0.75rem;
  font-weight: 750;
  font-size: 0.86rem;
}
.industry-card i { font-size: 1.05rem; }
.market-split-section {
  padding: 1rem 0 2.5rem;
}
.market-split {
  display: grid;
  grid-template-columns: 1.45fr .9fr;
  gap: 1rem;
}
.process-panel,
.technician-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}
.process-line {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.6rem;
}
.process-step {
  min-height: 44px;
  border: 1px solid #dcfce7;
  background: #f0fdf4;
  color: #166534;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 0.78rem;
  font-weight: 760;
}
.tech-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
  margin-top: 0.9rem;
}
.tech-stats span {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.65rem;
  color: #475569;
  font-size: 0.73rem;
}
.tech-stats strong {
  display: block;
  color: #0f172a;
  font-size: 0.88rem;
}
.brand-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}
.brand-cloud span {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  border-radius: 999px;
  padding: 0.38rem 0.75rem;
  font-size: 0.78rem;
  font-weight: 700;
}

/* Search in hero */
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
.ch-search-icon { color: rgba(255,255,255,.55); font-size: 0.9rem; flex-shrink: 0; }
.ch-search-input {
  background: none;
  border: none;
  outline: none;
  color: #fff;
  font-size: 0.88rem;
  flex: 1;
  min-width: 0;
}
.ch-search-input::placeholder { color: rgba(255,255,255,.4); }
.ch-search-clear {
  background: none;
  border: none;
  color: rgba(255,255,255,.6);
  cursor: pointer;
  padding: 0;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
}
.ch-search-clear:hover { color: #fff; }

/* ── Toolbar ────────────────────────────────────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
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
.tb-search-icon { color: #94a3b8; font-size: 0.85rem; flex-shrink: 0; }
.tb-search-input {
  border: none;
  outline: none;
  background: none;
  font-size: 0.85rem;
  color: #0f172a;
  flex: 1;
  min-width: 0;
}
.tb-search-input::placeholder { color: #94a3b8; }
.tb-search-clear {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
}
.tb-search-clear:hover { color: #374151; }

.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.tb-count { font-size: 0.78rem; color: #94a3b8; white-space: nowrap; }

/* Featured toggle toolbar */
.tb-feat-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}
.tb-feat-toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.tb-feat-track {
  display: block;
  width: 34px;
  height: 20px;
  border-radius: 999px;
  background: #e2e8f0;
  position: relative;
  flex-shrink: 0;
  transition: background 0.22s;
}
.tb-feat-track::after {
  content: '';
  position: absolute;
  top: 2px; left: 2px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
  transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1);
}
.tb-feat-toggle input:checked + .tb-feat-track { background: #d97706; }
.tb-feat-toggle input:checked + .tb-feat-track::after { transform: translateX(14px); }
.tb-feat-label { font-size: 0.82rem; font-weight: 600; color: #374151; }

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
  color: #d97706;
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
  background: linear-gradient(90deg, #fffbeb 25%, #fef3c7 37%, #fffbeb 63%);
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
  border: 1px solid #fef3c7;
}
.sk-card-grid .sk-img { height: 185px; }
.sk-card-list { display: flex; }
.sk-card-list .sk-img { width: 150px; height: 130px; flex-shrink: 0; border-radius: 0; }
.sk-body {
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex: 1;
  background: #fff;
}
.sk-line { height: 12px; border-radius: 6px; background: #fef3c7; }
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
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}
.es-icon { font-size: 2rem; color: #d97706; }
.es-title { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin: 0 0 0.5rem; }
.es-sub { font-size: 0.88rem; color: #64748b; line-height: 1.6; margin: 0 0 1.5rem; }
.es-btn {
  display: inline-flex;
  align-items: center;
  font-size: 0.88rem;
  font-weight: 600;
  color: #d97706;
  background: rgba(217,119,6,.08);
  border: 1.5px solid rgba(217,119,6,.22);
  border-radius: 9999px;
  padding: 0.55rem 1.4rem;
  cursor: pointer;
  transition: background 0.2s;
}
.es-btn:hover { background: rgba(217,119,6,.15); }

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
  background: #fffbeb;
  border-color: #fde68a;
  color: #d97706;
}
.pg-btn-active {
  background: #d97706;
  border-color: #d97706;
  color: #fff;
  box-shadow: 0 2px 10px rgba(217,119,6,.3);
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
  background: linear-gradient(135deg, #d97706, #b45309);
  color: #fff;
  border: none;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 4px 18px rgba(217,119,6,.45);
  z-index: 99;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.filter-fab:hover { transform: translateY(-2px); box-shadow: 0 6px 22px rgba(217,119,6,.5); }
.fab-label { font-size: 0.82rem; }
.fab-badge {
  position: absolute;
  top: -5px; right: -5px;
  background: #ef4444;
  color: #fff;
  font-size: 0.62rem;
  font-weight: 800;
  width: 18px; height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
}

/* ── Busquedas relacionadas ─────────────────────────────────────────────────── */
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
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
  border-radius: 999px;
  padding: 0.5rem 1rem;
  font-size: 0.82rem;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.18s, border-color 0.18s, transform 0.18s;
}
.related-search-chip i { font-size: 0.78rem; color: #d97706; }
.related-search-chip:hover {
  background: #fef3c7;
  border-color: #fbbf24;
  transform: translateY(-1px);
}

/* ── Mobile offcanvas header ────────────────────────────────────────────────── */
.mob-oc-header {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  border-bottom: 1px solid #fde68a;
}

/* ── Utilities ──────────────────────────────────────────────────────────────── */
.min-w-0 { min-width: 0; }

@media (max-width: 991px) {
  .mh-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 1rem;
  }
  .industry-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .market-split { grid-template-columns: 1fr; }
}

@media (max-width: 575px) {
  .catalog-hero { padding-bottom: 1.6rem; }
  .ch-actions { width: 100%; }
  .ch-cta-primary,
  .ch-cta-provider { justify-content: center; flex: 1 1 150px; }
  .mh-grid,
  .industry-strip,
  .process-line,
  .tech-stats { grid-template-columns: 1fr; }
  .mh-card { min-height: auto; }
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
