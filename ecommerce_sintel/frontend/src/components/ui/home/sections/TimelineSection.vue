<template>
  <div ref="el" class="tl-root">
    <div
      v-for="(card, i) in visibleCards"
      :key="card.uuid"
      :class="['tl-item', sectionVisible ? 'tl-item--visible' : '']"
      :style="`transition-delay:${i * 80}ms`"
    >
      <div class="tl-marker" :style="{ background: card.background_color }">
        <i :class="['bi', card.icon_class || 'bi-circle-fill']"></i>
      </div>
      <div class="tl-connector" v-if="i < visibleCards.length - 1"></div>
      <div class="tl-content">
        <div class="tl-title">{{ card.title }}</div>
        <div v-if="card.subtitle" class="tl-subtitle">{{ card.subtitle }}</div>
        <div v-if="card.description" class="tl-desc">{{ card.description }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useScrollReveal } from '@/composables/useScrollReveal';

const props = defineProps({ cards: { type: Array, default: () => [] } });

const { el, visible: sectionVisible } = useScrollReveal({ threshold: 0.05 });
const visibleCards = computed(() => props.cards.filter(c => c.is_active !== false));
</script>

<style scoped>
.tl-root { position: relative; padding-left: 2.5rem; }
.tl-item {
  position: relative;
  padding-bottom: 2rem;
  opacity: 0; transform: translateX(-16px);
  transition: opacity 500ms ease, transform 500ms cubic-bezier(.16,1,.3,1);
}
.tl-item--visible { opacity: 1; transform: none; }
.tl-marker {
  position: absolute; left: -2.5rem; top: 0;
  width: 36px; height: 36px;
  border-radius: 50%;
  display: grid; place-items: center;
  color: #fff; font-size: .9rem;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}
.tl-connector {
  position: absolute; left: -2.15rem; top: 36px; bottom: 0;
  width: 2px; background: #e2e8f0;
}
.tl-title { font-weight: 700; color: #0f172a; margin-bottom: .25rem; }
.tl-subtitle { font-size: .85rem; color: #2563eb; font-weight: 600; margin-bottom: .35rem; }
.tl-desc { font-size: .85rem; color: #64748b; line-height: 1.6; }
</style>
