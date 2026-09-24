<template>
  <div class="bv-gallery" :class="{ 'bv-gallery--vertical': thumbLayout === 'vertical' }">
    <div
      class="bv-gallery-main"
      :class="{ 'is-zoomable': zoom && activeImageUrl, 'is-expandable': lightbox && activeImageUrl }"
      :style="themeStyle"
      @mousemove="onZoomMove"
      @mouseleave="onZoomLeave"
      @click="openLightbox"
    >
      <img
        v-if="activeImageUrl"
        :src="activeImageUrl"
        :alt="activeImageAlt"
        class="bv-gallery-img"
        :style="zoomStyle"
      >
      <div v-else class="bv-gallery-placeholder">
        <i :class="['bi', iconClass]"></i>
      </div>
      <span v-if="lightbox && activeImageUrl" class="bv-gallery-expand-hint" aria-hidden="true">
        <i class="bi bi-arrows-fullscreen"></i>
      </span>
      <slot name="badge" :active-image="activeImage" :active-index="activeIndex" />
    </div>

    <!-- Plan "Rediseno ServiceForm + Content/Media" FASE 6 (2026-08-14) --
         caption/description por imagen, opt-in via `show-caption` (default
         false, Shop/Renting sin cambios). Solo Services los tiene hoy
         (ServiceImage.caption/description); si `img` no los trae, no
         renderiza nada -- no asume el campo existe en todos los dominios. -->
    <div v-if="showCaption && (activeImageCaption || activeImageDescription)" class="bv-gallery-caption">
      <p v-if="activeImageCaption" class="bv-gallery-caption-title">{{ activeImageCaption }}</p>
      <p v-if="activeImageDescription" class="bv-gallery-caption-desc">{{ activeImageDescription }}</p>
    </div>

    <div v-if="images.length > 1" class="bv-gallery-thumbs">
      <button
        v-for="(img, index) in images"
        :key="imageUrl(img) + index"
        type="button"
        class="bv-gallery-thumb"
        :class="{ active: activeIndex === index }"
        :style="themeStyle"
        :aria-label="`Ver imagen ${index + 1} de ${images.length}`"
        :aria-current="activeIndex === index ? 'true' : 'false'"
        @click="activeIndex = index"
      >
        <img :src="imageUrl(img)" :alt="`Vista ${index + 1}`">
      </button>
    </div>
  </div>

  <!-- Lightbox (opt-in via prop `lightbox`, default false -- Renting/Services sin
       cambios). Teleport a <body> para escapar el `position: sticky` del contenedor
       padre (Shop, .gallery-sticky) sin problemas de stacking context/overflow. -->
  <Teleport to="body">
    <div
      v-if="lightbox && lightboxOpen"
      class="bv-lightbox-backdrop"
      role="dialog"
      aria-modal="true"
      :aria-label="`Imagen ampliada: ${activeImageAlt}`"
      tabindex="-1"
      ref="lightboxEl"
      @click.self="closeLightbox"
      @keydown.esc="closeLightbox"
      @keydown.left="prevImage"
      @keydown.right="nextImage"
    >
      <button type="button" class="bv-lightbox-close" aria-label="Cerrar imagen ampliada" @click="closeLightbox">
        <i class="bi bi-x-lg"></i>
      </button>
      <button
        v-if="images.length > 1"
        type="button"
        class="bv-lightbox-nav bv-lightbox-prev"
        aria-label="Imagen anterior"
        @click="prevImage"
      >
        <i class="bi bi-chevron-left"></i>
      </button>
      <img v-if="activeImageUrl" :src="activeImageUrl" :alt="activeImageAlt" class="bv-lightbox-img">
      <button
        v-if="images.length > 1"
        type="button"
        class="bv-lightbox-nav bv-lightbox-next"
        aria-label="Imagen siguiente"
        @click="nextImage"
      >
        <i class="bi bi-chevron-right"></i>
      </button>
      <span v-if="images.length > 1" class="bv-lightbox-counter">{{ activeIndex + 1 }} / {{ images.length }}</span>
    </div>
  </Teleport>
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
import { ref, computed, nextTick, watch } from 'vue';

const props = defineProps({
  images:    { type: Array, default: () => [] }, // string[] | {image|url, alt_text?}[]
  title:     { type: String, default: '' },
  iconClass: { type: String, default: 'bi-tools' },
  theme:     { type: String, default: 'services' }, // 'renting' | 'services' | 'shop'
  // Generalizado para Shop (redesign hero PDP): layout de miniaturas y zoom on-hover son
  // opt-in via props, default preserva el comportamiento original (horizontal, sin zoom)
  // para Renting/Services sin tocar ningun call site existente.
  thumbLayout: { type: String, default: 'horizontal' }, // 'horizontal' | 'vertical'
  zoom:        { type: Boolean, default: false },
  // Plan "Rediseno ServiceForm + Content/Media" FASE 6 (2026-08-14) --
  // opt-in, default false: Shop/Renting no tienen caption/description en
  // su modelo de imagen hoy, no se les fuerza este bloque.
  showCaption: { type: Boolean, default: false },
  // Rediseno PDP 3 columnas (2026-09-16, gap real detectado en auditoria:
  // no existia click-to-expand/lightbox) -- opt-in, default false, Renting/
  // Services sin cambios. Reusa `images`/`activeIndex` ya existentes, no
  // duplica estado.
  lightbox: { type: Boolean, default: false },
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
  shop: {
    placeholderBg: 'linear-gradient(135deg, #eff6ff, #f8fafc)',
    placeholderColor: '#2563eb',
    thumbActive: '#2563eb',
    thumbActiveShadow: 'rgba(37,99,235,.16)',
    imageFit: 'contain',
  },
};

const activeIndex = ref(0);
const zoomOrigin = ref('center');

function onZoomMove(e) {
  if (!props.zoom) return;
  const rect = e.currentTarget.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * 100;
  const y = ((e.clientY - rect.top) / rect.height) * 100;
  zoomOrigin.value = `${x}% ${y}%`;
}
function onZoomLeave() {
  zoomOrigin.value = 'center';
}
const zoomStyle = computed(() => (props.zoom ? { transformOrigin: zoomOrigin.value } : {}));

function imageUrl(img) {
  return typeof img === 'string' ? img : (img?.image || img?.url || '');
}
function imageAlt(img) {
  return typeof img === 'string' ? '' : (img?.alt_text || img?.alt || '');
}
function imageCaption(img) {
  return typeof img === 'string' ? '' : (img?.caption || '');
}
function imageDescription(img) {
  return typeof img === 'string' ? '' : (img?.description || '');
}

const activeImage = computed(() => props.images[activeIndex.value] || null);
const activeImageUrl = computed(() => (activeImage.value ? imageUrl(activeImage.value) : ''));
const activeImageAlt = computed(() => imageAlt(activeImage.value) || props.title);
const activeImageCaption = computed(() => imageCaption(activeImage.value));
const activeImageDescription = computed(() => imageDescription(activeImage.value));

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

// Lightbox (opt-in) -- reusa activeIndex/images, no duplica estado de la galeria.
const lightboxOpen = ref(false);
const lightboxEl = ref(null);

function openLightbox() {
  if (!props.lightbox || !activeImageUrl.value) return;
  lightboxOpen.value = true;
}
function closeLightbox() {
  lightboxOpen.value = false;
}
function prevImage() {
  if (props.images.length < 2) return;
  activeIndex.value = (activeIndex.value - 1 + props.images.length) % props.images.length;
}
function nextImage() {
  if (props.images.length < 2) return;
  activeIndex.value = (activeIndex.value + 1) % props.images.length;
}
// Foco al abrir (accesibilidad -- el dialog debe poder cerrarse con Escape de
// inmediato) y bloqueo de scroll del body mientras esta abierto.
watch(lightboxOpen, async (open) => {
  document.body.style.overflow = open ? 'hidden' : '';
  if (open) {
    await nextTick();
    lightboxEl.value?.focus();
  }
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
.bv-gallery-img {
  width: 100%; height: 100%; object-fit: var(--bg-image-fit);
  transition: transform .25s ease;
}
.bv-gallery-main.is-zoomable { cursor: zoom-in; }
.bv-gallery-main.is-zoomable:hover .bv-gallery-img { transform: scale(1.8); }
.bv-gallery-main.is-expandable { cursor: pointer; }
.bv-gallery-expand-hint {
  position: absolute; bottom: 10px; right: 10px;
  width: 34px; height: 34px; border-radius: 999px;
  background: rgba(15, 23, 42, .55); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: .95rem; pointer-events: none;
}
.bv-gallery-placeholder {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-placeholder);
  color: var(--bg-placeholder-color); font-size: 5rem;
}
.bv-gallery-caption { margin-top: .6rem; }
.bv-gallery-caption-title { margin: 0 0 .2rem; font-size: .85rem; font-weight: 600; color: #1e293b; }
.bv-gallery-caption-desc { margin: 0; font-size: .8rem; color: #64748b; }
.bv-gallery-thumbs { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: .7rem; }
.bv-gallery-thumb {
  width: 72px; height: 72px;
  border: 1px solid #e2e8f0; border-radius: 12px;
  background: #fff; padding: 3px; overflow: hidden;
  cursor: pointer; transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}
.bv-gallery-thumb:hover { transform: translateY(-1px); }
.bv-gallery-thumb.active { border-color: var(--bg-thumb-active); box-shadow: 0 0 0 2px var(--bg-thumb-active-shadow); }
.bv-gallery-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 9px; }

/* Layout vertical (miniaturas a la izquierda) -- opt-in via prop thumb-layout="vertical",
   default horizontal preserva el comportamiento original de Renting/Services. */
.bv-gallery--vertical { display: flex; align-items: flex-start; gap: .75rem; }
.bv-gallery--vertical .bv-gallery-main { flex: 1; min-width: 0; }
.bv-gallery--vertical .bv-gallery-thumbs {
  order: -1; flex-direction: column; flex-wrap: nowrap; margin-top: 0;
  max-height: 100%; overflow-y: auto;
}
@media (max-width: 767px) {
  .bv-gallery--vertical { flex-direction: column; }
  .bv-gallery--vertical .bv-gallery-thumbs { order: 0; flex-direction: row; overflow-y: visible; overflow-x: auto; }
}

@media (prefers-reduced-motion: reduce) {
  .bv-gallery-img, .bv-gallery-thumb { transition: none; }
  .bv-gallery-main.is-zoomable:hover .bv-gallery-img { transform: none; }
}

/* Lightbox -- fuera de .bv-gallery (Teleport a body), namespaced con su propio
   prefijo bv-lightbox-* para no chocar con ningun otro modal del proyecto. */
.bv-lightbox-backdrop {
  position: fixed; inset: 0; z-index: 1080;
  background: rgba(15, 23, 42, .92);
  display: flex; align-items: center; justify-content: center;
  padding: 2rem;
}
.bv-lightbox-img {
  max-width: min(90vw, 1100px); max-height: 85vh;
  object-fit: contain; border-radius: 8px;
}
.bv-lightbox-close {
  position: absolute; top: 1.25rem; right: 1.25rem;
  width: 42px; height: 42px; border-radius: 999px; border: 0;
  background: rgba(255,255,255,.12); color: #fff; font-size: 1.1rem;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: background-color .15s ease;
}
.bv-lightbox-close:hover { background: rgba(255,255,255,.22); }
.bv-lightbox-nav {
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 48px; height: 48px; border-radius: 999px; border: 0;
  background: rgba(255,255,255,.12); color: #fff; font-size: 1.4rem;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: background-color .15s ease;
}
.bv-lightbox-nav:hover { background: rgba(255,255,255,.22); }
.bv-lightbox-prev { left: 1.25rem; }
.bv-lightbox-next { right: 1.25rem; }
.bv-lightbox-counter {
  position: absolute; bottom: 1.25rem; left: 50%; transform: translateX(-50%);
  color: #e2e8f0; font-size: .82rem; font-weight: 600;
  background: rgba(255,255,255,.12); border-radius: 999px; padding: .3rem .8rem;
}
.bv-lightbox-close:focus-visible, .bv-lightbox-nav:focus-visible {
  outline: 2px solid #fff; outline-offset: 2px;
}
@media (max-width: 575px) {
  .bv-lightbox-backdrop { padding: 1rem; }
  .bv-lightbox-nav { width: 40px; height: 40px; font-size: 1.15rem; }
}
</style>
