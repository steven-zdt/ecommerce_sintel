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
    <div v-else-if="detail" class="detail-content">
      <!-- Breadcrumb -->
      <nav class="mb-4" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/" class="text-decoration-none text-muted">Inicio</RouterLink>
          </li>
          <li class="breadcrumb-item">
            <RouterLink :to="`/${moduleType === 'renting' ? 'alquiler' : moduleType === 'shop' ? 'tienda' : 'servicios'}`"
              class="text-decoration-none text-muted">{{ moduleLabel }}</RouterLink>
          </li>
          <li class="breadcrumb-item active">{{ detail.hero?.name }}</li>
        </ol>
      </nav>

      <!-- Hero Section -->
      <PublicDetailHero v-if="detail.hero" :hero="detail.hero" :module-type="moduleType" />

      <!-- Gallery Section -->
      <PublicDetailGallery v-if="detail.gallery" :gallery="detail.gallery" />

      <!-- Pricing Section -->
      <PublicDetailPricing v-if="detail.pricing" :pricing="detail.pricing" :module-type="moduleType" />

      <!-- Marketing Section -->
      <PublicDetailMarketing v-if="detail.marketing" :marketing="detail.marketing" />

      <!-- Availability Section -->
      <PublicDetailAvailability v-if="detail.availability" :availability="detail.availability" />

      <!-- Description Section -->
      <PublicDetailDescription v-if="detail.description" :description="detail.description" />

      <!-- Technical Section -->
      <PublicDetailTechnical v-if="detail.technical" :technical="detail.technical" />

      <!-- Included Items -->
      <PublicDetailIncluded v-if="detail.included_items?.length"
        :items="detail.included_items"
        :excluded-items="detail.excluded_items"
        :requirements="detail.requirements" />

      <!-- FAQ Section -->
      <PublicDetailFAQ v-if="detail.faq?.length" :faq="detail.faq" />

      <!-- Documents Section -->
      <PublicDetailDocuments v-if="detail.documents?.length" :documents="detail.documents" />

      <!-- Videos Section -->
      <PublicDetailVideos v-if="detail.videos?.length" :videos="detail.videos" />

      <!-- Reviews Section -->
      <PublicDetailReviews v-if="detail.reviews" :reviews="detail.reviews" :module-type="moduleType" />

      <!-- Related Items -->
      <PublicDetailRelated v-if="detail.related_items?.length"
        :items="detail.related_items"
        :module-type="moduleType" />

      <!-- Recommendations -->
      <PublicDetailRecommendations v-if="detail.recommendations?.length"
        :recommendations="detail.recommendations"
        :module-type="moduleType" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useSeo } from '@/composables/useSeo';

// Lazy load components
import { defineAsyncComponent } from 'vue';

const PublicDetailHero = defineAsyncComponent(() => import('./components/PublicDetailHero.vue'));
const PublicDetailGallery = defineAsyncComponent(() => import('./components/PublicDetailGallery.vue'));
const PublicDetailPricing = defineAsyncComponent(() => import('./components/PublicDetailPricing.vue'));
const PublicDetailMarketing = defineAsyncComponent(() => import('./components/PublicDetailMarketing.vue'));
const PublicDetailAvailability = defineAsyncComponent(() => import('./components/PublicDetailAvailability.vue'));
const PublicDetailDescription = defineAsyncComponent(() => import('./components/PublicDetailDescription.vue'));
const PublicDetailTechnical = defineAsyncComponent(() => import('./components/PublicDetailTechnical.vue'));
const PublicDetailIncluded = defineAsyncComponent(() => import('./components/PublicDetailIncluded.vue'));
const PublicDetailFAQ = defineAsyncComponent(() => import('./components/PublicDetailFAQ.vue'));
const PublicDetailDocuments = defineAsyncComponent(() => import('./components/PublicDetailDocuments.vue'));
const PublicDetailVideos = defineAsyncComponent(() => import('./components/PublicDetailVideos.vue'));
const PublicDetailReviews = defineAsyncComponent(() => import('./components/PublicDetailReviews.vue'));
const PublicDetailRelated = defineAsyncComponent(() => import('./components/PublicDetailRelated.vue'));
const PublicDetailRecommendations = defineAsyncComponent(() => import('./components/PublicDetailRecommendations.vue'));

const api = useApi();
const toast = useToast();
const route = useRoute();
const { setSeo } = useSeo();

const loading = ref(true);
const error = ref(null);
const detail = ref(null);

// Determine module type from route path
const moduleType = computed(() => {
  const path = route.path;
  if (path.includes('alquiler')) return 'renting';
  if (path.includes('tienda')) return 'shop';
  if (path.includes('servicios')) return 'service';
  return 'renting';
});

const moduleLabel = computed(() => {
  return {
    renting: 'Alquiler',
    shop: 'Producto',
    service: 'Servicio'
  }[moduleType.value];
});

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

    setSeo({
      title: detail.value.hero?.name || 'Detalle',
      description: detail.value.hero?.description || detail.value.seo?.meta_description || ''
    });
  } catch (err) {
    error.value = err.response?.data?.detail || 'No se pudo cargar el detalle';
    toast.error(error.value);
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchDetail());
</script>

<style scoped>
.public-detail {
  min-height: 100vh;
}

.skeleton-container {
  padding: 2rem 0;
}

.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 0.5rem;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 3rem;
  padding: 2rem 0;
}
</style>
