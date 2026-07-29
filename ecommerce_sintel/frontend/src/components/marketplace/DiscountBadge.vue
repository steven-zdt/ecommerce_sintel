<template>
  <div v-if="discount > 0" class="discount-badge-container">
    <div class="discount-badge">
      <span class="discount-value">-{{ discount }}%</span>
      <span class="discount-label">Descuento</span>
    </div>
    <div v-if="formattedAmount" class="discount-amount">
      Ahorras {{ formattedAmount }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  discount: {
    type: Number,
    default: 0,
  },
  amount: {
    type: String,
    default: '',
  },
});

const formattedAmount = computed(() => props.amount || '');
</script>

<style scoped>
.discount-badge-container {
  position: relative;
  margin-bottom: 1rem;
}

.discount-badge {
  background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
  color: white;
  padding: 1rem 1.5rem;
  border-radius: 0.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
  animation: pulse-badge 2s ease-in-out infinite;
}

.discount-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 0.25rem;
}

.discount-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.9;
}

.discount-amount {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: #dc3545;
  font-weight: 600;
  text-align: center;
}

@keyframes pulse-badge {
  0%, 100% {
    box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
  }
  50% {
    box-shadow: 0 4px 20px rgba(220, 53, 69, 0.5);
  }
}

@media (max-width: 768px) {
  .discount-badge {
    padding: 0.75rem 1rem;
  }

  .discount-value {
    font-size: 1.5rem;
  }

  .discount-label {
    font-size: 0.7rem;
  }
}
</style>
