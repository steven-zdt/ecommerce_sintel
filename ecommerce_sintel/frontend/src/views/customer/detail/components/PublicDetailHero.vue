<template>
  <section class="hero-section">
    <div class="container-xl">
      <div class="row g-4 align-items-center">
        <!-- Hero Image -->
        <div class="col-lg-6">
          <img v-if="hero.hero_image" :src="hero.hero_image.url" :alt="hero.hero_image.alt_text"
            class="img-fluid hero-image rounded">
          <div v-else class="hero-placeholder rounded">No image available</div>
        </div>

        <!-- Hero Content -->
        <div class="col-lg-6">
          <!-- Badges -->
          <div v-if="hero.is_featured" class="mb-3">
            <span class="badge bg-info">Destacado</span>
          </div>

          <!-- Name & Brand -->
          <h1 class="display-5 fw-bold mb-2">{{ hero.name }}</h1>
          <p v-if="hero.brand_name" class="text-muted mb-1">{{ hero.brand_name }}</p>
          <p v-if="hero.category_name" class="text-muted mb-3">{{ hero.category_name }}</p>

          <!-- Description -->
          <p v-if="hero.description" class="lead mb-4">{{ hero.description }}</p>

          <!-- Rating -->
          <div v-if="hero.rating_count > 0" class="d-flex align-items-center mb-4">
            <div class="rating">
              <span class="badge bg-warning text-dark">⭐ {{ hero.rating_average.toFixed(1) }}</span>
              <span class="text-muted ms-2">({{ hero.rating_count }} reviews)</span>
            </div>
          </div>

          <!-- Availability Status -->
          <div class="alert" :class="hero.availability_status === 'available' ? 'alert-success' : 'alert-warning'">
            <strong>{{ hero.availability_label }}</strong>
            <p class="mb-0">{{ hero.availability_detail }}</p>
          </div>

          <!-- Pricing -->
          <div v-if="hero.pricing" class="pricing-box mb-4">
            <div class="display-4 fw-bold text-primary mb-2">
              {{ hero.pricing.formatted_promo_price }}
            </div>
            <p v-if="hero.pricing.has_promotion" class="text-muted">
              <del>{{ hero.pricing.formatted_reference_price }}</del>
              <span class="badge bg-danger ms-2">Ahorra {{ hero.pricing.discount_percentage }}%</span>
            </p>
          </div>

          <!-- CTA Button -->
          <button v-if="hero.cta_enabled" class="btn btn-primary btn-lg w-100 mb-3">
            {{ hero.cta_label }}
          </button>
          <button v-else class="btn btn-secondary btn-lg w-100 mb-3" disabled>
            {{ hero.cta_disabled_reason || 'No disponible' }}
          </button>

          <!-- Share Buttons -->
          <div class="d-flex gap-2">
            <button class="btn btn-outline-secondary btn-sm">Compartir</button>
            <button class="btn btn-outline-secondary btn-sm">Favorito</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  hero: {
    type: Object,
    required: true
  },
  moduleType: {
    type: String,
    required: true
  }
});
</script>

<style scoped>
.hero-section {
  padding: 3rem 0;
  border-bottom: 1px solid #dee2e6;
}

.hero-image {
  max-height: 500px;
  object-fit: cover;
}

.hero-placeholder {
  width: 100%;
  height: 500px;
  background: #f8f9fa;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6c757d;
}

.pricing-box {
  background: #f8f9fa;
  padding: 2rem;
  border-radius: 0.5rem;
}

.rating {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 992px) {
  .hero-section {
    padding: 2rem 0;
  }

  .display-5 {
    font-size: 2rem;
  }
}
</style>
