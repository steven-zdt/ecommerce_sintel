<template>
  <section v-if="recommendations && recommendations.length > 0" class="recommendations-section">
    <div class="container-xl">
      <h2>Complementa tu compra</h2>
      <p class="text-muted mb-4">Productos y servicios recomendados que complementan esta compra</p>
      <div class="row g-3">
        <div v-for="item in recommendations" :key="item.uuid" class="col-lg-3 col-md-4">
          <div class="card h-100 recommendation-card">
            <div class="card-img-wrapper">
              <img v-if="item.image" :src="item.image" class="card-img-top" :alt="item.name" loading="lazy">
              <div v-else class="card-img-placeholder">
                <span class="text-muted">No image</span>
              </div>
              <div v-if="item.reason" class="recommendation-badge">{{ item.reason }}</div>
            </div>
            <div class="card-body d-flex flex-column">
              <h5 class="card-title">{{ item.name }}</h5>
              <p v-if="item.category" class="text-muted small">{{ item.category }}</p>
              <div class="mt-auto">
                <p class="h5 text-primary fw-bold mb-3">{{ formatPrice(item.price) }}</p>
                <RouterLink
                  :to="getItemRoute(item)"
                  class="btn btn-sm btn-outline-primary w-100">
                  Ver detalles
                </RouterLink>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
import { computed } from 'vue';

const props = defineProps({
  recommendations: Array,
  moduleType: String
});

const formatPrice = (price) => {
  if (!price) return 'A cotizar';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(price);
};

const getItemRoute = (item) => {
  if (props.moduleType === 'renting') {
    return `/alquiler/${item.uuid}`;
  } else if (props.moduleType === 'shop') {
    return `/tienda/${item.uuid}`;
  } else if (props.moduleType === 'service') {
    return `/servicios/${item.uuid}`;
  }
  return '/';
};
</script>
<style scoped>
.recommendations-section {
  padding: 3rem 0;
  border-top: 1px solid #dee2e6;
  border-bottom: 1px solid #dee2e6;
  background-color: #f8f9fa;
}

.recommendation-card {
  transition: all 0.3s ease;
  border: 1px solid #dee2e6;
  cursor: pointer;
}

.recommendation-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

.card-img-wrapper {
  position: relative;
  overflow: hidden;
  height: 250px;
  background-color: #f8f9fa;
}

.card-img-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-img-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #e9ecef;
}

.recommendation-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: #ffc107;
  color: #333;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

@media (max-width: 768px) {
  .recommendations-section {
    padding: 2rem 0;
  }

  .col-md-4 {
    flex: 0 0 calc(50% - 0.75rem);
  }
}
</style>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
