<template>
  <div ref="el" class="cg-root">
    <div class="cg-grid" :style="gridStyle">
      <CardItem
        v-for="(card, i) in visibleCards"
        :key="card.uuid"
        :card="card"
        :visible="sectionVisible"
        :style="`transition-delay:${i * 60}ms`"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import CardItem from './CardItem.vue';
import { useScrollReveal } from '@/composables/useScrollReveal';

const props = defineProps({
  cards:         { type: Array,  default: () => [] },
  columns:       { type: Number, default: 3 },
  columnsTablet: { type: Number, default: 2 },
  columnsMobile: { type: Number, default: 1 },
  gap:           { type: Number, default: 1 }, // rem
  limit:         { type: Number, default: 0 },
  group:         { type: Object, default: () => ({}) }, // no usado aqui -- evita fallthrough attr
});

const { el, visible: sectionVisible } = useScrollReveal({ threshold: 0.05 });

const visibleCards = computed(() => {
  const active = [...props.cards.filter(c => c.is_active !== false)]
    .sort((a, b) => (b.priority || 0) - (a.priority || 0));
  return props.limit > 0 ? active.slice(0, props.limit) : active;
});

const clamp = (n, fallback) => Math.min(Math.max(Number(n) || fallback, 1), 6);

const gridStyle = computed(() => ({
  '--cg-cols-desktop': clamp(props.columns, 3),
  '--cg-cols-tablet':  clamp(props.columnsTablet, 2),
  '--cg-cols-mobile':  clamp(props.columnsMobile, 1),
  '--cg-gap':          `${props.gap}rem`,
}));
</script>

<style scoped>
.cg-grid {
  display: grid;
  gap: var(--cg-gap, 1rem);
  grid-template-columns: repeat(var(--cg-cols-mobile, 1), 1fr);
}

@media (min-width: 576px) {
  .cg-grid { grid-template-columns: repeat(var(--cg-cols-tablet, 2), 1fr); }
}
@media (min-width: 992px) {
  .cg-grid { grid-template-columns: repeat(var(--cg-cols-desktop, 3), 1fr); }
}
</style>
