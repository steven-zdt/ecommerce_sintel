<template>
  <span class="badge pmt-badge" :class="cssClass">
    <slot />
  </span>
</template>

<script setup>
/**
 * Envoltorio delgado del patron "subtle" de Bootstrap ya usado en Renting
 * y en CustomerStatusBadge.vue. Deliberadamente NO decide la clase/label --
 * el caller sigue resolviendola con useEnums() (mismo mecanismo que
 * PaymentResultView.vue ya usa), esto solo estandariza el markup del badge.
 * Ver PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 7/8.
 */
defineProps({
  cssClass: { type: String, default: 'bg-secondary-subtle text-secondary' },
});
</script>

<style scoped>
.pmt-badge { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; }
</style>
