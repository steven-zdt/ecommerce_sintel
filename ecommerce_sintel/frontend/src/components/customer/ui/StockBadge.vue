<template>
  <span :class="['badge rounded-pill stock-badge', badgeClass]">
    <i :class="['bi me-1', icon]"></i>{{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  stock: { type: Number, default: 0 },
  available: { type: Boolean, default: null }, // para equipos renting
});

const badgeClass = computed(() => {
  if (props.available !== null) {
    return props.available ? 'bg-success-subtle text-success border border-success-subtle'
                           : 'bg-secondary-subtle text-secondary border';
  }
  if (props.stock > 5) return 'bg-success-subtle text-success border border-success-subtle';
  if (props.stock > 0) return 'bg-warning-subtle text-warning border border-warning-subtle';
  return 'bg-danger-subtle text-danger border border-danger-subtle';
});

const icon = computed(() => {
  if (props.available !== null) return props.available ? 'bi-check-circle' : 'bi-x-circle';
  if (props.stock > 5) return 'bi-check-circle';
  if (props.stock > 0) return 'bi-exclamation-circle';
  return 'bi-x-circle';
});

const label = computed(() => {
  if (props.available !== null) return props.available ? 'Disponible' : 'No disponible';
  if (props.stock > 5) return `En stock (${props.stock})`;
  if (props.stock > 0) return `Últimas unidades (${props.stock})`;
  return 'Agotado';
});
</script>

<style scoped>
.stock-badge { font-size: .75rem; }
</style>
