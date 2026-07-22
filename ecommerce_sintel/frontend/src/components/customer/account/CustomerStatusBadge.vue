<template>
  <BaseStatusBadge
    class="acc-badge"
    :enum-name="enumName"
    :value="value"
    :show-icon="showIcon"
    :fallback-class="fallbackClass"
  />
</template>

<script setup>
/**
 * Badge de estado unico de "Mi Cuenta" -- delgado sobre
 * components/base/BaseStatusBadge.vue (que a su vez centraliza el patron que
 * antes estaba triplicado en OperationStatusBadge/ShipmentStatusBadge). Uso:
 * <CustomerStatusBadge enum-name="order-statuses" :value="order.status" />.
 */
import BaseStatusBadge from '@/components/base/BaseStatusBadge.vue';

defineProps({
  enumName: { type: String, required: true },
  value: { type: String, default: '' },
  showIcon: { type: Boolean, default: false },
  fallbackClass: { type: String, default: 'bg-secondary-subtle text-secondary' },
});
</script>

<style scoped>
.acc-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  font-size: 0.75rem;
}
</style>
