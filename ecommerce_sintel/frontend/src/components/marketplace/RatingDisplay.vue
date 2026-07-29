<template>
  <div v-if="rating" class="rating-display">
    <div class="rating-header">
      <div class="rating-stars">
        <div class="star-group">
          <i v-for="n in 5" :key="n" :class="['bi', getStarIcon(n), 'star']"></i>
        </div>
        <span class="rating-value">{{ rating.average_rating.toFixed(1) }}</span>
      </div>
      <span class="rating-count">{{ rating.total_count }} reseña{{ rating.total_count !== 1 ? 's' : '' }}</span>
    </div>

    <div v-if="showBreakdown" class="rating-breakdown">
      <div v-for="star in [5, 4, 3, 2, 1]" :key="star" class="breakdown-row">
        <span class="star-label">
          <i class="bi bi-star-fill"></i> {{ star }}
        </span>
        <div class="breakdown-bar">
          <div class="breakdown-fill" :style="{ width: getBreakdownPercent(star) + '%' }"></div>
        </div>
        <span class="breakdown-count">{{ rating.rating_breakdown[star] || 0 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  rating: {
    type: Object,
    default: null,
    // { average_rating: 4.5, total_count: 42, rating_breakdown: { 5: 30, 4: 10, 3: 2, 2: 0, 1: 0 } }
  },
  showBreakdown: {
    type: Boolean,
    default: true,
  },
});

function getStarIcon(position) {
  const rating = props.rating?.average_rating || 0;
  if (position <= Math.floor(rating)) {
    return 'bi-star-fill';
  }
  if (position - 0.5 < rating) {
    return 'bi-star-half';
  }
  return 'bi-star';
}

function getBreakdownPercent(star) {
  if (!props.rating?.total_count) return 0;
  return Math.round((props.rating.rating_breakdown[star] || 0) / props.rating.total_count * 100);
}
</script>

<style scoped>
.rating-display {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rating-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.rating-stars {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.star-group {
  display: flex;
  gap: 0.25rem;
}

.star {
  font-size: 1.25rem;
  color: #ffc107;
  line-height: 1;
}

.rating-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--bs-body-color);
  min-width: 40px;
}

.rating-count {
  font-size: 0.875rem;
  color: var(--bs-secondary);
}

.rating-breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.breakdown-row {
  display: grid;
  grid-template-columns: 50px 1fr 40px;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.85rem;
}

.star-label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--bs-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.star-label i {
  font-size: 0.9rem;
  color: #ffc107;
}

.breakdown-bar {
  height: 6px;
  background: var(--bs-gray-200);
  border-radius: 3px;
  overflow: hidden;
}

.breakdown-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffc107 0%, #ffb300 100%);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.breakdown-count {
  text-align: right;
  color: var(--bs-secondary);
  font-weight: 500;
}

@media (max-width: 576px) {
  .rating-header {
    gap: 0.75rem;
  }

  .star {
    font-size: 1rem;
  }

  .rating-value {
    font-size: 1.25rem;
  }

  .breakdown-row {
    grid-template-columns: 45px 1fr 35px;
  }
}
</style>
