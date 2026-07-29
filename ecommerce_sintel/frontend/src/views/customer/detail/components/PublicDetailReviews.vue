<template>
  <section v-if="reviews && reviews.items && reviews.items.length > 0" class="reviews-section">
    <div class="container-xl">
      <h2>Reseñas ({{ reviews.total_count }})</h2>
      <div class="row g-3">
        <div v-for="review in reviews.items" :key="review.uuid" class="col-md-12">
          <div class="card">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h5 class="card-title">{{ review.author_name }}</h5>
                  <p class="text-muted small">⭐ {{ review.rating }}/5 • {{ review.created_at }}</p>
                </div>
              </div>
              <p class="card-text">{{ review.text }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  reviews: Object,
  moduleType: String
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
