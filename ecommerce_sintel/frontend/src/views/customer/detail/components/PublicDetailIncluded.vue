<template>
  <section class="included-section">
    <div class="container-xl">
      <h2>Lo que incluye</h2>
      <div class="row g-3">
        <div class="col-md-6">
          <h4 v-if="items && items.length > 0" class="text-success mb-3">Incluido</h4>
          <ul v-if="items && items.length > 0" class="list-group">
            <li v-for="item in items" :key="item" class="list-group-item">
              <span class="text-success me-2">✓</span> {{ item }}
            </li>
          </ul>
        </div>
        <div class="col-md-6">
          <h4 v-if="excludedItems && excludedItems.length > 0" class="text-danger mb-3">No incluido</h4>
          <ul v-if="excludedItems && excludedItems.length > 0" class="list-group">
            <li v-for="item in excludedItems" :key="item" class="list-group-item">
              <span class="text-danger me-2">✕</span> {{ item }}
            </li>
          </ul>
        </div>
      </div>
      <div v-if="requirements && requirements.length > 0" class="mt-4">
        <h4>Requisitos</h4>
        <ul class="list-group">
          <li v-for="req in requirements" :key="req" class="list-group-item">{{ req }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  items: Array,
  excludedItems: Array,
  requirements: Array
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
