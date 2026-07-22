<template>
  <div class="toast-container position-fixed bottom-0 end-0 p-3" style="z-index:9999">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast align-items-center show"
        :class="toastClass(toast.type)"
        role="alert"
      >
        <div class="d-flex">
          <div class="toast-body d-flex align-items-center gap-2">
            <i :class="toastIcon(toast.type)"></i>
            {{ toast.message }}
          </div>
          <button type="button" class="btn-close me-2 m-auto" @click="removeToast(toast.id)"></button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToast } from '@/composables/useToast';
const { toasts, removeToast } = useToast();

function toastClass(type) {
  return {
    'bg-success text-white border-0': type === 'success',
    'bg-danger text-white border-0': type === 'error',
    'bg-warning border-0': type === 'warning',
    'bg-info text-white border-0': type === 'info',
  };
}
function toastIcon(type) {
  const icons = {
    success: 'bi bi-check-circle-fill',
    error: 'bi bi-x-circle-fill',
    warning: 'bi bi-exclamation-triangle-fill',
    info: 'bi bi-info-circle-fill',
  };
  return icons[type] || 'bi bi-bell-fill';
}
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all .3s ease; }
.toast-enter-from { opacity: 0; transform: translateX(100%); }
.toast-leave-to { opacity: 0; transform: translateX(100%); }
</style>
