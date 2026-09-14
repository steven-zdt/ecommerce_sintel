<template>
  <BaseContextCard icon="bi bi-file-earmark-text" icon-color="#0e7490" :title="`Cotización #${quotation.id}`">
    <template #badge>
      <span class="badge" :class="enums.cssClass('quote-statuses', quotation.status)">
        {{ enums.label('quote-statuses', quotation.status, quotation.status) }}
      </span>
    </template>
    <div v-if="Number(quotation.total_amount) > 0" class="ctx-row">
      <span>Total</span><strong>${{ fmt(quotation.total_amount) }}</strong>
    </div>
  </BaseContextCard>
</template>

<script setup>
import { useEnums } from '@/composables/useEnums';
import BaseContextCard from '@/components/base/BaseContextCard.vue';
import { formatCOP } from '@/utils/money';

defineProps({ quotation: { type: Object, required: true } });
const enums = useEnums();
const fmt = (v) => formatCOP(v);
</script>
