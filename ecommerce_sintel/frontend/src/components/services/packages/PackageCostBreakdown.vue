<template>
  <section class="cost-breakdown">
    <h3>Resumen de costos</h3>
    <div v-for="row in rows" :key="row.label" class="cost-row">
      <span>{{ row.label }}</span>
      <strong>{{ formatCOP(row.value) }}</strong>
    </div>
    <div v-if="breakdown.discount_amount > 0" class="cost-row discount">
      <span>Descuento ({{ breakdown.discount_pct }}%)</span>
      <strong>-{{ formatCOP(breakdown.discount_amount) }}</strong>
    </div>
    <div class="cost-row">
      <span>IVA ({{ breakdown.iva_rate }}%)</span>
      <strong>{{ formatCOP(breakdown.iva_amount) }}</strong>
    </div>
    <div class="cost-row total">
      <span>Total estimado</span>
      <strong>{{ formatCOP(breakdown.total) }}</strong>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { formatCOP as formatCOPBase } from '@/utils/money';

const props = defineProps({
  breakdown: { type: Object, required: true },
});

const rows = computed(() => {
  const b = props.breakdown;
  return [
    { label: 'Servicio', value: b.service_base },
    { label: 'Paquete', value: b.package_price },
    { label: 'Costos adicionales', value: b.additional_costs_total },
  ].filter((row) => parseFloat(row.value) > 0);
});

function formatCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) return '$ 0';
  return formatCOPBase(number, { withSymbol: true });
}
</script>

<style scoped>
.cost-breakdown {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.1rem;
}
.cost-breakdown h3 { font-size: 1rem; font-weight: 800; color: #0f172a; margin: 0 0 .6rem; }
.cost-row { display: flex; justify-content: space-between; padding: .45rem 0; color: #64748b; font-size: .86rem; }
.cost-row strong { color: #1e293b; }
.cost-row.discount strong { color: #16a34a; }
.cost-row.total { border-top: 1px solid #e2e8f0; margin-top: .4rem; padding-top: .9rem; font-size: 1.05rem; }
.cost-row.total strong { color: #d97706; }
</style>
