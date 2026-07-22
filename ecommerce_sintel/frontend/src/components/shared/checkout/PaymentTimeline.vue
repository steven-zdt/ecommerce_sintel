<template>
  <div>
    <div v-for="(ev, i) in events" :key="i" class="pmt-timeline-item">
      <div class="pmt-timeline-dot" :class="{ 'pmt-timeline-dot--active': i === 0 }"></div>
      <div class="pmt-timeline-content">
        <div class="small fw-semibold">{{ ev.status }}</div>
        <div v-if="ev.notes" class="text-muted" style="font-size:.75rem">{{ ev.notes }}</div>
        <div class="text-muted" style="font-size:.72rem">{{ fmtDatetime(ev.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Extraido de .pr-timeline-item/.pr-timeline-dot de PaymentResultView.vue.
// Mismo shape de datos que ya devuelve confirmation/ (TransactionEvent),
// sin cambios de contrato.
defineProps({
  events: { type: Array, default: () => [] },
});

function fmtDatetime(d) {
  if (!d) return '';
  return new Date(d).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
</script>

<style scoped>
.pmt-timeline-item { display: flex; gap: 12px; padding: 10px 20px; border-bottom: 1px solid #f3f4f6; }
.pmt-timeline-item:last-child { border-bottom: none; }
.pmt-timeline-dot { width: 10px; height: 10px; border-radius: 50%; background: #d1d5db; flex-shrink: 0; margin-top: 5px; }
.pmt-timeline-dot--active { background: #16a34a; box-shadow: 0 0 0 3px rgba(22,163,74,.2); }
.pmt-timeline-content { flex: 1; }
</style>
