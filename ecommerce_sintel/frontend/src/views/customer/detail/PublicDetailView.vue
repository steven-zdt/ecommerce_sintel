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

      <!-- ══════════════════════════════════════════════════════════════════
           Dispatch por modulo. Las 3 ramas son mutuamente excluyentes y
           viven cada una en su propio componente (item P2-2 de la
           auditoria) -- este archivo se queda como shell: loading/error,
           breadcrumb, SEO y la orquestacion de los fetch.

           Las condiciones `v-if` son exactamente las de antes de la
           descomposicion: cada hijo se monta solo cuando sus datos ya
           estan resueltos, por lo que la secuencia de carga percibida no
           cambia (un unico skeleton hasta que todo esta listo).
           ══════════════════════════════════════════════════════════════════ -->
      <RentingDetailContent
        v-if="moduleType === 'renting'"
        :detail="detail"
      />

      <ServiceDetailContent
        v-else-if="moduleType === 'service' && serviceDetail"
        :service-detail="serviceDetail"
        :service-packages="servicePackages"
      />

      <ShopDetailContent
        v-else-if="moduleType === 'shop' && shopProduct"
        :product="shopProduct"
        :initial-reviews="shopReviews"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useSeo } from '@/composables/useSeo';
import { servicesService } from '@/services/technical_services/servicesService';
import { shopService } from '@/services/shop/shopService';

import RentingDetailContent from './RentingDetailContent.vue';
import ServiceDetailContent from './ServiceDetailContent.vue';
import ShopDetailContent from './ShopDetailContent.vue';

const api = useApi();
const { error: showError } = useToast();
const route = useRoute();
const { setSeo } = useSeo();

const loading = ref(true);
const error = ref(null);
const detail = ref(null);

// Rama Services: el DTO unificado no alcanza (ver plan
// structured-strolling-sparkle.md), se complementa con un fetch propio a
// endpoints publicos ya existentes. El resultado se entrega ya resuelto a
// ServiceDetailContent.vue.
const serviceDetail = ref(null);
const servicePackages = ref([]);

// Rama Shop: mismo caso. A diferencia de Services, un fallo aqui SI debe
// propagarse (no hay rama v-else generica a la que degradar) -- fetchDetail()
// captura la excepcion y muestra el estado de error existente.
const shopProduct = ref(null);
const shopReviews = ref([]);

const moduleType = computed(() => {
  const path = route.path;
  if (path.includes('alquiler')) return 'renting';
  if (path.includes('tienda')) return 'shop';
  if (path.includes('servicios')) return 'service';
  return 'renting';
});

// Helper functions (shell: estado de error + breadcrumb)
function getModuleLabel() {
  return { renting: 'Equipo', shop: 'Producto', service: 'Servicio' }[moduleType.value];
}

function getModuleIcon() {
  return { renting: 'bi-hdd-rack', shop: 'bi-bag-check', service: 'bi-tools' }[moduleType.value];
}

function getBreadcrumbPath() {
  return { renting: '/alquiler', shop: '/tienda', service: '/servicios' }[moduleType.value];
}

async function fetchServiceRichDetail(uuid) {
  try {
    const [detailData, packagesData] = await Promise.all([
      servicesService.detail(uuid),
      servicesService.packages(uuid).catch(() => []),
    ]);
    serviceDetail.value = detailData;
    servicePackages.value = packagesData || [];
  } catch {
    serviceDetail.value = null;
    servicePackages.value = [];
  }
}

async function fetchShopRichDetail(uuid) {
  shopProduct.value = await shopService.detail(uuid);
  // Las resenas se resuelven dentro del mismo ciclo de carga (igual que
  // antes de la descomposicion) para que la pagina aparezca completa de
  // una sola vez, sin spinner secundario.
  try {
    const data = await shopService.reviews(uuid);
    shopReviews.value = data.results ?? data;
  } catch {
    shopReviews.value = [];
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

    if (moduleType.value === 'service') {
      await fetchServiceRichDetail(uuid);
    } else if (moduleType.value === 'shop') {
      await fetchShopRichDetail(uuid);
    }

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
</style>
