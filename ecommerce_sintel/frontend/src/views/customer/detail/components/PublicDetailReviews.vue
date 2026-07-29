<template>
  <section class="detail-section">
    <div class="container-xl">
      <p>{{ title }} component</p>
    </div>
  </section>
</template>
<script setup>
defineProps(['availability', 'description', 'technical', 'items', 'excludedItems', 'requirements', 'faq', 'documents', 'videos', 'reviews', 'recommendations', 'moduleType']);
const title = inject('COMPONENT_TITLE', 'Section');
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
