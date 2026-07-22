<template>
  <div class="bv-gallery">
    <div class="bv-gallery-main" :style="themeStyle">
      <img v-if="activeImageUrl" :src="activeImageUrl" :alt="activeImageAlt" class="bv-gallery-img">
      <div v-else class="bv-gallery-placeholder">
        <i :class="['bi', iconClass]"></i>
      </div>
      <slot name="badge" :active-image="activeImage" :active-index="activeIndex" />
    </div>

    <div v-if="images.length > 1" class="bv-gallery-thumbs">
      <button
        v-for="(img, index) in images"
        :key="imageUrl(img) + index"
        type="button"
        class="bv-gallery-thumb"
        :class="{ active: activeIndex === index }"
        :style="themeStyle"
        @click="activeIndex = index"
      >
        <img :src="imageUrl(img)" :alt="`Vista ${index + 1}`">
      </button>
    </div>
  </div>
</template>

<script setup>
/**
 * BaseGallery.vue -- fusion de renting/detail/EquipmentGallery.vue y
 * services/detail/ServiceGallery.vue (Fase 2 §2.1). Acepta `images` como
 * array de strings (URL directa, patron Services) o de objetos con
 * `.image`/`.url` (patron Renting) sin que el consumidor tenga que
 * remapear su prop existente. El badge flotante (tipo de imagen en Renting,
 * "Destacado" en Services) se deja como slot con scope -- son datos y
 * posiciones distintas por dominio, forzar una sola API de badge hubiera
 * añadido props sin reducir codigo real.
 */
import { ref, computed } from 'vue';

const props = defineProps({
  images:    { type: Array, default: () => [] }, // string[] | {image|url, alt_text?}[]
  title:     { type: String, default: '' },
  iconClass: { type: String, default: 'bi-tools' },
  theme:     { type: String, default: 'services' }, // 'renting' | 'services'
});

const THEMES = {
  renting: {
    placeholderBg: 'linear-gradient(135deg, #f0f9ff, #eef2ff)',
    placeholderColor: '#6366f1',
    thumbActive: '#2563eb',
    thumbActiveShadow: 'rgba(37,99,235,.16)',
    imageFit: 'contain',
  },
  services: {
    placeholderBg: 'linear-gradient(135deg, #eff6ff, #ecfeff)',
    placeholderColor: '#0e7490',
    thumbActive: '#0f766e',
    thumbActiveShadow: 'rgba(15,118,110,.16)',
    imageFit: 'cover',
  },
};

const activeIndex = ref(0);

function imageUrl(img) {
  return typeof img === 'string' ? img : (img?.image || img?.url || '');
}
function imageAlt(img) {
  return typeof img === 'string' ? '' : (img?.alt_text || img?.alt || '');
}

const activeImage = computed(() => props.images[activeIndex.value] || null);
const activeImageUrl = computed(() => (activeImage.value ? imageUrl(activeImage.value) : ''));
const activeImageAlt = computed(() => imageAlt(activeImage.value) || props.title);

const themeStyle = computed(() => {
  const t = THEMES[props.theme] || THEMES.services;
  return {
    '--bg-placeholder': t.placeholderBg,
    '--bg-placeholder-color': t.placeholderColor,
    '--bg-thumb-active': t.thumbActive,
    '--bg-thumb-active-shadow': t.thumbActiveShadow,
    '--bg-image-fit': t.imageFit,
  };
});
</script>

<style scoped>
.bv-gallery-main {
  position: relative;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  aspect-ratio: 1 / .86;
  box-shadow: 0 16px 34px rgba(15,23,42,.08);
}
.bv-gallery-img { width: 100%; height: 100%; object-fit: var(--bg-image-fit); }
.bv-gallery-placeholder {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-placeholder);
  color: var(--bg-placeholder-color); font-size: 5rem;
}
.bv-gallery-thumbs { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: .7rem; }
.bv-gallery-thumb {
  width: 72px; height: 72px;
  border: 1px solid #e2e8f0; border-radius: 12px;
  background: #fff; padding: 3px; overflow: hidden;
}
.bv-gallery-thumb.active { border-color: var(--bg-thumb-active); box-shadow: 0 0 0 2px var(--bg-thumb-active-shadow); }
.bv-gallery-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 9px; }
</style>
