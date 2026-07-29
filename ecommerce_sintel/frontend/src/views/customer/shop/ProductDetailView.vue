<template>
  <div class="product-detail">
    <div class="container-xl py-3 py-lg-4">
      <!-- Breadcrumb -->
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/tienda" class="text-decoration-none text-muted">
              Tienda
            </RouterLink>
          </li>
          <li v-if="product?.hero?.category_name" class="breadcrumb-item text-muted">
            {{ product.hero.category_name }}
          </li>
          <li class="breadcrumb-item active">{{ product?.hero?.name }}</li>
        </ol>
      </nav>

      <!-- Loading -->
      <div v-if="loading" class="skeleton" style="height:400px"></div>

      <!-- Content -->
      <div v-else-if="product" class="row g-4">
        <div class="col-lg-5">
          <BaseGallery :images="product.media?.gallery?.all_images || []" />
        </div>
        <div class="col-lg-7">
          <TagBadge v-for="tag in product.marketing?.tags" :key="tag.code" :tag="tag" />
          <h1>{{ product.hero?.name }}</h1>
          <p>{{ product.hero?.description }}</p>

          <UrgencyBanner :status="product.availability?.status" :available-now="product.availability?.available_now || 0" />
          <DiscountBadge v-if="product.pricing?.has_promotion" :discount="product.pricing?.discount_percentage" :amount="product.pricing?.formatted_discount_amount" />

          <div class="pricing-card">
            <div class="pricing-value">{{ product.pricing?.formatted_price_per_day }}</div>
            <button class="btn btn-primary w-100 mt-3" @click="addToCart">Agregar al carrito</button>
          </div>

          <RatingDisplay v-if="product.reviews" :rating="product.reviews" />
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
const product = ref(null);

async function fetchProduct() {
  try {
    const slug = route.params.slug;
    const res = await api.get(`shop/products/${slug}/detail/`);
    product.value = res.data;
    setSeo({ title: product.value.hero?.name, description: product.value.hero?.description });
  } catch {
    toast.error('Producto no encontrado');
  } finally {
    loading.value = false;
  }
}

function addToCart() {
  toast.success('Producto agregado al carrito');
}

onMounted(() => fetchProduct());
</script>

<style scoped>
.product-detail { min-height: 100vh; }
.pricing-card { background: var(--bs-gray-100); padding: 1.5rem; border-radius: 0.5rem; }
.pricing-value { font-size: 2rem; font-weight: 700; color: var(--bs-primary); }
.skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); animation: loading 1.5s infinite; }
@keyframes loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
