<template>
  <div class="pmt-alert" :class="`pmt-alert--${variant}`">
    <i v-if="icon" :class="['bi', icon, 'flex-shrink-0', 'mt-1']"></i>
    <div v-if="spinner" class="d-flex align-items-center gap-2 flex-shrink-0">
      <div class="spinner-grow spinner-grow-sm text-warning" role="status"></div>
    </div>
    <div>
      <strong v-if="title">{{ title }}</strong>
      <slot />
    </div>
  </div>
</template>

<script setup>
// Mensaje contextual -- extraido de .pr-notice--info/warning/danger de
// PaymentResultView.vue. `spinner` reemplaza el icono cuando el mensaje
// acompaña un estado "en proceso" (mismo patron que ya usaba pr-notice--warning
// para "Pago en proceso").
defineProps({
  variant: { type: String, default: 'info' }, // 'info' | 'warning' | 'danger'
  icon: { type: String, default: '' },
  title: { type: String, default: '' },
  spinner: { type: Boolean, default: false },
});
</script>

<style scoped>
.pmt-alert {
  display: flex; align-items: flex-start; gap: 12px;
  border-radius: 10px; padding: 14px 16px;
}
.pmt-alert--info    { background: #eff6ff; border: 1px solid #bfdbfe; }
.pmt-alert--warning { background: #fffbeb; border: 1px solid #fde68a; }
.pmt-alert--danger  { background: #fef2f2; border: 1px solid #fecaca; }
</style>
