<template>
  <div class="acc-error">
    <i class="bi bi-exclamation-triangle acc-error-icon"></i>
    <h5 class="acc-error-title">{{ title }}</h5>
    <p v-if="description" class="acc-error-desc">{{ description }}</p>
    <CustomerButton variant="secondary" @click="$emit('retry')">
      <i class="bi bi-arrow-clockwise me-1"></i>Reintentar
    </CustomerButton>
  </div>
</template>

<script setup>
import CustomerButton from './CustomerButton.vue';

defineProps({
  title: { type: String, default: 'No se pudo cargar la informacion' },
  description: { type: String, default: 'Ocurrio un error inesperado. Intenta de nuevo.' },
});
defineEmits(['retry']);
</script>

<style scoped>
.acc-error {
  text-align: center;
  padding: 60px 20px;
  background: #fff;
  border: 1px solid var(--acc-border, #e5e7eb);
  border-radius: var(--acc-radius, 14px);
}

.acc-error-icon {
  font-size: 2.5rem;
  color: #f59e0b;
}

.acc-error-title {
  font-weight: 700;
  color: var(--acc-text, #111827);
  margin: 16px 0 8px;
}

.acc-error-desc {
  color: var(--acc-muted, #6b7280);
  margin-bottom: 20px;
}
</style>
