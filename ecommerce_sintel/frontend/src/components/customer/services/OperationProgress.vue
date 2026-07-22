<template>
  <div v-if="status === 'CANCELLED'" class="op-cancelled">
    <i class="bi bi-x-circle-fill me-2"></i>Operacion cancelada.
  </div>
  <div v-else class="op-progress">
    <div v-for="(s, i) in STAGES" :key="s" class="op-stage" :class="{ 'op-stage--done': i <= activeIndex }">
      <div class="op-dot"><i v-if="i < activeIndex" class="bi bi-check"></i></div>
      <span class="op-label d-none d-md-inline">{{ LABELS[s] }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({ status: { type: String, required: true } });

const STAGES = [
  'READY_FOR_PLANNING', 'PLANNED', 'TECHNICIAN_ASSIGNED', 'CUSTOMER_NOTIFIED',
  'READY_TO_VISIT', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED',
];
const LABELS = {
  READY_FOR_PLANNING: 'Recepcion', PLANNED: 'Planeada', TECHNICIAN_ASSIGNED: 'Asignada',
  CUSTOMER_NOTIFIED: 'Notificada', READY_TO_VISIT: 'Lista', ON_THE_WAY: 'En camino',
  ARRIVED: 'En sitio', IN_PROGRESS: 'Ejecutando', COMPLETED: 'Realizado', CLOSED: 'Cerrada',
};
const activeIndex = computed(() => Math.max(0, STAGES.indexOf(props.status)));
</script>

<style scoped>
.op-progress { display: flex; align-items: center; }
.op-stage { display: flex; align-items: center; gap: 6px; flex: 1; color: #9ca3af; }
.op-dot { width: 20px; height: 20px; border-radius: 50%; background: #e5e7eb; display: flex; align-items: center; justify-content: center; font-size: .65rem; flex-shrink: 0; }
.op-stage--done { color: #172033; }
.op-stage--done .op-dot { background: #16a34a; color: #fff; }
.op-label { font-size: .68rem; white-space: nowrap; }
.op-stage:not(:last-child)::after { content: ''; flex: 1; height: 2px; background: #e5e7eb; margin: 0 4px; }
.op-stage--done:not(:last-child)::after { background: #16a34a; }
.op-cancelled { background: #fef2f2; color: #7f1d1d; border-radius: 8px; padding: 10px 14px; font-weight: 600; }
</style>
