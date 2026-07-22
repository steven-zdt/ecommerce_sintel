<template>
  <div class="acc-row">
    <div class="acc-row-label">
      <i v-if="icon" :class="['bi', icon]"></i>
      {{ label }}
    </div>
    <div class="acc-row-value">
      <slot>{{ value || '—' }}</slot>
    </div>
    <div v-if="$slots.action" class="acc-row-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '' },
  icon: { type: String, default: '' },
});
</script>

<style scoped>
.acc-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f3f4f6;
}

.acc-row:last-child { border-bottom: none; }

.acc-row-label {
  flex: 0 0 40%;
  color: var(--acc-muted, #6b7280);
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.acc-row-value {
  flex: 1;
  color: var(--acc-text, #111827);
  font-size: 0.9rem;
  font-weight: 500;
}

.acc-row-action { flex-shrink: 0; }

@media (max-width: 576px) {
  .acc-row { flex-wrap: wrap; }
  .acc-row-label { flex: 1 1 100%; }
}
</style>
