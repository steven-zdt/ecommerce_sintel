<template>
  <div class="sk-wrap" :style="wrapStyle">
    <div
      v-for="n in count"
      :key="n"
      class="sk-block"
      :class="dark ? 'sk-dark' : 'sk-light'"
      :style="blockStyle"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  width:  { type: String,  default: '100%' },
  height: { type: String,  default: '20px' },
  radius: { type: String,  default: '8px' },
  dark:   { type: Boolean, default: false },
  count:  { type: Number,  default: 1 },
  gap:    { type: String,  default: '0.5rem' },
  inline: { type: Boolean, default: false },
});

const wrapStyle = computed(() => {
  if (props.count <= 1) return {};
  return {
    display: 'flex',
    flexDirection: props.inline ? 'row' : 'column',
    gap: props.gap,
  };
});

const blockStyle = computed(() => ({
  width: props.width,
  height: props.height,
  borderRadius: props.radius === 'full' ? '9999px' : props.radius,
  flexShrink: props.inline ? '0' : undefined,
}));
</script>

<style scoped>
.sk-block {
  animation: sk-shimmer 1.5s infinite linear;
}
.sk-light {
  background: linear-gradient(90deg, #e2e8f0 25%, #cbd5e1 50%, #e2e8f0 75%);
  background-size: 1000px 100%;
}
.sk-dark {
  background: linear-gradient(90deg,
    rgba(255,255,255,.06) 25%,
    rgba(255,255,255,.13) 50%,
    rgba(255,255,255,.06) 75%
  );
  background-size: 1000px 100%;
}
@keyframes sk-shimmer {
  0%   { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}
</style>
