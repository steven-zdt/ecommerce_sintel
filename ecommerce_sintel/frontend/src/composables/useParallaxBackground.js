import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

/**
 * Efecto parallax ligero para fondos de MarketplaceShowcase (Fase 3/11).
 *
 * Solo calcula transform mientras el elemento esta en viewport
 * (IntersectionObserver + requestAnimationFrame condicionado) -- evita CPU
 * ocioso cuando el carrusel esta fuera de pantalla. Anima unicamente
 * `transform: translate3d` (nunca left/top/margin, Fase 11 -- evita layout
 * thrashing). Respeta `prefers-reduced-motion` devolviendo un estilo vacio.
 */
export function useParallaxBackground(elRef, { strength = 0.3, disabled = false } = {}) {
  const offset  = ref(0);
  const inView  = ref(false);
  let observer  = null;
  let rafId     = null;

  const reduceMotion = typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  function tick() {
    if (!inView.value) { rafId = null; return; }
    if (elRef.value) {
      const rect = elRef.value.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      // Delta respecto al centro del viewport -- 0 cuando el elemento esta centrado.
      const centerDelta = (rect.top + rect.height / 2) - vh / 2;
      offset.value = centerDelta * strength * -1;
    }
    rafId = requestAnimationFrame(tick);
  }

  function startLoop() { if (rafId == null) rafId = requestAnimationFrame(tick); }
  function stopLoop()  { if (rafId != null) { cancelAnimationFrame(rafId); rafId = null; } }

  onMounted(() => {
    if (disabled || reduceMotion || !elRef.value) return;
    observer = new IntersectionObserver(([entry]) => {
      inView.value = entry.isIntersecting;
      if (inView.value) startLoop(); else stopLoop();
    }, { threshold: 0 });
    observer.observe(elRef.value);
  });

  onBeforeUnmount(() => {
    stopLoop();
    observer?.disconnect();
  });

  const style = computed(() => {
    if (disabled || reduceMotion) return {};
    return {
      transform: `translate3d(0, ${offset.value.toFixed(1)}px, 0)`,
      willChange: 'transform',
    };
  });

  return { style, inView };
}
