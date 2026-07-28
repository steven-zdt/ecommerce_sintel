<template>
  <div class="mt-3">
    <div v-if="cardApiFlowEnabled && widgetFlowEnabled" class="btn-group w-100 mb-3" role="group">
      <button
        type="button" class="btn btn-sm"
        :class="subMethod === 'CARD' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
        @click="$emit('update:subMethod', 'CARD')"
      >
        <i class="bi bi-credit-card-2-front me-1"></i>Tarjeta
      </button>
      <button
        type="button" class="btn btn-sm"
        :class="subMethod === 'WIDGET' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
        @click="$emit('update:subMethod', 'WIDGET')"
      >
        <i class="bi bi-bank me-1"></i>PSE / Otros
      </button>
    </div>

    <div v-if="subMethod === 'CARD'">
      <div v-if="loadingCards" class="text-center py-2">
        <span class="spinner-border spinner-border-sm text-checkout-accent"></span>
      </div>
      <div v-else class="d-flex flex-column gap-2">
        <PaymentMethodCard
          v-for="card in savedCards" :key="card.uuid"
          :active="selectedCardId === card.token_id"
          @select="$emit('update:selectedCardId', card.token_id)"
        >
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-credit-card"></i>
            <span class="small">{{ card.brand }} •••• {{ card.masked_number.slice(-4) }}</span>
            <span class="text-muted small ms-auto">{{ card.exp_month }}/{{ card.exp_year }}</span>
            <i class="bi flex-shrink-0" :class="selectedCardId === card.token_id ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
          </div>
        </PaymentMethodCard>

        <PaymentMethodCard :active="selectedCardId === 'NEW'" @select="$emit('update:selectedCardId', 'NEW')">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-plus-circle"></i>
            <span class="small fw-semibold">Agregar tarjeta nueva</span>
            <i class="bi flex-shrink-0 ms-auto" :class="selectedCardId === 'NEW' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
          </div>
        </PaymentMethodCard>

        <div v-if="selectedCardId === 'NEW'" class="row g-2 mt-1">
          <div class="col-12">
            <input :value="newCard.number" @input="updateNewCard('number', $event.target.value)"
              type="text" inputmode="numeric" autocomplete="cc-number"
              class="form-control form-control-sm" placeholder="Numero de tarjeta" maxlength="19">
          </div>
          <div class="col-4">
            <input :value="newCard.exp_month" @input="updateNewCard('exp_month', $event.target.value)"
              type="text" inputmode="numeric" autocomplete="cc-exp-month"
              class="form-control form-control-sm" placeholder="MM" maxlength="2">
          </div>
          <div class="col-4">
            <input :value="newCard.exp_year" @input="updateNewCard('exp_year', $event.target.value)"
              type="text" inputmode="numeric" autocomplete="cc-exp-year"
              class="form-control form-control-sm" placeholder="AA" maxlength="2">
          </div>
          <div class="col-4">
            <input :value="newCard.cvc" @input="updateNewCard('cvc', $event.target.value)"
              type="password" inputmode="numeric" autocomplete="cc-csc"
              class="form-control form-control-sm" placeholder="CVC" maxlength="4">
          </div>
          <div class="col-12">
            <input :value="newCard.card_holder" @input="updateNewCard('card_holder', $event.target.value)"
              type="text" autocomplete="cc-name"
              class="form-control form-control-sm" placeholder="Nombre del titular">
          </div>
        </div>
        <p class="text-muted mb-0" style="font-size:.7rem">
          <i class="bi bi-shield-lock-fill me-1"></i>Tus datos de tarjeta se envian directo a Wompi, nunca pasan por nuestros servidores.
        </p>

        <button v-if="showSubmit" class="btn btn-checkout-accent w-100 mt-2" :disabled="loading || !cardStepValid" @click="$emit('pay')">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          Pagar
        </button>
      </div>
    </div>

    <!-- Bug real (hallado 2026-07-22): este panel no tenia NINGUN markup para
         subMethod==='WIDGET' -- el boton "Pagar" solo vivia dentro del bloque
         CARD de arriba. Tienda no lo sufre porque usa su propio boton fuera
         de este componente (show-submit="false"); Servicios y Renting SI
         dependen del boton de aqui (showSubmit por defecto true), asi que
         para ambos, elegir "PSE / Otros" dejaba la pantalla sin ningun boton
         de pago -- el click en @pay ya soporta este camino (abre el widget
         completo de Wompi), solo faltaba el boton para dispararlo. -->
    <div v-if="subMethod === 'WIDGET'">
      <p class="text-muted mb-2" style="font-size:.8rem">
        <i class="bi bi-bank me-1"></i>Seras redirigido a Wompi para pagar con PSE, Bancolombia u otros medios.
      </p>
      <button v-if="showSubmit" class="btn btn-checkout-accent w-100" :disabled="loading" @click="$emit('pay')">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        Pagar
      </button>
    </div>
  </div>
</template>

<script setup>
import PaymentMethodCard from './PaymentMethodCard.vue';

defineProps({
  subMethod:      { type: String, required: true },     // 'CARD' | 'WIDGET'
  savedCards:     { type: Array, default: () => [] },
  loadingCards:   { type: Boolean, default: false },
  selectedCardId: { type: String, default: 'NEW' },
  newCard:        { type: Object, required: true },      // { number, exp_month, exp_year, cvc, card_holder }
  cardStepValid:  { type: Boolean, default: false },
  loading:        { type: Boolean, default: false },
  // Ambos por defecto true: el toggle Tarjeta/PSE solo se oculta cuando el
  // admin realmente apago uno de los dos caminos (plan hibrido Widget+API).
  cardApiFlowEnabled: { type: Boolean, default: true },
  widgetFlowEnabled:  { type: Boolean, default: true },
  // Servicios/Renting muestran su propio boton "Pagar" dentro de este panel
  // (porque ocultan el boton generico de PaymentMethodSelector con
  // hide-submit); Tienda ya tiene su propio boton en el sidebar del resumen.
  showSubmit:     { type: Boolean, default: true },
});

const emit = defineEmits(['update:subMethod', 'update:selectedCardId', 'update:newCard', 'pay']);

function updateNewCard(field, value) {
  emit('update:newCard', { field, value });
}
</script>
