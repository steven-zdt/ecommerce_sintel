<template>
  <div class="public-detail">
    <!-- Loading State -->
    <div v-if="loading" class="skeleton-container">
      <div class="skeleton" style="height: 400px"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger" role="alert">
      <h4 class="alert-heading">{{ moduleLabel }} no encontrado</h4>
      <p>{{ error }}</p>
      <RouterLink to="/" class="btn btn-sm btn-outline-primary">Volver al inicio</RouterLink>
    </div>

    <!-- Content State -->
    <div v-else-if="detail" class="detail-container container-xl py-3 py-lg-4">
      <!-- Breadcrumb -->
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink :to="getBreadcrumbPath()" class="text-decoration-none text-muted">
              <i :class="['bi', getModuleIcon()]"></i>{{ getModuleLabel() }}
            </RouterLink>
          </li>
          <li v-if="detail?.hero?.category_name" class="breadcrumb-item text-muted">{{ detail.hero.category_name }}</li>
          <li class="breadcrumb-item active text-truncate" style="max-width:240px">{{ detail?.hero?.name }}</li>
        </ol>
      </nav>

      <!-- MAIN CONTENT -->
      <div class="mb-5">
        <!-- Hero Title -->
        <h1 class="detail-title mb-3">{{ detail.hero?.name }}</h1>

        <!-- Trust Grid -->
        <div class="trust-grid mb-4">
          <div><i class="bi bi-shield-check text-success"></i><span>{{ getTrustMsg(0) }}</span></div>
          <div><i class="bi bi-credit-card text-primary"></i><span>{{ getTrustMsg(1) }}</span></div>
          <div><i class="bi bi-truck text-info"></i><span>{{ getTrustMsg(2) }}</span></div>
          <div><i class="bi bi-headset text-warning"></i><span>{{ getTrustMsg(3) }}</span></div>
        </div>

        <!-- 2-Column: Left (Availability/Gallery) + Right (Details) -->
        <div class="row g-5 mb-5">
          <!-- LEFT: Availability + Gallery -->
          <div class="col-lg-6">
            <!-- DISPONIBILIDAD SECTION -->
            <div class="availability-section mb-5">
              <h3 class="section-title">DISPONIBILIDAD</h3>
              <p class="availability-status">{{ detail.availability?.status_label }}</p>
              <p class="availability-detail">{{ detail.availability?.status_detail }}</p>
              <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="btn btn-primary">
                Consultar fechas exactas
              </RouterLink>
            </div>

            <!-- Gallery -->
            <div class="gallery-area rounded-3 mb-4" style="height:420px;background:#f8f9fa;display:flex;align-items:center;justify-content:center">
              <span class="text-muted">Galería de imágenes</span>
            </div>
          </div>

          <!-- RIGHT: Product Details -->
          <div class="col-lg-6">
            <!-- Badges -->
            <div class="d-flex flex-wrap gap-2 mb-3">
              <span v-if="detail.hero?.brand_name" class="badge bg-light text-dark border">{{ detail.hero.brand_name }}</span>
              <span v-if="detail.hero?.category_name" class="badge bg-light text-dark border">{{ detail.hero.category_name }}</span>
              <span :class="getAvailBadge()">{{ detail.availability?.status_label }}</span>
            </div>

            <!-- Description -->
            <p v-if="detail.hero?.description" class="detail-description mb-4">{{ detail.hero.description }}</p>

            <!-- Quick Specs -->
            <div class="quick-specs mb-4">
              <div class="spec-row">
                <span class="spec-label">Marca</span>
                <span class="spec-val">{{ detail.hero?.brand_name || 'N/A' }}</span>
              </div>
              <div class="spec-row">
                <span class="spec-label">Categoría</span>
                <span class="spec-val">{{ detail.hero?.category_name || 'N/A' }}</span>
              </div>
              <div class="spec-row">
                <span class="spec-label">Disponibilidad</span>
                <span class="spec-val">{{ detail.availability?.status_label }}</span>
              </div>
              <div class="spec-row">
                <span class="spec-label">Stock total</span>
                <span class="spec-val">{{ detail.availability?.available_now || 0 }} unidad(es)</span>
              </div>
            </div>

            <!-- CONFIGURACIÓN SECTION -->
            <div class="config-section mb-4">
              <h4 class="section-subtitle">CONFIGURACION</h4>
              <div class="config-item">
                <span class="config-label">Valor del alquiler</span>
                <span class="config-val" v-if="moduleType === 'renting'">Desde {{ detail.pricing?.formatted_price_per_day }} / dia</span>
                <span class="config-val" v-else>{{ detail.pricing?.formatted_promo_price }}</span>
              </div>
            </div>

            <!-- Pricing Card -->
            <div v-if="detail.pricing" class="pricing-card mb-4">
              <div class="price-display">
                <span class="price-label" v-if="moduleType === 'renting'">${{ detail.pricing?.price_per_day }} / dia</span>
                <span class="price-label" v-else>{{ detail.pricing?.formatted_promo_price }}</span>
              </div>
              <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="btn btn-primary btn-lg w-100">
                {{ getCTALabel() }}
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- OPINIONES SECTION -->
        <div class="section-opiniones mb-5">
          <h3 class="section-title">OPINIONES</h3>
          <p class="section-subtitle">Reseñas de clientes</p>
          <div v-if="detail?.reviews?.items?.length" class="reviews-list">
            <div v-for="review in detail.reviews.items" :key="review.uuid" class="review-item">
              <div class="review-header">
                <h5>{{ review.author_name }}</h5>
                <span class="review-rating">⭐ {{ review.rating }}/5</span>
              </div>
              <p class="review-text">{{ review.text }}</p>
            </div>
          </div>
          <div v-else class="no-reviews">
            <p>—</p>
            <p class="text-muted">0 reseñas</p>
            <p class="text-muted">Aun no hay reseñas para este {{ getModuleLabel().toLowerCase() }}.</p>
            <button class="btn btn-outline-primary btn-sm" @click="toggleFavorite">Escribe tu reseña</button>
          </div>
        </div>

        <!-- INTEGRACIONES SECTION (Renting only) -->
        <div v-if="moduleType === 'renting'" class="section-integraciones mb-5">
          <h3 class="section-title">INTEGRACIONES</h3>
          <p class="section-subtitle">Completa la solucion</p>
          <div class="row g-3">
            <div class="col-md-4">
              <div class="integration-card">
                <h5>Shop</h5>
                <p>Accesorios, consumibles y repuestos compatibles</p>
              </div>
            </div>
            <div class="col-md-4">
              <div class="integration-card">
                <h5>Technical Services</h5>
                <p>Instalacion, configuracion, monitoreo y soporte</p>
              </div>
            </div>
            <div class="col-md-4">
              <div class="integration-card">
                <h5>Proyecto</h5>
                <p>Solucion temporal con alcance y SLA personalizado</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useSeo } from '@/composables/useSeo';

const api = useApi();
const { success, error: showError } = useToast();
const route = useRoute();
const { setSeo } = useSeo();

const loading = ref(true);
const error = ref(null);
const detail = ref(null);
const isFavorite = ref(false);
const FAVORITES_KEY = 'sintel_favorites';

const moduleType = computed(() => {
  const path = route.path;
  if (path.includes('alquiler')) return 'renting';
  if (path.includes('tienda')) return 'shop';
  if (path.includes('servicios')) return 'service';
  return 'renting';
});

// Helper functions
function getModuleLabel() {
  return { renting: 'Equipo', shop: 'Producto', service: 'Servicio' }[moduleType.value];
}

function getModuleIcon() {
  return { renting: 'bi-hdd-rack', shop: 'bi-bag-check', service: 'bi-tools' }[moduleType.value];
}

function getBreadcrumbPath() {
  return { renting: '/alquiler', shop: '/tienda', service: '/servicios' }[moduleType.value];
}

function getTrustMsg(idx) {
  const msgs = {
    renting: ['Equipo certificado', 'Pago seguro', 'Logística opcional', 'Soporte postventa'],
    shop: ['Productos certificados', 'Pago seguro', 'Envío rápido', 'Soporte postventa'],
    service: ['Servicio profesional', 'Pago seguro', 'Garantía incluida', 'Soporte postventa'],
  };
  return msgs[moduleType.value]?.[idx];
}

function getCTALabel() {
  return { renting: 'Reservar ahora', shop: 'Comprar ahora', service: 'Solicitar servicio' }[moduleType.value];
}

function getAvailBadge() {
  const status = detail.value?.availability?.status;
  const base = 'badge border';
  return {
    available: `${base} bg-success-subtle text-success`,
    limited: `${base} bg-warning-subtle text-warning`,
    unavailable: `${base} bg-danger-subtle text-danger`,
  }[status] || base;
}

function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
  } catch {
    return [];
  }
}

function toggleFavorite() {
  const favorites = loadFavorites();
  const uuid = detail.value?.uuid;
  const index = favorites.indexOf(uuid);
  if (index >= 0) {
    favorites.splice(index, 1);
    isFavorite.value = false;
  } else {
    favorites.push(uuid);
    isFavorite.value = true;
  }
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
}

async function shareItem() {
  const shareData = {
    title: detail.value?.hero?.name,
    text: `Mira este ${getModuleLabel().toLowerCase()}: ${detail.value?.hero?.name}`,
    url: window.location.href,
  };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
    } else {
      await navigator.clipboard.writeText(window.location.href);
      success('Enlace copiado al portapapeles');
    }
  } catch {
    // Usuario canceló
  }
}

async function fetchDetail() {
  loading.value = true;
  error.value = null;

  try {
    const uuid = route.params.uuid;
    if (!uuid) {
      throw new Error('UUID not found in route');
    }

    const res = await api.get(`unified/detail/${uuid}/?module=${moduleType.value}`);
    detail.value = res.data;
    isFavorite.value = loadFavorites().includes(detail.value.uuid);

    setSeo({
      title: detail.value.hero?.name || 'Detalle',
      description: detail.value.hero?.description || detail.value.seo?.meta_description || ''
    });
  } catch (err) {
    error.value = err.response?.data?.detail || 'No se pudo cargar el detalle';
    showError(error.value);
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchDetail());
</script>

<style scoped>
.detail-container { background: #fff; }

.skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200%; animation: loading 1.5s infinite; border-radius: 0.5rem; }

@keyframes loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.breadcrumb { font-size: 0.875rem; background: none; padding: 0; }

.breadcrumb-item a { color: #666; }

.breadcrumb-item.active { color: #333; }

/* MAIN LAYOUT */
.availability-section {
  margin-bottom: 2rem;
}

.availability-section h3 {
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #495057;
  margin-bottom: 1rem;
}

.availability-status {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0d6efd;
  margin-bottom: 0.5rem;
}

.availability-detail {
  font-size: 0.95rem;
  color: #495057;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.gallery-area {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
}

/* TRUST GRID */
.trust-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin: 2rem 0;
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
}

.trust-grid div {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9rem;
}

.trust-grid i {
  font-size: 1.5rem;
  flex-shrink: 0;
}

/* BADGES */
.badge {
  padding: 0.375rem 0.75rem;
  font-size: 0.8rem;
}

/* QUICK SPECS */
.quick-specs {
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  padding: 1.5rem;
  background: #f8f9fa;
}

.spec-row {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #dee2e6;
}

.spec-row:last-child {
  border-bottom: none;
}

.spec-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #6c757d;
  text-transform: uppercase;
}

.spec-val {
  font-weight: 500;
  color: #212529;
  text-align: right;
}

/* CONFIGURACION SECTION */
.config-section {
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  padding: 1.5rem;
  background: #f8f9fa;
}

.config-section h4 {
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #495057;
  margin-bottom: 1rem;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
}

.config-label {
  font-size: 0.9rem;
  color: #495057;
  font-weight: 500;
}

.config-val {
  font-weight: 700;
  color: #0d6efd;
  font-size: 1rem;
}

/* PRICING CARD */
.pricing-card {
  border: 2px solid #0d6efd;
  border-radius: 0.5rem;
  padding: 1.5rem;
  background: #f0f7ff;
}

.price-display {
  text-align: center;
  margin-bottom: 1rem;
}

.price-label {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0d6efd;
}

/* OPINIONES SECTION */
.section-opiniones {
  padding: 2rem 0;
  border-bottom: 1px solid #dee2e6;
}

.section-opiniones h3 {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.section-subtitle {
  font-size: 0.9rem;
  color: #6c757d;
  margin-bottom: 1.5rem;
}

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.review-item {
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  padding: 1.5rem;
  background: white;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.review-header h5 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.review-rating {
  font-weight: 600;
  color: #ffc107;
}

.review-text {
  font-size: 0.95rem;
  color: #495057;
  line-height: 1.6;
  margin: 0;
}

.no-reviews {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
}

.no-reviews p {
  margin: 0.5rem 0;
}

/* INTEGRACIONES SECTION */
.section-integraciones {
  padding: 2rem 0;
}

.section-integraciones h3 {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.integration-card {
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  padding: 1.5rem;
  background: #f8f9fa;
  transition: all 0.3s ease;
}

.integration-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.integration-card h5 {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.integration-card p {
  font-size: 0.85rem;
  color: #6c757d;
  margin: 0;
  line-height: 1.5;
}

/* DETAIL TITLE */
.detail-title {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 1rem;
}

.detail-description {
  font-size: 1rem;
  line-height: 1.6;
  color: #495057;
  margin-bottom: 1rem;
}

/* RESPONSIVE */
@media (max-width: 992px) {
  .trust-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-title {
    font-size: 1.75rem;
  }
}

@media (max-width: 576px) {
  .detail-title {
    font-size: 1.5rem;
  }

  .trust-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .config-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .config-val {
    margin-top: 0.5rem;
  }
}
</style>
