<template>
  <div ref="rootEl" class="mpb-root">
    <div class="mpb-layer" :style="parallaxStyle">
      <video
        v-if="type === 'video' && videoSrc && !videoFailed"
        ref="videoEl"
        class="mpb-media mpb-media--video"
        :style="mediaFilterStyle"
        :poster="poster || undefined"
        muted
        :loop="loop"
        playsinline
        preload="none"
        @loadeddata="onLoaded"
        @error="onVideoError"
      >
        <source v-if="videoSrcWebm" :src="videoSrcWebm" type="video/webm">
        <source :src="videoSrc" type="video/mp4">
      </video>

      <img
        v-else-if="(type === 'image' || (type === 'video' && videoFailed)) && effectiveImage"
        :src="effectiveImage"
        class="mpb-media mpb-media--image"
        :style="mediaFilterStyle"
        loading="lazy"
        decoding="async"
        alt=""
        @load="onLoaded"
        @error="onImageError"
      >

      <div v-else class="mpb-media mpb-media--color" :style="colorStyle"></div>
    </div>

    <div v-if="overlay" class="mpb-overlay" :style="overlayStyle"></div>
  </div>
</template>

<script setup>
/**
 * MarketplaceBackground — fondo multimedia generico (Fase 3).
 *
 * Reutilizado tanto por MarketplaceCard.vue (fondo por-card, config en
 * module.layout_config.media) como por MarketplaceShowcase.vue (fondo de
 * seccion completa, config en layout_config.section_background) -- mismo
 * contrato de props para ambos casos, evita duplicar la logica de
 * video/imagen/parallax/blur/pausa-por-visibilidad dos veces.
 *
 * Autoplay real de video en navegadores exige `muted` -- se fija siempre
 * (no es configurable): un fondo decorativo sin control de usuario no tiene
 * caso de uso legitimo con audio, y exponerlo rompe el autoplay en Chrome/
 * Safari sin ningun beneficio real.
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useParallaxBackground } from '@/composables/useParallaxBackground';

const props = defineProps({
  type:             { type: String,  default: 'color' }, // image | video | color
  image:            { type: String,  default: '' },
  videoSrc:         { type: String,  default: '' },
  videoSrcWebm:     { type: String,  default: '' },
  poster:           { type: String,  default: '' },
  color:            { type: String,  default: '#0f172a' },
  autoplay:         { type: Boolean, default: true },
  loop:             { type: Boolean, default: true },
  overlay:          { type: Boolean, default: false },
  overlayColor:     { type: String,  default: '#000000' },
  overlayOpacity:   { type: Number,  default: 45 }, // 0-100
  blur:             { type: Number,  default: 0 },  // px
  parallax:         { type: Boolean, default: false },
  parallaxStrength: { type: Number,  default: 0.3 },
});

const emit = defineEmits(['loaded', 'error']);

const rootEl       = ref(null);
const videoEl      = ref(null);
const videoFailed  = ref(false);
let visibilityObserver = null;

const { style: parallaxStyle } = useParallaxBackground(rootEl, {
  strength: props.parallaxStrength,
  disabled: !props.parallax,
});

// Si el video falla (source invalida, formato no soportado), cae a `image`
// si existe, o si no, al poster (que ya deberia ser la primera escena del
// video) -- nunca deja el fondo en blanco.
const effectiveImage = computed(() => props.image || props.poster || '');

// scale(1.08) evita que el desenfoque revele el borde nitido del elemento.
const mediaFilterStyle = computed(() => (
  props.blur > 0 ? { filter: `blur(${props.blur}px)`, transform: 'scale(1.08)' } : {}
));

const colorStyle = computed(() => ({ background: props.color }));

const overlayStyle = computed(() => ({
  background: props.overlayColor,
  opacity: Math.min(Math.max(props.overlayOpacity, 0), 100) / 100,
}));

function onLoaded() { emit('loaded'); }
function onImageError() { emit('error', 'image'); }
function onVideoError() {
  videoFailed.value = true;
  emit('error', 'video');
}

// ── Pausa real (no solo logica) cuando el fondo sale de viewport: libera CPU/GPU. ──
onMounted(() => {
  if (props.type !== 'video' || !rootEl.value) return;
  visibilityObserver = new IntersectionObserver(([entry]) => {
    const v = videoEl.value;
    if (!v) return;
    if (entry.isIntersecting) {
      if (props.autoplay) v.play().catch(() => {}); // rechazo de autoplay (politica navegador): silencioso
    } else {
      v.pause();
    }
  }, { threshold: 0.1 });
  visibilityObserver.observe(rootEl.value);
});

onBeforeUnmount(() => visibilityObserver?.disconnect());

// Reacciona si autoplay cambia en caliente (Vista Previa del Home Builder).
watch(() => props.autoplay, (val) => {
  const v = videoEl.value;
  if (!v) return;
  if (val) v.play().catch(() => {});
  else v.pause();
});
</script>

<style scoped>
.mpb-root {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}
/* Margen extra: el translate3d del parallax nunca revela un borde vacio. */
.mpb-layer {
  position: absolute;
  inset: -10%;
}
.mpb-media {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.mpb-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .mpb-layer { transform: none !important; }
}
</style>
