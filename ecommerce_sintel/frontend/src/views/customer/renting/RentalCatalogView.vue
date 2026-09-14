<template>
  <div class="rental-catalog">

    <!-- ── Hero premium ─────────────────────────────────────────────────────── -->
    <RentalCatalogHero
      :total-count="totalCount"
      :loading="loading"
      :featured="filterFeatured"
      @update:featured="filterFeatured = $event; fetchEquipment()"
    />
    <RentalSolutionStrip :solutions="premiumSolutions" />

    <div id="renting-marketplace" class="container-xl py-4">

      <!-- ── Toolbar ─────────────────────────────────────────────────────────── -->
      <div class="toolbar mb-4">
        <!-- Featured toggle mobile -->
        <label class="tb-feat-toggle d-lg-none">
          <input v-model="filterFeatured" type="checkbox" @change="fetchEquipment">
          <span class="tb-feat-track"></span>
          <span class="tb-feat-label">Destacados</span>
        </label>

        <div class="tb-right">
          <span v-if="totalCount && !loading" class="tb-count d-none d-lg-block">
            {{ totalCount.toLocaleString('es-CO') }} equipos
          </span>

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
            brand-label="Marca"
            :show-price="false"
            :filters="filterState"
            @change="onFilterChange"
            @reset="onFilterReset"
          />
        </aside>

        <!-- ── Area de equipos ───────────────────────────────────────────────── -->
        <div class="flex-grow-1 min-w-0">

          <!-- Loading skeleton -->
          <div v-if="loading" class="row g-3">
            <div
              v-for="i in 6"
              :key="i"
              :class="viewMode === 'list' ? 'col-12' : 'col-6 col-md-4'"
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
          <div v-else-if="equipment.length === 0" class="empty-state">
            <div class="es-icon-wrap">
              <i class="bi bi-truck es-icon"></i>
            </div>
            <h3 class="es-title">Sin equipos disponibles</h3>
            <p class="es-sub">No hay equipos con estos filtros.<br>Prueba con otros criterios de busqueda.</p>
            <button class="es-btn" @click="onFilterReset">
              <i class="bi bi-arrow-counterclockwise me-2"></i>Limpiar filtros
            </button>
          </div>

          <!-- Vista cuadricula -->
          <div v-else-if="viewMode === 'grid'" class="row g-3">
            <div
              v-for="item in equipment"
              :key="item.uuid"
              class="col-6 col-md-4 col-xl-3"
            >
              <ItemCard
                :item="item"
                type="rental"
                @view="goToDetail"
                @quote="goToRentalRequest"
              />
            </div>
          </div>

          <!-- Vista lista -->
          <div v-else class="d-flex flex-column gap-2">
            <EquipmentHorizontalCard
              v-for="item in equipment"
              :key="item.uuid"
              :equipment="item"
              @view="goToDetail"
              @quote="goToRentalRequest"
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
          <i class="bi bi-sliders2" style="color:#7c3aed"></i>
          <h6 class="mb-0 fw-bold">Filtros</h6>
        </div>
        <button class="btn-close" @click="showFilterMobile = false"></button>
      </div>
      <div class="offcanvas-body p-0">
        <FilterPanel
          :categories="categories"
          :brands="brands"
          brand-label="Marca"
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
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import ItemCard from '@/components/customer/ui/ItemCard.vue';
import FilterPanel from '@/components/customer/ui/FilterPanel.vue';
import EquipmentHorizontalCard from '@/components/renting/EquipmentHorizontalCard.vue';
import RentalCatalogHero from './rental-catalog/RentalCatalogHero.vue';
import RentalSolutionStrip from './rental-catalog/RentalSolutionStrip.vue';

const api = useApi();
const toast = useToast();
const router = useRouter();

const loading = ref(true);
const equipment = ref([]);
const categories = ref([]);
const brands = ref([]);
const totalCount = ref(0);
const totalPages = ref(0);
const currentPage = ref(1);
const filterFeatured = ref(false);
const showFilterMobile = ref(false);
const viewMode = ref('grid');
const homeCards = ref([]);
const homeCardGroups = ref([]);

const fallbackPremiumSolutions = [
  { icon: 'bi-camera-video', title: 'Seguridad temporal', copy: 'CCTV, control perimetral y monitoreo para eventos, obras y sedes temporales.' },
  { icon: 'bi-router', title: 'Conectividad por proyecto', copy: 'Redes, WiFi, switching y enlaces listos para operar durante el periodo contratado.' },
  { icon: 'bi-hdd-rack', title: 'Infraestructura TI', copy: 'Racks, energia, respaldo, computo y equipos empresariales con soporte tecnico.' },
  { icon: 'bi-person-workspace', title: 'Solucion con operador', copy: 'Equipo, transporte, instalacion, configuracion, capacitacion y operador especializado.' },
];

const filterState = reactive({
  categorySlug: '',
  brandSlug: '',
  minPrice: '',
  maxPrice: '',
  isFeatured: null,
});

const activeFilterCount = computed(() => {
  let c = 0;
  if (filterState.categorySlug) c++;
  if (filterState.brandSlug) c++;
  return c;
});

const visiblePages = computed(() => {
  const pages = [];
  const start = Math.max(1, currentPage.value - 2);
  const end = Math.min(totalPages.value, currentPage.value + 2);
  for (let i = start; i <= end; i++) pages.push(i);
  return pages;
});

function cardsFor(groupName) {
  return homeCards.value
    .filter((card) => card.group_name === groupName && card.is_active !== false)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
}

const premiumSolutions = computed(() => {
  const cards = cardsFor('renting_home_solutions');
  if (!cards.length) return fallbackPremiumSolutions;
  return cards.map((card) => ({
    title: card.title,
    copy: card.description || card.subtitle || '',
    icon: card.icon_class || 'bi-star',
  }));
});

async function fetchEquipment() {
  loading.value = true;
  try {
    const params = { page: currentPage.value, is_active: true };
    if (filterState.categorySlug) params['category__slug'] = filterState.categorySlug;
    if (filterState.brandSlug) params['brand__slug'] = filterState.brandSlug;
    if (filterFeatured.value) params['is_featured'] = true;
    const res = await api.get('renting/equipment/', { params });
    equipment.value = res.data.results || res.data;
    totalCount.value = res.data.count || equipment.value.length;
    totalPages.value = Math.ceil(totalCount.value / 24);
  } catch {
    toast.error('Error al cargar equipos');
  } finally {
    loading.value = false;
  }
}

async function fetchMarketplaceContent() {
  try {
    const { data } = await api.get('core/home-feed/');
    homeCards.value = data.home_cards || [];
    homeCardGroups.value = data.card_groups || [];
  } catch {
    homeCards.value = [];
    homeCardGroups.value = [];
  }
}

async function fetchFilters() {
  const [catRes, brandRes] = await Promise.all([
    api.get('renting/categories/').catch(() => ({ data: [] })),
    api.get('renting/brands/').catch(() => ({ data: [] })),
  ]);
  categories.value = catRes.data.results || catRes.data || [];
  brands.value = brandRes.data.results || brandRes.data || [];
}

function onFilterChange(f) {
  Object.assign(filterState, f);
  currentPage.value = 1;
  fetchEquipment();
}

function onFilterReset() {
  Object.assign(filterState, { categorySlug: '', brandSlug: '', minPrice: '', maxPrice: '', isFeatured: null });
  filterFeatured.value = false;
  currentPage.value = 1;
  fetchEquipment();
}

function searchByCategory(cat) {
  onFilterChange({ categorySlug: cat.slug, brandSlug: filterState.brandSlug });
  document.getElementById('renting-marketplace')?.scrollIntoView({ behavior: 'smooth' });
}

function changePage(p) {
  if (p >= 1 && p <= totalPages.value) {
    currentPage.value = p;
    fetchEquipment();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function goToDetail(item) {
  router.push({ name: 'rental-detail', params: { uuid: item.uuid } });
}

// Bug real (hallado 2026-07-29, probando pago con Nequi/Daviplata contra
// produccion): este handler enrutaba a quote-wizard ("Cotizar") aunque el
// boton dice "Solicitar alquiler" -- el cliente terminaba en un formulario
// de cotizacion generico en vez del wizard real de reserva/pago
// (rental-request, el mismo que usa el CTA de RentalDetailView.vue). variant
// se omite a proposito: RentalBookingWizard ya hace fallback a
// variants.value[0] cuando route.query.variant no viene (ver su onMounted).
function goToRentalRequest(item) {
  router.push({ name: 'rental-request', params: { uuid: item.uuid } });
}

onMounted(() => { fetchMarketplaceContent(); fetchFilters(); fetchEquipment(); });
</script>

<style scoped>
/* ── Catalog hero ───────────────────────────────────────────────────────────── */
.catalog-hero {
  position: relative;
  background: linear-gradient(135deg, #1a0533 0%, #4c1d95 55%, #7c3aed 100%);
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
  background: #a78bfa;
  top: -120px; right: -80px;
}
.ch-glow-2 {
  width: 300px; height: 300px;
  background: #c4b5fd;
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
  gap: .75rem;
  margin-top: 1rem;
}
.ch-cta-primary,
.ch-cta-secondary {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  border-radius: 999px;
  padding: .58rem 1.1rem;
  font-size: .82rem;
  font-weight: 760;
  text-decoration: none;
  transition: transform .16s ease, background .16s ease;
}
.ch-cta-primary {
  background: #fff;
  color: #111827;
  box-shadow: 0 14px 30px rgba(15,23,42,.2);
}
.ch-cta-secondary {
  background: rgba(255,255,255,.12);
  color: #fff;
  border: 1px solid rgba(255,255,255,.24);
}
.ch-cta-primary:hover,
.ch-cta-secondary:hover {
  transform: translateY(-1px);
}
.ch-cta-primary:hover { color: #111827; background: #f8fafc; }
.ch-cta-secondary:hover { color: #fff; background: rgba(255,255,255,.18); }
.ch-trust-row {
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
  margin-top: 1rem;
}
.ch-trust-row span {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  color: rgba(255,255,255,.8);
  background: rgba(15,23,42,.18);
  border: 1px solid rgba(255,255,255,.15);
  border-radius: 999px;
  padding: .28rem .65rem;
  font-size: .76rem;
  font-weight: 650;
}

/* ── Premium renting home ──────────────────────────────────────────────────── */
.renting-home {
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  border-bottom: 1px solid #e2e8f0;
  padding: 1.35rem 0 1.85rem;
}
.rh-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .9rem;
  margin-top: -2.35rem;
  position: relative;
  z-index: 2;
}
.rh-card {
  min-height: 150px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  display: flex;
  gap: .85rem;
  box-shadow: 0 16px 34px rgba(15,23,42,.08);
}
.rh-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #f0f9ff;
  color: #0369a1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1.12rem;
}
.rh-card h2,
.section-head h2,
.availability-panel h2,
.process-panel h2 {
  color: #0f172a;
  font-weight: 850;
  letter-spacing: 0;
  margin: 0;
}
.rh-card h2 { font-size: .98rem; line-height: 1.2; }
.rh-card p {
  color: #64748b;
  font-size: .82rem;
  line-height: 1.55;
  margin: .35rem 0 0;
}
.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.8rem 0 .9rem;
}
.section-head h2 { font-size: 1.35rem; }
.section-head.compact { margin-top: 0; }
.section-kicker {
  display: block;
  color: #0369a1;
  font-size: .72rem;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: .25rem;
}
.use-case-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: .75rem;
}
.use-case-card {
  display: flex;
  align-items: center;
  gap: .5rem;
  min-height: 58px;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 14px;
  color: #3730a3;
  padding: .75rem;
  font-size: .84rem;
  font-weight: 780;
}
.renting-split-section {
  padding: 1rem 0 2.5rem;
}
.renting-split {
  display: grid;
  grid-template-columns: 1fr 1.25fr;
  gap: 1rem;
}
.availability-panel,
.process-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}
.availability-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .6rem;
  margin-top: .85rem;
}
.availability-grid div {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: .75rem;
}
.availability-grid span {
  display: block;
  color: #64748b;
  font-size: .72rem;
  font-weight: 760;
}
.availability-grid strong {
  display: block;
  color: #0f172a;
  font-size: .88rem;
  margin-top: .2rem;
}
.process-line {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .55rem;
  margin-top: .85rem;
}
.process-line span {
  min-height: 44px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: .76rem;
  font-weight: 780;
}

/* Featured toggle in hero */
.ch-right { align-items: center; }
.ch-featured-toggle {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  cursor: pointer;
  background: rgba(255,255,255,.1);
  backdrop-filter: blur(12px);
  border: 1.5px solid rgba(255,255,255,.2);
  border-radius: 12px;
  padding: 0.65rem 1rem;
}
.ch-featured-toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.ch-toggle-track {
  display: block;
  width: 38px;
  height: 22px;
  border-radius: 999px;
  background: rgba(255,255,255,.2);
  position: relative;
  flex-shrink: 0;
  transition: background 0.22s;
}
.ch-toggle-track::after {
  content: '';
  position: absolute;
  top: 3px; left: 3px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.2);
  transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1);
}
.ch-featured-toggle input:checked + .ch-toggle-track { background: #a78bfa; }
.ch-featured-toggle input:checked + .ch-toggle-track::after { transform: translateX(16px); }
.ch-toggle-label { font-size: 0.82rem; font-weight: 600; color: rgba(255,255,255,.9); }

/* ── Toolbar ────────────────────────────────────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
/* featured toggle mobile */
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
.tb-feat-toggle input:checked + .tb-feat-track { background: #7c3aed; }
.tb-feat-toggle input:checked + .tb-feat-track::after { transform: translateX(14px); }
.tb-feat-label { font-size: 0.82rem; font-weight: 600; color: #374151; }

.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.tb-count { font-size: 0.78rem; color: #94a3b8; white-space: nowrap; }

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
  color: #7c3aed;
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
  background: linear-gradient(90deg, #f5f3ff 25%, #ede9fe 37%, #f5f3ff 63%);
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
  border: 1px solid #f5f3ff;
}
.sk-card-grid .sk-img { height: 200px; }
.sk-card-list { display: flex; }
.sk-card-list .sk-img { width: 150px; height: 130px; flex-shrink: 0; border-radius: 0; }
.sk-body {
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex: 1;
}
.sk-line { height: 12px; border-radius: 6px; }
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
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}
.es-icon { font-size: 2rem; color: #7c3aed; }
.es-title { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin: 0 0 0.5rem; }
.es-sub { font-size: 0.88rem; color: #64748b; line-height: 1.6; margin: 0 0 1.5rem; }
.es-btn {
  display: inline-flex;
  align-items: center;
  font-size: 0.88rem;
  font-weight: 600;
  color: #7c3aed;
  background: rgba(124,58,237,.08);
  border: 1.5px solid rgba(124,58,237,.22);
  border-radius: 9999px;
  padding: 0.55rem 1.4rem;
  cursor: pointer;
  transition: background 0.2s;
}
.es-btn:hover { background: rgba(124,58,237,.15); }

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
  background: #f5f3ff;
  border-color: #ddd6fe;
  color: #7c3aed;
}
.pg-btn-active {
  background: #7c3aed;
  border-color: #7c3aed;
  color: #fff;
  box-shadow: 0 2px 10px rgba(124,58,237,.3);
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
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  border: none;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 4px 18px rgba(124,58,237,.45);
  z-index: 99;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.filter-fab:hover { transform: translateY(-2px); box-shadow: 0 6px 22px rgba(124,58,237,.5); }
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
  border: 1px solid #ddd6fe;
  background: #f5f3ff;
  color: #5b21b6;
  border-radius: 999px;
  padding: 0.5rem 1rem;
  font-size: 0.82rem;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.18s, border-color 0.18s, transform 0.18s;
}
.related-search-chip i { font-size: 0.78rem; color: #7c3aed; }
.related-search-chip:hover {
  background: #ede9fe;
  border-color: #c4b5fd;
  transform: translateY(-1px);
}

/* ── Mobile offcanvas header ────────────────────────────────────────────────── */
.mob-oc-header {
  background: linear-gradient(135deg, #faf5ff, #f3e8ff);
  border-bottom: 1px solid #e9d5ff;
}

/* ── Utilities ──────────────────────────────────────────────────────────────── */
.min-w-0 { min-width: 0; }

@media (max-width: 991px) {
  .rh-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 1rem;
  }
}

@media (max-width: 575px) {
  .ch-actions { width: 100%; }
  .ch-cta-primary,
  .ch-cta-secondary { justify-content: center; flex: 1 1 150px; }
  .rh-grid,
  .use-case-strip,
  .availability-grid,
  .process-line { grid-template-columns: 1fr; }
  .rh-card { min-height: auto; }
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
