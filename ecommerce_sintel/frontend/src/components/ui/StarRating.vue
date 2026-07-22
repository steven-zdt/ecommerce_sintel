<template>
  <div class="flex items-center gap-1" :class="{ 'cursor-pointer': !readOnly }">
    <div
      v-for="index in maxRating"
      :key="index"
      class="relative inline-block select-none"
      :style="{ width: size + 'px', height: size + 'px' }"
      @click="handleRatingClick(index)"
      @mousemove="handleMouseMove($event, index)"
      @mouseleave="handleMouseLeave"
    >
      <!-- Background Star (gray) -->
      <svg
        class="w-full h-full text-gray-300 transition-colors duration-200"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
      </svg>

      <!-- Foreground Star (gold/amber) -->
      <div
        class="absolute top-0 left-0 h-full overflow-hidden transition-all duration-100"
        :style="{ width: getFillWidth(index) + '%' }"
      >
        <svg
          class="text-amber-500 transition-colors duration-200"
          :style="{ width: size + 'px', height: size + 'px' }"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
        </svg>
      </div>
    </div>
    <span v-if="showValue" class="text-sm font-semibold text-gray-700 ml-1">
      {{ rating.toFixed(1) }}
    </span>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  rating: {
    type: Number,
    default: 0,
  },
  maxRating: {
    type: Number,
    default: 5,
  },
  size: {
    type: Number,
    default: 24,
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
  showValue: {
    type: Boolean,
    default: false,
  },
  allowHalf: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:rating']);

const hoverValue = ref(null);

const activeValue = computed(() => {
  if (hoverValue.value !== null) {
    return hoverValue.value;
  }
  return props.rating;
});

const getFillWidth = (index) => {
  const value = activeValue.value;
  if (value >= index) {
    return 100;
  }
  if (value > index - 1) {
    return (value - (index - 1)) * 100;
  }
  return 0;
};

const handleMouseMove = (event, index) => {
  if (props.readOnly) return;
  
  if (props.allowHalf) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    if (x < rect.width / 2) {
      hoverValue.value = index - 0.5;
    } else {
      hoverValue.value = index;
    }
  } else {
    hoverValue.value = index;
  }
};

const handleMouseLeave = () => {
  if (props.readOnly) return;
  hoverValue.value = null;
};

const handleRatingClick = (index) => {
  if (props.readOnly) return;
  
  const value = hoverValue.value !== null ? hoverValue.value : index;
  emit('update:rating', value);
};
</script>

<style scoped>
.text-gray-300 {
  color: #d1d5db;
}
.text-amber-500 {
  color: #f59e0b;
  filter: drop-shadow(0 0 2px rgba(245, 158, 11, 0.4));
}
.flex {
  display: flex;
}
.items-center {
  align-items: center;
}
.gap-1 {
  gap: 0.25rem;
}
.relative {
  position: relative;
}
.inline-block {
  display: inline-block;
}
.absolute {
  position: absolute;
}
.top-0 {
  top: 0;
}
.left-0 {
  left: 0;
}
.h-full {
  height: 100%;
}
.w-full {
  width: 100%;
}
.overflow-hidden {
  overflow: hidden;
}
.select-none {
  user-select: none;
}
.cursor-pointer {
  cursor: pointer;
}
.ml-1 {
  margin-left: 0.25rem;
}
.text-sm {
  font-size: 0.875rem;
}
.font-semibold {
  font-weight: 600;
}
.text-gray-700 {
  color: #374151;
}
.transition-colors {
  transition-property: color, background-color, border-color, text-decoration-color, fill, stroke;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 200ms;
}
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}
</style>
