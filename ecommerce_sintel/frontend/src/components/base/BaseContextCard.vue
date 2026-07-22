<template>
  <div class="ctx-card">
    <div class="ctx-head">
      <i :class="icon" :style="{ color: iconColor }"></i>
      <strong>{{ title }}</strong>
      <slot name="badge" />
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, required: true },
  iconColor: { type: String, default: '#1e40af' },
  title: { type: String, required: true },
});
</script>

<style scoped>
.ctx-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 12px; font-size: 13px; }
.ctx-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.ctx-head :deep(.badge) { margin-left: auto; }
/* :deep() -- las filas .ctx-row llegan via slot desde el componente que envuelve
   este shell, y el CSS scoped normal no penetra contenido de slots ajenos. */
:deep(.ctx-row) { display: flex; justify-content: space-between; color: #6b7280; padding: 2px 0; }
:deep(.ctx-row strong) { color: #111827; }
</style>
