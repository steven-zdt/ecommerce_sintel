<template>
  <div class="mq-viewport">
    <div class="mq-track" :style="{ animationDuration: `${duration}s` }">
      <div v-for="(card, i) in loopCards" :key="i" class="mq-item">
        <CardItem :card="card" :visible="true" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import CardItem from './CardItem.vue';

const props = defineProps({
  cards: { type: Array, default: () => [] },
});

// Reutiliza el estilo 'compact' ya existente de CardItem.vue (icono +
// etiqueta) sin importar el card_type guardado -- una tira de marcas debe
// verse uniforme aunque las tarjetas se hayan creado con otra variante.
const visibleCards = computed(() =>
  props.cards
    .filter(c => c.is_active !== false)
    .map(c => ({ ...c, card_type: 'compact' }))
);

// Se duplica la lista una vez para lograr un loop continuo sin salto visible
// (el track anima de 0% a -50%, que es exactamente el ancho de la lista original).
const loopCards = computed(() => [...visibleCards.value, ...visibleCards.value]);

// Duracion proporcional a la cantidad de elementos para que la velocidad de
// desplazamiento se sienta pareja sin importar cuantas marcas se agreguen.
const duration = computed(() => Math.max(visibleCards.value.length * 3, 15));
</script>

<style scoped>
.mq-viewport {
  overflow: hidden;
  width: 100%;
  -webkit-mask-image: linear-gradient(to right, transparent, black 4%, black 96%, transparent);
  mask-image: linear-gradient(to right, transparent, black 4%, black 96%, transparent);
}
.mq-track {
  display: flex;
  width: max-content;
  gap: 1rem;
  animation-name: mq-scroll;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: transform;
}
.mq-viewport:hover .mq-track {
  animation-play-state: paused;
}
.mq-item {
  flex: 0 0 auto;
  width: 220px;
}

@keyframes mq-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

@media (prefers-reduced-motion: reduce) {
  .mq-track { animation: none; }
}

@media (max-width: 576px) {
  .mq-item { width: 180px; }
}
</style>
