<template>
  <div v-if="priceInfo" class="spb-root">
    <div class="spb-row">
      <span class="spb-label"><i class="bi bi-tools me-1"></i>Costo mano de obra</span>
      <span class="fw-semibold">${{ fmt(priceInfo.labor_cost) }}</span>
    </div>
    <div v-if="Number(priceInfo.material_cost) > 0" class="spb-row">
      <span class="spb-label"><i class="bi bi-box-seam me-1"></i>Materiales</span>
      <span class="fw-semibold">${{ fmt(priceInfo.material_cost) }}</span>
    </div>
    <div class="spb-row spb-row--sub">
      <span class="spb-label">Subtotal</span>
      <span>${{ fmt(priceInfo.base) }}</span>
    </div>
    <div v-if="Number(priceInfo.discount_amount) > 0" class="spb-row">
      <span class="spb-label text-success">
        <span class="badge rounded-pill bg-success-subtle text-success me-1">-</span>
        Descuento ({{ priceInfo.discount_pct }}%)
      </span>
      <span class="fw-semibold text-success">-${{ fmt(priceInfo.discount_amount) }}</span>
    </div>
    <div class="spb-row">
      <span class="spb-label">IVA ({{ priceInfo.iva_rate }}%)</span>
      <span>${{ fmt(priceInfo.iva_amount) }}</span>
    </div>
    <div class="spb-row spb-row--total">
      <span class="fw-bold">Total</span>
      <span class="fw-bold fs-5 text-violet">${{ fmt(priceInfo.total ?? priceInfo.total_price) }}</span>
    </div>
  </div>
  <div v-else class="text-muted small text-center py-3">
    Sin desglose de precios disponible.
  </div>
</template>

<script setup>
defineProps({
  priceInfo: { type: Object, default: null },
});

function fmt(val) {
  return new Intl.NumberFormat('es-CO').format(Math.round(parseFloat(val) || 0));
}
</script>

<style scoped>
.spb-root { font-size: .875rem; }
.spb-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
.spb-row--sub { color: #6b7280; }
.spb-row--total { border-bottom: none; border-top: 1px solid #e5e7eb; margin-top: 4px; padding-top: 10px; }
.spb-label { color: #6b7280; }
.text-violet { color: #7c3aed !important; }
</style>
