<template>
  <div class="pmt-section-label">{{ label }}</div>
</template>

<script setup>
// Divisor de seccion dentro de una PaymentCard -- extraido de .pr-section-label
defineProps({ label: { type: String, required: true } });
</script>

<style scoped>
.pmt-section-label {
  padding: 8px 20px; background: #f3f4f6;
  font-size: .7rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .08em;
  color: #6b7280; border-top: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}
</style>
