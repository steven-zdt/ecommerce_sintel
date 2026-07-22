<template>
  <p class="text-center text-muted small mb-0">
    <slot>Procesado de forma segura a traves de Wompi Colombia.</slot>
    <template v-if="referenceId">
      Referencia de transaccion: <code class="small">{{ referenceId }}</code>
    </template>
  </p>
</template>

<script setup>
// Nota legal -- extraida de PaymentResultView.vue, sin cambios de texto.
defineProps({
  referenceId: { type: String, default: '' },
});
</script>
