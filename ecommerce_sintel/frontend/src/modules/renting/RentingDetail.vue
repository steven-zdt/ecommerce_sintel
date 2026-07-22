<template>
  <div class="renting-detail">
    <!-- Galería/Imagen Principal -->
    <div class="position-relative mb-4 rounded-3 overflow-hidden shadow-sm" style="height: 250px;">
      <img 
        v-if="equipment.images && equipment.images.length" 
        :src="equipment.images.find(img => img.is_primary)?.image || equipment.images[0].image" 
        class="w-100 h-100 object-fit-cover"
      />
      <div v-else class="w-100 h-100 d-flex align-items-center justify-content-center bg-light text-muted">
        <i class="bi bi-truck display-3"></i>
      </div>
      <div class="position-absolute bottom-0 start-0 w-100 p-3 bg-gradient-dark">
        <h5 class="text-white fw-bold mb-0">{{ equipment.name }}</h5>
        <div class="text-white-50 smaller">{{ equipment.brand?.name }} • {{ equipment.category?.name }}</div>
      </div>
    </div>

    <!-- Descripción -->
    <div class="mb-4">
      <h6 class="fw-bold text-dark mb-2 small text-uppercase letter-spacing-1">Descripción del Equipo</h6>
      <p class="text-muted small mb-0">{{ equipment.description }}</p>
    </div>

    <!-- Variantes / Modelos -->
    <div v-if="equipment.variants && equipment.variants.length">
      <h6 class="fw-bold mb-3 d-flex align-items-center small text-uppercase letter-spacing-1">
        <i class="bi bi-info-circle me-2 text-primary"></i>
        Disponibilidad y Tarifas
      </h6>
      
      <div class="row g-3">
        <div v-for="variant in equipment.variants" :key="variant.uuid" class="col-12">
          <div class="card border border-light-subtle shadow-none bg-light-subtle">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start mb-3">
                <div>
                  <div class="fw-bold text-dark">{{ variant.sku }}</div>
                  <div 
                    class="badge rounded-pill mt-1"
                    :class="variant.stock > 0 ? 'bg-success text-white' : 'bg-danger text-white'"
                  >
                    {{ variant.stock > 0 ? 'Disponible: ' + variant.stock : 'Agotado' }}
                  </div>
                </div>
                <div class="text-end">
                  <div class="fw-bold text-primary fs-5">{{ formatCurrency(variant.rental_price_per_day) }}</div>
                  <div class="text-muted smaller">Tarifa por día</div>
                </div>
              </div>

              <div class="row g-2 pt-2 border-top border-white">
                <div class="col-6">
                  <div class="d-flex flex-column">
                    <span class="text-muted smaller">Precio / Hora</span>
                    <span class="fw-medium text-dark">{{ formatCurrency(variant.rental_price_per_hour) }}</span>
                  </div>
                </div>
                <div class="col-6 text-end">
                  <div class="d-flex flex-column">
                    <span class="text-muted smaller">Depósito Sugerido</span>
                    <span class="fw-medium text-dark">{{ formatCurrency(variant.rental_price_per_day * 2) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Especificaciones Técnicas (Placeholder/Extra) -->
    <div class="mt-4 p-3 bg-primary-subtle rounded-3 border border-primary-subtle">
      <div class="d-flex gap-3">
        <div class="bg-primary text-white rounded-circle p-2 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
          <i class="bi bi-shield-check"></i>
        </div>
        <div>
          <h6 class="fw-bold text-primary mb-1 small">Garantía Sintel Pro</h6>
          <p class="text-primary-emphasis smaller mb-0">Todos nuestros equipos cuentan con mantenimiento certificado y seguro contra fallas mecánicas.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  equipment: { type: Object, required: true }
});

function formatCurrency(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0
  }).format(value);
}
</script>

<style scoped>
.smaller {
  font-size: 0.75rem;
}
.letter-spacing-1 {
  letter-spacing: 0.5px;
}
.object-fit-cover {
  object-fit: cover;
}
.bg-gradient-dark {
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
}
</style>
