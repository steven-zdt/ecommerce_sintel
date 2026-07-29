<template>
  <div v-if="showBanner" :class="['urgency-banner', bannerType]">
    <div class="banner-icon">
      <i :class="['bi', getIcon()]"></i>
    </div>
    <div class="banner-content">
      <span class="banner-text">{{ bannerText }}</span>
      <span v-if="detail" class="banner-detail">{{ detail }}</span>
    </div>
    <div class="banner-badge">
      {{ badgeText }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: String,
    default: 'available', // available, limited, unavailable
  },
  availableNow: {
    type: Number,
    default: 0,
  },
  totalStock: {
    type: Number,
    default: 0,
  },
  urgencyMessage: {
    type: String,
    default: '',
  },
});

const showBanner = computed(() => {
  return props.status !== 'unavailable' && (props.availableNow <= 5 || props.urgencyMessage);
});

const bannerType = computed(() => {
  if (props.availableNow <= 2) return 'critical';
  if (props.availableNow <= 5) return 'limited';
  return 'normal';
});

const bannerText = computed(() => {
  if (props.urgencyMessage) return props.urgencyMessage;

  if (props.availableNow <= 2) {
    return 'Últimas unidades disponibles';
  }
  if (props.availableNow <= 5) {
    return `Solo ${props.availableNow} unidades en stock`;
  }
  return 'Stock limitado';
});

const detail = computed(() => {
  if (props.availableNow === 1) return 'Esta es la última unidad';
  if (props.availableNow <= 5) return `Quedan solo ${props.availableNow} de ${props.totalStock}`;
  return '';
});

const badgeText = computed(() => {
  if (props.availableNow <= 2) return 'Aprisa!';
  if (props.availableNow <= 5) return 'Limitado';
  return 'Disponible';
});

function getIcon() {
  if (props.availableNow <= 2) return 'bi-exclamation-circle-fill';
  if (props.availableNow <= 5) return 'bi-hourglass-split';
  return 'bi-info-circle-fill';
}
</script>

<style scoped>
.urgency-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
  animation: slideInDown 0.5s ease-out;
}

.urgency-banner.critical {
  background: linear-gradient(135deg, #f8d7da 0%, #ffe0e0 100%);
  border: 2px solid #dc3545;
  color: #721c24;
}

.urgency-banner.limited {
  background: linear-gradient(135deg, #fff3cd 0%, #fffacd 100%);
  border: 2px solid #ffc107;
  color: #856404;
}

.urgency-banner.normal {
  background: linear-gradient(135deg, #d1ecf1 0%, #e7f4ff 100%);
  border: 2px solid #0c5460;
  color: #0c5460;
}

.banner-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.urgency-banner.critical .banner-icon {
  animation: pulse-critical 1.5s ease-in-out infinite;
}

.urgency-banner.limited .banner-icon {
  animation: pulse-limited 2s ease-in-out infinite;
}

.banner-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.banner-text {
  font-weight: 700;
  font-size: 1rem;
}

.banner-detail {
  font-size: 0.875rem;
  opacity: 0.85;
}

.banner-badge {
  flex-shrink: 0;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  background: rgba(0, 0, 0, 0.1);
}

.urgency-banner.critical .banner-badge {
  background: rgba(220, 53, 69, 0.2);
}

.urgency-banner.limited .banner-badge {
  background: rgba(255, 193, 7, 0.2);
}

@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse-critical {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

@keyframes pulse-limited {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

@media (max-width: 768px) {
  .urgency-banner {
    padding: 0.75rem 1rem;
    gap: 0.75rem;
  }

  .banner-text {
    font-size: 0.9rem;
  }

  .banner-detail {
    font-size: 0.8rem;
  }

  .banner-icon {
    font-size: 1.25rem;
  }
}
</style>
