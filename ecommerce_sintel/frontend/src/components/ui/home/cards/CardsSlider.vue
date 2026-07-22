<template>
  <div class="cs-root">
    <div class="cs-track" ref="track">
      <CardItem
        v-for="(card, i) in visibleCards"
        :key="card.uuid"
        :card="card"
        :visible="true"
        class="cs-item"
      />
    </div>
    <div v-if="visibleCards.length > 3" class="cs-controls">
      <button class="cs-btn" @click="scroll(-1)" aria-label="Anterior">
        <i class="bi bi-chevron-left"></i>
      </button>
      <button class="cs-btn" @click="scroll(1)" aria-label="Siguiente">
        <i class="bi bi-chevron-right"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import CardItem from './CardItem.vue';

const props = defineProps({
  cards: { type: Array, default: () => [] },
});

const track = ref(null);

const visibleCards = computed(() => props.cards.filter(c => c.is_active !== false));

function scroll(dir) {
  if (!track.value) return;
  const itemW = track.value.querySelector('.cs-item')?.offsetWidth || 280;
  track.value.scrollBy({ left: dir * (itemW + 16), behavior: 'smooth' });
}
</script>

<style scoped>
.cs-root { position: relative; }
.cs-track {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
  padding-bottom: .5rem;
}
.cs-track::-webkit-scrollbar { display: none; }
.cs-item {
  flex: 0 0 280px;
  scroll-snap-align: start;
}
.cs-controls {
  display: flex;
  gap: .5rem;
  justify-content: flex-end;
  margin-top: .75rem;
}
.cs-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  border: 1px solid #e2e8f0;
  background: #fff;
  display: grid; place-items: center;
  cursor: pointer;
  transition: background 200ms, border-color 200ms;
}
.cs-btn:hover { background: #2563eb; border-color: #2563eb; color: #fff; }
</style>
