<template>
  <div
    class="dw-root"
    :class="{ 'dw-flip': flip }"
    :style="{ background: from }"
    aria-hidden="true"
  >
    <svg
      viewBox="0 0 1440 56"
      preserveAspectRatio="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M0,28 C240,56 480,0 720,28 C960,56 1200,0 1440,28 L1440,56 L0,56 Z"
        :fill="fill"
      />
    </svg>
  </div>
</template>

<script setup>
defineProps({
  fill: { type: String, default: '#ffffff' },
  from: { type: String, default: 'transparent' },
  flip: { type: Boolean, default: false },
});
</script>

<style scoped>
.dw-root {
  width: 100%;
  line-height: 0;
  overflow: hidden;
  height: 56px;
}
.dw-root svg {
  display: block;
  width: 100%;
  height: 100%;
}
.dw-flip svg { transform: scaleY(-1); }
</style>
