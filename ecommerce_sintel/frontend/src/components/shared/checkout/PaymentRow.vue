<template>
  <div class="pmt-row">
    <slot name="label">
      <span class="pmt-label" :class="{ 'fw-bold': boldLabel }">{{ label }}</span>
    </slot>
    <slot />
  </div>
</template>

<script setup>
// Fila label/valor dentro de una PaymentCard -- extraida de .pr-row/.pr-label.
// `label` cubre el caso comun (texto simple); el slot #label permite un area
// mas rica (ej. nombre + subtitulo de un item de orden) sin forzar a cada
// consumidor a salirse de PaymentRow para ese unico caso.
defineProps({
  label: { type: String, default: '' },
  boldLabel: { type: Boolean, default: false },
});
</script>

<style scoped>
.pmt-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 20px; gap: 12px;
  border-bottom: 1px solid #f3f4f6;
}
.pmt-row:last-child { border-bottom: none; }
.pmt-label { color: #6b7280; font-size: .85rem; flex-shrink: 0; }
</style>
