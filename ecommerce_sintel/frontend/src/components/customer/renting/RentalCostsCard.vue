<template>
  <section class="premium-card">
    <h3>Resumen de costos</h3>
    <div v-for="group in groups" :key="group.label" class="cost-group">
      <div class="cost-row">
        <span>{{ group.label }}</span>
        <strong>{{ money(group.value) }}</strong>
      </div>
      <div v-if="group.detail" class="cost-detail">{{ group.detail }}</div>
    </div>
    <div class="cost-row total">
      <span>Total estimado</span>
      <strong>{{ money(costs.total) }}</strong>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({ costs: { type: Object, required: true } });

const money = (v) => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0);

const groups = computed(() => {
  const c = props.costs;
  const logistics = (c.delivery || 0) + (c.pickup || 0);
  const services = (c.installation || 0) + (c.training || 0);
  return [
    { label: 'Alquiler', value: c.rental },
    { label: 'Logistica', value: logistics, detail: logistics ? 'Entrega y recogida' : '' },
    { label: 'Servicios', value: services, detail: services ? 'Instalacion y capacitacion' : '' },
    { label: 'Impuestos', value: c.tax },
  ].filter((group) => group.value > 0 || group.label === 'Alquiler');
});
</script>

<style scoped>
.premium-card {
  background: white;
  border: 1px solid #e8e7ee;
  border-radius: 20px;
  padding: 1.4rem;
  box-shadow: 0 12px 35px rgba(31, 25, 55, .05);
}
h3 { font-size: 1.05rem; font-weight: 750; margin-bottom: .3rem; }
.cost-group { border-bottom: 1px solid #f1f0f5; }
.cost-group:last-of-type { border-bottom: 0; }
.cost-row { display: flex; justify-content: space-between; padding: .52rem 0; color: #64748b; }
.cost-row strong { color: #1e293b; }
.cost-detail { color: #94a3b8; font-size: .72rem; margin: -.3rem 0 .4rem; }
.total { border-top: 1px solid #e2e8f0; margin-top: .4rem; padding-top: 1rem; font-size: 1.08rem; }
.total strong { color: #6d28d9; }
</style>
