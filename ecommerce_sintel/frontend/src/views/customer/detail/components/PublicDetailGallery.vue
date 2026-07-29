<template>
  <section class="gallery-section">
    <div class="container-xl">
      <h2>Galería</h2>
      <div class="row g-3">
        <div v-for="(img, idx) in gallery.all_images" :key="idx" class="col-md-6 col-lg-4">
          <img :src="img.url" :alt="img.alt_text" class="img-fluid gallery-image rounded">
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  gallery: {
    type: Object,
    required: true
  }
});
</script>

<style scoped>
.gallery-section {
  padding: 3rem 0;
  border-bottom: 1px solid #dee2e6;
}

.gallery-image {
  height: 300px;
  object-fit: cover;
}
</style>
