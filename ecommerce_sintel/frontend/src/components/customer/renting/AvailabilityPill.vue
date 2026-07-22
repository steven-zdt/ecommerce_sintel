<template>
  <button type="button" class="avail-pill" :class="state" @click="emit('click')">
    <i :class="icon"></i>
    <span>
      <strong>{{ title }}</strong>
      <small v-if="subtitle">{{ subtitle }}</small>
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  checking: { type: Boolean, default: false },
  available: { type: Boolean, default: null },
  nextAvailableDate: { type: String, default: null },
  nextAvailableTime: { type: String, default: null },
});
const emit = defineEmits(['click']);

const state = computed(() => {
  if (props.checking) return 'checking';
  if (props.available === true) return 'available';
  if (props.available === false) return 'unavailable';
  return 'idle';
});

function formatSuggestion() {
  if (!props.nextAvailableDate) return '';
  const label = new Date(`${props.nextAvailableDate}T12:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
  return props.nextAvailableTime ? `${label} · ${props.nextAvailableTime.slice(0, 5)}` : label;
}

const icon = computed(() => ({
  checking: 'bi bi-arrow-repeat spin',
  available: 'bi bi-check-circle-fill',
  unavailable: 'bi bi-exclamation-circle-fill',
  idle: 'bi bi-calendar3',
}[state.value]));

const title = computed(() => ({
  checking: 'Verificando disponibilidad…',
  available: 'Disponible',
  unavailable: 'No disponible en estas fechas',
  idle: 'Selecciona tus fechas',
}[state.value]));

const subtitle = computed(() => {
  if (state.value === 'unavailable') {
    const suggestion = formatSuggestion();
    return suggestion ? `Próxima fecha libre: ${suggestion}` : '';
  }
  return '';
});
</script>

<style scoped>
.avail-pill { display: flex; align-items: center; gap: .6rem; border: 0; border-radius: 14px; padding: .75rem .9rem; width: 100%; text-align: left; }
.avail-pill strong, .avail-pill small { display: block; }
.avail-pill small { font-weight: 500; opacity: .85; }
.avail-pill.checking { background: #f1f5f9; color: #475569; }
.avail-pill.available { background: #ecfdf5; color: #166534; }
.avail-pill.unavailable { background: #fff7ed; color: #9a3412; }
.avail-pill.idle { background: #f8fafc; color: #64748b; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
