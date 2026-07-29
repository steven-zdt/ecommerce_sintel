<template>
  <span :class="['tag-badge', tagClass]">
    <i v-if="icon" :class="['bi', icon, 'me-1']"></i>
    {{ tag.label }}
  </span>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  tag: {
    type: Object,
    required: true,
    // { code: 'OFERTA', label: 'Oferta', color: 'danger' }
  },
});

const colorMap = {
  danger: 'tag-danger',
  info: 'tag-info',
  warning: 'tag-warning',
  success: 'tag-success',
  primary: 'tag-primary',
  secondary: 'tag-secondary',
};

const iconMap = {
  OFERTA: 'bi-lightning-charge-fill',
  NUEVO: 'bi-star-fill',
  POPULAR: 'bi-fire',
  PREMIUM: 'bi-gem',
  RECOMENDADO: 'bi-hand-thumbs-up-fill',
  HOT: 'bi-flame',
  TOP_VENTAS: 'bi-trophy-fill',
  IDEAL_EVENTOS: 'bi-calendar-event',
  ULTIMAS_UNIDADES: 'bi-exclamation-triangle-fill',
};

const tagClass = computed(() => {
  const color = props.tag.color || 'primary';
  return colorMap[color] || 'tag-primary';
});

const icon = computed(() => {
  return iconMap[props.tag.code] || null;
});
</script>

<style scoped>
.tag-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.875rem;
  border-radius: 0.25rem;
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid;
  white-space: nowrap;
  animation: fadeIn 0.3s ease-out;
}

.tag-badge i {
  font-size: 0.9rem;
}

.tag-danger {
  background-color: #f8d7da;
  border-color: #f5c2c7;
  color: #842029;
}

.tag-info {
  background-color: #cfe2ff;
  border-color: #b6d4fe;
  color: #084298;
}

.tag-warning {
  background-color: #fff3cd;
  border-color: #ffecb5;
  color: #664d03;
}

.tag-success {
  background-color: #d1e7dd;
  border-color: #badbcc;
  color: #0a3622;
}

.tag-primary {
  background-color: #cfe2ff;
  border-color: #b6d4fe;
  color: #084298;
}

.tag-secondary {
  background-color: #e2e3e5;
  border-color: #d3d3d7;
  color: #41464b;
}

/* Hover effects */
.tag-badge {
  transition: all 0.2s ease;
  cursor: default;
}

.tag-badge:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 576px) {
  .tag-badge {
    padding: 0.375rem 0.625rem;
    font-size: 0.8rem;
  }

  .tag-badge i {
    font-size: 0.8rem;
  }
}
</style>
