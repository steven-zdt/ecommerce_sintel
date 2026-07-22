<template>
  <div v-if="available === false" class="avail-card">
    <span class="eyebrow">Próxima disponibilidad</span>
    <strong class="suggestion-date">{{ formattedDate }}</strong>
    <span v-if="nextAvailableTime" class="suggestion-time">{{ nextAvailableTime.slice(0, 5) }}</span>
    <span class="badge-pill">{{ rentalMode === 'hours' ? 'Programada' : 'Programado' }}</span>

    <ul v-if="occupiedSlots?.length" class="occupied-list">
      <li v-for="(slot, index) in occupiedSlots.slice(0, 3)" :key="index">
        Ocupado: {{ formatRange(slot) }}
      </li>
    </ul>

    <button type="button" class="select-btn" :disabled="!nextAvailableDate" @click="emit('select', { date: nextAvailableDate, time: nextAvailableTime })">
      Seleccionar esta fecha
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  checking: { type: Boolean, default: false },
  available: { type: Boolean, default: null },
  nextAvailableDate: { type: String, default: null },
  nextAvailableTime: { type: String, default: null },
  rentalMode: { type: String, default: 'days' },
  occupiedSlots: { type: Array, default: () => [] },
});
const emit = defineEmits(['select']);

const formattedDate = computed(() => {
  if (!props.nextAvailableDate) return 'Sin fecha disponible en el rango consultado';
  return new Date(`${props.nextAvailableDate}T12:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' });
});

function shortDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
}

function formatRange(slot) {
  if (slot.rental_mode === 'hours' && slot.start_time && slot.end_time) {
    return `${shortDate(slot.start_date)} ${slot.start_time.slice(0, 5)}–${slot.end_time.slice(0, 5)}`;
  }
  return `${shortDate(slot.start_date)} – ${shortDate(slot.end_date)}`;
}
</script>

<style scoped>
.avail-card { background: #fff; border: 1px solid #fde68a; border-radius: 20px; padding: 1.2rem; display: grid; gap: .3rem; text-align: center; }
.eyebrow { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: #92400e; font-weight: 800; }
.suggestion-date { font-size: 1.3rem; color: #1f2937; }
.suggestion-time { color: #6b7280; font-weight: 600; }
.badge-pill { justify-self: center; background: #fef3c7; color: #92400e; border-radius: 999px; padding: .25rem .75rem; font-size: .72rem; font-weight: 700; margin: .3rem 0; }
.occupied-list { list-style: none; padding: 0; margin: .4rem 0; color: #94a3b8; font-size: .78rem; }
.select-btn { border: 0; border-radius: 999px; background: #7c3aed; color: #fff; font-weight: 750; padding: .7rem 1.2rem; margin-top: .5rem; }
.select-btn:hover { background: #5b21b6; }
.select-btn:disabled { opacity: .5; }
</style>
