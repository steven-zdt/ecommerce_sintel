<template>
  <div
    class="pmc-card" :class="{ 'pmc-card--active': active }"
    role="radio" :aria-checked="active" tabindex="0"
    @click="$emit('select')"
    @keydown.enter.prevent="$emit('select')"
    @keydown.space.prevent="$emit('select')"
  >
    <slot />
  </div>
</template>

<script setup>
/**
 * Card individual seleccionable -- extraida de `.pay-card` de
 * PaymentMethodSelector.vue (mismo estilo, mismos atributos de
 * accesibilidad: role="radio"/aria-checked/tabindex/teclado, ver
 * PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 7). No se retoco
 * PaymentMethodSelector.vue para usar este componente -- ya es codigo
 * estable y auditado de accesibilidad, se evita el riesgo de tocarlo sin
 * necesidad. Este componente se usa donde hace falta el mismo patron fuera
 * de PaymentMethodSelector (ej. seleccion de tarjeta guardada en Shop).
 */
defineProps({
  active: { type: Boolean, default: false },
});
defineEmits(['select']);
</script>

<style scoped>
.pmc-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; cursor: pointer; transition: all .15s; }
.pmc-card:hover { border-color: #c4b5fd; }
.pmc-card:focus-visible { outline: 2px solid var(--payment-accent, #7c3aed); outline-offset: 2px; }
.pmc-card--active { border-color: var(--payment-accent, #7c3aed); background: var(--payment-accent-tint, #f5f3ff); box-shadow: 0 0 0 2px rgba(124,58,237,.15); }
</style>
