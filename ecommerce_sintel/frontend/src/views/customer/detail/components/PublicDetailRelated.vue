<template>
  <section v-if="items && items.length > 0" class="related-section">
    <div class="container-xl">
      <h2>Productos Relacionados</h2>
      <div class="row g-3">
        <div v-for="item in items" :key="item.uuid" class="col-md-3">
          <div class="card h-100">
            <img v-if="item.image" :src="item.image" class="card-img-top" :alt="item.name">
            <div class="card-body">
              <h5 class="card-title">{{ item.name }}</h5>
              <p class="card-text text-muted small">{{ item.category }}</p>
              <p class="h5 text-primary">${{ item.price }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  items: Array,
  moduleType: String
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
