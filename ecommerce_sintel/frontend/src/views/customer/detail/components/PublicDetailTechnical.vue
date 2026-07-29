<template>
  <section v-if="technical" class="technical-section">
    <div class="container-xl">
      <h2>Especificaciones Técnicas</h2>
      <div class="row g-3">
        <div v-for="(value, key) in technical" :key="key" class="col-md-6">
          <div class="card">
            <div class="card-body">
              <p class="text-muted mb-2">{{ key }}</p>
              <p class="mb-0">{{ value }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  technical: Object
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
