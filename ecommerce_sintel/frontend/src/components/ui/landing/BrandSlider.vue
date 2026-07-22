<template>
  <section
    v-if="activeItems.length"
    class="bs-section"
    role="region"
    :aria-label="config.title || 'Marcas y clientes que confian en nosotros'"
    :style="sectionStyle"
  >
    <div class="container-xl">
      <div v-if="config.title || config.subtitle" class="bs-header">
        <h2 v-if="config.title" class="bs-title">{{ config.title }}</h2>
        <p v-if="config.subtitle" class="bs-subtitle">{{ config.subtitle }}</p>
      </div>

      <div
        class="bs-viewport"
        :class="{ 'bs-viewport--static': !loopEnabled }"
        :style="viewportVars"
      >
        <div
          class="bs-track"
          :class="{ 'bs-track--paused': !autoplayEnabled, 'bs-track--pausable': pauseOnHover }"
          :style="trackStyle"
        >
          <a
            v-for="(item, i) in loopItems"
            :key="`${item.uuid}-${i}`"
            class="bs-item"
            :href="item.website || undefined"
            :target="item.open_new_tab && item.website ? '_blank' : undefined"
            :rel="item.open_new_tab && item.website ? 'noopener noreferrer' : undefined"
            @click="!item.website && $event.preventDefault()"
          >
            <img
              v-if="item.logo"
              :src="item.logo"
              :alt="item.name"
              class="bs-img"
              loading="lazy"
            >
            <span v-else class="bs-fallback">{{ item.name }}</span>
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { PADDING_MAP } from '@/composables/useLayoutEngine';

const props = defineProps({
  config: { type: Object, default: () => ({}) },
  items:  { type: Array,  default: () => [] },
});

const activeItems = computed(() => props.items.filter(i => i.is_active !== false));

const loopEnabled     = computed(() => props.config.loop !== false);
const autoplayEnabled = computed(() => props.config.autoplay !== false);
const pauseOnHover    = computed(() => props.config.pause_on_hover !== false);

// Duplicar la lista una unica vez logra un loop continuo sin salto visible
// (el track anima de 0% a -50%/+50%, exactamente el ancho de la lista original).
const loopItems = computed(() =>
  loopEnabled.value ? [...activeItems.value, ...activeItems.value] : activeItems.value
);

const duration = computed(() => Math.max((props.config.speed || 3500) / 1000, 1));

const trackStyle = computed(() => ({
  animationDuration: `${duration.value}s`,
  animationDirection: props.config.direction === 'right' ? 'reverse' : 'normal',
}));

const viewportVars = computed(() => ({
  '--bs-items-desktop': props.config.items_desktop || 6,
  '--bs-items-tablet':  props.config.items_tablet  || 4,
  '--bs-items-mobile':  props.config.items_mobile  || 2,
}));

const sectionStyle = computed(() => {
  const style = {
    paddingTop:    PADDING_MAP[props.config.padding_top]    || PADDING_MAP.normal,
    paddingBottom: PADDING_MAP[props.config.padding_bottom] || PADDING_MAP.normal,
  };
  if (props.config.background_color) style.background = props.config.background_color;
  return style;
});
</script>

<style scoped>
.bs-section { width: 100%; }

.bs-header { text-align: center; margin-bottom: 2rem; }
.bs-title { font-size: clamp(1.4rem, 2.5vw, 1.9rem); font-weight: 800; color: #0a0f1e; margin-bottom: .4rem; }
.bs-subtitle { color: #64748b; font-size: .95rem; margin: 0; }

.bs-viewport {
  overflow: hidden;
  width: 100%;
  -webkit-mask-image: linear-gradient(to right, transparent, black 4%, black 96%, transparent);
  mask-image: linear-gradient(to right, transparent, black 4%, black 96%, transparent);
}
.bs-viewport--static { overflow-x: auto; -webkit-mask-image: none; mask-image: none; }

.bs-track {
  display: flex;
  width: max-content;
  gap: 2rem;
  align-items: center;
  animation-name: bs-scroll;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: transform;
}
.bs-track--paused { animation-play-state: paused; }
.bs-track--pausable:hover { animation-play-state: paused; }

.bs-item {
  flex: 0 0 auto;
  width: calc(100% / var(--bs-items-desktop));
  min-width: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: .5rem;
  text-decoration: none;
}
.bs-img {
  max-width: 100%;
  max-height: 56px;
  object-fit: contain;
  filter: grayscale(1) opacity(.55);
  transition: filter 250ms ease, transform 250ms ease;
}
.bs-item:hover .bs-img { filter: grayscale(0) opacity(1); transform: scale(1.05); }
.bs-fallback { font-size: .85rem; font-weight: 700; color: #94a3b8; text-align: center; }

@keyframes bs-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

@media (prefers-reduced-motion: reduce) {
  .bs-track { animation: none; }
}

@media (max-width: 991px) {
  .bs-item { width: calc(100% / var(--bs-items-tablet)); }
}
@media (max-width: 576px) {
  .bs-item { width: calc(100% / var(--bs-items-mobile)); }
}
</style>
