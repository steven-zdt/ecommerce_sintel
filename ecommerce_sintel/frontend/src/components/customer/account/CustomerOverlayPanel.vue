<template>
  <div v-if="modelValue" class="acc-overlay" @click.self="close">
    <div class="acc-overlay-panel" :style="{ maxWidth: width }" role="dialog" aria-modal="true">
      <div class="acc-overlay-header">
        <div>
          <h5 class="acc-overlay-title">{{ title }}</h5>
          <p v-if="subtitle" class="acc-overlay-subtitle">{{ subtitle }}</p>
        </div>
        <button type="button" class="btn-close" aria-label="Cerrar" @click="close"></button>
      </div>
      <div class="acc-overlay-body">
        <slot />
      </div>
      <div v-if="$slots.footer" class="acc-overlay-footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Une `.form-overlay`/`.form-panel` (Address) y `.modal-overlay`/
 * `.detail-modal` (Orders/Quotes) en un unico componente -- exclusivo para
 * formularios/detalle, NUNCA para confirmaciones (usar CustomerConfirmInline).
 */
const props = defineProps({
  modelValue: { type: Boolean, required: true },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width: { type: String, default: '560px' },
});
const emit = defineEmits(['update:modelValue']);

function close() {
  emit('update:modelValue', false);
}
</script>

<style scoped>
.acc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1055;
  padding: 20px;
}

.acc-overlay-panel {
  background: #fff;
  border-radius: var(--acc-radius-lg, 16px);
  padding: 28px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.acc-overlay-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.acc-overlay-title {
  font-weight: 700;
  color: var(--acc-text, #111827);
  margin: 0;
}

.acc-overlay-subtitle {
  color: var(--acc-muted, #6b7280);
  font-size: 0.8rem;
  margin: 4px 0 0;
}

.acc-overlay-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}
</style>
