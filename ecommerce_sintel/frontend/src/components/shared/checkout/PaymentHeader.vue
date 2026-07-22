<template>
  <div class="pmt-header" :class="`pmt-header--${variant}`">
    <div class="pmt-header-icon"><i :class="['bi', icon]" class="fs-2"></i></div>
    <div class="flex-grow-1">
      <div class="pmt-header-title">{{ title }}</div>
      <div v-if="subtitle" class="pmt-header-sub">{{ subtitle }}</div>
    </div>
    <span v-if="$slots.badge" class="ms-auto"><slot name="badge" /></span>
  </div>
</template>

<script setup>
/**
 * Banner de estado -- extraido de .pr-status-banner de PaymentResultView.vue.
 * Version reducida del hero de Renting (mismo gradiente, dimensionado para
 * una pantalla transaccional, ver PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md
 * seccion 5).
 */
defineProps({
  variant: { type: String, default: 'secondary' }, // 'success' | 'warning' | 'danger' | 'secondary'
  icon: { type: String, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
});
</script>

<style scoped>
.pmt-header {
  display: flex; align-items: center; gap: 16px;
  padding: 20px 24px; border-radius: 14px;
  color: #fff; flex-wrap: wrap;
}
.pmt-header--success { background: linear-gradient(135deg, #166534 0%, #16a34a 100%); box-shadow: 0 8px 24px rgba(22,163,74,.25); }
.pmt-header--warning { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); box-shadow: 0 8px 24px rgba(217,119,6,.25); }
.pmt-header--danger  { background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); box-shadow: 0 8px 24px rgba(220,38,38,.25); }
.pmt-header--secondary { background: linear-gradient(135deg, #374151 0%, #6b7280 100%); box-shadow: 0 8px 24px rgba(107,114,128,.25); }
.pmt-header-icon {
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(255,255,255,.2);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.pmt-header-title { font-size: 1.25rem; font-weight: 800; }
.pmt-header-sub { font-size: .88rem; opacity: .85; margin-top: 2px; }
</style>
