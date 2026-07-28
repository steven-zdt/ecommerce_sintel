<template>
  <div class="service-detail">
    <!-- Header/Banner -->
    <div class="position-relative mb-4 rounded-3 overflow-hidden bg-light" style="height: 200px;">
      <img 
        v-if="service.images && service.images.length" 
        :src="service.images.find(img => img.is_primary)?.image || service.images[0].image" 
        class="w-100 h-100 object-fit-cover"
      />
      <div v-else class="w-100 h-100 d-flex align-items-center justify-content-center text-muted">
        <i class="bi bi-tools display-4"></i>
      </div>
      <div class="position-absolute top-0 end-0 p-3">
        <span v-if="service.is_featured" class="badge bg-warning text-dark rounded-pill shadow-sm">
          <i class="bi bi-star-fill me-1"></i> Destacado
        </span>
      </div>
    </div>

    <!-- Info Básica -->
    <div class="mb-4">
      <div class="d-flex gap-2 mb-2">
        <span class="badge bg-light text-secondary border rounded-pill">{{ service.category?.name }}</span>
        <span class="badge bg-info-subtle text-info border border-info-subtle rounded-pill">{{ service.level?.name }}</span>
      </div>
      <h5 class="fw-bold text-dark mb-2">{{ service.name }}</h5>
      <p class="text-muted small mb-0">{{ service.description }}</p>
    </div>

    <!-- Variantes -->
    <div v-if="service.variants && service.variants.length">
      <h6 class="fw-bold mb-3 d-flex align-items-center">
        <i class="bi bi-layers me-2 text-primary"></i>
        Variantes y Precios
      </h6>
      
      <div class="list-group list-group-flush border rounded-3 overflow-hidden">
        <div 
          v-for="variant in service.variants" 
          :key="variant.uuid"
          class="list-group-item p-3 border-bottom"
        >
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <div class="fw-bold text-dark">{{ variant.sku }}</div>
              <div class="text-muted smaller">SKU del servicio</div>
            </div>
            <div class="text-end">
              <div class="fw-bold text-primary fs-5">{{ formatCurrency(variant.calculated_price) }}</div>
              <span v-if="variant.is_default" class="badge bg-success-subtle text-success rounded-pill smaller">Principal</span>
            </div>
          </div>

          <div class="row g-3 mt-1">
            <div class="col-6">
              <div class="d-flex align-items-center gap-2">
                <div class="bg-light p-2 rounded-circle">
                  <i class="bi bi-clock text-muted"></i>
                </div>
                <div>
                  <div class="fw-medium small">{{ variant.estimated_hours }}h</div>
                  <div class="text-muted smaller">Estimadas</div>
                </div>
              </div>
            </div>
            <div class="col-6">
              <div class="d-flex align-items-center gap-2">
                <div class="bg-light p-2 rounded-circle">
                  <i class="bi bi-lightning text-muted"></i>
                </div>
                <div>
                  <div class="fw-medium small">{{ variant.complexity_factor }}x</div>
                  <div class="text-muted smaller">Complejidad</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Materiales -->
          <div v-if="variant.materials && variant.materials.length" class="mt-3 bg-light rounded-3 p-3">
            <div class="fw-bold text-dark smaller mb-2 text-uppercase letter-spacing-1">Materiales Incluidos</div>
            <div class="d-flex flex-wrap gap-2">
              <div 
                v-for="mat in variant.materials" 
                :key="mat.uuid"
                class="bg-white border rounded px-2 py-1 d-flex align-items-center"
              >
                <span class="text-dark fw-medium smaller me-1">{{ mat.quantity }}x</span>
                <span class="text-muted smaller text-truncate" style="max-width: 120px;">{{ mat.product_name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatCOP } from '@/utils/money';

const props = defineProps({
  service: { type: Object, required: true }
});

function formatCurrency(value) {
  return formatCOP(value, { withSymbol: true });
}
</script>

<style scoped>
.smaller {
  font-size: 0.7rem;
}
.letter-spacing-1 {
  letter-spacing: 0.5px;
}
.object-fit-cover {
  object-fit: cover;
}
</style>
