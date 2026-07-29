<template>
  <section v-if="videos && videos.length > 0" class="videos-section">
    <div class="container-xl">
      <h2>Vídeos</h2>
      <div class="row g-3">
        <div v-for="video in videos" :key="video.uuid" class="col-md-6">
          <div class="ratio ratio-16x9">
            <iframe :src="video.url" allowfullscreen></iframe>
          </div>
          <p v-if="video.title" class="mt-2">{{ video.title }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  videos: Array
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
