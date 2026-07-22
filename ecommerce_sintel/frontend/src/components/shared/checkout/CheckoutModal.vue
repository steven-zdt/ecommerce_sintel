<template>
  <div v-if="open" class="ckm-overlay" :style="accentStyle" role="dialog" aria-modal="true" :aria-label="ariaLabel" @keydown.esc="handleEscape">
    <div class="ckm-box" tabindex="-1" ref="boxRef">
      <div class="ckm-topbar">
        <CheckoutStepper :steps="steps" :current="stepIndex" />
        <button
          v-if="canClose"
          type="button" class="btn-close ms-2 flex-shrink-0" aria-label="Cerrar"
          @click="requestClose"
        ></button>
      </div>

      <div class="ckm-content">
        <slot v-if="phase === 'summary'" name="summary" />
        <slot v-else-if="phase === 'method'" name="method" />
        <slot v-else-if="phase === 'status'" name="status" />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Shell generico de checkout en modal -- extraido de ServiceCheckoutModal.vue
 * (technical_services, rediseño 2026-07-09) para que Shop/Renting/Services
 * compartan el mismo contenedor, stepper y comportamiento de cierre.
 *
 * Este componente NO conoce pagos, ordenes ni ningun store especifico --
 * cada dominio sigue siendo dueño de su propia logica de pago/polling y
 * solo le pasa `phase`/`open`/`canClose` como props y llena los 3 slots
 * (summary/method/status) con SUS propios componentes de contenido (que
 * pueden ser los genericos de este mismo directorio -- PaymentMethodSelector,
 * PaymentStatusPanel -- o un resumen comercial propio del dominio).
 */
import { computed, ref, watch, nextTick } from 'vue';
import CheckoutStepper from './CheckoutStepper.vue';

const props = defineProps({
  open:       { type: Boolean, required: true },
  phase:      { type: String, required: true }, // 'summary' | 'method' | 'status'
  canClose:   { type: Boolean, default: true },
  steps:      { type: Array, default: () => ['Resumen', 'Metodo de pago', 'Estado'] },
  ariaLabel:  { type: String, default: 'Checkout' },
  // Color de acento del checkout -- violeta por defecto (decision de diseno
  // ya tomada por Renting y Services de forma independiente, ver
  // PLAN_DE_ACCION_UI_SERVICES_PAYMENT.md). Cada dominio puede sobreescribir
  // si en el futuro se decide lo contrario, pero el default es compartido.
  accentColor: { type: String, default: '#7c3aed' },
});
const emit = defineEmits(['close']);

const boxRef = ref(null);

const stepIndex = computed(() => ({ summary: 1, method: 2, status: 3 }[props.phase] || 1));

const accentStyle = computed(() => ({ '--checkout-accent': props.accentColor }));

function requestClose() {
  if (!props.canClose) return;
  emit('close');
}
function handleEscape() {
  requestClose();
}

// ── Manejo de foco (WCAG 2.4.3) -- mismo patron que SintelOffcanvas.vue:
// al abrir, mueve el foco al dialogo; al cerrar, lo devuelve al elemento
// que lo disparo (normalmente el boton "Pagar"/"Proceder al pago").
let triggerEl = null;
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    triggerEl = document.activeElement;
    nextTick(() => boxRef.value?.focus());
  } else {
    triggerEl?.focus?.();
    triggerEl = null;
  }
});
</script>

<style scoped>
.ckm-overlay {
  position: fixed; inset: 0; z-index: 1055;
  background: rgba(15, 23, 42, .55);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.ckm-box {
  background: #fff; border-radius: 18px;
  width: 100%; max-width: 520px;
  max-height: 90vh; overflow-y: auto;
  box-shadow: 0 24px 70px rgba(0,0,0,.3);
  outline: none;
}
.ckm-topbar { display: flex; align-items: flex-start; padding: 20px 24px 0; }
.ckm-content { padding: 4px 24px 28px; }
</style>
