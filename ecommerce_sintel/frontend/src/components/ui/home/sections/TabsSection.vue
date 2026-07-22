<template>
  <div class="tb-root">
    <div class="tb-tabs" role="tablist">
      <button
        v-for="(card, i) in visibleCards"
        :key="card.uuid"
        :class="['tb-tab', activeIndex === i ? 'tb-tab--active' : '']"
        role="tab"
        @click="activeIndex = i"
      >
        <i :class="['bi', card.icon_class || 'bi-star']"></i>
        <span>{{ card.title }}</span>
      </button>
    </div>
    <div v-if="active" class="tb-panel">
      <div class="tb-panel-icon" :style="{ background: active.background_color + '22', color: active.background_color }">
        <i :class="['bi', active.icon_class || 'bi-star']"></i>
      </div>
      <div v-if="active.subtitle" class="tb-panel-subtitle">{{ active.subtitle }}</div>
      <div v-if="active.description" class="tb-panel-desc">{{ active.description }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({ cards: { type: Array, default: () => [] } });
const activeIndex = ref(0);
const visibleCards = computed(() => props.cards.filter(c => c.is_active !== false));
const active = computed(() => visibleCards.value[activeIndex.value] || null);
</script>

<style scoped>
.tb-root { display: flex; flex-direction: column; gap: 1.25rem; }
.tb-tabs {
  display: flex; flex-wrap: wrap; gap: .5rem;
  justify-content: center; border-bottom: 1px solid #e2e8f0; padding-bottom: .75rem;
}
.tb-tab {
  display: flex; align-items: center; gap: .5rem;
  padding: .55rem 1.1rem; border-radius: 999px; border: 1px solid #e2e8f0;
  background: #fff; color: #64748b; font-size: .85rem; font-weight: 600;
  cursor: pointer; transition: all 200ms ease;
}
.tb-tab:hover { border-color: #2563eb55; color: #2563eb; }
.tb-tab--active { background: #2563eb; border-color: #2563eb; color: #fff; }
.tb-panel {
  display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: .75rem; max-width: 560px; margin: 0 auto;
}
.tb-panel-icon {
  width: 52px; height: 52px; border-radius: 14px;
  display: grid; place-items: center; font-size: 1.4rem;
}
.tb-panel-subtitle { font-weight: 700; color: #0f172a; font-size: 1rem; }
.tb-panel-desc { color: #64748b; font-size: .9rem; line-height: 1.7; }
</style>
