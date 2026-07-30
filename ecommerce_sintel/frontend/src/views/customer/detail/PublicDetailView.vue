<template>
  <div class="public-detail">
    <!-- Loading State -->
    <div v-if="loading" class="skeleton-container">
      <div class="skeleton" style="height: 400px"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger" role="alert">
      <h4 class="alert-heading">{{ getModuleLabel() }} no encontrado</h4>
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

      <!-- MAIN 2-COLUMN LAYOUT (mirrors production: col-lg-5 gallery/availability, col-lg-7 details) -->
      <div class="row g-4 g-lg-5">
        <!-- LEFT COLUMN -->
        <div class="col-lg-5">
          <div class="gallery-sticky">
            <!-- Gallery -->
            <div class="bv-gallery">
              <div class="bv-gallery-main">
                <i :class="['bi', getModuleIcon()]"></i>
              </div>
            </div>

            <!-- Trust Grid -->
            <div class="trust-grid">
              <div><i class="bi bi-shield-check text-success"></i><span>{{ getTrustMsg(0) }}</span></div>
              <div><i class="bi bi-credit-card text-primary"></i><span>{{ getTrustMsg(1) }}</span></div>
              <div><i class="bi bi-truck text-info"></i><span>{{ getTrustMsg(2) }}</span></div>
              <div><i class="bi bi-headset text-warning"></i><span>{{ getTrustMsg(3) }}</span></div>
            </div>

            <!-- Availability Card -->
            <div class="availability-card">
              <span class="section-kicker">Disponibilidad</span>
              <h2>{{ detail.availability?.status_label }}</h2>
              <p>{{ detail.availability?.status_detail }}</p>
              <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="availability-link">
                Consultar fechas exactas <i class="bi bi-arrow-right"></i>
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN -->
        <div class="col-lg-7">
          <!-- Badges + Actions -->
          <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span v-if="detail.hero?.brand_name" class="badge bg-primary-subtle text-primary border border-primary-subtle">{{ detail.hero.brand_name }}</span>
            <span v-if="detail.hero?.category_name" class="badge bg-light text-muted border">{{ detail.hero.category_name }}</span>
            <span :class="getAvailBadge()">{{ detail.availability?.status_label }}</span>
            <div class="ms-lg-auto d-flex gap-2">
              <button type="button" class="icon-action-btn" @click="shareItem"><i class="bi bi-share"></i></button>
              <button type="button" class="icon-action-btn" :class="{ active: isFavorite }" @click="toggleFavorite"><i :class="['bi', isFavorite ? 'bi-heart-fill' : 'bi-heart']"></i></button>
            </div>
          </div>

          <!-- Title -->
          <h1 class="equipment-title">{{ detail.hero?.name }}</h1>
          <p v-if="detail.hero?.description" class="value-prop">{{ detail.hero.description }}</p>

          <!-- Quick Specs -->
          <div class="quick-specs">
            <div>
              <span>Marca</span>
              <strong>{{ detail.hero?.brand_name || 'N/A' }}</strong>
            </div>
            <div>
              <span>Categoria</span>
              <strong>{{ detail.hero?.category_name || 'N/A' }}</strong>
            </div>
            <div>
              <span>Variantes</span>
              <strong>{{ variantsCount }}</strong>
            </div>
            <div>
              <span>Stock total</span>
              <strong>{{ detail.availability?.available_now || 0 }} unidad(es)</strong>
            </div>
          </div>

          <!-- Configuracion / Package Panel -->
          <div class="package-panel">
            <div class="panel-head">
              <div>
                <span class="section-kicker">Configuracion</span>
                <h2>{{ moduleType === 'renting' ? 'Valor del alquiler' : 'Valor' }}</h2>
              </div>
              <span class="from-price" v-if="moduleType === 'renting'">Desde {{ detail.pricing?.formatted_price_per_day }} / dia</span>
              <span class="from-price" v-else>{{ detail.pricing?.formatted_promo_price }}</span>
            </div>
            <div class="selected-package">
              <div>
                <h3>{{ packageLabel }}</h3>
                <p v-if="moduleType === 'renting'">{{ detail.pricing?.formatted_price_per_day }} / dia</p>
                <p v-else>{{ detail.pricing?.formatted_promo_price }}</p>
              </div>
              <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="reserve-btn">
                <i class="bi bi-calendar-check me-2"></i>{{ getCTALabel() }}
              </RouterLink>
            </div>
          </div>
        </div>
      </div>

      <!-- SECTIONS BELOW (mirrors production: detail-sections flex column) -->
      <div class="detail-sections">
        <!-- OPINIONES -->
        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Opiniones</span>
            <h2>Reseñas de clientes</h2>
          </div>
          <div class="bv-reviews">
            <div class="bv-reviews-summary">
              <div class="bv-reviews-score">
                <strong>{{ reviewScoreDisplay }}</strong>
                <span>{{ detail.reviews?.total_count || 0 }} reseñas</span>
              </div>
            </div>

            <div v-if="detail?.reviews?.items?.length" class="bv-reviews-list">
              <div v-for="(review, i) in detail.reviews.items" :key="i" class="bv-review-item">
                <div class="bv-review-item-header">
                  <strong>{{ review.user_name }}</strong>
                  <span>⭐ {{ review.rating }}/5</span>
                </div>
                <p>{{ review.comment }}</p>
              </div>
            </div>

            <div class="bv-review-form">
              <p class="bv-review-form-title">Escribe tu reseña</p>
              <div class="bv-review-stars-input">
                <button
                  v-for="star in 5"
                  :key="star"
                  type="button"
                  class="bv-star-btn"
                  :class="{ active: reviewRating >= star }"
                  @click="reviewRating = star">
                  ⭐
                </button>
              </div>
              <textarea
                v-model="reviewText"
                class="bv-review-textarea"
                rows="3"
                placeholder="Cuentanos tu experiencia..."></textarea>
              <button type="button" class="bv-review-submit" :disabled="isSubmittingReview" @click="submitReview">
                {{ isSubmittingReview ? 'Enviando...' : 'Publicar reseña' }}
              </button>
            </div>

            <p v-if="!detail?.reviews?.items?.length" class="bv-review-empty">
              Aun no hay reseñas para este {{ getModuleLabel().toLowerCase() }}.
            </p>
          </div>
        </section>

        <!-- INTEGRACIONES (Renting only, matches production) -->
        <section v-if="moduleType === 'renting'" class="detail-section related-section">
          <div class="section-head">
            <span class="section-kicker">Integraciones</span>
            <h2>Completa la solucion</h2>
          </div>
          <div class="related-grid">
            <RouterLink to="/tienda" class="related-card">
              <i class="bi bi-box-seam"></i>
              <span>Shop</span>
              <strong>Accesorios, consumibles y repuestos compatibles</strong>
            </RouterLink>
            <RouterLink to="/servicios" class="related-card">
              <i class="bi bi-tools"></i>
              <span>Technical Services</span>
              <strong>Instalacion, configuracion, monitoreo y soporte</strong>
            </RouterLink>
            <RouterLink to="/cotizar" class="related-card">
              <i class="bi bi-file-earmark-text"></i>
              <span>Proyecto</span>
              <strong>Solucion temporal con alcance y SLA personalizado</strong>
            </RouterLink>
          </div>
        </section>
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

const reviewRating = ref(0);
const reviewText = ref('');
const isSubmittingReview = ref(false);

const moduleType = computed(() => {
  const path = route.path;
  if (path.includes('alquiler')) return 'renting';
  if (path.includes('tienda')) return 'shop';
  if (path.includes('servicios')) return 'service';
  return 'renting';
});

const reviewScoreDisplay = computed(() => {
  const avg = detail.value?.reviews?.average_rating;
  return avg ? avg.toFixed(1) : '—';
});

const variantsCount = computed(() => {
  return detail.value?.pricing?.components?.length || 1;
});

const packageLabel = computed(() => {
  return detail.value?.hero?.category_name || getModuleLabel();
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

async function submitReview() {
  if (reviewRating.value === 0 || !reviewText.value.trim()) {
    showError('Por favor completa la calificación y comentario');
    return;
  }
  isSubmittingReview.value = true;
  try {
    // TODO: Implementar endpoint de POST review
    success('Reseña enviada correctamente');
    reviewRating.value = 0;
    reviewText.value = '';
  } catch {
    showError('Error al enviar la reseña');
  } finally {
    isSubmittingReview.value = false;
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

/* SECTION KICKER (shared, matches production .section-kicker) */
.section-kicker {
  display: block;
  font-size: 0.72rem;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #0369a1;
  margin-bottom: 0.25rem;
}

/* LEFT COLUMN */
.gallery-sticky { position: sticky; top: 88px; }

.bv-gallery-main {
  height: 376px;
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(135deg, #f0f9ff, #eef2ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
  font-size: 4rem;
}

/* TRUST GRID */
.trust-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.6rem;
  margin-top: 1rem;
}

.trust-grid div {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.8rem;
  color: #333;
}

.trust-grid i {
  font-size: 1.1rem;
  flex-shrink: 0;
}

/* AVAILABILITY CARD */
.availability-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  margin-top: 1rem;
}

.availability-card h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0 0 0.25rem;
}

.availability-card p {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0 0 0.75rem;
}

.availability-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #2563eb;
  font-weight: 750;
  font-size: 0.8rem;
  text-decoration: none;
}

.availability-link:hover { text-decoration: underline; }

/* RIGHT COLUMN */
.icon-action-btn {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-action-btn:hover { border-color: #adb5bd; }

.icon-action-btn.active { color: #dc3545; border-color: #dc3545; }

.badge { padding: 0.375rem 0.6rem; font-size: 0.78rem; }

.equipment-title {
  font-size: 2.4rem;
  font-weight: 900;
  color: #0f172a;
  line-height: 1.15;
  margin: 0.5rem 0 0.75rem;
}

.value-prop {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.65;
  margin-bottom: 1rem;
}

/* QUICK SPECS */
.quick-specs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.quick-specs > div span {
  display: block;
  font-size: 0.72rem;
  color: #64748b;
  font-weight: 760;
  margin-bottom: 0.15rem;
}

.quick-specs > div strong {
  display: block;
  font-size: 0.86rem;
  color: #0f172a;
  font-weight: 700;
}

/* PACKAGE PANEL / CONFIGURACION */
.package-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.9rem;
}

.panel-head h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0.25rem 0 0;
}

.from-price {
  font-size: 1rem;
  font-weight: 850;
  color: #2563eb;
}

.selected-package {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  border-top: 1px solid #e2e8f0;
  margin-top: 0.9rem;
  padding-top: 0.9rem;
}

.selected-package h3 {
  font-size: 1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0 0 0.25rem;
}

.selected-package p {
  font-size: 0.86rem;
  color: #64748b;
  margin: 0;
}

.reserve-btn {
  display: inline-flex;
  align-items: center;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 999px;
  font-weight: 850;
  padding: 0.75rem 1.15rem;
  white-space: nowrap;
  text-decoration: none;
  transition: background 0.2s;
}

.reserve-btn:hover { background: #1d4ed8; color: #fff; }

/* DETAIL SECTIONS (below fold) */
.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2.5rem;
}

.detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}

.section-head { margin-bottom: 0.9rem; }

.section-head h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0.25rem 0 0;
}

/* REVIEWS */
.bv-reviews-summary { margin-bottom: 1rem; }

.bv-reviews-score {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.bv-reviews-score strong {
  font-size: 1.6rem;
  font-weight: 900;
  color: #0f172a;
}

.bv-reviews-score span { color: #64748b; font-size: 0.85rem; }

.bv-reviews-list { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1rem; }

.bv-review-item { border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem; }

.bv-review-item-header { display: flex; justify-content: space-between; margin-bottom: 0.35rem; }

.bv-review-item p { margin: 0; color: #495057; font-size: 0.9rem; }

.bv-review-form {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  padding: 1rem;
}

.bv-review-form-title { font-weight: 700; margin-bottom: 0.75rem; color: #0f172a; }

.bv-review-stars-input { display: flex; gap: 0.35rem; margin-bottom: 0.75rem; }

.bv-star-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #cbd5e1;
  filter: grayscale(1);
  opacity: 0.6;
}

.bv-star-btn.active { filter: none; opacity: 1; }

.bv-review-textarea {
  width: 100%;
  border: 1px solid #bfdbfe;
  border-radius: 0.5rem;
  padding: 0.6rem;
  margin-bottom: 0.75rem;
  font-family: inherit;
  resize: vertical;
}

.bv-review-submit {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 999px;
  padding: 0.5rem 1.1rem;
  font-weight: 700;
}

.bv-review-submit:disabled { opacity: 0.6; }

.bv-review-empty { color: #64748b; font-size: 0.9rem; margin-top: 1rem; margin-bottom: 0; }

/* INTEGRACIONES */
.related-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.related-card {
  display: block;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.9rem;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}

.related-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.related-card i {
  font-size: 1.35rem;
  color: #2563eb;
  display: block;
  margin-bottom: 0.5rem;
}

.related-card span {
  display: block;
  font-size: 0.72rem;
  font-weight: 760;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.related-card strong {
  display: block;
  font-size: 0.86rem;
  font-weight: 700;
  color: #0f172a;
}

/* RESPONSIVE */
@media (max-width: 992px) {
  .gallery-sticky { position: static; }
  .equipment-title { font-size: 1.9rem; }
  .quick-specs { grid-template-columns: repeat(2, 1fr); }
  .related-grid { grid-template-columns: 1fr; }
}

@media (max-width: 576px) {
  .equipment-title { font-size: 1.5rem; }
  .trust-grid { grid-template-columns: 1fr; }
  .selected-package { flex-direction: column; align-items: stretch; }
  .reserve-btn { justify-content: center; }
  .panel-head { flex-direction: column; align-items: flex-start; }
}
</style>
