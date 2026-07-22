<template>
  <div class="acc-shell">
    <AccountSidebar class="d-none d-lg-block" />
    <div class="acc-content" :style="contentStyle">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import AccountSidebar from '@/components/customer/AccountSidebar.vue';

/**
 * Layout unico de "Mi Cuenta" -- reemplaza el wrapper `.account-page` +
 * `<AccountSidebar>` + `.account-content` que estaba copy-pasteado en cada
 * vista. Define aqui las CSS custom properties del design system: heredan
 * por cascada a cualquier componente hijo (Card, Badge, EmptyState, etc.)
 * sin necesitar un CSS global, que el proyecto prohibe para el portal cliente.
 */
const props = defineProps({
  maxWidth: { type: String, default: '1100px' },
});

const contentStyle = computed(() => ({ '--acc-max-width': props.maxWidth }));
</script>

<style scoped>
.acc-shell {
  --acc-radius: 14px;
  --acc-radius-sm: 10px;
  --acc-radius-lg: 16px;
  --acc-border: #e5e7eb;
  --acc-text: #111827;
  --acc-muted: #6b7280;
  --acc-accent: #2563eb;
  --acc-accent-bg: #eff6ff;
  --acc-accent-border: #93c5fd;
  --acc-shadow-hover: 0 4px 16px rgba(0, 0, 0, 0.07);
  --acc-gap: 12px;

  display: flex;
  gap: 28px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 20px;
}

.acc-content {
  flex: 1;
  min-width: 0;
  max-width: var(--acc-max-width);
}
</style>
