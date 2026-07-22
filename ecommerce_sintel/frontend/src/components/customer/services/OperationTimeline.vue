<template>
  <TrackingTimeline :events="translated" />
</template>

<script setup>
import { computed } from 'vue';
import TrackingTimeline from '@/components/customer/ui/TrackingTimeline.vue';

const props = defineProps({
  events: { type: Array, default: () => [] },
});

// Traduce el vocabulario propio de ServiceOperationEvent al vocabulario que ya
// entiende TrackingTimeline.vue (compartido con la app operations) -- reuso sin
// tocar ese componente, en vez de construir un timeline nuevo desde cero.
const MILESTONE_MAP = {
  OPERATION_CREATED:    'CREATED',
  PLANNED:              'SCHEDULED',
  RESCHEDULED:          'SCHEDULED',
  TECHNICIAN_ASSIGNED:  'ASSIGNED',
  TECHNICIAN_UNASSIGNED:'NOTE',
  CUSTOMER_NOTIFIED:    'NOTIFIED',
  READY_TO_VISIT:       'READY',
  ON_THE_WAY:           'EN_ROUTE',
  ARRIVED:              'EN_ROUTE',
  IN_PROGRESS:          'IN_PROGRESS',
  COMPLETED:            'COMPLETED',
  CLOSED:               'COMPLETED',
  CANCELLED:            'CANCELLED',
  INCIDENT_REPORTED:    'NOTE',
  INCIDENT_RESOLVED:    'NOTE',
};

const translated = computed(() => props.events.map((ev) => ({
  ...ev,
  milestone: MILESTONE_MAP[ev.milestone] || ev.milestone,
})));
</script>
