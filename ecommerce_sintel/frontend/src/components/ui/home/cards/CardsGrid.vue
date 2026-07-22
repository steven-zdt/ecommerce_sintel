<template>
  <div ref="el" class="cg-root">
    <div :class="gridClass">
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
  cards:   { type: Array,  default: () => [] },
  columns: { type: Number, default: 3 },
  limit:   { type: Number, default: 0 },
});

const { el, visible: sectionVisible } = useScrollReveal({ threshold: 0.05 });

const visibleCards = computed(() => {
  const active = [...props.cards.filter(c => c.is_active !== false)]
    .sort((a, b) => (b.priority || 0) - (a.priority || 0));
  return props.limit > 0 ? active.slice(0, props.limit) : active;
});

const gridClass = computed(() => {
  const col = Math.min(Math.max(props.columns, 1), 6);
  return ['cg-grid', `cg-grid--cols-${col}`];
});
</script>

<style scoped>
.cg-grid {
  display: grid;
  gap: 1rem;
}
.cg-grid--cols-1 { grid-template-columns: 1fr; }
.cg-grid--cols-2 { grid-template-columns: repeat(2, 1fr); }
.cg-grid--cols-3 { grid-template-columns: repeat(3, 1fr); }
.cg-grid--cols-4 { grid-template-columns: repeat(4, 1fr); }
.cg-grid--cols-5 { grid-template-columns: repeat(5, 1fr); }
.cg-grid--cols-6 { grid-template-columns: repeat(6, 1fr); }

@media (max-width: 767px) {
  .cg-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .cg-grid { grid-template-columns: 1fr; }
}
</style>
