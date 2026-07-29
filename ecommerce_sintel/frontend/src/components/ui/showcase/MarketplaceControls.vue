<template>
  <div class="mps-controls">
    <button
      type="button"
      class="mps-ctrl-btn mps-ctrl-btn--prev"
      :disabled="!canPrev"
      aria-label="Tarjeta anterior"
      @click="$emit('prev')"
    >
      <i class="bi bi-chevron-left"></i>
    </button>
    <button
      type="button"
      class="mps-ctrl-btn mps-ctrl-btn--next"
      :disabled="!canNext"
      aria-label="Tarjeta siguiente"
      @click="$emit('next')"
    >
      <i class="bi bi-chevron-right"></i>
    </button>
  </div>
</template>

<script setup>
/**
 * MarketplaceControls — flechas prev/next (Fase 8).
 * Se autoposiciona como overlay absoluto (inset:0) sobre quien lo monte --
 * el padre solo necesita `position: relative`. `disabled` real (no solo
 * visual) cuando no hay a donde ir y el carrusel no tiene loop.
 */
defineProps({
  canPrev: { type: Boolean, default: false },
  canNext: { type: Boolean, default: false },
});
defineEmits(['prev', 'next']);
</script>

<style scoped>
.mps-controls {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.5rem;
  pointer-events: none; /* el contenedor no bloquea clicks sobre las cards */
  z-index: 5;
}
.mps-ctrl-btn {
  pointer-events: auto;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(15,23,42,.1);
  background: rgba(255,255,255,.92);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: grid;
  place-items: center;
  font-size: 1.05rem;
  color: #0f172a;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(15,23,42,.1);
  transition: background 200ms ease, border-color 200ms ease, transform 200ms cubic-bezier(.16,1,.3,1), opacity 200ms ease;
}
.mps-ctrl-btn:hover:not(:disabled) {
  background: #0f172a;
  border-color: #0f172a;
  color: #fff;
  transform: translateY(-2px) scale(1.05);
}
.mps-ctrl-btn:disabled { opacity: 0.32; cursor: not-allowed; }

@media (max-width: 575px) {
  .mps-ctrl-btn { width: 36px; height: 36px; font-size: 0.9rem; }
}
@media (prefers-reduced-motion: reduce) {
  .mps-ctrl-btn { transition: none !important; }
}
</style>
