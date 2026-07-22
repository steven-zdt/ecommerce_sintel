<template>
  <div class="sosc-card">
    <div class="sosc-header">
      <i class="bi bi-receipt-cutoff me-2 text-violet"></i>
      <span>Resumen de tu servicio</span>
    </div>

    <div class="sosc-body">
      <div class="sosc-row">
        <span class="sosc-label">Servicio</span>
        <span class="fw-semibold text-end">{{ serviceName }}</span>
      </div>
      <div v-if="variantSku" class="sosc-row">
        <span class="sosc-label">Variante</span>
        <code class="small">{{ variantSku }}</code>
      </div>
      <div class="sosc-row">
        <span class="sosc-label">Profesional</span>
        <span class="text-end">
          <span v-if="technicianName" class="fw-semibold">{{ technicianName }}</span>
          <span v-else class="badge bg-secondary-subtle text-secondary border border-secondary-subtle">Por asignar</span>
        </span>
      </div>
      <div v-if="durationHours" class="sosc-row">
        <span class="sosc-label">Duracion estimada</span>
        <span>{{ durationHours }} h</span>
      </div>
    </div>

    <div class="sosc-divider"></div>

    <div class="sosc-body">
      <ServicePriceBreakdown :price-info="priceInfo" />
    </div>
  </div>
</template>

<script setup>
import ServicePriceBreakdown from './ServicePriceBreakdown.vue';

defineProps({
  serviceName:    { type: String, default: '' },
  variantSku:     { type: String, default: '' },
  technicianName: { type: String, default: '' },
  durationHours:  { type: [Number, String], default: null },
  priceInfo:      { type: Object, default: null },
});
</script>

<style scoped>
.sosc-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.04); }
.sosc-header { display: flex; align-items: center; padding: 14px 20px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; font-weight: 700; font-size: .9rem; }
.sosc-body { padding: 6px 20px; }
.sosc-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 9px 0; border-bottom: 1px solid #f3f4f6; }
.sosc-row:last-child { border-bottom: none; }
.sosc-label { color: #6b7280; font-size: .85rem; flex-shrink: 0; }
.sosc-divider { border-top: 1px solid #e5e7eb; }
.text-violet { color: #7c3aed !important; }
</style>
