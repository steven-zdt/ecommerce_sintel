<template>
  <div
    class="gc-root"
    :class="[
      dark ? 'gc-dark' : 'gc-light',
      { 'gc-hoverable': hoverable, 'gc-padded': padded }
    ]"
  >
    <slot />
  </div>
</template>

<script setup>
defineProps({
  dark:      { type: Boolean, default: false },
  hoverable: { type: Boolean, default: false },
  padded:    { type: Boolean, default: true },
});
</script>

<style scoped>
.gc-root {
  border-radius: 20px;
  backdrop-filter: blur(14px) saturate(180%);
  -webkit-backdrop-filter: blur(14px) saturate(180%);
  transition: transform 0.38s cubic-bezier(0.16,1,0.3,1),
              box-shadow 0.38s cubic-bezier(0.16,1,0.3,1);
}
.gc-dark {
  background: rgba(255,255,255,.07);
  border: 1px solid rgba(255,255,255,.11);
}
.gc-light {
  background: rgba(255,255,255,.72);
  border: 1px solid rgba(255,255,255,.45);
  box-shadow: 0 4px 20px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.04);
}
.gc-padded { padding: 1.5rem; }
.gc-hoverable:hover {
  transform: translateY(-5px) scale(1.01);
  box-shadow: 0 16px 48px rgba(0,0,0,.12), 0 4px 12px rgba(0,0,0,.06);
}
</style>
