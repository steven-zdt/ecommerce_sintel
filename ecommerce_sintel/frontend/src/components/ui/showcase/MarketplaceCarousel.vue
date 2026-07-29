<template>
  <div class="mps-carousel-wrap">
    <div
      ref="trackEl"
      class="mps-track"
      role="region"
      aria-roledescription="carousel"
      tabindex="0"
      :style="carouselVars"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @wheel="onWheel"
      @keydown="onKeydown"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
      @touchstart.passive="onTouchStart"
      @touchend.passive="onTouchEnd"
      @focusin="onFocusIn"
      @focusout="onFocusOut"
    >
      <div
        v-for="(card, i) in cards"
        :key="`real-${card.key ?? card.uuid ?? i}`"
        class="mps-card"
        role="group"
        aria-roledescription="slide"
        :aria-label="`${i + 1} de ${cards.length}`"
      >
        <slot name="card" :card="card" :index="i" />
      </div>

      <!-- Clon del contenido para loop sin salto (Fase 7, MarketplaceAutoScroll.js).
           inert + aria-hidden: fuera del arbol de accesibilidad y de foco/click,
           pointer-events:none como red de seguridad en navegadores sin `inert`. -->
      <template v-if="loop">
        <div
          v-for="(card, i) in cards"
          :key="`clone-${card.key ?? card.uuid ?? i}`"
          class="mps-card mps-card--clone"
          aria-hidden="true"
          inert
        >
          <slot name="card" :card="card" :index="i" />
        </div>
      </template>
    </div>

    <MarketplaceControls
      v-if="showArrows"
      :can-prev="canScrollPrev"
      :can-next="canScrollNext"
      @prev="scrollPrev"
      @next="scrollNext"
    />
  </div>
</template>

<script setup>
/**
 * MarketplaceCarousel — mecanica de scroll horizontal pura (Fase 4).
 *
 * NO conoce el shape de una "card de modulo" -- recibe `cards` generico y
 * delega el render de cada item al scoped slot `card` (el llamador, i.e.
 * MarketplaceShowcase.vue, decide que se dibuja). Esto lo hace reutilizable
 * para cualquier coleccion horizontal, no solo modulos del Home Builder.
 *
 * Flechas (MarketplaceControls, Fase 8) se renderizan aqui adentro, ya que
 * necesitan `position: relative` del wrapper directo del track para
 * autoposicionarse en los bordes. Indicadores (MarketplaceIndicators) SI
 * viven en el padre (MarketplaceShowcase.vue) -- por eso este componente
 * sigue exponiendo activeIndex/canScrollPrev/Next/scrollToIndex via
 * defineExpose, para que el padre pueda sincronizar los dots sin duplicar
 * la logica de scroll.
 *
 * Autoplay (Fase 7, MarketplaceAutoScroll.js) se conecta desde afuera
 * observando `interaction-start/end` para pausar/reanudar -- este componente
 * no sabe nada de autoplay, solo informa cuando hay interaccion real.
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useHorizontalScroll } from '@/composables/useHorizontalScroll';
import { createAutoScroll } from './MarketplaceAutoScroll.js';
import MarketplaceControls from './MarketplaceControls.vue';

const props = defineProps({
  cards:        { type: Array,   default: () => [] },
  itemsDesktop: { type: [Number, String], default: 6 },
  itemsTablet:  { type: [Number, String], default: 3 },
  itemsMobile:  { type: [Number, String], default: 1.2 },
  gap:          { type: Number,  default: 1.25 }, // rem

  // ── Autoplay (Fase 7) ──
  autoplay:     { type: Boolean, default: false },
  loop:         { type: Boolean, default: false },
  speed:        { type: Number,  default: 40 }, // px/segundo
  pauseOnHover: { type: Boolean, default: true },
  pauseOnTouch: { type: Boolean, default: true },
  pauseOnFocus: { type: Boolean, default: true },

  // ── Navegacion (Fase 8) ──
  showArrows:   { type: Boolean, default: true },
});

const emit = defineEmits(['slide-change', 'interaction-start', 'interaction-end']);

const trackEl = ref(null);

// Los clones (loop) llevan la MISMA clase `.mps-card` para heredar el CSS de
// tamano/gap -- se excluyen aqui por selector para que activeIndex/
// canScrollPrev/Next (Fase 8, indicadores) solo cuenten items reales.
const {
  activeIndex, canScrollPrev, canScrollNext,
  scrollToIndex, scrollPrev, scrollNext,
  onPointerDown: onPointerDownRaw, onPointerMove, onPointerUp: onPointerUpRaw,
  onWheel, onKeydown, wasDragged, refreshItems,
} = useHorizontalScroll(trackEl, { itemSelector: '.mps-card:not(.mps-card--clone)' });

watch(activeIndex, (i) => emit('slide-change', i));
watch(() => props.cards.length, () => refreshItems());

// ── Autoplay: crear/destruir junto con el ciclo de vida del track ───────────
let autoScroll = null;

onMounted(() => {
  if (!trackEl.value) return;
  autoScroll = createAutoScroll(trackEl.value, { speed: props.speed, loop: props.loop });
  if (props.autoplay) autoScroll.start();
});
onBeforeUnmount(() => autoScroll?.stop());

watch(() => props.autoplay, (v) => {
  if (!autoScroll) return;
  if (v) autoScroll.start(); else autoScroll.stop();
});

// Envuelve pointerdown/up del composable para tambien emitir interaction-* y
// pausar/reanudar el autoscroll durante un drag real con mouse.
function onPointerDown(e) {
  onPointerDownRaw(e);
  if (e.pointerType === 'mouse') { emit('interaction-start', 'drag'); autoScroll?.pause('drag'); }
}
function onPointerUp(e) {
  onPointerUpRaw(e);
  if (e.pointerType === 'mouse') { emit('interaction-end', 'drag'); autoScroll?.resume('drag'); }
}

function onMouseEnter()  { if (props.pauseOnHover) autoScroll?.pause('hover'); }
function onMouseLeave()  { if (props.pauseOnHover) autoScroll?.resume('hover'); }
function onTouchStart()  { if (props.pauseOnTouch) autoScroll?.pause('touch'); }
function onTouchEnd()    { if (props.pauseOnTouch) autoScroll?.resume('touch'); }
function onFocusIn()     { if (props.pauseOnFocus) autoScroll?.pause('focus'); }
function onFocusOut()    { if (props.pauseOnFocus) autoScroll?.resume('focus'); }

const carouselVars = computed(() => ({
  '--mps-cols-desktop': props.itemsDesktop,
  '--mps-cols-tablet':  props.itemsTablet,
  '--mps-cols-mobile':  props.itemsMobile,
  '--mps-gap':          `${props.gap}rem`,
}));

defineExpose({
  activeIndex, canScrollPrev, canScrollNext,
  scrollPrev, scrollNext, scrollToIndex, wasDragged,
  pauseAutoScroll:  () => autoScroll?.pause('manual'),
  resumeAutoScroll: () => autoScroll?.resume('manual'),
});
</script>

<style scoped>
.mps-carousel-wrap { position: relative; }

.mps-track {
  display: flex;
  gap: var(--mps-gap, 1.25rem);
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
  outline: none;
  cursor: grab;
  /* pan-y: deja el scroll vertical de la pagina libre en touch; el navegador
     captura el gesto horizontal para este track via overflow-x nativo. */
  touch-action: pan-y;
}
.mps-track::-webkit-scrollbar { display: none; }
.mps-track.mps-dragging { cursor: grabbing; scroll-snap-type: none; }

.mps-card {
  flex: 0 0 calc((100% - (var(--mps-cols-mobile, 1.2) - 1) * var(--mps-gap, 1.25rem)) / var(--mps-cols-mobile, 1.2));
  scroll-snap-align: start;
  will-change: transform;
}
/* Clon de loop (Fase 7): red de seguridad para navegadores sin soporte de
   `inert` -- ni clickeable ni enfocable, aunque visualmente identico. */
.mps-card--clone {
  pointer-events: none;
  scroll-snap-align: none;
}

@media (min-width: 576px) {
  .mps-card {
    flex-basis: calc((100% - (var(--mps-cols-tablet, 3) - 1) * var(--mps-gap, 1.25rem)) / var(--mps-cols-tablet, 3));
  }
}
@media (min-width: 992px) {
  .mps-card {
    flex-basis: calc((100% - (var(--mps-cols-desktop, 6) - 1) * var(--mps-gap, 1.25rem)) / var(--mps-cols-desktop, 6));
  }
}
</style>
