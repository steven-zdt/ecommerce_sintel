<template>
  <div class="pmt-card">
    <div v-if="title || $slots['header-end']" class="pmt-card-header">
      <i v-if="icon" :class="['bi', icon, 'me-2', iconClass]"></i>
      <span v-if="title">{{ title }}</span>
      <span v-if="headerExtra" class="ms-auto text-muted small fw-normal">{{ headerExtra }}</span>
      <span v-if="$slots['header-end']" class="ms-auto"><slot name="header-end" /></span>
    </div>
    <slot />
  </div>
</template>

<script setup>
/**
 * Card generica de Payment -- extraida de .pr-card/.pr-card-header de
 * PaymentResultView.vue (mismo border/radius/header-con-franja-gris que
 * .sosc-card de Services y .acc-card de Mi Cuenta, ver
 * PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 3, hallazgo 3).
 *
 * El body es un slot libre -- PaymentResultView.vue arma varias secciones
 * dentro de UNA sola card (Transaccion/Orden/Articulos/...) usando
 * PaymentSectionLabel + markup de fila propio, igual que hoy, para no
 * cambiar la agrupacion visual existente.
 */
defineProps({
  icon: { type: String, default: '' },
  iconClass: { type: String, default: 'text-payment-accent' },
  title: { type: String, default: '' },
  headerExtra: { type: String, default: '' },
});
</script>

<style scoped>
.pmt-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.04); }
.pmt-card-header {
  display: flex; align-items: center;
  padding: 14px 20px; background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 700; font-size: .9rem; color: #111;
}
.text-payment-accent { color: var(--payment-accent, #7c3aed) !important; }
</style>
