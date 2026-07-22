<template>
  <div class="srs-stack">
    <div class="srs-card srs-head">
      <span>Resumen de tu solicitud</span>
      <strong v-if="variant?.estimated_hours">{{ variant.estimated_hours }} h estimadas</strong>
    </div>

    <div class="srs-card">
      <div class="srs-row">
        <i class="bi bi-tools text-violet"></i>
        <div>
          <div class="srs-service-name">{{ serviceName }}</div>
          <code v-if="variant?.sku" class="srs-sku">{{ variant.sku }}</code>
        </div>
      </div>

      <div v-if="pkg" class="srs-row srs-row--pkg">
        <i class="bi bi-box-seam-fill text-violet"></i>
        <div>
          <div class="srs-service-name">{{ pkg.name }}</div>
          <span class="srs-pkg-label">Paquete seleccionado</span>
        </div>
      </div>

      <div v-if="scheduleLabel" class="srs-row">
        <i class="bi bi-calendar-check-fill text-primary"></i>
        <div>
          <div class="srs-service-name">{{ scheduleLabel }}</div>
          <span class="srs-pkg-label">Fecha y jornada preferida</span>
        </div>
      </div>
    </div>

    <div v-if="priceInfo" class="srs-card">
      <ServicePriceBreakdown :price-info="priceInfo" />
    </div>
  </div>
</template>

<script setup>
import ServicePriceBreakdown from '@/components/customer/services/ServicePriceBreakdown.vue';

defineProps({
  serviceName:   { type: String, default: '' },
  variant:       { type: Object, default: null },
  pkg:           { type: Object, default: null },
  priceInfo:     { type: Object, default: null },
  scheduleLabel: { type: String, default: '' },
});
</script>

<style scoped>
.srs-stack { display: flex; flex-direction: column; gap: .75rem; position: sticky; top: 88px; }
.srs-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: .9rem 1rem; box-shadow: 0 1px 6px rgba(0,0,0,.04);
}
.srs-head { display: flex; align-items: center; justify-content: space-between; font-size: .82rem; color: #6b7280; font-weight: 700; }
.srs-head strong { color: #7c3aed; font-weight: 800; }
.srs-row { display: flex; align-items: flex-start; gap: .6rem; }
.srs-row--pkg { margin-top: .7rem; padding-top: .7rem; border-top: 1px dashed #e5e7eb; }
.srs-row + .srs-row:not(.srs-row--pkg) { margin-top: .7rem; padding-top: .7rem; border-top: 1px dashed #e5e7eb; }
.srs-row i { font-size: 1.05rem; margin-top: .1rem; }
.srs-service-name { font-weight: 750; color: #111827; font-size: .86rem; }
.srs-sku { color: #6b7280; font-size: .74rem; }
.srs-pkg-label { display: block; color: #9ca3af; font-size: .72rem; font-weight: 600; margin-top: .1rem; }
.text-violet { color: #7c3aed !important; }
</style>
