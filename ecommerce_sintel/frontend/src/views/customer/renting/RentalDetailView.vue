<template>
  <div class="rental-detail">
    <div class="container-xl py-3 py-lg-4">
      <!-- Breadcrumb -->
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/alquiler" class="text-decoration-none text-muted">
              <i class="bi bi-hdd-rack me-1"></i>Renting
            </RouterLink>
          </li>
          <li v-if="detail?.hero?.category_name" class="breadcrumb-item text-muted">
            {{ detail.hero.category_name }}
          </li>
          <li class="breadcrumb-item active text-truncate" style="max-width:240px">
            {{ detail?.hero?.name }}
          </li>
        </ol>
      </nav>

      <!-- Loading State -->
      <div v-if="loading" class="row g-4">
        <div class="col-lg-5">
          <div class="skeleton rounded-3" style="height:420px"></div>
        </div>
        <div class="col-lg-7">
          <div class="skeleton rounded mb-3" style="height:34px;width:76%"></div>
          <div class="skeleton rounded mb-4" style="height:92px"></div>
          <div class="skeleton rounded" style="height:260px"></div>
        </div>
      </div>

      <!-- Main Content -->
      <div v-else-if="detail" class="row g-4 g-lg-5">
        <!-- Left Column: Gallery & Availability -->
        <div class="col-lg-5">
          <div class="gallery-sticky">
            <!-- Gallery -->
            <BaseGallery
              :images="detail.media?.gallery?.all_images || []"
              :title="detail.hero?.name"
              icon-class="bi-hdd-rack"
              theme="renting"
            >
              <template #badge="{ activeImage }">
                <span v-if="activeImage" class="eq-gallery-type-badge">
                  {{ activeImage.image_type || 'Galería' }}
                </span>
              </template>
            </BaseGallery>

            <!-- Trust Grid -->
            <div class="trust-grid">
              <div>
                <i class="bi bi-shield-check text-success"></i>
                <span>Equipo certificado</span>
              </div>
              <div>
                <i class="bi bi-credit-card text-primary"></i>
                <span>Pago seguro</span>
              </div>
              <div>
                <i class="bi bi-truck text-info"></i>
                <span>Logística opcional</span>
              </div>
              <div>
                <i class="bi bi-headset text-warning"></i>
                <span>Soporte postventa</span>
              </div>
            </div>

            <!-- Availability Card -->
            <div class="availability-card">
              <span class="section-kicker">Disponibilidad</span>
              <h2>{{ detail.availability?.status_label }}</h2>
              <p>{{ detail.availability?.status_detail }}</p>
              <RouterLink
                v-if="detail.hero?.cta_enabled"
                :to="{ name: 'rental-request', params: { uuid: detail.uuid } }"
                class="availability-link"
              >
                Consultar fechas exactas <i class="bi bi-arrow-right"></i>
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- Right Column: Details & Info -->
        <div class="col-lg-7">
          <!-- Badges & Actions -->
          <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <!-- Tags from Marketing -->
            <TagBadge v-for="tag in detail.marketing?.tags" :key="tag.code" :tag="tag" />

            <!-- Brand Badge -->
            <span v-if="detail.hero?.brand_name" class="badge bg-primary-subtle text-primary border border-primary-subtle">
              {{ detail.hero.brand_name }}
            </span>

            <!-- Category Badge -->
            <span v-if="detail.hero?.category_name" class="badge bg-light text-muted border">
              {{ detail.hero.category_name }}
            </span>

            <!-- Availability Badge -->
            <span :class="getAvailabilityBadgeClass()">
              {{ detail.availability?.status_label }}
            </span>

            <!-- Rating Badge -->
            <div v-if="detail.reviews?.average_rating" class="rating-badge-inline">
              <i class="bi bi-star-fill text-warning"></i>
              <span class="rating-value">{{ detail.reviews.average_rating.toFixed(1) }}</span>
              <span class="rating-count">({{ detail.reviews.total_count }})</span>
            </div>

            <!-- Actions -->
            <div class="ms-lg-auto d-flex gap-2">
              <button type="button" class="icon-action-btn" title="Compartir" @click="shareEquipment">
                <i class="bi bi-share"></i>
              </button>
              <button
                type="button"
                class="icon-action-btn"
                :class="{ active: isFavorite }"
                :title="isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'"
                @click="toggleFavorite"
              >
                <i :class="['bi', isFavorite ? 'bi-heart-fill' : 'bi-heart']"></i>
              </button>
            </div>
          </div>

          <!-- Title & Description -->
          <h1 class="equipment-title">{{ detail.hero?.name }}</h1>
          <p v-if="detail.hero?.description" class="value-prop">{{ detail.hero.description }}</p>

          <!-- Marketing Messages -->
          <div v-if="detail.marketing?.featured_benefit || detail.marketing?.trust_message" class="d-flex flex-wrap gap-2 mb-3">
            <span v-if="detail.marketing?.featured_benefit" class="badge bg-primary-subtle text-primary border border-primary-subtle">
              <i class="bi bi-lightning-charge-fill me-1"></i>{{ detail.marketing.featured_benefit }}
            </span>
            <span v-if="detail.marketing?.trust_message" class="badge bg-success-subtle text-success border border-success-subtle">
              <i class="bi bi-check-circle-fill me-1"></i>{{ detail.marketing.trust_message }}
            </span>
          </div>

          <!-- Urgency Banner -->
          <UrgencyBanner
            :status="detail.availability?.status"
            :available-now="detail.availability?.available_now || 0"
            :total-stock="detail.availability?.total_stock || 0"
            :urgency-message="detail.marketing?.urgency_message"
          />

          <!-- Discount Badge -->
          <DiscountBadge
            v-if="detail.pricing?.has_promotion"
            :discount="detail.pricing?.discount_percentage"
            :amount="detail.pricing?.formatted_discount_amount"
          />

          <!-- Pricing Card -->
          <div v-if="detail.pricing" class="pricing-card mb-4">
            <div class="row g-3">
              <div class="col-6">
                <span class="section-kicker">Precio por día</span>
                <div class="pricing-value">{{ detail.pricing.formatted_price_per_day || 'A cotizar' }}</div>
              </div>
              <div class="col-6">
                <span class="section-kicker">Precio por hora</span>
                <div class="pricing-value">{{ detail.pricing.formatted_price_per_hour || 'A cotizar' }}</div>
              </div>
            </div>

            <!-- Discount Banner -->
            <div v-if="detail.pricing.has_promotion" class="discount-banner mt-3">
              <span class="discount-badge">-{{ detail.pricing.discount_percentage }}%</span>
              <span>Ahorra {{ detail.pricing.formatted_discount_amount }}</span>
            </div>

            <!-- Promotion Message -->
            <p v-if="detail.pricing.saving_message" class="promo-message">{{ detail.pricing.saving_message }}</p>

            <!-- CTA Button -->
            <RouterLink
              v-if="detail.hero?.cta_enabled"
              :to="{ name: 'rental-request', params: { uuid: detail.uuid } }"
              class="btn btn-primary w-100"
            >
              {{ detail.hero?.cta_label || 'Reservar ahora' }}
            </RouterLink>
            <p v-else-if="detail.hero?.cta_disabled_reason" class="text-danger small mt-2">
              {{ detail.hero.cta_disabled_reason }}
            </p>
          </div>

          <!-- Quick Benefits -->
          <div v-if="detail.marketing?.quick_benefits?.length" class="quick-benefits mb-4">
            <span class="section-kicker">Beneficios destacados</span>
            <div class="benefits-grid">
              <div v-for="benefit in detail.marketing.quick_benefits" :key="benefit.label" class="benefit-item">
                <i :class="['bi', benefit.icon || 'bi-check-circle-fill']" class="benefit-icon"></i>
                <span>{{ benefit.label }}</span>
              </div>
            </div>
          </div>

          <!-- Quick Specs -->
          <div class="quick-specs mb-4">
            <span class="section-kicker">Especificaciones rápidas</span>
            <div class="specs-grid">
              <div v-for="spec in quickSpecs" :key="spec.label" class="spec-item">
                <span class="spec-label">{{ spec.label }}</span>
                <span class="spec-value">{{ spec.value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Features Section -->
      <div v-if="detail?.technical?.features?.length" class="section-features mt-5">
        <div class="section-header">
          <h2>Características destacadas</h2>
          <p class="section-subtitle">Lo que hace especial este equipo</p>
        </div>
        <div class="row g-3">
          <div v-for="feature in detail.technical.features" :key="feature.title" class="col-md-6 col-lg-4">
            <div class="feature-card">
              <span v-if="feature.icon" :class="['feature-icon', `bi ${feature.icon}`]"></span>
              <h5>{{ feature.title }}</h5>
              <p>{{ feature.value }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Included vs Excluded -->
      <div v-if="detail?.services?.included_items?.length || detail?.services?.excluded_items?.length" class="section-scope mt-5">
        <div class="section-header">
          <h2>Alcance del alquiler</h2>
          <p class="section-subtitle">Qué incluye y qué no</p>
        </div>
        <div class="row g-4">
          <div v-if="detail?.services?.included_items?.length" class="col-lg-6">
            <h5 class="mb-3">
              <i class="bi bi-check-circle text-success me-2"></i>Incluido en el precio
            </h5>
            <EquipmentIncludedList :items="detail.services.included_items" />
          </div>
          <div v-if="detail?.services?.excluded_items?.length" class="col-lg-6">
            <h5 class="mb-3">
              <i class="bi bi-x-circle text-danger me-2"></i>No incluido
            </h5>
            <EquipmentExcludedList :items="detail.services.excluded_items" />
          </div>
        </div>
      </div>

      <!-- Optional Services -->
      <div v-if="detail?.services?.optional_services?.length" class="section-optional-services mt-5">
        <div class="section-header">
          <h2>Servicios adicionales</h2>
          <p class="section-subtitle">Opciones disponibles por costo extra</p>
        </div>
        <div class="row g-3">
          <div v-for="service in detail.services.optional_services" :key="service.title" class="col-md-6 col-lg-4">
            <div class="optional-service-card">
              <span v-if="service.icon" :class="['service-icon', `bi ${service.icon}`]"></span>
              <h6>{{ service.title }}</h6>
              <p class="service-description">{{ service.description }}</p>
              <div class="service-price">{{ service.formatted_price }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Specifications by Group -->
      <div v-if="detail?.technical?.specification_groups?.length" class="section-specs mt-5">
        <div class="section-header">
          <h2>Especificaciones técnicas</h2>
          <p class="section-subtitle">Detalles técnicos completos</p>
        </div>
        <div class="row g-4">
          <div v-for="group in detail.technical.specification_groups" :key="group.name" class="col-lg-6">
            <div class="spec-group-card">
              <h5>{{ group.name }}</h5>
              <div class="specs-table">
                <div v-for="spec in group.specs" :key="spec.name" class="spec-row">
                  <span class="spec-name">{{ spec.name }}</span>
                  <span class="spec-val">{{ spec.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Requirements -->
      <div v-if="detail?.technical?.requirements?.length" class="section-requirements mt-5">
        <div class="section-header">
          <h2>Requisitos de alquiler</h2>
          <p class="section-subtitle">Lo que necesitas cumplir</p>
        </div>
        <EquipmentRequirementList :items="detail.technical.requirements" />
      </div>

      <!-- FAQs -->
      <div v-if="detail?.faqs?.length" class="section-faqs mt-5">
        <div class="section-header">
          <h2>Preguntas frecuentes</h2>
          <p class="section-subtitle">Respuestas a dudas comunes</p>
        </div>
        <div class="faqs-list">
          <BaseAccordion :items="detail.faqs.map(faq => ({ title: faq.question, content: faq.answer }))" />
        </div>
      </div>

      <!-- Videos -->
      <div v-if="detail?.media?.videos?.length" class="section-videos mt-5">
        <div class="section-header">
          <h2>Videos</h2>
          <p class="section-subtitle">Visualiza el equipo en acción</p>
        </div>
        <EquipmentVideoGallery :videos="detail.media.videos" />
      </div>

      <!-- Documents -->
      <div v-if="detail?.media?.documents?.length" class="section-documents mt-5">
        <div class="section-header">
          <h2>Documentación</h2>
          <p class="section-subtitle">Manuales y certificados</p>
        </div>
        <EquipmentDocumentList :documents="detail.media.documents" />
      </div>

      <!-- Reviews -->
      <div v-if="detail?.reviews" class="section-reviews mt-5">
        <div class="section-header">
          <h2>Reseñas</h2>
          <p class="section-subtitle">Experiencias de otros clientes</p>
        </div>

        <!-- Rating Summary -->
        <div class="rating-summary-card">
          <RatingDisplay :rating="detail.reviews" :show-breakdown="true" />
        </div>

        <!-- Reviews List -->
        <div v-if="detail.reviews.items?.length" class="reviews-list mt-4">
          <BaseReviews :reviews="detail.reviews.items" />
        </div>
        <div v-else class="empty-reviews">
          <p class="text-muted">Sé el primero en dejar una reseña</p>
        </div>
      </div>

      <!-- Related Equipment -->
      <div v-if="detail?.related_equipment?.length" class="section-related mt-5">
        <div class="section-header">
          <h2>Equipos relacionados</h2>
          <p class="section-subtitle">Otros equipos que podrían interesarte</p>
        </div>
        <div class="row g-3">
          <div v-for="equipment in detail.related_equipment" :key="equipment.uuid" class="col-md-6 col-lg-4">
            <RouterLink :to="{ name: 'rental-detail', params: { uuid: equipment.uuid } }" class="related-card text-decoration-none">
              <img :src="equipment.image_url" :alt="equipment.name" class="related-image" />
              <h6>{{ equipment.name }}</h6>
              <span class="price">{{ equipment.price_from }}</span>
            </RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useSeo } from '@/composables/useSeo';
import { usePreloadImage } from '@/composables/useLazyImage';

// Hero section (above fold - eager load)
import BaseGallery from '@/components/base/BaseGallery.vue';
import DiscountBadge from '@/components/marketplace/DiscountBadge.vue';
import UrgencyBanner from '@/components/marketplace/UrgencyBanner.vue';
import TagBadge from '@/components/marketplace/TagBadge.vue';
import RatingDisplay from '@/components/marketplace/RatingDisplay.vue';

// Below fold - lazy load con defineAsyncComponent
const EquipmentIncludedList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentIncludedList.vue')
);
const EquipmentExcludedList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentExcludedList.vue')
);
const EquipmentRequirementList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentRequirementList.vue')
);
const EquipmentDocumentList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentDocumentList.vue')
);
const EquipmentVideoGallery = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentVideoGallery.vue')
);
const BaseAccordion = defineAsyncComponent(() =>
  import('@/components/base/BaseAccordion.vue')
);
const BaseReviews = defineAsyncComponent(() =>
  import('@/components/base/BaseReviews.vue')
);

const api = useApi();
const toast = useToast();
const route = useRoute();
const router = useRouter();
const { setSeo } = useSeo();

const loading = ref(true);
const detail = ref(null);
const isFavorite = ref(false);

const FAVORITES_KEY = 'sintel_renting_favorites';

const quickSpecs = computed(() => {
  if (!detail.value?.hero) return [];
  return [
    { label: 'Marca', value: detail.value.hero.brand_name || 'Sintel' },
    { label: 'Categoría', value: detail.value.hero.category_name || 'Equipo' },
    { label: 'Disponibilidad', value: detail.value.availability?.status_label || 'N/A' },
    { label: 'Stock', value: `${detail.value.availability?.available_now || 0} unidad(es)` },
  ];
});


function getAvailabilityBadgeClass() {
  const status = detail.value?.availability?.status;
  const baseClass = 'badge border';
  if (status === 'available') return `${baseClass} bg-success-subtle text-success border-success-subtle`;
  if (status === 'limited') return `${baseClass} bg-warning-subtle text-warning border-warning-subtle`;
  return `${baseClass} bg-danger-subtle text-danger border-danger-subtle`;
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
    toast.info('Eliminado de favoritos');
  } else {
    favorites.push(uuid);
    isFavorite.value = true;
    toast.success('Agregado a favoritos');
  }
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
}

async function shareEquipment() {
  const shareData = {
    title: detail.value?.hero?.name,
    text: `Mira este equipo en alquiler: ${detail.value?.hero?.name}`,
    url: window.location.href,
  };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
    } else {
      await navigator.clipboard.writeText(window.location.href);
      toast.success('Enlace copiado al portapapeles');
    }
  } catch {
    // Usuario canceló el diálogo nativo de compartir
  }
}

async function fetchDetail() {
  loading.value = true;
  try {
    const uuid = route.params.uuid;
    const res = await api.get(`renting/equipment/${uuid}/detail/`);
    detail.value = res.data;
    isFavorite.value = loadFavorites().includes(detail.value.uuid);

    // Preload hero image
    const heroImageUrl = detail.value.media?.gallery?.principal?.url || detail.value.hero?.hero_image?.url;
    if (heroImageUrl) {
      usePreloadImage(heroImageUrl);
    }

    setSeo({
      title: detail.value.seo?.meta_title || detail.value.hero?.name,
      description: detail.value.seo?.meta_description || detail.value.hero?.description,
      ogImage: detail.value.seo?.og_image_url || detail.value.hero?.hero_image?.url,
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'Product',
        name: detail.value.hero?.name,
        description: detail.value.hero?.description,
        image: detail.value.media?.gallery?.principal?.url,
        brand: detail.value.hero?.brand_name || undefined,
        offers: {
          '@type': 'Offer',
          priceCurrency: 'COP',
          price: detail.value.pricing?.price_per_day || undefined,
          availability: detail.value.availability?.status === 'available' ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
        },
        aggregateRating: detail.value.reviews?.average_rating ? {
          '@type': 'AggregateRating',
          ratingValue: detail.value.reviews.average_rating,
          ratingCount: detail.value.reviews.total_count,
        } : undefined,
      },
    });
  } catch (error) {
    console.error('Error fetching equipment detail:', error);
    toast.error('No pudimos cargar los detalles del equipo');
    router.push('/alquiler');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchDetail();
});
</script>

<style scoped>
.rental-detail {
  min-height: 100vh;
  background: var(--bs-body-bg);
}

.gallery-sticky {
  position: sticky;
  top: 80px;
  z-index: 10;
}

.pricing-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
}

.pricing-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--bs-primary);
}

.discount-banner {
  background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
  padding: 0.75rem;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #856404;
  font-size: 0.875rem;
}

.discount-badge {
  background: #dc3545;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 600;
}

.quick-benefits {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.benefits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.benefit-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.benefit-icon {
  color: var(--bs-success);
  font-size: 1.25rem;
}

.quick-specs {
  background: var(--bs-body-bg);
  padding: 0;
}

.specs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: var(--bs-gray-100);
  border-radius: 0.375rem;
}

.spec-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--bs-secondary);
}

.spec-value {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--bs-body-color);
}

.section-features,
.section-scope,
.section-optional-services,
.section-specs,
.section-requirements,
.section-faqs,
.section-videos,
.section-documents,
.section-reviews,
.section-related {
  padding: 2rem 0;
  border-top: 1px solid var(--bs-border-color);
}

.section-header {
  margin-bottom: 2rem;
}

.section-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.section-subtitle {
  color: var(--bs-secondary);
  margin: 0;
  font-size: 0.95rem;
}

.feature-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
  text-align: center;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  font-size: 2rem;
  color: var(--bs-primary);
  display: block;
  margin-bottom: 0.75rem;
}

.feature-card h5 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.feature-card p {
  font-size: 0.875rem;
  color: var(--bs-secondary);
  margin: 0;
}

.optional-service-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
}

.service-icon {
  font-size: 2rem;
  color: var(--bs-info);
  display: block;
  margin-bottom: 0.75rem;
}

.optional-service-card h6 {
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.service-description {
  font-size: 0.875rem;
  color: var(--bs-secondary);
  margin-bottom: 0.75rem;
}

.service-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--bs-success);
}

.spec-group-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.spec-group-card h5 {
  font-weight: 600;
  margin-bottom: 1rem;
}

.specs-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.spec-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--bs-border-color);
  font-size: 0.875rem;
}

.spec-row:last-child {
  border-bottom: none;
}

.spec-name {
  color: var(--bs-secondary);
  font-weight: 500;
}

.spec-val {
  font-weight: 600;
  color: var(--bs-body-color);
}

.faqs-list {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.related-card {
  display: block;
  background: var(--bs-gray-100);
  padding: 1rem;
  border-radius: 0.5rem;
  transition: all 0.3s ease;
  overflow: hidden;
}

.related-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.related-image {
  width: 100%;
  height: 180px;
  object-fit: cover;
  border-radius: 0.375rem;
  margin-bottom: 0.75rem;
}

.related-card h6 {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--bs-body-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price {
  display: block;
  color: var(--bs-primary);
  font-weight: 700;
  font-size: 1rem;
}

.section-kicker {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--bs-secondary);
  margin-bottom: 0.5rem;
}

.trust-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--bs-gray-100);
  border-radius: 0.5rem;
}

.trust-grid > div {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.trust-grid i {
  font-size: 1.5rem;
}

.availability-card {
  background: linear-gradient(135deg, #e7f1ff 0%, #f0f6ff 100%);
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid #c3deff;
}

.availability-card h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--bs-body-color);
}

.availability-card p {
  font-size: 0.875rem;
  color: var(--bs-secondary);
  margin-bottom: 1rem;
}

.availability-link {
  display: inline-block;
  color: var(--bs-primary);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.availability-link:hover {
  transform: translateX(4px);
}

.icon-action-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--bs-border-color);
  background: var(--bs-body-bg);
  border-radius: 0.375rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--bs-body-color);
  transition: all 0.3s ease;
}

.icon-action-btn:hover {
  border-color: var(--bs-primary);
  color: var(--bs-primary);
}

.icon-action-btn.active {
  background: var(--bs-danger);
  border-color: var(--bs-danger);
  color: white;
}

.equipment-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
}

.value-prop {
  font-size: 1.125rem;
  color: var(--bs-secondary);
  margin-bottom: 1rem;
}

.promo-message {
  color: var(--bs-success);
  font-size: 0.875rem;
  margin-top: 0.75rem;
  margin-bottom: 0;
}

.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.eq-gallery-type-badge {
  display: inline-block;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.rating-badge-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: var(--bs-gray-100);
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.rating-badge-inline .rating-value {
  font-weight: 700;
  color: var(--bs-body-color);
}

.rating-badge-inline .rating-count {
  color: var(--bs-secondary);
}

.rating-summary-card {
  background: var(--bs-gray-100);
  padding: 2rem;
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
}

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.empty-reviews {
  text-align: center;
  padding: 2rem;
  background: var(--bs-gray-100);
  border-radius: 0.5rem;
}
</style>
