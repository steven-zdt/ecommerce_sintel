<template>
  <div class="pms-card">
    <div class="pms-header">
      <i class="bi bi-credit-card me-2 text-checkout-accent"></i>
      <span>Selecciona como pagar</span>
    </div>
    <div class="pms-body">
      <div class="d-flex flex-column gap-2 mb-3" role="radiogroup" aria-label="Metodo de pago">
        <div
          class="pay-card" :class="{ 'pay-card--active': modelValue === 'WOMPI' }"
          role="radio" :aria-checked="modelValue === 'WOMPI'" tabindex="0"
          @click="$emit('update:modelValue', 'WOMPI')"
          @keydown.enter.prevent="$emit('update:modelValue', 'WOMPI')"
          @keydown.space.prevent="$emit('update:modelValue', 'WOMPI')"
        >
          <div class="d-flex align-items-center gap-3">
            <div class="pay-badge pay-badge--wompi">W</div>
            <div class="flex-grow-1">
              <div class="fw-semibold small">Pago en linea</div>
              <div class="text-muted" style="font-size:.72rem">Tarjeta, PSE, Bancolombia — via Wompi</div>
            </div>
            <i class="bi" :class="modelValue === 'WOMPI' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
          </div>
        </div>

        <div v-if="allowNequi">
          <div
            class="pay-card" :class="{ 'pay-card--active': modelValue === 'NEQUI' }"
            role="radio" :aria-checked="modelValue === 'NEQUI'" tabindex="0"
            @click="$emit('update:modelValue', 'NEQUI')"
            @keydown.enter.prevent="$emit('update:modelValue', 'NEQUI')"
            @keydown.space.prevent="$emit('update:modelValue', 'NEQUI')"
          >
            <div class="d-flex align-items-center gap-3">
              <div class="pay-badge pay-badge--nequi">N</div>
              <div class="flex-grow-1">
                <div class="fw-semibold small">Nequi Push</div>
                <div class="text-muted" style="font-size:.72rem">Aprueba desde tu app Nequi</div>
              </div>
              <i class="bi" :class="modelValue === 'NEQUI' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
            </div>
          </div>
          <label v-if="modelValue === 'NEQUI'" class="visually-hidden" for="pms-nequi-phone">Celular Nequi</label>
          <input
            v-if="modelValue === 'NEQUI'"
            id="pms-nequi-phone"
            :value="nequiPhone"
            @input="$emit('update:nequiPhone', $event.target.value)"
            type="tel"
            class="form-control form-control-sm mt-1"
            :class="{ 'is-invalid': nequiError }"
            placeholder="Celular Nequi (10 digitos)"
            maxlength="10"
          >
        </div>

        <div
          v-if="allowCod" class="pay-card" :class="{ 'pay-card--active': modelValue === 'COD' }"
          role="radio" :aria-checked="modelValue === 'COD'" tabindex="0"
          @click="$emit('update:modelValue', 'COD')"
          @keydown.enter.prevent="$emit('update:modelValue', 'COD')"
          @keydown.space.prevent="$emit('update:modelValue', 'COD')"
        >
          <div class="d-flex align-items-center gap-3">
            <div class="pay-badge pay-badge--cod"><i class="bi bi-cash"></i></div>
            <div class="flex-grow-1">
              <div class="fw-semibold small">{{ codLabel }}</div>
              <div class="text-muted" style="font-size:.72rem">{{ codDescription }}</div>
            </div>
            <i class="bi" :class="modelValue === 'COD' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
          </div>
        </div>
      </div>

      <template v-if="!hideSubmit">
        <button v-if="modelValue === 'WOMPI'" class="btn btn-checkout-accent fw-bold w-100 py-3" :disabled="loading" @click="$emit('pay')">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-credit-card me-2"></i>
          {{ loading ? 'Preparando...' : 'Pagar con Wompi' }}
        </button>
        <button v-else-if="modelValue === 'NEQUI'" class="btn btn-checkout-accent fw-bold w-100 py-3" :disabled="loading" @click="$emit('pay')">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-phone me-2"></i>
          {{ loading ? 'Enviando...' : 'Pagar con Nequi' }}
        </button>
        <button v-else-if="modelValue === 'COD'" class="btn btn-checkout-accent fw-bold w-100 py-3" :disabled="loading" @click="$emit('pay')">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-check-circle me-2"></i>
          {{ loading ? 'Confirmando...' : codConfirmLabel }}
        </button>
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue:      { type: String, default: 'WOMPI' },
  nequiPhone:      { type: String, default: '' },
  nequiError:      { type: Boolean, default: false },
  loading:         { type: Boolean, default: false },
  // Shop ya tiene su propio boton de pago (con monto dinamico del carrito)
  // en el sidebar del resumen -- hideSubmit evita renderizar un segundo
  // boton redundante aqui cuando el dominio consumidor prefiere el suyo.
  hideSubmit:      { type: Boolean, default: false },
  // Nequi Push requiere credenciales de sandbox/produccion reales -- cuando
  // no estan configuradas (ver payment/online/api/views.py:_is_nequi_configured)
  // el consumidor debe pasar false aqui para no ofrecer un metodo de pago
  // que siempre va a fallar.
  allowNequi:      { type: Boolean, default: true },
  // COD ("pago contra entrega/en sitio") no aplica igual en los 3 dominios
  // (Shop = contraentrega, Services = pagar al tecnico, Renting no lo usa
  // hoy) -- se deja configurable en vez de asumir un solo texto.
  allowCod:        { type: Boolean, default: true },
  codLabel:        { type: String, default: 'Pago contra entrega' },
  codDescription:  { type: String, default: 'Paga en efectivo o datafono al recibir' },
  codConfirmLabel: { type: String, default: 'Confirmar — pago contra entrega' },
});
defineEmits(['update:modelValue', 'update:nequiPhone', 'pay']);
</script>

<style scoped>
.pms-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.04); }
.pms-header { display: flex; align-items: center; padding: 14px 20px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; font-weight: 700; font-size: .9rem; }
.pms-body { padding: 16px 20px; }
.pay-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; cursor: pointer; transition: all .15s; }
.pay-card:hover { border-color: #c4b5fd; }
.pay-card:focus-visible { outline: 2px solid var(--checkout-accent, #7c3aed); outline-offset: 2px; }
.pay-card--active { border-color: var(--checkout-accent, #7c3aed); background: var(--checkout-accent-tint, #f5f3ff); box-shadow: 0 0 0 2px var(--checkout-accent-ring, rgba(124,58,237,.15)); }
.pay-badge { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem; flex-shrink: 0; }
.pay-badge--wompi { background: #dbeafe; color: #1d4ed8; }
.pay-badge--nequi { background: #fce7f3; color: #9d174d; }
.pay-badge--cod { background: #fef3c7; color: #92400e; }
.text-checkout-accent { color: var(--checkout-accent, #7c3aed) !important; }
.btn-checkout-accent { background: var(--checkout-accent, #7c3aed); color: #fff; border: none; }
.btn-checkout-accent:hover:not(:disabled) { background: var(--checkout-accent-hover, #6d28d9); color: #fff; }
.btn-checkout-accent:disabled { background: var(--checkout-accent-disabled, #c4b5fd); color: #fff; cursor: not-allowed; }
</style>
