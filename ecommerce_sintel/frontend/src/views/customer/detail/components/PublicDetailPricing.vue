<template>
  <section class="pricing-section">
    <div class="container-xl">
      <h2>Precio</h2>
      <div class="pricing-card">
        <div class="display-4 fw-bold text-primary">{{ pricing.formatted_promo_price }}</div>
        <p v-if="pricing.has_promotion" class="text-muted"><del>{{ pricing.formatted_reference_price }}</del></p>
        <p v-if="pricing.saving_message" class="text-success">{{ pricing.saving_message }}</p>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps(['pricing', 'moduleType']);
</script>
<style scoped>
.pricing-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
.pricing-card { background: #f8f9fa; padding: 2rem; border-radius: 0.5rem; }
</style>
