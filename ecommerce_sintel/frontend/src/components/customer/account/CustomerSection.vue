<template>
  <section class="acc-section">
    <div class="acc-section-head">
      <h3 class="acc-section-title">
        <i v-if="icon" :class="['bi', icon]"></i>
        {{ title }}
      </h3>
      <div v-if="$slots.actions" class="acc-section-actions">
        <slot name="actions" />
      </div>
    </div>
    <div class="acc-section-body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  icon: { type: String, default: '' },
});
</script>

<style scoped>
.acc-section {
  background: #fff;
  border: 1px solid var(--acc-border, #e5e7eb);
  border-radius: var(--acc-radius, 14px);
  padding: 24px;
}

.acc-section + .acc-section { margin-top: 16px; }

.acc-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.acc-section-title {
  font-weight: 700;
  color: var(--acc-text, #111827);
  font-size: 0.95rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
