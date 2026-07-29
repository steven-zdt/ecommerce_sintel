import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';

/**
 * Mecanica de scroll horizontal para MarketplaceCarousel.vue (Fase 4).
 *
 * Nunca usa Swiper/Slick/Splide -- CSS Scroll Snap nativo (overflow-x +
 * scroll-snap-type) hace el trabajo pesado; este composable solo agrega:
 *   - Drag con mouse (Pointer Events) -- SOLO pointerType 'mouse'. El touch
 *     se deja 100% a la fisica nativa del navegador (momentum + snap ya
 *     funcionan solos sobre overflow-x; reimplementarlo con Pointer Events
 *     para touch compite con esa fisica nativa y se siente peor).
 *   - Wheel horizontal (trackpads mandan deltaX; mouse-wheel vertical se
 *     traduce a scroll horizontal).
 *   - Teclado (flechas/Home/End).
 *   - activeIndex real via IntersectionObserver sobre los items (no
 *     matematica de scrollLeft/itemWidth, que se desincroniza durante
 *     drag/inercia).
 *   - Coalescencia de pointermove en requestAnimationFrame -- evita escribir
 *     scrollLeft mas de una vez por frame (mantiene 60 FPS con eventos de
 *     puntero de alta frecuencia).
 */
export function useHorizontalScroll(trackRef, { itemSelector = '.mps-card' } = {}) {
  const activeIndex    = ref(0);
  const itemCount      = ref(0);
  const canScrollPrev  = computed(() => activeIndex.value > 0);
  const canScrollNext  = computed(() => activeIndex.value < itemCount.value - 1);

  let items = [];
  let itemObserver = null;

  function getItems() {
    if (!trackRef.value) return [];
    return Array.from(trackRef.value.querySelectorAll(itemSelector));
  }

  function setupObserver() {
    itemObserver?.disconnect();
    if (!trackRef.value || !items.length) return;
    itemObserver = new IntersectionObserver((entries) => {
      let best = null;
      for (const entry of entries) {
        if (entry.isIntersecting && (!best || entry.intersectionRatio > best.intersectionRatio)) {
          best = entry;
        }
      }
      if (best) {
        const idx = items.indexOf(best.target);
        if (idx !== -1) activeIndex.value = idx;
      }
    }, { root: trackRef.value, threshold: [0.5, 0.75, 0.9] });
    items.forEach((el) => itemObserver.observe(el));
  }

  function refreshItems() {
    items = getItems();
    itemCount.value = items.length;
    setupObserver();
  }

  function scrollToIndex(i) {
    const item = items[i];
    if (!trackRef.value || !item) return;
    trackRef.value.scrollTo({ left: item.offsetLeft, behavior: 'smooth' });
  }

  function scrollPrev() { if (canScrollPrev.value) scrollToIndex(activeIndex.value - 1); }
  function scrollNext() { if (canScrollNext.value) scrollToIndex(activeIndex.value + 1); }

  // ── Drag con mouse (Pointer Events, solo desktop) ──────────────────────────
  let dragging   = false;
  let startX     = 0;
  let startScroll = 0;
  let moved      = false;
  let pendingDx  = null;
  let rafPending = false;

  function onPointerDown(e) {
    if (e.pointerType !== 'mouse' || !trackRef.value) return;
    dragging = true;
    moved = false;
    startX = e.clientX;
    startScroll = trackRef.value.scrollLeft;
    trackRef.value.setPointerCapture?.(e.pointerId);
    trackRef.value.classList.add('mps-dragging');
  }

  function onPointerMove(e) {
    if (!dragging || !trackRef.value) return;
    const dx = e.clientX - startX;
    if (Math.abs(dx) > 4) moved = true;
    pendingDx = dx;
    if (!rafPending) {
      rafPending = true;
      requestAnimationFrame(() => {
        if (trackRef.value && pendingDx != null) {
          trackRef.value.scrollLeft = startScroll - pendingDx;
        }
        rafPending = false;
      });
    }
  }

  function onPointerUp(e) {
    if (!dragging || !trackRef.value) return;
    dragging = false;
    trackRef.value.classList.remove('mps-dragging');
    trackRef.value.releasePointerCapture?.(e.pointerId);
  }

  // MarketplaceCard usa esto para cancelar su propia navegacion (click) si el
  // puntero se movio lo suficiente como para considerarse un drag real.
  function wasDragged() { return moved; }

  // ── Wheel horizontal ────────────────────────────────────────────────────────
  function onWheel(e) {
    if (!trackRef.value) return;
    const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (delta === 0) return;
    e.preventDefault();
    trackRef.value.scrollLeft += delta;
  }

  // ── Teclado ──────────────────────────────────────────────────────────────────
  function onKeydown(e) {
    if (e.key === 'ArrowRight')      { e.preventDefault(); scrollNext(); }
    else if (e.key === 'ArrowLeft')  { e.preventDefault(); scrollPrev(); }
    else if (e.key === 'Home')       { e.preventDefault(); scrollToIndex(0); }
    else if (e.key === 'End')        { e.preventDefault(); scrollToIndex(itemCount.value - 1); }
  }

  onMounted(() => { nextTick(refreshItems); });
  onBeforeUnmount(() => itemObserver?.disconnect());

  return {
    activeIndex, itemCount, canScrollPrev, canScrollNext,
    scrollToIndex, scrollPrev, scrollNext,
    onPointerDown, onPointerMove, onPointerUp,
    onWheel, onKeydown, wasDragged, refreshItems,
  };
}
