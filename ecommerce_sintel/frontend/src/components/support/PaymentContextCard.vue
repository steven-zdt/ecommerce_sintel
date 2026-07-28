<template>
  <BaseContextCard icon="bi bi-credit-card" icon-color="#b45309" :title="`Pago del pedido #${order.id}`">
    <template #badge>
      <span class="badge" :class="enums.cssClass('order-statuses', order.status)">
        {{ enums.label('order-statuses', order.status, order.status) }}
      </span>
    </template>
    <div class="ctx-row"><span>Método</span><strong>{{ enums.label('order-payment-methods', order.payment_method, order.payment_method) }}</strong></div>
    <div class="ctx-row"><span>Monto</span><strong>${{ fmt(order.total_amount) }}</strong></div>
  </BaseContextCard>
</template>

<script setup>
import { useEnums } from '@/composables/useEnums';
import BaseContextCard from '@/components/base/BaseContextCard.vue';
import { formatCOP } from '@/utils/money';

defineProps({ order: { type: Object, required: true } });
const enums = useEnums();
const fmt = (v) => formatCOP(v);
</script>
