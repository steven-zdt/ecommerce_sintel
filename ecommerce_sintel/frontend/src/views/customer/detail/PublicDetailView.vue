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

      <!-- MAIN 2-COLUMN LAYOUT -->
      <div class="row g-4 g-lg-5 mb-5">
        <!-- LEFT COLUMN: Gallery + Availability -->
        <div class="col-lg-5">
          <div class="gallery-sticky">
            <!-- Trust Grid -->
            <div class="trust-grid mb-4">
              <div><i class="bi bi-shield-check text-success"></i><span>{{ getTrustMsg(0) }}</span></div>
              <div><i class="bi bi-credit-card text-primary"></i><span>{{ getTrustMsg(1) }}</span></div>
              <div><i class="bi bi-truck text-info"></i><span>{{ getTrustMsg(2) }}</span></div>
              <div><i class="bi bi-headset text-warning"></i><span>{{ getTrustMsg(3) }}</span></div>
            </div>
            <!-- Gallery Placeholder -->
            <div class="gallery-area mb-4 rounded-3" style="height:420px;background:#f8f9fa;display:flex;align-items:center;justify-content:center">
              <span class="text-muted">Galería</span>
            </div>
            <!-- Availability Card -->
            <div class="availability-card">
              <span class="section-kicker">Disponibilidad</span>
              <h2>{{ detail.availability?.status_label }}</h2>
              <p>{{ detail.availability?.status_detail }}</p>
              <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="availability-link">
                Consultar fechas <i class="bi bi-arrow-right"></i>
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN: Details -->
        <div class="col-lg-7">
          <!-- Badges Row -->
          <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
            <span v-for="tag in detail.marketing?.tags" :key="tag" class="badge bg-primary-subtle text-primary border">{{ tag }}</span>
            <span v-if="detail.hero?.brand_name" class="badge bg-primary-subtle text-primary border">{{ detail.hero.brand_name }}</span>
            <span v-if="detail.hero?.category_name" class="badge bg-light text-muted border">{{ detail.hero.category_name }}</span>
            <span :class="getAvailBadge()">{{ detail.availability?.status_label }}</span>
            <div v-if="detail.reviews?.total_count > 0" class="rating-inline">
              <i class="bi bi-star-fill text-warning"></i>
              <span>{{ detail.reviews.average_rating?.toFixed(1) }}</span> ({{ detail.reviews.total_count }})
            </div>
            <div class="ms-lg-auto d-flex gap-2">
              <button type="button" class="icon-btn" @click="shareItem"><i class="bi bi-share"></i></button>
              <button type="button" class="icon-btn" :class="{ active: isFavorite }" @click="toggleFavorite"><i :class="['bi', isFavorite ? 'bi-heart-fill' : 'bi-heart']"></i></button>
            </div>
          </div>

          <!-- Title -->
          <h1 class="detail-title">{{ detail.hero?.name }}</h1>
          <p v-if="detail.hero?.description" class="detail-description">{{ detail.hero.description }}</p>

          <!-- Pricing Card -->
          <div v-if="detail.pricing" class="pricing-section mb-4">
            <div class="row g-3" v-if="moduleType === 'renting'">
              <div class="col-6">
                <span class="kicker">Precio por día</span>
                <div class="price-value">{{ detail.pricing.formatted_price_per_day }}</div>
              </div>
              <div class="col-6">
                <span class="kicker">Precio por hora</span>
                <div class="price-value">{{ detail.pricing.formatted_price_per_hour }}</div>
              </div>
            </div>
            <div v-else class="row g-3">
              <div class="col-12">
                <span class="kicker">Precio</span>
                <div class="price-value">{{ detail.pricing.formatted_promo_price }}</div>
              </div>
            </div>
            <div v-if="detail.pricing?.has_promotion" class="discount-banner mt-3">
              <span class="discount-badge">-{{ detail.pricing.discount_percentage }}%</span>
              <span>Ahorra {{ detail.pricing.formatted_discount_amount }}</span>
            </div>
            <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="btn btn-primary w-100 mt-3">
              {{ getCTALabel() }}
            </RouterLink>
          </div>

          <!-- Quick Specs -->
          <div class="quick-specs">
            <span class="kicker">Especificaciones rápidas</span>
            <div class="specs-grid">
              <div><span class="spec-label">Marca</span><span class="spec-val">{{ detail.hero?.brand_name || 'N/A' }}</span></div>
              <div><span class="spec-label">Categoría</span><span class="spec-val">{{ detail.hero?.category_name || 'N/A' }}</span></div>
              <div><span class="spec-label">Disponibilidad</span><span class="spec-val">{{ detail.availability?.status_label }}</span></div>
              <div><span class="spec-label">Stock</span><span class="spec-val">{{ detail.availability?.available_now || 0 }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- SECTIONS BELOW FOLD -->
      <div v-if="detail?.included_items?.length || detail?.excluded_items?.length" class="section mt-5">
        <h2>Alcance</h2>
        <p class="subtitle">Qué incluye y qué no</p>
        <div class="row g-4">
          <div v-if="detail?.included_items?.length" class="col-lg-6">
            <h5 class="mb-3"><i class="bi bi-check-circle text-success me-2"></i>Incluido</h5>
            <ul class="item-list">
              <li v-for="(item, i) in detail.included_items" :key="i">{{ item }}</li>
            </ul>
          </div>
          <div v-if="detail?.excluded_items?.length" class="col-lg-6">
            <h5 class="mb-3"><i class="bi bi-x-circle text-danger me-2"></i>No incluido</h5>
            <ul class="item-list">
              <li v-for="(item, i) in detail.excluded_items" :key="i">{{ item }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- FAQ -->
      <div v-if="detail?.faq?.length" class="section mt-5">
        <h2>Preguntas frecuentes</h2>
        <div class="accordion">
          <div v-for="(faq, i) in detail.faq" :key="i" class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button" type="button" :data-bs-target="`#faq${i}`" data-bs-toggle="collapse">{{ faq.question }}</button>
            </h2>
            <div :id="`faq${i}`" class="accordion-collapse collapse" data-bs-parent=".accordion">
              <div class="accordion-body">{{ faq.answer }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Related Items -->
      <div v-if="detail?.related_items?.length" class="section mt-5">
        <h2>{{ getModuleLabel() }}s relacionados</h2>
        <p class="subtitle">Otros que podrían interesarte</p>
        <div class="row g-3">
          <div v-for="item in detail.related_items" :key="item.uuid" class="col-md-6 col-lg-4">
            <RouterLink :to="`/${moduleType}/${item.uuid}`" class="item-card">
              <div class="item-image"></div>
              <h6>{{ item.name }}</h6>
              <span class="price">{{ item.price_from }}</span>
            </RouterLink>
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

.gallery-sticky { position: sticky; top: 20px; }

.gallery-area { background: #f8f9fa; }

.trust-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }

.trust-grid > div { display: flex; align-items: center; gap: 0.75rem; font-size: 0.875rem; color: #333; }

.trust-grid i { font-size: 1.25rem; }

.availability-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 0.75rem; margin-top: 2rem; }

.availability-card h2 { font-size: 1.5rem; margin: 0.5rem 0; font-weight: 700; }

.availability-card p { margin-bottom: 1.5rem; font-size: 0.95rem; }

.availability-link { display: inline-flex; align-items: center; gap: 0.5rem; color: white; text-decoration: none; font-weight: 600; transition: gap 0.2s; }

.availability-link:hover { gap: 0.75rem; }

.kicker { display: block; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #999; margin-bottom: 0.5rem; }

.detail-title { font-size: 2rem; font-weight: 700; margin: 1rem 0 0.5rem; color: #1a1a1a; }

.detail-description { font-size: 1.1rem; color: #666; margin-bottom: 1.5rem; line-height: 1.6; }

.pricing-section { background: #f8f9fa; border-radius: 0.75rem; padding: 1.5rem; border: 1px solid #e9ecef; }

.price-value { font-size: 1.75rem; font-weight: 700; color: #007bff; }

.discount-banner { background: #fff3cd; padding: 1rem; border-radius: 0.5rem; display: flex; align-items: center; gap: 1rem; }

.discount-badge { background: #dc3545; color: white; padding: 0.5rem 0.75rem; border-radius: 0.25rem; font-weight: 700; font-size: 0.875rem; }

.quick-specs { background: #f8f9fa; border-radius: 0.75rem; padding: 1.5rem; }

.specs-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }

.specs-grid > div { display: flex; flex-direction: column; }

.spec-label { font-size: 0.875rem; color: #999; font-weight: 600; }

.spec-val { font-size: 1rem; font-weight: 600; color: #1a1a1a; margin-top: 0.25rem; }

.icon-btn { background: none; border: none; font-size: 1.25rem; cursor: pointer; color: #666; transition: color 0.2s; }

.icon-btn:hover,
.icon-btn.active { color: #dc3545; }

.rating-inline { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background: #fff3cd; border-radius: 0.5rem; font-weight: 600; font-size: 0.875rem; }

.rating-inline i { color: #ff8c00; }

.section { padding: 2rem 0; border-bottom: 1px solid #e9ecef; }

.section h2 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; }

.subtitle { color: #999; font-size: 1rem; margin-bottom: 2rem; }

.item-list { list-style: none; padding: 0; margin: 0; }

.item-list li { padding: 0.75rem 0; border-bottom: 1px solid #e9ecef; color: #333; }

.item-list li:last-child { border-bottom: none; }

.accordion-item { background: none; border: 1px solid #e9ecef; margin-bottom: 0.5rem; border-radius: 0.5rem; }

.accordion-button { padding: 1rem; background: none; font-weight: 600; }

.accordion-button:not(.collapsed) { background: #f8f9fa; }

.accordion-body { padding: 1rem; }

.item-card { display: block; background: #fff; border-radius: 0.75rem; overflow: hidden; border: 1px solid #e9ecef; text-decoration: none; transition: all 0.3s; }

.item-card:hover { box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1); transform: translateY(-4px); }

.item-image { width: 100%; height: 200px; background: #f8f9fa; }

.item-card h6 { padding: 1rem 1rem 0.5rem; margin: 0; font-weight: 600; color: #1a1a1a; }

.item-card .price { display: block; padding: 0 1rem 1rem; color: #007bff; font-weight: 700; }

@media (max-width: 992px) {
  .detail-title { font-size: 1.5rem; }
  .specs-grid { grid-template-columns: 1fr; }
  .trust-grid { grid-template-columns: 1fr; }
  .gallery-sticky { position: static; }
}
</style>
