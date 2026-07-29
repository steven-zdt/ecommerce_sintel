<template>
  <div class="service-detail">
    <div class="container-xl py-3 py-lg-4">
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/servicios" class="text-decoration-none text-muted">Servicios</RouterLink>
          </li>
          <li class="breadcrumb-item active">{{ service?.hero?.name }}</li>
        </ol>
      </nav>

      <div v-if="loading" class="skeleton" style="height:400px"></div>

      <div v-else-if="service" class="row g-4">
        <div class="col-lg-5">
          <BaseGallery :images="service.media?.gallery?.all_images || []" />
        </div>
        <div class="col-lg-7">
          <TagBadge v-for="tag in service.marketing?.tags" :key="tag.code" :tag="tag" />
          <h1>{{ service.hero?.name }}</h1>
          <p>{{ service.hero?.description }}</p>

          <UrgencyBanner :status="service.availability?.status" :available-now="service.availability?.available_now || 0" />
          <DiscountBadge v-if="service.pricing?.has_promotion" :discount="service.pricing?.discount_percentage" :amount="service.pricing?.formatted_discount_amount" />

          <div class="pricing-card">
            <div class="pricing-value">{{ service.pricing?.formatted_price_per_hour || 'A cotizar' }}</div>
            <button class="btn btn-primary w-100 mt-3" @click="requestService">Solicitar servicio</button>
          </div>

          <RatingDisplay v-if="service.reviews" :rating="service.reviews" />
        </div>
      </div>

      <!-- Technicians -->
      <div v-if="service?.services?.included_items" class="mt-5 pt-5 border-top">
        <h2 class="mb-4">Equipo profesional</h2>
        <div class="row g-3">
          <div v-for="item in service.services.included_items" :key="item.title" class="col-md-6 col-lg-4">
            <div class="technician-card">
              <h6>{{ item.title }}</h6>
              <p class="text-muted">{{ item.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useSeo } from '@/composables/useSeo';

import BaseGallery from '@/components/base/BaseGallery.vue';
import DiscountBadge from '@/components/marketplace/DiscountBadge.vue';
import UrgencyBanner from '@/components/marketplace/UrgencyBanner.vue';
import TagBadge from '@/components/marketplace/TagBadge.vue';
import RatingDisplay from '@/components/marketplace/RatingDisplay.vue';

const api = useApi();
const toast = useToast();
const route = useRoute();
const { setSeo } = useSeo();

const loading = ref(true);
const service = ref(null);

async function fetchService() {
  try {
    const slug = route.params.slug;
    const res = await api.get(`technical-services/services/${slug}/detail/`);
    service.value = res.data;
    setSeo({ title: service.value.hero?.name, description: service.value.hero?.description });
  } catch {
    toast.error('Servicio no encontrado');
  } finally {
    loading.value = false;
  }
}

function requestService() {
  toast.success('Solicitud enviada. Nos contactaremos pronto.');
}

onMounted(() => fetchService());
</script>

<style scoped>
.service-detail { min-height: 100vh; }
.pricing-card { background: var(--bs-gray-100); padding: 1.5rem; border-radius: 0.5rem; }
.pricing-value { font-size: 2rem; font-weight: 700; color: var(--bs-primary); }
.technician-card { background: var(--bs-gray-100); padding: 1.5rem; border-radius: 0.5rem; }
.skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); animation: loading 1.5s infinite; }
@keyframes loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
