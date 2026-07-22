<template>
  <div class="pkg-summary">
    <div class="pkg-summary-head">
      <span class="pkg-summary-kicker">Paquete seleccionado</span>
      <h3>{{ pkg.name }}</h3>
    </div>

    <ul v-if="pkg.included_items?.length" class="pkg-summary-includes">
      <li v-for="item in pkg.included_items" :key="item.uuid">
        <i class="bi bi-check2"></i>{{ item.title }}
      </li>
    </ul>

    <div v-if="selectedCosts.length" class="pkg-summary-costs">
      <span class="pkg-summary-costs-title">Costos adicionales</span>
      <div v-for="entry in selectedCosts" :key="entry.cost.uuid" class="pkg-summary-cost-row">
        <span>{{ entry.cost.name }} <small v-if="entry.quantity > 1">x{{ entry.quantity }}</small></span>
        <strong>{{ formatCOP(entry.cost.price * entry.quantity) }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  pkg: { type: Object, required: true },
  selectedCosts: { type: Array, default: () => [] },
});

function formatCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) return '';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(number);
}
</script>

<style scoped>
.pkg-summary { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1rem; }
.pkg-summary-head { margin-bottom: .7rem; }
.pkg-summary-kicker {
  display: block; color: #d97706; font-size: .68rem; font-weight: 800;
  text-transform: uppercase; letter-spacing: .07em; margin-bottom: .2rem;
}
.pkg-summary-head h3 { color: #0f172a; font-size: 1.05rem; font-weight: 850; margin: 0; }
.pkg-summary-includes { list-style: none; margin: 0 0 .8rem; padding: 0; display: flex; flex-direction: column; gap: .3rem; }
.pkg-summary-includes li { color: #475569; font-size: .8rem; }
.pkg-summary-includes i { color: #16a34a; margin-right: .35rem; }
.pkg-summary-costs { border-top: 1px solid #f1f5f9; padding-top: .7rem; }
.pkg-summary-costs-title { display: block; color: #64748b; font-size: .72rem; font-weight: 700; text-transform: uppercase; margin-bottom: .45rem; }
.pkg-summary-cost-row { display: flex; justify-content: space-between; font-size: .82rem; color: #475569; padding: .25rem 0; }
.pkg-summary-cost-row small { color: #94a3b8; }
.pkg-summary-cost-row strong { color: #0f172a; }
</style>
