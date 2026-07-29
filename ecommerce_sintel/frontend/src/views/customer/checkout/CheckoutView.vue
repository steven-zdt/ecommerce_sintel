<template>
  <div class="checkout-view">
    <div class="container py-5" style="max-width: 980px">

      <div class="text-center mb-5">
        <h1 class="h3 fw-bold">Finalizar pedido</h1>
        <p class="text-muted mb-0">Revisa tu pedido y completa el pago</p>
      </div>

      <!-- Carrito vacio -->
      <div v-if="!cartStore.loading && cartStore.isEmpty" class="text-center py-5">
        <i class="bi bi-bag display-4 text-muted"></i>
        <p class="mt-3 text-muted">Tu carrito esta vacio.</p>
        <RouterLink to="/tienda" class="btn btn-checkout-accent btn-sm">Ir a la tienda</RouterLink>
      </div>

      <div v-else class="row g-4 g-lg-5">

        <!-- Columna principal -->
        <div class="col-lg-7">

          <!-- Direccion de envio -->
          <PaymentCard icon="bi-geo-alt" title="Dirección de envío" class="mb-4">
            <div class="p-3">
              <ColombianAddressForm ref="addressFormRef" />
            </div>
          </PaymentCard>

          <!-- Metodo de pago -->
          <PaymentCard icon="bi-credit-card" title="Metodo de pago">
            <div class="p-3">

            <!-- Selector compartido con Services/Renting (ver
                 PLAN_DE_ACCION_UI_SERVICES_PAYMENT.md, Paso 3). hide-submit
                 porque Shop usa su propio boton de pago (con el monto del
                 carrito) en el sidebar, no el boton generico del selector. -->
            <PaymentMethodSelector
              v-model="selectedPaymentMethod"
              v-model:nequi-phone="nequiPhone"
              :nequi-error="errors.nequiPhone"
              :allow-nequi="nequiEnabled"
              hide-submit
              cod-label="Contra entrega"
              cod-description="Paga al recibir tu pedido"
            />

            <!-- Sub-opciones de "Pago en linea": Tarjeta (backend directo, sin widget) vs PSE/Otros (widget completo).
                 El sub-selector de "Tarjeta" solo aparece si cardApiFlowEnabled (ADR-001 Fase 5,
                 feature flag consultado a GET payments/feature-flags/ -- kill-switch editable
                 desde /admin/ sin desplegar codigo, tambien aplicado del lado del backend). -->
            <CardOrWidgetPanel
              v-if="selectedPaymentMethod === 'WOMPI' && cardApiFlowEnabled"
              v-model:sub-method="wompiSubMethod"
              v-model:selected-card-id="selectedCardId"
              :saved-cards="savedCards"
              :loading-cards="loadingCards"
              :new-card="newCardRaw"
              :card-step-valid="cardStepValid"
              :show-submit="false"
              :card-api-flow-enabled="cardApiFlowEnabled"
              :widget-flow-enabled="widgetFlowEnabled"
              @update:new-card="({ field, value }) => newCardRaw[field] = value"
            />

            <!-- Info COD -->
            <PaymentAlert v-if="selectedPaymentMethod === 'COD'" variant="warning" icon="bi-info-circle-fill" class="mt-3">
              El pago se realiza en efectivo o transferencia al momento de la entrega. El inventario se reserva de inmediato al confirmar.
            </PaymentAlert>
            </div>
          </PaymentCard>
        </div>

        <!-- Resumen del pedido -->
        <div class="col-lg-5">
          <div class="order-summary-sticky">
            <PaymentCard title="Resumen del pedido">
              <div class="p-3">

              <div v-if="cartStore.loading || loadingCheckout" class="text-center py-3">
                <span class="spinner-border spinner-border-sm text-checkout-accent"></span>
              </div>

              <div v-else>
                <!-- Items -->
                <PaymentRow v-for="item in displayItems" :key="item.uuid || item.variant_uuid">
                  <template #label>
                    <div><p class="fw-semibold small mb-0">{{ item.product_name || item.item_name }}</p><p class="text-muted small mb-0">Cant: {{ item.quantity }}</p></div>
                  </template>
                  <p class="fw-bold small mb-0">${{ fmt(item.final_price) }}</p>
                </PaymentRow>

                <!-- Desglose de precios -->
                <template v-if="checkoutPayload">
                  <PaymentRow label="Subtotal (sin IVA)"><span class="small">${{ fmt(checkoutPayload.subtotal) }}</span></PaymentRow>
                  <PaymentRow label="IVA"><span class="small">${{ fmt(checkoutPayload.total_tax) }}</span></PaymentRow>
                  <PaymentRow label="Envio"><span class="small text-success fw-semibold">Gratis</span></PaymentRow>
                  <PaymentRow label="Total" bold-label><span class="fw-bold fs-5">${{ fmt(checkoutPayload.total_amount) }}</span></PaymentRow>
                </template>
                <PaymentRow v-else label="Total (IVA incluido)" bold-label>
                  <span class="fw-bold fs-5">${{ fmt(cartStore.total) }}</span>
                </PaymentRow>

                <!-- Error de stock -->
                <PaymentAlert v-if="stockError" variant="danger" icon="bi-exclamation-triangle" class="mt-3">
                  {{ stockError }}
                </PaymentAlert>

                <!-- Boton de pago -->
                <PaymentCTA
                  class="w-100 mt-4"
                  :loading="submitting"
                  :disabled="cartStore.isEmpty || !!stockError"
                  :icon="selectedPaymentMethod === 'COD' ? 'bi-check-circle' : selectedPaymentMethod === 'NEQUI' ? 'bi-send' : 'bi-lock-fill'"
                  @click="submitOrder"
                >
                  <span v-if="selectedPaymentMethod === 'COD'">
                    Confirmar pedido — ${{ fmt(checkoutPayload?.total_amount ?? cartStore.total) }}
                  </span>
                  <span v-else-if="selectedPaymentMethod === 'NEQUI'">
                    Pagar con Nequi — ${{ fmt(checkoutPayload?.total_amount ?? cartStore.total) }}
                  </span>
                  <span v-else>
                    Pagar ${{ fmt(checkoutPayload?.total_amount ?? cartStore.total) }}
                  </span>
                </PaymentCTA>

                <p v-if="selectedPaymentMethod === 'WOMPI'" class="text-center text-muted mt-2" style="font-size:.75rem">
                  <i class="bi bi-shield-check me-1"></i>Pago seguro — procesado por Wompi
                </p>
                <p v-else-if="selectedPaymentMethod === 'NEQUI'" class="text-center text-muted mt-2" style="font-size:.75rem">
                  <i class="bi bi-phone me-1"></i>Recibiras una notificacion en tu app Nequi
                </p>
                <p v-else class="text-center text-muted mt-2" style="font-size:.75rem">
                  <i class="bi bi-truck me-1"></i>Pagaras al recibir tu pedido en casa
                </p>
              </div>
              </div>
            </PaymentCard>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { ordersService } from '@/services/orders/ordersService';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useAuthStore } from '@/store/auth';
import { useCartStore } from '@/store/cart';
import { useWompiWidget } from '@/composables/useWompiWidget';
import { useCardOrWidgetPayment } from '@/composables/useCardOrWidgetPayment';
import { formatCOP } from '@/utils/money';
import ColombianAddressForm from '@/components/customer/checkout/ColombianAddressForm.vue';
import PaymentMethodSelector from '@/components/shared/checkout/PaymentMethodSelector.vue';
import CardOrWidgetPanel from '@/components/shared/checkout/CardOrWidgetPanel.vue';
import PaymentCard from '@/components/shared/checkout/PaymentCard.vue';
import PaymentRow from '@/components/shared/checkout/PaymentRow.vue';
import PaymentAlert from '@/components/shared/checkout/PaymentAlert.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';

const api       = useApi();
const toast     = useToast();
const { handleError } = useErrorHandler();
const authStore = useAuthStore();
const cartStore = useCartStore();
const router    = useRouter();
const route     = useRoute();
const { openWompiWidget }  = useWompiWidget();

const submitting            = ref(false);
const loadingCheckout       = ref(false);
const checkoutPayload       = ref(null);
const stockError            = ref('');
const selectedPaymentMethod = ref('WOMPI');
const nequiPhone            = ref('');
const addressFormRef        = ref(null);

// Sub-metodo "Tarjeta (API) / PSE-Otros (Widget)" dentro de "Pago en linea" --
// estado y logica compartidos con ServiceCheckoutModal.vue y
// RentalConfirmationView.vue via useCardOrWidgetPayment() (extraido en la
// auditoria 2026-07-22, plan hibrido Widget+API, para no duplicar esta logica
// una tercera vez).
const {
  wompiSubMethod, cardApiFlowEnabled, widgetFlowEnabled, nequiEnabled,
  savedCards, loadingCards, selectedCardId, newCardRaw, cardStepValid,
  fetchFeatureFlags, fetchSavedCards, resolveCardToken, resetNewCard,
} = useCardOrWidgetPayment();

const errors = reactive({ nequiPhone: false });

const displayItems = computed(() =>
  checkoutPayload.value?.items?.length ? checkoutPayload.value.items : cartStore.items
);

const fmt = (val) => formatCOP(val);

function validate() {
  errors.nequiPhone = selectedPaymentMethod.value === 'NEQUI'
    ? !/^\d{10}$/.test(nequiPhone.value.trim())
    : false;
  const addressValid = addressFormRef.value?.validate() ?? false;

  const cardValid = (selectedPaymentMethod.value === 'WOMPI' && wompiSubMethod.value === 'CARD')
    ? cardStepValid.value
    : true;

  return addressValid && !errors.nequiPhone && cardValid;
}

async function fetchCheckoutPreview() {
  if (cartStore.isEmpty) return;
  loadingCheckout.value = true;
  stockError.value = '';
  try {
    const res = await api.post('cart/checkout/');
    checkoutPayload.value = res.data;
  } catch (e) {
    const msg = e.response?.data?.detail || '';
    if (msg) stockError.value = msg;
  } finally {
    loadingCheckout.value = false;
  }
}

async function submitOrder() {
  if (!validate()) { toast.error('Completa todos los campos requeridos'); return; }
  if (cartStore.isEmpty) { toast.error('El carrito esta vacio'); return; }

  const isCardFlow = selectedPaymentMethod.value === 'WOMPI' && wompiSubMethod.value === 'CARD' && cardApiFlowEnabled.value;

  submitting.value = true;
  try {
    // Para el flujo de tarjeta (backend-directo), resolver el card_token
    // ANTES de crear direccion/orden -- si la tokenizacion falla (tarjeta
    // invalida, red, etc.) no queda ninguna orden huerfana creada.
    const cardToken = isCardFlow ? await resolveCardToken() : null;

    // 1. Obtener datos del formulario de dirección
    const addrData = addressFormRef.value.getFormData();

    // 2. Crear dirección de envío
    const addrData2 = await ordersService.addresses.create({
      full_name:      addrData.full_name,
      address_line_1: addrData.address_line_1,
      address_line_2: addrData.address_line_2 || '',
      city:           addrData.city,
      state:          addrData.state,
      phone_number:   addrData.phone_number,
      country:        'CO',
    });

    // 3. Crear orden desde el carrito con metodo de pago seleccionado
    const orderData = await ordersService.createFromCart({
      shipping_address_uuid: addrData2.uuid,
      payment_method:        selectedPaymentMethod.value,
    });

    // 4. Flujo condicional por metodo de pago
    if (selectedPaymentMethod.value === 'COD') {
      cartStore.reset();
      router.push(`/payment/result?status=COD_APPROVED&order_uuid=${orderData.uuid}`);
    } else if (selectedPaymentMethod.value === 'NEQUI') {
      const nequiRes = await api.post('payment/nequi/initialize/', {
        order_uuid:   orderData.uuid,
        phone_number: nequiPhone.value.trim(),
      });
      cartStore.reset();
      router.push(`/checkout/nequi-espera?tx=${nequiRes.data.uuid}`);
    } else if (isCardFlow) {
      // Backend crea la transaccion SINCRONA en Wompi (ADR-001 Sec.4) -- sin
      // abrir el widget completo. wompi_id/status ya vienen listos en la
      // respuesta; /payment/result hace su propio polling si sigue PENDING.
      const wompiRes = await api.post('payment/payments/initialize/', {
        order_uuid: orderData.uuid,
        card_token: cardToken,
      });
      cartStore.reset();
      router.push({ path: '/payment/result', query: { tx: wompiRes.data.transaction_uuid } });
    } else {
      // PSE/Otros: flujo de siempre, sin cambios -- abre el widget completo.
      const wompiRes = await api.post('payment/payments/initialize/', {
        order_uuid: orderData.uuid,
      });
      await openWompiWidget(wompiRes.data);
    }

  } catch (e) {
    handleError(e, 'Error al procesar el pedido');
  } finally {
    if (isCardFlow) resetNewCard();
    submitting.value = false;
  }
}

onMounted(async () => {
  // Wompi PSE redirect: transaction-redirect.wompi.co redirige de vuelta al referrer (/checkout)
  // con ?id=WOMPI_TX_ID (y opcionalmente ?reference=OUR_UUID&status=APPROVED).
  // El UUID interno se persiste en sessionStorage por useWompiWidget antes de abandonar la SPA.
  const wompiTxId = route.query.id;
  if (wompiTxId) {
    const ref    = route.query.reference
                || sessionStorage.getItem('wompi_pending_tx')
                || '';
    const status = route.query.status || '';
    sessionStorage.removeItem('wompi_pending_tx');
    router.replace({
      path:  '/payment/result',
      query: { tx: ref || wompiTxId, id: wompiTxId, status },
    });
    return;
  }

  if (!authStore.isAuthenticated) { router.push('/login'); return; }
  if (cartStore.isEmpty) await cartStore.fetchCart();
  if (authStore.user) {
    addressFormRef.value?.prefill({
      fullName: authStore.user.full_name || authStore.user.first_name || '',
      email:    authStore.user.email || '',
      phone:    authStore.user.phone || '',
    });
  }
  await fetchCheckoutPreview();
  await fetchFeatureFlags();
  await fetchSavedCards();
});
</script>

<style scoped>
/* Paleta unificada con Services/Renting (ver
   PLAN_DE_ACCION_UI_SERVICES_PAYMENT.md, Paso 3) -- mismo violeta
   #7c3aed que ya usan los otros dos dominios, en vez del azul propio de
   Shop. Mismo nombre de custom property que components/shared/checkout/
   por convencion, aunque esta pagina no esta dentro de CheckoutModal. */
.checkout-view {
  --checkout-accent: #7c3aed;
  --checkout-accent-hover: #6d28d9;
  --checkout-accent-tint: #f5f3ff;
  --checkout-accent-ring: #c4b5fd;
}
.text-checkout-accent { color: var(--checkout-accent) !important; }
.btn-checkout-accent { background: var(--checkout-accent); border-color: var(--checkout-accent); color: #fff; }
.btn-checkout-accent:hover { background: var(--checkout-accent-hover); border-color: var(--checkout-accent-hover); color: #fff; }
.btn-checkout-accent:disabled { opacity: .65; }

.order-summary-sticky { position: sticky; top: 90px; }
</style>
