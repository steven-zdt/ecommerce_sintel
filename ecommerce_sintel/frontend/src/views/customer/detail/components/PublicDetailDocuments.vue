<template>
  <section v-if="documents && documents.length > 0" class="documents-section">
    <div class="container-xl">
      <h2>Documentos</h2>
      <div class="row g-3">
        <div v-for="doc in documents" :key="doc.uuid" class="col-md-4">
          <a :href="doc.url" class="card text-decoration-none" download>
            <div class="card-body text-center">
              <p class="text-muted mb-2">📄</p>
              <p class="card-text">{{ doc.name }}</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  documents: Array
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
