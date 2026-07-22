<template>
  <div ref="el" class="fcar-root">
    <!-- Skeleton -->
    <div v-if="loading" class="fcar-grid">
      <div v-for="n in 4" :key="n" class="fcar-skeleton"></div>
    </div>

    <!-- Items -->
    <div v-else class="fcar-grid">
      <FeaturedCard
        v-for="(item, i) in items"
        :key="item.uuid"
        :item="item"
        :type="type"
        class="fcar-card-reveal"
        :class="{ 'fcar-card-visible': sectionVisible }"
        :style="`transition-delay: ${i * 60}ms`"
      />
    </div>
  </div>
</template>

<script setup>
import FeaturedCard from './FeaturedCard.vue';
import { useScrollReveal } from '@/composables/useScrollReveal';

defineProps({
  items:   { type: Array,   default: () => [] },
  type:    { type: String,  default: 'product' },
  loading: { type: Boolean, default: false },
});

const { el, visible: sectionVisible } = useScrollReveal({ threshold: 0.06 });
</script>

<style scoped>
/* ── Mobile: scroll horizontal snap ────────────────────────────────────────── */
.fcar-grid {
  display: flex;
  gap: 0.85rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
  padding-bottom: 0.5rem;
}
.fcar-grid::-webkit-scrollbar { display: none; }
.fcar-grid > * {
  flex: 0 0 220px;
  scroll-snap-align: start;
}

/* ── Skeleton mobile ────────────────────────────────────────────────────────── */
.fcar-skeleton {
  flex: 0 0 220px;
  height: 280px;
  border-radius: 18px;
  background: linear-gradient(90deg, #e2e8f0 25%, #cbd5e1 50%, #e2e8f0 75%);
  background-size: 800px 100%;
  animation: fcar-shimmer 1.4s infinite linear;
}
@keyframes fcar-shimmer {
  0%   { background-position: -800px 0; }
  100% { background-position: 800px 0; }
}

/* ── Card reveal ────────────────────────────────────────────────────────────── */
.fcar-card-reveal {
  opacity: 0;
  transform: translateY(20px) scale(0.97);
  transition:
    opacity 0.55s cubic-bezier(0.16,1,0.3,1),
    transform 0.55s cubic-bezier(0.16,1,0.3,1);
}
.fcar-card-visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* ── Desktop: CSS grid ──────────────────────────────────────────────────────── */
@media (min-width: 768px) {
  .fcar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    overflow-x: unset;
    scroll-snap-type: unset;
    padding-bottom: 0;
  }
  .fcar-grid > * { flex: unset; }
  .fcar-skeleton {
    flex: unset;
    height: 300px;
  }
}
</style>
