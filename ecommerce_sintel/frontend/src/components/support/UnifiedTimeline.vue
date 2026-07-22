<template>
  <StatusTimeline mode="events" :events="normalized" empty-message="Sin actividad registrada." />
</template>

<script setup>
import { computed } from 'vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';

const props = defineProps({ events: { type: Array, default: () => [] } });

const ICONS = {
  account: 'bi-person-check',
  order: 'bi-bag-check',
  rental: 'bi-truck',
  kyc: 'bi-patch-check',
  conversation: 'bi-headset',
};
const COLORS = {
  order: '#1e40af',
  rental: '#6d28d9',
  kyc: '#15803d',
  conversation: '#92400e',
};

const normalized = computed(() => props.events.map((ev) => ({
  key: `${ev.type}-${ev.uuid}`,
  label: ev.label,
  icon: ICONS[ev.type] || 'bi-dot',
  color: COLORS[ev.type],
  date: ev.date,
})));
</script>
