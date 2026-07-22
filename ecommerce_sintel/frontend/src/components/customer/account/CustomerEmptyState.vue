<template>
  <div class="acc-empty">
    <i class="bi acc-empty-icon" :class="icon"></i>
    <h5 class="acc-empty-title">{{ title }}</h5>
    <p v-if="description" class="acc-empty-desc">{{ description }}</p>
    <slot name="action" />
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: 'bi-inbox' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
});
</script>

<style scoped>
.acc-empty {
  text-align: center;
  padding: 60px 20px;
  background: #fff;
  border: 1px solid var(--acc-border, #e5e7eb);
  border-radius: var(--acc-radius, 14px);
}

.acc-empty-icon {
  font-size: 2.5rem;
  color: #9ca3af;
}

.acc-empty-title {
  font-weight: 700;
  color: var(--acc-text, #111827);
  margin: 16px 0 8px;
}

.acc-empty-desc {
  color: var(--acc-muted, #6b7280);
  margin-bottom: 20px;
}
</style>
