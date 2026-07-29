<template>
  <div v-if="stats.length" class="mps-stats">
    <AnimatedCounter v-for="(s, i) in stats" :key="i" :value="s.value" :label="s.label" />
  </div>
</template>

<script setup>
/**
 * MarketplaceStats — fila de contadores por card (Fase 5/6).
 * Envuelve AnimatedCounter.vue (landing/) en vez de duplicar su logica de
 * animacion (RAF + easeOutExpo + IntersectionObserver propio) -- solo
 * sobreescribe color para verse bien sobre fondos oscuros/imagen.
 */
import AnimatedCounter from '@/components/ui/landing/AnimatedCounter.vue';

defineProps({
  stats: { type: Array, default: () => [] }, // [{ value, label }]
});
</script>

<style scoped>
.mps-stats {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.25rem;
}
.mps-stats :deep(.ac-root) { padding: 0.5rem 0.75rem; }
.mps-stats :deep(.ac-value) {
  font-size: 1.2rem;
  -webkit-text-fill-color: #fff;
  background: none;
}
.mps-stats :deep(.ac-label) { color: rgba(255,255,255,.72); }
</style>
