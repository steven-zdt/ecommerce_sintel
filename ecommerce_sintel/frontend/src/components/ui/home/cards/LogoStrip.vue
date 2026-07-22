<template>
  <div ref="el" class="ls-grid" :class="{ 'ls-visible': visible }" :style="gridStyle">
    <a
      v-for="c in visibleCards"
      :key="c.uuid"
      :href="c.redirect_url || undefined"
      class="ls-item"
      :target="c.redirect_url ? '_blank' : undefined"
      rel="noopener"
      @click="!c.redirect_url && $event.preventDefault()"
    >
      <img v-if="c.image" :src="c.image" :alt="c.title" class="ls-img" loading="lazy">
      <span v-else class="ls-fallback">{{ c.title }}</span>
    </a>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useScrollReveal } from '@/composables/useScrollReveal';

const props = defineProps({
  cards:   { type: Array,  default: () => [] },
  columns: { type: Number, default: 6 },
});

const { el, visible } = useScrollReveal({ threshold: 0.05 });

const visibleCards = computed(() => props.cards.filter(c => c.is_active !== false));
const gridStyle = computed(() => ({ gridTemplateColumns: `repeat(${Math.min(Math.max(props.columns, 2), 8)}, 1fr)` }));
</script>

<style scoped>
.ls-grid {
  display: grid;
  gap: 2rem;
  align-items: center;
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.ls-grid.ls-visible { opacity: 1; transform: translateY(0); }

.ls-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
}
.ls-img {
  max-width: 100%;
  max-height: 56px;
  object-fit: contain;
  filter: grayscale(1) opacity(.55);
  transition: filter 250ms ease, transform 250ms ease;
}
.ls-item:hover .ls-img {
  filter: grayscale(0) opacity(1);
  transform: scale(1.05);
}
.ls-fallback {
  font-size: .85rem;
  font-weight: 700;
  color: #94a3b8;
  text-align: center;
}

@media (max-width: 767px) {
  .ls-grid { gap: 1.25rem; }
}
</style>
