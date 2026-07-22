<template>
  <StatusTimeline
    mode="steps"
    accent-color="#2563eb"
    :steps="STAGES"
    :active-index="activeIndex"
    :cancelled="isFailed"
    :cancelled-message="failedMessage"
  />
</template>

<script setup>
import { computed } from 'vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';

const props = defineProps({
  shipment: { type: Object, default: null },
});

// Orden 1:1 con orders.Shipment.STATUS_CHOICES -- a diferencia de ServiceTimeline
// (que aproxima 9 etapas visuales sobre estados que no existen en el backend),
// aqui el shipment YA tiene el estado real, sin necesidad de inferir nada.
const STAGES = [
  { key: 'PREPARING',          label: 'Pedido recibido',      icon: 'bi bi-file-earmark-check' },
  { key: 'READY_FOR_DISPATCH', label: 'Empacado',              icon: 'bi bi-box-seam' },
  { key: 'ASSIGNED',           label: 'Transportista asignado', icon: 'bi bi-person-check' },
  { key: 'PICKED_UP',          label: 'Despachado',            icon: 'bi bi-truck' },
  { key: 'IN_TRANSIT',         label: 'En transito',           icon: 'bi bi-signpost-split' },
  { key: 'OUT_FOR_DELIVERY',   label: 'En reparto',            icon: 'bi bi-geo-alt' },
  { key: 'delivered',          label: 'Entregado',             icon: 'bi bi-check2-circle' },
];

const stepOrder = STAGES.map(s => s.key);

const isFailed = computed(() => ['FAILED_DELIVERY', 'LOST'].includes(props.shipment?.status));
const failedMessage = computed(() => (
  props.shipment?.status === 'LOST'
    ? 'Este envio se reporto como perdido.'
    : 'La entrega de este envio fallo. Nuestro equipo se pondra en contacto.'
));

const activeIndex = computed(() => {
  const status = props.shipment?.status;
  if (!status) return 0;
  const idx = stepOrder.indexOf(status);
  if (idx >= 0) return idx;
  return status === 'COMPLETED' ? stepOrder.length - 1 : 0;
});
</script>
