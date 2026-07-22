<template>
  <div class="ac-root">
    <div
      v-for="(card, i) in visibleCards"
      :key="card.uuid"
      :class="['ac-item', openIndex === i ? 'ac-item--open' : '']"
    >
      <button class="ac-header" @click="toggle(i)">
        <div class="ac-header-left">
          <div class="ac-icon" :style="{ background: card.background_color + '22', color: card.background_color }">
            <i :class="['bi', card.icon_class || 'bi-question-circle']"></i>
          </div>
          <span class="ac-title">{{ card.title }}</span>
        </div>
        <i :class="['bi', openIndex === i ? 'bi-dash' : 'bi-plus', 'ac-chevron']"></i>
      </button>
      <div class="ac-body" v-show="openIndex === i">
        <div v-if="card.subtitle" class="ac-subtitle">{{ card.subtitle }}</div>
        <div v-if="card.description" class="ac-desc">{{ card.description }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({ cards: { type: Array, default: () => [] } });
const openIndex = ref(0);
const visibleCards = computed(() => props.cards.filter(c => c.is_active !== false));
function toggle(i) { openIndex.value = openIndex.value === i ? -1 : i; }
</script>

<style scoped>
.ac-root { display: flex; flex-direction: column; gap: .5rem; }
.ac-item { border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #fff; }
.ac-item--open { border-color: #2563eb22; }
.ac-header {
  width: 100%; display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem; background: none; border: none; cursor: pointer; text-align: left;
}
.ac-header-left { display: flex; align-items: center; gap: .875rem; }
.ac-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: grid; place-items: center; flex-shrink: 0;
}
.ac-title { font-weight: 600; color: #0f172a; font-size: .925rem; }
.ac-chevron { color: #94a3b8; font-size: 1.1rem; transition: color 200ms; }
.ac-item--open .ac-chevron { color: #2563eb; }
.ac-body { padding: 0 1.25rem 1rem 3.75rem; }
.ac-subtitle { font-size: .875rem; color: #2563eb; font-weight: 600; margin-bottom: .35rem; }
.ac-desc { font-size: .875rem; color: #64748b; line-height: 1.7; }
</style>
