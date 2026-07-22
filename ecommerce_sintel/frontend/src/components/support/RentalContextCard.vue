<template>
  <BaseContextCard icon="bi bi-truck" icon-color="#6d28d9" :title="`Alquiler #${rental.id}`">
    <template #badge>
      <span class="badge" :class="enums.cssClass('rental-statuses', rental.status)">
        {{ enums.label('rental-statuses', rental.status, rental.status) }}
      </span>
    </template>
    <div class="ctx-row"><span>Solicitado</span><strong>{{ formatDate(rental.created_at) }}</strong></div>
  </BaseContextCard>
</template>

<script setup>
import { useEnums } from '@/composables/useEnums';
import BaseContextCard from '@/components/base/BaseContextCard.vue';

defineProps({ rental: { type: Object, required: true } });
const enums = useEnums();

function formatDate(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }); } catch { return ''; }
}
</script>
