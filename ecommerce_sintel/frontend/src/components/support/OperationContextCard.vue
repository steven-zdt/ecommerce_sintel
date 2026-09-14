<template>
  <BaseContextCard icon="bi bi-truck" icon-color="#b45309" :title="`${typeLabel} #${operation.ticket_number}`">
    <template #badge>
      <span class="badge" :class="enums.cssClass('operation-statuses', operation.status)">
        {{ enums.label('operation-statuses', operation.status, operation.status) }}
      </span>
    </template>
    <div v-if="operation.technician" class="ctx-row">
      <span>Técnico</span><strong>{{ operation.technician }}</strong>
    </div>
    <div v-if="operation.scheduled_date" class="ctx-row">
      <span>Programado</span><strong>{{ operation.scheduled_date }}</strong>
    </div>
  </BaseContextCard>
</template>

<script setup>
import { computed } from 'vue';
import { useEnums } from '@/composables/useEnums';
import BaseContextCard from '@/components/base/BaseContextCard.vue';

const props = defineProps({ operation: { type: Object, required: true } });
const enums = useEnums();
const typeLabel = computed(() => enums.label('operation-types', props.operation.operation_type, props.operation.operation_type));
</script>
