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
      <CardOrWidgetPanel
        v-if="store.paymentMethod === 'WOMPI' && cardApiFlowEnabled"
        v-model:sub-method="wompiSubMethod"
        v-model:selected-card-id="selectedCardId"
        :saved-cards="savedCards"
        :loading-cards="loadingCards"
        :new-card="newCardRaw"
        :card-step-valid="cardStepValid"
        :loading="methodLoading"
        :card-api-flow-enabled="cardApiFlowEnabled"
        :widget-flow-enabled="widgetFlowEnabled"
        @update:new-card="({ field, value }) => newCardRaw[field] = value"
        @pay="pay"
      />

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
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useWompiWidget } from '@/composables/useWompiWidget';
import { useCardOrWidgetPayment } from '@/composables/useCardOrWidgetPayment';
import { usePaymentPolling } from '@/composables/usePaymentPolling';
import { useServiceCheckoutStore } from '@/store/services/serviceCheckoutStore';
import CheckoutModal from '@/components/shared/checkout/CheckoutModal.vue';
import PaymentMethodSelector from '@/components/shared/checkout/PaymentMethodSelector.vue';
import CardOrWidgetPanel from '@/components/shared/checkout/CardOrWidgetPanel.vue';
import PaymentStatusPanel from '@/components/shared/checkout/PaymentStatusPanel.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';
import ServiceOrderSummaryCard from './ServiceOrderSummaryCard.vue';

const emit = defineEmits(['view-tracking']);

const router = useRouter();
const api    = useApi();
const toast  = useToast();
const { handleError } = useErrorHandler();
const { openWompiWidget } = useWompiWidget();
const store  = useServiceCheckoutStore();

const STEPS = ['Resumen', 'Metodo de pago', 'Estado'];
const stepIndex = computed(() => ({ summary: 1, method: 2, status: 3 }[store.phase] || 1));
const ariaLabel = computed(() => `Pago del servicio — ${STEPS[stepIndex.value - 1]}`);

const methodLoading = ref(false);
const nequiError    = ref(false);

// Sub-metodo "Tarjeta (API) / PSE-Otros (Widget)" dentro de "Pago en linea" --
// estado y logica compartidos con CheckoutView.vue y RentalConfirmationView.vue
// via useCardOrWidgetPayment() (extraido en la auditoria 2026-07-22, plan
// hibrido Widget+API, para no duplicar esta logica una tercera vez).
const {
  wompiSubMethod, cardApiFlowEnabled, widgetFlowEnabled,
  savedCards, loadingCards, selectedCardId, newCardRaw, cardStepValid,
  fetchFeatureFlags, fetchSavedCards, resolveCardToken, resetNewCard,
} = useCardOrWidgetPayment();

onMounted(fetchFeatureFlags);
// immediate: true -- 'WOMPI' ya es el valor por defecto de store.paymentMethod
// al montar el modal, asi que un watch sin immediate nunca dispara (no hay
// cambio de valor que detectar) y las tarjetas guardadas jamas se cargaban
// (bug real, hallado en smoke test E2E 2026-07-22).
watch(() => store.paymentMethod, (method) => {
  if (method === 'WOMPI') fetchSavedCards();
}, { immediate: true });

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
          // Sin esto, si el widget nunca responde (bug real: PSE/Otros se queda
          // sin abrir en dev, o cualquier timeout de Wompi) el modal quedaba
          // trabado para siempre en "Procesando pago..." -- canClose es false
          // en esa fase y nada mas movia paymentStatus fuera de 'processing'.
          onStuck: () => {
            stopPolling();
            store.setPhase('method');
            store.setPaymentStatus(null);
          },
        });
      }
    } catch (err) {
      // err puede ser un error de axios (respuesta de nuestro backend) o un
      // Error plano lanzado por tokenizeCard/resolveCardToken (fetch directo
      // a Wompi, sin response de axios) -- antes el fallback generico tapaba
      // por completo el mensaje real de este segundo caso.
      toast.error(err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'No se pudo iniciar el pago. Intenta de nuevo.');
    } finally {
      if (isCardFlow) resetNewCard();
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
      handleError(err, 'Error al inicializar Nequi. Intenta de nuevo.');
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
      handleError(err, 'No se pudo confirmar el pago en sitio.');
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
