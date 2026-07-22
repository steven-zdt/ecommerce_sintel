<template>
  <div class="acc-confirm">
    <span class="acc-confirm-msg">
      <i class="bi bi-exclamation-triangle-fill text-danger me-1"></i>{{ message }}
    </span>
    <div class="d-flex gap-2">
      <CustomerButton variant="danger" :loading="loading" @click="$emit('confirm')">
        {{ confirmLabel }}
      </CustomerButton>
      <CustomerButton variant="secondary" :disabled="loading" @click="$emit('cancel')">
        Cancelar
      </CustomerButton>
    </div>
  </div>
</template>

<script setup>
import CustomerButton from './CustomerButton.vue';

/**
 * Generaliza el patron `.addr-confirm-delete` (CustomerAddressView.vue) --
 * confirmacion destructiva inline, NUNCA `confirm()` nativo ni modal
 * flotante (regla ya documentada del proyecto en dialogs.md).
 */
defineProps({
  message: { type: String, default: 'Estas seguro de eliminar este elemento?' },
  confirmLabel: { type: String, default: 'Eliminar' },
  loading: { type: Boolean, default: false },
});
defineEmits(['confirm', 'cancel']);
</script>

<style scoped>
.acc-confirm {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--acc-radius-sm, 10px);
  background: #fef2f2;
  border: 1px solid #fecaca;
  flex-wrap: wrap;
}

.acc-confirm-msg {
  font-size: 0.875rem;
  color: #374151;
}
</style>
