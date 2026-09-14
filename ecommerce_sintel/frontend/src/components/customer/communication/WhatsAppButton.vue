<template>
  <button
    type="button"
    role="menuitem"
    class="comm-option comm-option--whatsapp"
    :disabled="!ready"
    @click="$emit('click')"
  >
    <span class="comm-option-icon">
      <i class="bi bi-whatsapp"></i>
    </span>
    <span class="comm-option-text">
      <span class="comm-option-title">WhatsApp</span>
      <span class="comm-option-subtitle">
        {{ ready ? 'Escríbenos, respondemos rápido' : 'No disponible en este momento' }}
      </span>
    </span>
    <i class="bi bi-chevron-right comm-option-chevron" aria-hidden="true"></i>
  </button>
</template>

<script setup>
defineProps({
  ready: { type: Boolean, default: false },
});
defineEmits(['click']);
</script>

<style scoped>
.comm-option {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.comm-option:hover:not(:disabled),
.comm-option:focus-visible:not(:disabled) {
  background: #eff6ff;
  border-color: #93c5fd;
}

.comm-option:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.comm-option:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.comm-option-icon {
  width: 40px;
  height: 40px;
  min-width: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  background: #eff6ff;
  color: #1e3a8a;
}

.comm-option-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.comm-option-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: #111827;
}

.comm-option-subtitle {
  font-size: 0.78rem;
  color: #6b7280;
}

.comm-option-chevron {
  margin-left: auto;
  color: #9ca3af;
  font-size: 0.8rem;
}
</style>
