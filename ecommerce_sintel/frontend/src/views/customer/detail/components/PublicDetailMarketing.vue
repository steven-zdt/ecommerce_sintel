<template>
  <section class="marketing-section">
    <div class="container-xl">
      <h2>Información Comercial</h2>
      <div v-if="marketing.main_message" class="alert alert-info">{{ marketing.main_message }}</div>
      <div v-if="marketing.tags?.length" class="mb-3">
        <span v-for="tag in marketing.tags" :key="tag.code" class="badge me-2" :class="`bg-${tag.color}`">{{ tag.label }}</span>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps(['marketing']);
</script>
<style scoped>
.marketing-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
