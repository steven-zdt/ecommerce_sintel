<template>
  <!-- Backdrop -->
  <div
    v-if="modelValue"
    class="offcanvas-backdrop fade show"
    @click="$emit('update:modelValue', false)"
  ></div>

  <!-- Panel -->
  <div
    ref="panelEl"
    class="offcanvas offcanvas-end sintel-offcanvas"
    :class="{ show: modelValue }"
    :style="{ visibility: modelValue ? 'visible' : 'hidden', '--oc-width': width }"
    tabindex="-1"
    role="dialog"
    aria-modal="true"
    :aria-label="title || 'Panel'"
  >
    <!-- Header -->
    <div class="offcanvas-header border-bottom">
      <div>
        <h5 class="offcanvas-title mb-0">{{ title }}</h5>
        <p v-if="subtitle" class="text-muted small mb-0 mt-1">{{ subtitle }}</p>
      </div>
      <button
        type="button"
        class="btn-close"
        aria-label="Cerrar"
        @click="$emit('update:modelValue', false)"
        :disabled="loading"
      ></button>
    </div>

    <!-- Body -->
    <!-- El slot se monta/desmonta con el panel (en vez de quedar siempre
         montado y solo oculto) para que el formulario hijo arranque limpio
         en cada apertura -- de lo contrario su estado interno (reactive/ref)
         sobrevive al cierre y la siguiente apertura muestra datos viejos. -->
    <div class="offcanvas-body">
      <slot v-if="modelValue" />
    </div>

    <!-- Footer (slot opcional) -->
    <div v-if="$slots.footer" class="offcanvas-footer border-top p-3 d-flex gap-2 justify-content-end">
      <slot name="footer" />
    </div>
  </div>

</template>

<script setup>
import { ref, watch, nextTick } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  title:    { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width:    { type: String, default: '480px' },
  loading:  { type: Boolean, default: false },
});

defineEmits(['update:modelValue']);

// --- Manejo de foco (WCAG 2.2 — 2.4.3 Focus Order) ---------------------------
// Al abrir: mueve el foco al panel. Al cerrar: lo devuelve al elemento que lo
// disparo (normalmente el boton "Editar"/"Nueva Marca" de la vista List).
const panelEl = ref(null);
let triggerEl = null;

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    triggerEl = document.activeElement;
    nextTick(() => panelEl.value?.focus());
  } else {
    triggerEl?.focus?.();
    triggerEl = null;
  }
});
</script>

<style scoped>
.sintel-offcanvas {
  width: var(--oc-width, 480px) !important;
  transition: transform .3s ease-in-out;
  border-left: 1px solid rgba(0,0,0,.08);
  box-shadow: -10px 0 30px rgba(0,0,0,0.05);
}
.offcanvas-footer {
  background: #f8fafc;
}
.offcanvas-header {
  background: #f8fafc;
}
</style>
