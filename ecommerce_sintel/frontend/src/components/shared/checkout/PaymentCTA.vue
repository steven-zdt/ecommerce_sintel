<template>
  <RouterLink
    v-if="to"
    :to="to"
    class="pmt-cta"
    :class="[`pmt-cta--${variant}`, sizeClass]"
  >
    <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
    <i v-else-if="icon" :class="['bi', icon, 'me-2']"></i>
    <slot />
  </RouterLink>
  <button
    v-else
    type="button"
    class="pmt-cta"
    :class="[`pmt-cta--${variant}`, sizeClass]"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
    <i v-else-if="icon" :class="['bi', icon, 'me-2']"></i>
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

/**
 * CTA pill de Payment -- tomado de .reserve-btn/.ch-cta-primary de Renting
 * (ver PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 5). Estilo distinto a
 * proposito de CustomerButton.vue (que es Bootstrap utilitario, sin pill) --
 * confirmado NO duplicado en la Fase 8 del plan, mismo mecanismo de `loading`
 * + spinner que CustomerButton ya usa.
 */
const props = defineProps({
  variant: { type: String, default: 'primary' }, // 'primary' | 'secondary'
  size: { type: String, default: 'lg' }, // 'lg' | 'md'
  icon: { type: String, default: '' },
  to: { type: [String, Object], default: null },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
});
defineEmits(['click']);

const sizeClass = computed(() => (props.size === 'md' ? 'pmt-cta--md' : 'pmt-cta--lg'));
</script>

<style scoped>
.pmt-cta {
  display: inline-flex; align-items: center; justify-content: center;
  border: 0; border-radius: 999px;
  font-weight: 800; text-decoration: none;
  transition: transform .16s ease, background .16s ease;
}
.pmt-cta--lg { padding: .85rem 2rem; font-size: .95rem; }
.pmt-cta--md { padding: .58rem 1.1rem; font-size: .82rem; }
.pmt-cta--primary {
  background: var(--payment-accent, #7c3aed); color: #fff;
}
.pmt-cta--primary:hover:not(:disabled) { background: var(--payment-accent-hover, #6d28d9); color: #fff; }
.pmt-cta--secondary {
  background: #fff; color: #374151; border: 1px solid #d1d5db;
}
.pmt-cta--secondary:hover:not(:disabled) { background: #f9fafb; color: #374151; }
.pmt-cta:disabled { opacity: .6; cursor: not-allowed; }
</style>
