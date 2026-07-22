<template>
  <button
    type="button"
    class="btn acc-btn"
    :class="[variantClass, sizeClass]"
    :disabled="disabled || loading"
    :aria-label="variant === 'icon' ? ariaLabel : null"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="spinner-border spinner-border-sm me-1" role="status"></span>
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue';

/**
 * Boton unico de "Mi Cuenta" -- variant/size consistentes en toda la
 * seccion en vez de clases Bootstrap sueltas por archivo. `variant="icon"`
 * exige ariaLabel (accesibilidad para boton solo-icono).
 */
const props = defineProps({
  variant: { type: String, default: 'primary' }, // 'primary' | 'secondary' | 'danger' | 'icon'
  size: { type: String, default: 'sm' }, // 'sm' | 'md'
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  // Requerido cuando variant="icon" (boton solo-icono sin texto visible) --
  // Vue no permite validar contra otra prop aqui, se documenta por convencion.
  ariaLabel: { type: String, default: null },
});
defineEmits(['click']);

const variantClass = computed(() => ({
  primary: 'btn-primary',
  secondary: 'btn-outline-secondary',
  danger: 'btn-danger',
  icon: 'btn-outline-secondary acc-btn--icon',
}[props.variant] || 'btn-primary'));

const sizeClass = computed(() => (props.size === 'md' ? '' : 'btn-sm'));
</script>

<style scoped>
.acc-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}

.acc-btn--icon {
  padding: 0.35rem 0.55rem;
  line-height: 1;
}
</style>
