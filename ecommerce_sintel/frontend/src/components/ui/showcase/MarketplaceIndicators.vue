<template>
  <div v-if="total > 1" class="mps-indicators" role="tablist" aria-label="Seleccionar tarjeta">
    <button
      v-for="i in total"
      :key="i"
      type="button"
      role="tab"
      class="mps-dot"
      :class="{ 'mps-dot--active': i - 1 === activeIndex }"
      :aria-selected="i - 1 === activeIndex"
      :aria-label="`Ir a la tarjeta ${i} de ${total}`"
      @click="$emit('select', i - 1)"
    ></button>
  </div>
</template>

<script setup>
/**
 * MarketplaceIndicators — dots de posicion (Fase 8).
 * <button> nativos -- foco/activacion por teclado (Tab + Enter/Espacio)
 * vienen gratis del navegador, sin JS adicional.
 */
defineProps({
  total:       { type: Number, default: 0 },
  activeIndex: { type: Number, default: 0 },
});
defineEmits(['select']);
</script>

<style scoped>
.mps-indicators {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
}
.mps-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  border: none;
  background: rgba(15,23,42,.18);
  cursor: pointer;
  padding: 0;
  transition: width 260ms cubic-bezier(.16,1,.3,1), background 260ms ease;
}
.mps-dot--active { width: 26px; background: #0f172a; }
.mps-dot:hover:not(.mps-dot--active) { background: rgba(15,23,42,.34); }
.mps-dot:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }

@media (prefers-reduced-motion: reduce) {
  .mps-dot { transition: none !important; }
}
</style>
