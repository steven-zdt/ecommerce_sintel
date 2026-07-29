/**
 * MarketplaceAutoScroll — autoplay del carrusel (Fase 7).
 *
 * Modulo plano, NO composable Vue: es un temporizador de scroll puro sin
 * estado reactivo propio. MarketplaceCarousel.vue decide cuando llamar
 * start()/pause()/resume()/stop() desde su ciclo de vida y sus handlers de
 * interaccion (hover/touch/focus/drag).
 *
 * Usa requestAnimationFrame con delta-time real (no setInterval) para que
 * `speed` (px/segundo) sea consistente sin importar el framerate real del
 * dispositivo.
 *
 * Loop SIN salto visible: exige que el llamador haya duplicado el contenido
 * del track una vez (mismo contenido, doble ancho real -- ver el bloque
 * `v-if="loop"` en MarketplaceCarousel.vue, mismo truco que ya usa
 * BrandSlider.vue para su marquee CSS). Al llegar `scrollLeft` a la mitad
 * exacta de `scrollWidth`, se resta esa mitad en el mismo frame (sin
 * `behavior: 'smooth'`) -- como esa mitad es contenido identico pixel a
 * pixel, el reset es invisible al ojo.
 */
export function createAutoScroll(trackEl, { speed = 40, loop = true } = {}) {
  let rafId    = null;
  let lastTime = null;
  let running  = false;
  const pausedBy = new Set(); // motivos activos de pausa: 'hover' | 'touch' | 'focus' | 'drag' | 'manual'

  function frame(now) {
    if (lastTime == null) lastTime = now;
    const dt = (now - lastTime) / 1000; // segundos
    lastTime = now;

    if (trackEl && pausedBy.size === 0) {
      const half = trackEl.scrollWidth / 2;
      let next = trackEl.scrollLeft + speed * dt;

      if (loop && half > 0 && next >= half) {
        next -= half; // reset instantaneo -- contenido duplicado identico, sin salto visible
      } else if (!loop) {
        const max = trackEl.scrollWidth - trackEl.clientWidth;
        if (next >= max) { next = max; stop(); }
      }
      trackEl.scrollLeft = next;
    }

    if (running) rafId = requestAnimationFrame(frame);
  }

  function start() {
    if (running || !trackEl) return;
    running = true;
    lastTime = null;
    rafId = requestAnimationFrame(frame);
  }

  function stop() {
    running = false;
    if (rafId != null) cancelAnimationFrame(rafId);
    rafId = null;
  }

  function pause(reason = 'manual') {
    pausedBy.add(reason);
  }

  // lastTime=null al reanudar: evita contar el tiempo pausado como un solo
  // delta enorme (eso produciria un salto hacia adelante de golpe).
  function resume(reason = 'manual') {
    pausedBy.delete(reason);
    lastTime = null;
  }

  return { start, stop, pause, resume };
}
