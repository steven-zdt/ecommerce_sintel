<template>
  <CheckoutModal
    :open="store.open"
    :phase="store.phase"
    :can-close="canClose"
    :steps="STEPS"
    :aria-label="ariaLabel"
    @close="requestClose"
  >
    <!-- 1. RESUMEN -->
    <template #summary>
      <ServiceOrderSummaryCard
        :service-name="store.serviceName"
        :variant-sku="store.variantSku"
        :technician-name="store.technicianName"
        :duration-hours="store.durationHours"
        :price-info="store.priceInfo"
      />
      <PaymentCTA class="w-100 mt-3" @click="store.setPhase('method')">
        Continuar al pago <i class="bi bi-arrow-right ms-2"></i>
      </PaymentCTA>
    </template>

    <!-- 2. METODO -->
    <template #method>
      <PaymentMethodSelector
        v-model="store.paymentMethod"
        v-model:nequi-phone="store.nequiPhone"
        :nequi-error="nequiError"
        :loading="methodLoading"
        :hide-submit="store.paymentMethod === 'WOMPI' && cardApiFlowEnabled"
        cod-label="Pagar en sitio"
        cod-description="Paga al tecnico al momento de la visita"
        cod-confirm-label="Confirmar — pagar en sitio"
        @pay="pay"
      />

      <!-- Sub-opciones de "Pago en linea" (mismo patron que CheckoutView.vue / ADR-001
           Fase 3b): Tarjeta usa el flujo backend-directo, sin abrir el widget completo
           de Wompi; PSE/Otros mantiene el widget porque el banco exige esa redireccion. -->
      <div v-if="store.paymentMethod === 'WOMPI' && cardApiFlowEnabled" class="mt-3">
        <div class="btn-group w-100 mb-3" role="group">
          <button
            type="button" class="btn btn-sm"
            :class="wompiSubMethod === 'CARD' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
            @click="wompiSubMethod = 'CARD'"
          >
            <i class="bi bi-credit-card-2-front me-1"></i>Tarjeta
          </button>
          <button
            type="button" class="btn btn-sm"
            :class="wompiSubMethod === 'WIDGET' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
            @click="wompiSubMethod = 'WIDGET'"
          >
            <i class="bi bi-bank me-1"></i>PSE / Otros
          </button>
        </div>

        <div v-if="wompiSubMethod === 'CARD'">
          <div v-if="loadingCards" class="text-center py-2">
            <span class="spinner-border spinner-border-sm text-checkout-accent"></span>
          </div>
          <div v-else class="d-flex flex-column gap-2">
            <PaymentMethodCard
              v-for="card in savedCards" :key="card.uuid"
              :active="selectedCardId === card.token_id"
              @select="selectedCardId = card.token_id"
            >
              <div class="d-flex align-items-center gap-2">
                <i class="bi bi-credit-card"></i>
                <span class="small">{{ card.brand }} •••• {{ card.masked_number.slice(-4) }}</span>
                <span class="text-muted small ms-auto">{{ card.exp_month }}/{{ card.exp_year }}</span>
                <i class="bi flex-shrink-0" :class="selectedCardId === card.token_id ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
              </div>
            </PaymentMethodCard>

            <PaymentMethodCard :active="selectedCardId === 'NEW'" @select="selectedCardId = 'NEW'">
              <div class="d-flex align-items-center gap-2">
                <i class="bi bi-plus-circle"></i>
                <span class="small fw-semibold">Agregar tarjeta nueva</span>
                <i class="bi flex-shrink-0 ms-auto" :class="selectedCardId === 'NEW' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
              </div>
            </PaymentMethodCard>

            <div v-if="selectedCardId === 'NEW'" class="row g-2 mt-1">
              <div class="col-12">
                <input v-model="newCardRaw.number" type="text" inputmode="numeric" autocomplete="cc-number"
                  class="form-control form-control-sm" placeholder="Numero de tarjeta" maxlength="19">
              </div>
              <div class="col-4">
                <input v-model="newCardRaw.exp_month" type="text" inputmode="numeric" autocomplete="cc-exp-month"
                  class="form-control form-control-sm" placeholder="MM" maxlength="2">
              </div>
              <div class="col-4">
                <input v-model="newCardRaw.exp_year" type="text" inputmode="numeric" autocomplete="cc-exp-year"
                  class="form-control form-control-sm" placeholder="AA" maxlength="2">
              </div>
              <div class="col-4">
                <input v-model="newCardRaw.cvc" type="password" inputmode="numeric" autocomplete="cc-csc"
                  class="form-control form-control-sm" placeholder="CVC" maxlength="4">
              </div>
              <div class="col-12">
                <input v-model="newCardRaw.card_holder" type="text" autocomplete="cc-name"
                  class="form-control form-control-sm" placeholder="Nombre del titular">
              </div>
            </div>
            <p class="text-muted mb-0" style="font-size:.7rem">
              <i class="bi bi-shield-lock-fill me-1"></i>Tus datos de tarjeta se envian directo a Wompi, nunca pasan por nuestros servidores.
            </p>

            <button class="btn btn-checkout-accent w-100 mt-2" :disabled="methodLoading || !cardStepValid" @click="pay">
              <span v-if="methodLoading" class="spinner-border spinner-border-sm me-2"></span>
              Pagar
            </button>
          </div>
        </div>
      </div>

      <button class="btn btn-link btn-sm mt-2" @click="store.setPhase('summary')">
        <i class="bi bi-arrow-left me-1"></i>Volver al resumen
      </button>
    </template>

    <!-- 3. ESTADO -->
    <template #status>
      <PaymentStatusPanel
        :status="store.paymentStatus"
        :order-uuid="store.order?.uuid"
        :tx-uuid="store.txUuid"
        :total="store.order?.total_amount"
        :poll-timed-out="store.pollTimedOut"
        approved-message="Tu solicitud de servicio quedo confirmada."
        tracking-label="Ver seguimiento"
        @view-tracking="viewTracking"
        @retry="retry"
        @change-method="changeMethod"
        @new-payment="newPayment"
        @close="changeMethod"
      />
    </template>
  </CheckoutModal>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useWompiWidget } from '@/composables/useWompiWidget';
import { useCardTokenization } from '@/composables/useCardTokenization';
import { usePaymentPolling } from '@/composables/usePaymentPolling';
import { useServiceCheckoutStore } from '@/store/services/serviceCheckoutStore';
import CheckoutModal from '@/components/shared/checkout/CheckoutModal.vue';
import PaymentMethodSelector from '@/components/shared/checkout/PaymentMethodSelector.vue';
import PaymentMethodCard from '@/components/shared/checkout/PaymentMethodCard.vue';
import PaymentStatusPanel from '@/components/shared/checkout/PaymentStatusPanel.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';
import ServiceOrderSummaryCard from './ServiceOrderSummaryCard.vue';

const emit = defineEmits(['view-tracking']);

const router = useRouter();
const api    = useApi();
const toast  = useToast();
const { openWompiWidget } = useWompiWidget();
const { tokenizeCard }    = useCardTokenization();
const store  = useServiceCheckoutStore();

const STEPS = ['Resumen', 'Metodo de pago', 'Estado'];
const stepIndex = computed(() => ({ summary: 1, method: 2, status: 3 }[store.phase] || 1));
const ariaLabel = computed(() => `Pago del servicio — ${STEPS[stepIndex.value - 1]}`);

const methodLoading = ref(false);
const nequiError    = ref(false);

// Sub-metodo dentro de "Pago en linea" (mismo patron que CheckoutView.vue,
// ADR-001 Fase 3b, portado aqui — Servicios Tecnicos se habia quedado en el
// flujo pre-ADR-001 de solo-widget, que es la causa raiz del hallazgo F4 de
// la auditoria: el iframe de Wompi nunca renderizaba en el navegador de prueba).
const wompiSubMethod     = ref('CARD');
const cardApiFlowEnabled = ref(false); // fail-safe: widget completo hasta confirmar el flag
const savedCards     = ref([]);
const loadingCards   = ref(false);
const cardsFetched   = ref(false);
const selectedCardId = ref('NEW');
const defaultNewCard = () => ({ number: '', exp_month: '', exp_year: '', cvc: '', card_holder: '' });
const newCardRaw     = ref(defaultNewCard());

const cardStepValid = computed(() => selectedCardId.value !== 'NEW'
  || Object.values(newCardRaw.value).every((v) => String(v).trim() !== ''));

async function fetchFeatureFlags() {
  try {
    const res = await api.get('payment/payments/feature-flags/');
    cardApiFlowEnabled.value = !!res.data.card_api_flow_enabled;
  } catch {
    cardApiFlowEnabled.value = false; // fail-safe, no fail-open
  }
  if (!cardApiFlowEnabled.value) wompiSubMethod.value = 'WIDGET';
}

async function fetchSavedCards() {
  if (cardsFetched.value) return;
  cardsFetched.value = true;
  loadingCards.value = true;
  try {
    const res = await api.get('payment/cards/');
    savedCards.value = res.data.results ?? res.data ?? [];
    if (savedCards.value.length > 0) selectedCardId.value = savedCards.value[0].token_id;
  } catch {
    // Sin tarjetas guardadas o error de red -- el usuario ve "agregar tarjeta nueva".
  } finally {
    loadingCards.value = false;
  }
}

async function resolveCardToken() {
  if (selectedCardId.value !== 'NEW') return selectedCardId.value;
  const tokenData = await tokenizeCard(newCardRaw.value);
  await api.post('payment/cards/', {
    token_id: tokenData.id,
    masked_number: `************${tokenData.last_four}`,
    brand: tokenData.brand,
    exp_month: tokenData.exp_month,
    exp_year: tokenData.exp_year,
    cardholder_name: tokenData.card_holder || newCardRaw.value.card_holder,
  });
  return tokenData.id;
}

onMounted(fetchFeatureFlags);
watch(() => store.paymentMethod, (method) => {
  if (method === 'WOMPI') fetchSavedCards();
});

const canClose = computed(() => !(store.phase === 'status' && store.paymentStatus === 'processing'));

function requestClose() {
  if (!canClose.value) return;
  stopPolling();
  store.close();
}

// ── Polling (mismo patron que PaymentResultView.vue / transaction-status/) ──
// Mecanica del timer/timeout delegada a usePaymentPolling (ver
// PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 2, hallazgo 1) -- las
// decisiones de que hacer con cada respuesta/error se mantienen exactamente
// iguales a como estaban, incluido el manejo silencioso de errores dentro
// del intervalo (nunca se detiene el polling por un fallo puntual de red).
const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS  = 120000;
let pollTxUuid = null;
let pollWompiIdHint = null;

const polling = usePaymentPolling({
  intervalMs: POLL_INTERVAL_MS,
  timeoutMs: POLL_TIMEOUT_MS,
  onTimeout: () => {
    store.setPaymentStatus('expired', { txUuid: pollTxUuid, wompiId: pollWompiIdHint, pollTimedOut: true });
  },
});

function stopPolling() {
  polling.stop();
}

// NEQUI vive en un modelo/endpoint distinto a WOMPI (ver payment/models.py::
// NequiTransaction vs Transaction): status en 'status' (PENDING/APPROVED/
// REJECTED/ERROR), sin wompi_id. fetchTxStatus normaliza ambos a la misma
// forma { status, wompiId } para que el resto del flujo no distinga metodos.
async function fetchTxStatus(method, txUuid, wompiIdHint) {
  if (method === 'NEQUI') {
    const res = await api.get(`payment/nequi/status/?${new URLSearchParams({ tx: txUuid })}`);
    const NEQUI_TO_COMMON = { REJECTED: 'DECLINED' };
    return { status: NEQUI_TO_COMMON[res.data.status] || res.data.status, wompiId: undefined };
  }
  const params = new URLSearchParams({ tx: txUuid });
  if (wompiIdHint) params.set('id', wompiIdHint);
  const res = await api.get(`payment/payments/transaction-status/?${params.toString()}`);
  return { status: res.data.tx_status, wompiId: res.data.wompi_id || wompiIdHint };
}

async function checkStatusOnce(txUuid, wompiIdHint, method = 'WOMPI') {
  try {
    const { status: s, wompiId } = await fetchTxStatus(method, txUuid, wompiIdHint);
    if (s === 'APPROVED') {
      store.setPaymentStatus('approved', { txUuid, wompiId });
      stopPolling();
    } else if (['DECLINED', 'VOIDED', 'ERROR'].includes(s)) {
      store.setPaymentStatus('declined', { txUuid, wompiId });
      stopPolling();
    } else {
      store.setPaymentStatus('pending', { txUuid, wompiId });
      startPolling(txUuid, wompiIdHint, method);
    }
  } catch {
    store.setPaymentStatus('pending', { txUuid, wompiId: wompiIdHint });
    startPolling(txUuid, wompiIdHint, method);
  }
}

function startPolling(txUuid, wompiIdHint, method = 'WOMPI') {
  pollTxUuid = txUuid;
  pollWompiIdHint = wompiIdHint;
  polling.start(async () => {
    try {
      const { status: s, wompiId } = await fetchTxStatus(method, txUuid, wompiIdHint);
      if (s && s !== 'PENDING') {
        stopPolling();
        if (s === 'APPROVED') {
          store.setPaymentStatus('approved', { txUuid, wompiId });
        } else {
          store.setPaymentStatus('declined', { txUuid, wompiId });
        }
      }
    } catch { /* sigue intentando hasta el timeout */ }
  });
}

onUnmounted(stopPolling);

function resolveWompiResult(resultQuery) {
  store.setPhase('status');
  store.setPaymentStatus('processing', { txUuid: resultQuery.tx });
  checkStatusOnce(resultQuery.tx, resultQuery.id);
}

// ── Acciones de pago ──
async function pay() {
  if (!store.order?.uuid) return;

  if (store.paymentMethod === 'WOMPI') {
    const isCardFlow = wompiSubMethod.value === 'CARD' && cardApiFlowEnabled.value;
    if (isCardFlow && !cardStepValid.value) return;

    methodLoading.value = true;
    try {
      // Flujo tarjeta (backend-directo, ADR-001 Sec.4): tokenizar/resolver
      // ANTES de llamar a initialize/ -- si la tokenizacion falla, no queda
      // ninguna Transaction PENDING huerfana creada.
      const cardToken = isCardFlow ? await resolveCardToken() : null;
      const payload = isCardFlow
        ? { order_uuid: store.order.uuid, card_token: cardToken }
        : { order_uuid: store.order.uuid };

      const res = await api.post('payment/payments/initialize/', payload);
      store.setPhase('status');
      store.setPaymentStatus('processing', { txUuid: res.data.uuid });

      if (isCardFlow) {
        // El backend ya creo la transaccion de forma sincrona en Wompi -- sin
        // widget que abrir, solo seguir el mismo polling que ya usa el resto
        // del flujo (wompi_id llega listo desde la respuesta de initialize/).
        checkStatusOnce(res.data.uuid, res.data.wompi_id);
      } else {
        // PSE/Otros: unico caso que aun abre el widget completo de Wompi,
        // porque el banco exige esa redireccion -- no es una limitacion
        // eliminable del lado nuestro.
        await openWompiWidget(res.data, {
          onApproved: resolveWompiResult,
          onDeclined: resolveWompiResult,
          onPending:  resolveWompiResult,
        });
      }
    } catch (err) {
      // err puede ser un error de axios (respuesta de nuestro backend) o un
      // Error plano lanzado por tokenizeCard/resolveCardToken (fetch directo
      // a Wompi, sin response de axios) -- antes el fallback generico tapaba
      // por completo el mensaje real de este segundo caso.
      toast.error(err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'No se pudo iniciar el pago. Intenta de nuevo.');
    } finally {
      if (isCardFlow) newCardRaw.value = defaultNewCard();
      methodLoading.value = false;
    }
    return;
  }

  if (store.paymentMethod === 'NEQUI') {
    nequiError.value = !/^\d{10}$/.test(store.nequiPhone.trim());
    if (nequiError.value) return;
    methodLoading.value = true;
    try {
      const res = await api.post('payment/nequi/initialize/', {
        order_uuid:   store.order.uuid,
        phone_number: store.nequiPhone.trim(),
      });
      store.setPhase('status');
      store.setPaymentStatus('processing', { txUuid: res.data.uuid });
      checkStatusOnce(res.data.uuid, undefined, 'NEQUI');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Error al inicializar Nequi. Intenta de nuevo.');
    } finally {
      methodLoading.value = false;
    }
    return;
  }

  if (store.paymentMethod === 'COD') {
    methodLoading.value = true;
    try {
      await api.post(`orders/service-orders/${store.order.uuid}/confirm-cod/`);
      store.setPhase('status');
      store.setPaymentStatus('approved', { txUuid: '' });
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'No se pudo confirmar el pago en sitio.');
    } finally {
      methodLoading.value = false;
    }
  }
}

function retry() {
  pay();
}

function changeMethod() {
  stopPolling();
  store.setPhase('method');
}

function newPayment() {
  stopPolling();
  pay();
}

function viewTracking() {
  store.close();
  emit('view-tracking');
  router.push('/mi-cuenta/pedidos');
}
</script>
