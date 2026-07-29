<template>
  <section v-if="description" class="description-section">
    <div class="container-xl">
      <h2>Descripción</h2>
      <div class="description-content">{{ description.text }}</div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  description: Object
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
