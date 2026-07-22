<template>
  <div v-if="modelValue" class="bm-backdrop" @click.self="close">
    <div class="bm-modal" :class="{ 'bm-modal--wide': wide }">
      <div class="bm-modal__header">
        <h5>{{ title }}</h5>
        <button class="btn-close" @click="close"></button>
      </div>
      <div class="bm-modal__body" :class="bodyClass">
        <slot />
      </div>
      <div v-if="$slots.footer" class="bm-modal__footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, required: true },
  title: { type: String, default: '' },
  wide: { type: Boolean, default: false },
  bodyClass: { type: [String, Array, Object], default: '' },
});

const emit = defineEmits(['update:modelValue']);

function close() {
  emit('update:modelValue', false);
}
</script>

<style scoped>
.bm-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  z-index: 1050; display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px); padding: 1rem;
}
.bm-modal {
  background: #fff; border-radius: 18px;
  width: 100%; max-width: 540px; max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,.18);
  overflow: hidden;
}
.bm-modal--wide { max-width: 800px; }
.bm-modal__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}
.bm-modal__header h5 { font-weight: 800; font-size: .95rem; color: #0f172a; margin: 0; }
.bm-modal__body { padding: 1.5rem; overflow-y: auto; flex: 1; }
.bm-modal__body--two-col { display: grid; grid-template-columns: 1fr 280px; gap: 1.25rem; }
.bm-modal__footer {
  display: flex; align-items: center; justify-content: flex-end; gap: .5rem;
  padding: 1rem 1.5rem; border-top: 1px solid #f1f5f9; flex-shrink: 0;
}
</style>
