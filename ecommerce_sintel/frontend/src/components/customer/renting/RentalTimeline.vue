<template>
  <StatusTimeline mode="steps" accent-color="#7c3aed" :steps="STEPS" :active-index="activeIndex" />
</template>
<script setup>
import { computed } from 'vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';

const props = defineProps({ status: { type: String, default: 'CREATED' } });
const STEPS = [
  ['CREATED','Reserva creada','bi bi-file-earmark-check'], ['PAID','Pago recibido','bi bi-credit-card'],
  ['CONFIRMED','Reserva confirmada','bi bi-patch-check'], ['PREPARING','Preparando equipo','bi bi-tools'],
  ['DISPATCHED','Equipo despachado','bi bi-truck'], ['DELIVERED','Equipo entregado','bi bi-geo-alt'],
  ['INSTALLED','Equipo instalado','bi bi-wrench'], ['ACTIVE','Alquiler activo','bi bi-play-circle'],
  ['PICKUP_DUE','Próxima recogida','bi bi-calendar-event'], ['RECEIVED','Equipo recibido','bi bi-box-arrow-in-down'],
  ['INSPECTION','Inspección','bi bi-search'], ['CLOSED','Contrato cerrado','bi bi-check2-circle'],
].map(([key,label,icon]) => ({ key,label,icon }));
const aliases = { PENDING:'CREATED', PAYMENT_PENDING:'CREATED', APPROVED:'CONFIRMED', IN_PROGRESS:'ACTIVE', COMPLETED:'CLOSED' };
const activeIndex = computed(() => Math.max(0, STEPS.findIndex(e => e.key === (aliases[props.status] || props.status))));
</script>
