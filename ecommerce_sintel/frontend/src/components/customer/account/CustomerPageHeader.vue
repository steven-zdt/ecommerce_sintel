<template>
  <div class="acc-header">
    <div class="acc-header-text">
      <h2 class="acc-header-title">{{ title }}</h2>
      <p v-if="subtitle" class="acc-header-subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="acc-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
});
</script>

<style scoped>
.acc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.acc-header-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--acc-text, #111827);
  margin: 0 0 2px;
}

.acc-header-subtitle {
  color: var(--acc-muted, #6b7280);
  font-size: 0.875rem;
  margin: 0;
}

.acc-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

@media (max-width: 576px) {
  .acc-header { flex-direction: column; }
}
</style>
