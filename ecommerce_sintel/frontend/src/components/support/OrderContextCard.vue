<template>
  <BaseContextCard icon="bi bi-bag-check" icon-color="#1e40af" :title="`Pedido #${order.id}`">
    <template #badge>
      <span class="badge" :class="enums.cssClass('order-statuses', order.status)">
        {{ enums.label('order-statuses', order.status, order.status) }}
      </span>
    </template>
    <div class="ctx-row"><span>Total</span><strong>${{ fmt(order.total_amount) }}</strong></div>
    <div v-if="order.items_count" class="ctx-row"><span>Artículos</span><strong>{{ order.items_count }}</strong></div>
    <ShipmentStatusBadge v-if="order.shipment_status" :status="order.shipment_status" class="mt-1" />
  </BaseContextCard>
</template>

<script setup>
import { useEnums } from '@/composables/useEnums';
import ShipmentStatusBadge from '@/components/customer/orders/ShipmentStatusBadge.vue';
import BaseContextCard from '@/components/base/BaseContextCard.vue';
import { formatCOP } from '@/utils/money';

defineProps({ order: { type: Object, required: true } });
const enums = useEnums();
const fmt = (v) => formatCOP(v);
</script>
