<template>
  <component
    :is="tag"
    class="acc-card"
    :class="[{ 'acc-card--highlighted': highlighted, 'acc-card--hover': hoverable, 'acc-card--brand': variant === 'brand' }, brandClass]"
  >
    <slot />
  </component>
</template>

<script setup>
import { computed } from 'vue';

/**
 * Card generica de "Mi Cuenta" -- centraliza el radio/sombra/padding que
 * antes estaba redefinido en cada vista (.order-card/.wishlist-card/
 * .quote-card/.address-card/.card-item). `variant="brand"` conserva el
 * unico tratamiento visual legitimamente distinto (gradiente de tarjeta de
 * credito en Metodos de Pago); `brandTone` elige el gradiente.
 */
const props = defineProps({
  tag: { type: String, default: 'div' },
  highlighted: { type: Boolean, default: false },
  hoverable: { type: Boolean, default: true },
  variant: { type: String, default: 'default' }, // 'default' | 'brand'
  brandTone: { type: String, default: 'blue' }, // 'blue' | 'green'
});

const brandClass = computed(() => (props.variant === 'brand' ? `acc-card--brand-${props.brandTone}` : ''));
</script>

<style scoped>
.acc-card {
  background: #fff;
  border: 1px solid var(--acc-border, #e5e7eb);
  border-radius: var(--acc-radius, 14px);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.acc-card--hover:hover {
  box-shadow: var(--acc-shadow-hover, 0 4px 16px rgba(0, 0, 0, 0.07));
}

.acc-card--highlighted {
  border-color: var(--acc-accent-border, #93c5fd);
  background: var(--acc-accent-bg, #eff6ff);
}

.acc-card--brand {
  color: #fff;
  min-height: 160px;
  gap: 8px;
}

.acc-card--brand-blue {
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
}

.acc-card--brand-green {
  background: linear-gradient(135deg, #065f46 0%, #059669 100%);
}
</style>
