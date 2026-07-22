<template>
  <div v-if="videos.length" class="eq-video-grid">
    <article v-for="video in videos" :key="video.uuid" class="eq-video-card">
      <button type="button" class="eq-video-thumb" @click="activeVideo = video">
        <img v-if="video.thumbnail" :src="video.thumbnail" :alt="video.title">
        <div v-else class="eq-video-thumb-fallback"><i class="bi bi-camera-reels"></i></div>
        <i class="bi bi-play-circle-fill eq-video-play"></i>
      </button>
      <span v-if="video.title" class="eq-video-title">{{ video.title }}</span>
    </article>
  </div>

  <Teleport to="body">
    <div v-if="activeVideo" class="modal d-block eq-video-modal" tabindex="-1" @click.self="activeVideo = null">
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ activeVideo.title || 'Video del equipo' }}</h5>
            <button type="button" class="btn-close" @click="activeVideo = null"></button>
          </div>
          <div class="modal-body p-0">
            <div class="ratio ratio-16x9">
              <video v-if="activeVideo.source_type === 'MP4'" :src="activeVideo.video_file" controls autoplay></video>
              <iframe v-else :src="activeVideo.embed_url" title="Video del equipo" allowfullscreen allow="autoplay; encrypted-media"></iframe>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="activeVideo" class="modal-backdrop show"></div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue';

defineProps({
  videos: { type: Array, default: () => [] },
});

const activeVideo = ref(null);
</script>

<style scoped>
.eq-video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: .85rem; }
.eq-video-card { border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; background: #fff; }
.eq-video-thumb {
  position: relative; display: block; width: 100%; aspect-ratio: 16 / 9;
  border: 0; padding: 0; background: #0f172a; overflow: hidden;
}
.eq-video-thumb img { width: 100%; height: 100%; object-fit: cover; }
.eq-video-thumb-fallback {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  color: #64748b; font-size: 2rem;
}
.eq-video-play {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  color: #fff; font-size: 2.4rem; text-shadow: 0 2px 8px rgba(0, 0, 0, .4);
}
.eq-video-title { display: block; padding: .55rem .75rem; color: #0f172a; font-size: .8rem; font-weight: 700; }
.eq-video-modal { z-index: 1060; }
.eq-video-modal iframe, .eq-video-modal video { width: 100%; height: 100%; border: 0; }
</style>
