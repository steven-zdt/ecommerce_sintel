<template>
  <StatusTimeline
    mode="steps"
    accent-color="#7c3aed"
    :steps="STAGES"
    :active-index="activeIndex"
    :cancelled="isCancelled"
    cancelled-message="Esta solicitud de servicio fue cancelada."
  />
</template>

<script setup>
import { computed } from 'vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';

const props = defineProps({
  order: { type: Object, default: null },
});

const STAGES = [
  { key: 'CREATED',             label: 'Solicitud creada',       icon: 'bi bi-file-earmark-check' },
  { key: 'PAYMENT_INITIATED',   label: 'Pago iniciado',          icon: 'bi bi-credit-card' },
  { key: 'PAID',                label: 'Pago aprobado',          icon: 'bi bi-patch-check' },
  { key: 'AWAITING_ASSIGNMENT', label: 'Esperando asignacion',   icon: 'bi bi-hourglass-split' },
  { key: 'ASSIGNED',            label: 'Profesional asignado',   icon: 'bi bi-person-check' },
  { key: 'SCHEDULED',           label: 'Programado',             icon: 'bi bi-calendar-event' },
  { key: 'EN_ROUTE',            label: 'En camino',              icon: 'bi bi-truck' },
  { key: 'DONE',                label: 'Servicio realizado',     icon: 'bi bi-tools' },
  { key: 'FINISHED',            label: 'Finalizado',             icon: 'bi bi-check2-circle' },
];

const isCancelled = computed(() => props.order?.status === 'cancelled');

// Deriva la etapa visual a partir de Order.status + OrderServiceTimeline + presencia de
// tecnico/agenda -- no existen estos 9 estados como tal en el backend (ver plan: mismo
// "aliasing" que RentalTimeline.vue), asi que se aproxima con las senales reales disponibles.
const activeIndex = computed(() => {
  const order = props.order;
  if (!order) return 0;

  const detail = order.service_detail;
  const timelineStatuses = new Set((order.timeline || []).map(e => e.status));
  const paid = ['paid', 'delivered'].includes(order.status);
  const hasTechnician = !!detail?.technician;
  const hasSchedule = !!(detail?.confirmed_date || detail?.booked_date);
  const inProgress = timelineStatuses.has('in_progress');
  const done = order.status === 'delivered' || timelineStatuses.has('completed');

  let idx = paid ? 2 : 1; // al menos "pago iniciado" una vez la orden existe
  if (hasTechnician || timelineStatuses.has('assigned') || inProgress || done) idx = Math.max(idx, 4);
  if (hasSchedule) idx = Math.max(idx, 5);
  if (inProgress) idx = Math.max(idx, 6);
  if (done) idx = Math.max(idx, 8);
  return idx;
});
</script>
