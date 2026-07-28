<template>
  <div class="pstp-root" role="status" aria-live="polite" aria-atomic="true">

    <!-- PROCESANDO -->
    <div v-if="status === 'processing'" class="pstp-state text-center">
      <div class="spinner-border text-checkout-accent mb-3" style="width:3rem;height:3rem;" role="status"></div>
      <h3 class="fw-bold mb-2">Procesando pago...</h3>
      <p class="text-muted mb-0">Estamos verificando la respuesta de la pasarela.</p>
      <p class="text-muted small fw-semibold mt-2"><i class="bi bi-shield-lock me-1"></i>No cierres esta ventana.</p>
    </div>

    <!-- APROBADO -->
    <div v-else-if="status === 'approved'" class="pstp-state text-center">
      <div class="pstp-icon pstp-icon--success mx-auto mb-3"><i class="bi bi-check-lg"></i></div>
      <h3 class="fw-bold mb-1">Pago aprobado</h3>
      <p class="text-muted mb-3">{{ approvedMessage }}</p>
      <div class="pstp-summary mb-3">
        <div v-if="orderUuid" class="pstp-row"><span class="text-muted small">N. de orden</span><code class="small">{{ orderUuid }}</code></div>
        <div v-if="txUuid" class="pstp-row"><span class="text-muted small">N. de pago</span><code class="small">{{ txUuid }}</code></div>
        <div v-if="total" class="pstp-row"><span class="text-muted small">Total pagado</span><span class="fw-bold text-success">${{ fmt(total) }} COP</span></div>
      </div>
      <button class="btn btn-checkout-accent fw-bold w-100 py-3" @click="$emit('view-tracking')">
        <i class="bi bi-arrow-right-circle me-2"></i>{{ trackingLabel }}
      </button>
    </div>

    <!-- RECHAZADO -->
    <div v-else-if="status === 'declined'" class="pstp-state text-center">
      <div class="pstp-icon pstp-icon--danger mx-auto mb-3"><i class="bi bi-x-lg"></i></div>
      <h3 class="fw-bold mb-1">Pago rechazado</h3>
      <p class="text-muted mb-3">Verifica los datos de tu tarjeta o intenta con otro metodo de pago. No se realizo ningun cargo.</p>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary flex-fill py-3" @click="$emit('retry')">
          <i class="bi bi-arrow-clockwise me-2"></i>Reintentar
        </button>
        <button class="btn btn-checkout-accent fw-bold flex-fill py-3" @click="$emit('change-method')">
          <i class="bi bi-credit-card-2-front me-2"></i>Cambiar metodo
        </button>
      </div>
    </div>

    <!-- PENDIENTE -->
    <div v-else-if="status === 'pending'" class="pstp-state text-center">
      <div class="pstp-icon pstp-icon--warning mx-auto mb-3"><i class="bi bi-hourglass-split"></i></div>
      <h3 class="fw-bold mb-1">Pago pendiente</h3>
      <p class="text-muted mb-2">Estamos verificando tu transaccion. Esto se actualiza automaticamente.</p>
      <p v-if="pollTimedOut" class="text-muted small mb-0">
        Esto esta tomando mas de lo usual. Puedes cerrar esta ventana — te avisaremos por correo cuando se confirme.
      </p>
      <div class="spinner-grow spinner-grow-sm text-warning mt-2" role="status"></div>
    </div>

    <!-- EXPIRADO -->
    <div v-else-if="status === 'expired'" class="pstp-state text-center">
      <div class="pstp-icon pstp-icon--secondary mx-auto mb-3"><i class="bi bi-clock-history"></i></div>
      <h3 class="fw-bold mb-1">El pago expiro</h3>
      <p class="text-muted mb-3">No completaste el pago a tiempo. Puedes generar uno nuevo.</p>
      <button class="btn btn-checkout-accent fw-bold w-100 py-3" @click="$emit('new-payment')">
        <i class="bi bi-arrow-repeat me-2"></i>Generar nuevo pago
      </button>
    </div>

    <!-- CANCELADO -->
    <div v-else-if="status === 'cancelled'" class="pstp-state text-center">
      <div class="pstp-icon pstp-icon--secondary mx-auto mb-3"><i class="bi bi-slash-circle"></i></div>
      <h3 class="fw-bold mb-1">Pago cancelado</h3>
      <p class="text-muted mb-3">Cerraste la ventana de pago sin completar la transaccion.</p>
      <button class="btn btn-outline-secondary w-100 py-3" @click="$emit('close')">
        <i class="bi bi-arrow-left me-2"></i>Volver
      </button>
    </div>

  </div>
</template>

<script setup>
import { formatCOP } from '@/utils/money';

defineProps({
  status:          { type: String, required: true }, // processing | approved | declined | pending | expired | cancelled
  orderUuid:       { type: String, default: '' },
  txUuid:          { type: String, default: '' },
  total:           { type: [String, Number], default: null },
  pollTimedOut:    { type: Boolean, default: false },
  approvedMessage: { type: String, default: 'Tu pedido quedo confirmado.' },
  trackingLabel:   { type: String, default: 'Ver seguimiento' },
});
defineEmits(['view-tracking', 'retry', 'change-method', 'new-payment', 'close']);

function fmt(val) {
  return formatCOP(Math.round(parseFloat(val) || 0));
}
</script>

<style scoped>
.pstp-state { padding: 8px 4px; }
.pstp-icon {
  width: 72px; height: 72px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem; color: #fff;
}
.pstp-icon--success   { background: linear-gradient(135deg, #166534 0%, #16a34a 100%); }
.pstp-icon--danger    { background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); }
.pstp-icon--warning   { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); }
.pstp-icon--secondary { background: linear-gradient(135deg, #374151 0%, #6b7280 100%); }
.pstp-summary { background: #f9fafb; border-radius: 10px; padding: 4px 14px; text-align: left; }
.pstp-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eef0f2; }
.pstp-row:last-child { border-bottom: none; }
.text-checkout-accent { color: var(--checkout-accent, #7c3aed) !important; }
.btn-checkout-accent { background: var(--checkout-accent, #7c3aed); color: #fff; border: none; }
.btn-checkout-accent:hover:not(:disabled) { background: var(--checkout-accent-hover, #6d28d9); color: #fff; }
</style>
