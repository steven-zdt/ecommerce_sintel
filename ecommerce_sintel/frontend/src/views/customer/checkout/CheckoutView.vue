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
              hide-submit
              cod-label="Contra entrega"
              cod-description="Paga al recibir tu pedido"
            />

            <!-- Sub-opciones de "Pago en linea": Tarjeta (backend directo, sin widget) vs PSE/Otros (widget completo).
                 El sub-selector de "Tarjeta" solo aparece si cardApiFlowEnabled (ADR-001 Fase 5,
                 feature flag consultado a GET payments/feature-flags/ -- kill-switch editable
                 desde /admin/ sin desplegar codigo, tambien aplicado del lado del backend). -->
            <div v-if="selectedPaymentMethod === 'WOMPI' && cardApiFlowEnabled" class="mt-3">
              <div class="btn-group w-100 mb-3" role="group">
                <button
                  type="button"
                  class="btn btn-sm"
                  :class="wompiSubMethod === 'CARD' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
                  @click="wompiSubMethod = 'CARD'"
                >
                  <i class="bi bi-credit-card-2-front me-1"></i>Tarjeta
                </button>
                <button
                  type="button"
                  class="btn btn-sm"
                  :class="wompiSubMethod === 'WIDGET' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
                  @click="wompiSubMethod = 'WIDGET'"
                >
                  <i class="bi bi-bank me-1"></i>PSE / Otros
                </button>
              </div>

              <!-- Tarjeta: guardadas + agregar nueva, sin abrir el widget de Wompi -->
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
                      <i
                        class="bi flex-shrink-0"
                        :class="selectedCardId === card.token_id ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"
                      ></i>
                    </div>
                  </PaymentMethodCard>

                  <PaymentMethodCard :active="selectedCardId === 'NEW'" @select="selectedCardId = 'NEW'">
                    <div class="d-flex align-items-center gap-2">
                      <i class="bi bi-plus-circle"></i>
                      <span class="small fw-semibold">Agregar tarjeta nueva</span>
                      <i
                        class="bi flex-shrink-0 ms-auto"
                        :class="selectedCardId === 'NEW' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"
                      ></i>
                    </div>
                  </PaymentMethodCard>

                  <div v-if="selectedCardId === 'NEW'" class="row g-2 mt-1">
                    <div class="col-12">
                      <input
                        v-model="newCardRaw.number" type="text" inputmode="numeric" autocomplete="cc-number"
                        class="form-control form-control-sm" placeholder="Numero de tarjeta" maxlength="19"
                      />
                    </div>
                    <div class="col-4">
                      <input
                        v-model="newCardRaw.exp_month" type="text" inputmode="numeric" autocomplete="cc-exp-month"
                        class="form-control form-control-sm" placeholder="MM" maxlength="2"
                      />
                    </div>
                    <div class="col-4">
                      <input
                        v-model="newCardRaw.exp_year" type="text" inputmode="numeric" autocomplete="cc-exp-year"
                        class="form-control form-control-sm" placeholder="AA" maxlength="2"
                      />
                    </div>
                    <div class="col-4">
                      <input
                        v-model="newCardRaw.cvc" type="password" inputmode="numeric" autocomplete="cc-csc"
                        class="form-control form-control-sm" placeholder="CVC" maxlength="4"
                      />
                    </div>
                    <div class="col-12">
                      <input
                        v-model="newCardRaw.card_holder" type="text" autocomplete="cc-name"
                        class="form-control form-control-sm" placeholder="Nombre del titular"
                      />
                    </div>
                  </div>
                  <p class="text-muted mb-0" style="font-size:.7rem">
                    <i class="bi bi-shield-lock-fill me-1"></i>Tus datos de tarjeta se envian directo a Wompi, nunca pasan por nuestros servidores.
                  </p>
                </div>
              </div>
            </div>

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
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/store/auth';
import { useCartStore } from '@/store/cart';
import { useWompiWidget } from '@/composables/useWompiWidget';
import { useCardTokenization } from '@/composables/useCardTokenization';
import ColombianAddressForm from '@/components/customer/checkout/ColombianAddressForm.vue';
import PaymentMethodSelector from '@/components/shared/checkout/PaymentMethodSelector.vue';
import PaymentCard from '@/components/shared/checkout/PaymentCard.vue';
import PaymentRow from '@/components/shared/checkout/PaymentRow.vue';
import PaymentAlert from '@/components/shared/checkout/PaymentAlert.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';
import PaymentMethodCard from '@/components/shared/checkout/PaymentMethodCard.vue';

const api       = useApi();
const toast     = useToast();
const authStore = useAuthStore();
const cartStore = useCartStore();
const router    = useRouter();
const route     = useRoute();
const { openWompiWidget }  = useWompiWidget();
const { tokenizeCard }     = useCardTokenization();

const submitting            = ref(false);
const loadingCheckout       = ref(false);
const checkoutPayload       = ref(null);
const stockError            = ref('');
const selectedPaymentMethod = ref('WOMPI');
const nequiPhone            = ref('');
const addressFormRef        = ref(null);

// Sub-metodo dentro de "Pago en linea" (ADR-001 Fase 3b): Tarjeta usa el flujo
// backend-directo (initialize/ con card_token, sin abrir el widget completo);
// PSE/Otros sigue exactamente el flujo de siempre (widget completo de Wompi),
// ya que PSE requiere redireccion al banco -- no es algo que se pueda eliminar.
const wompiSubMethod     = ref('CARD');
const cardApiFlowEnabled = ref(true); // ADR-001 Fase 5: kill-switch, GET payments/feature-flags/
const savedCards     = ref([]);
const loadingCards   = ref(false);
const selectedCardId = ref('NEW'); // 'NEW' o el token_id de una tarjeta guardada
const defaultNewCard = () => ({ number: '', exp_month: '', exp_year: '', cvc: '', card_holder: '' });
const newCardRaw     = ref(defaultNewCard());

const errors = reactive({ nequiPhone: false });

const displayItems = computed(() =>
  checkoutPayload.value?.items?.length ? checkoutPayload.value.items : cartStore.items
);

const fmt = (val) => new Intl.NumberFormat('es-CO').format(parseFloat(val) || 0);

function validate() {
  errors.nequiPhone = selectedPaymentMethod.value === 'NEQUI'
    ? !/^\d{10}$/.test(nequiPhone.value.trim())
    : false;
  const addressValid = addressFormRef.value?.validate() ?? false;

  let cardValid = true;
  if (selectedPaymentMethod.value === 'WOMPI' && wompiSubMethod.value === 'CARD') {
    cardValid = selectedCardId.value === 'NEW'
      ? Object.values(newCardRaw.value).every((v) => String(v).trim() !== '')
      : !!selectedCardId.value;
  }

  return addressValid && !errors.nequiPhone && cardValid;
}

async function fetchFeatureFlags() {
  try {
    const res = await api.get('payment/payments/feature-flags/');
    cardApiFlowEnabled.value = !!res.data.card_api_flow_enabled;
  } catch {
    // Ante cualquier duda (endpoint caido, red, etc.) se prefiere el camino
    // ya probado y mas antiguo (Widget completo) -- fail-safe, no fail-open.
    cardApiFlowEnabled.value = false;
  }
  if (!cardApiFlowEnabled.value) wompiSubMethod.value = 'WIDGET';
}

async function fetchSavedCards() {
  loadingCards.value = true;
  try {
    const res = await api.get('payment/cards/');
    savedCards.value = res.data.results ?? res.data ?? [];
    if (savedCards.value.length > 0) selectedCardId.value = savedCards.value[0].token_id;
  } catch {
    // Sin tarjetas guardadas o error de red -- el usuario simplemente ve el
    // formulario de "agregar tarjeta nueva" (selectedCardId ya empieza en 'NEW').
  } finally {
    loadingCards.value = false;
  }
}

/**
 * Resuelve el card_token a usar en initialize/: si el usuario eligio una
 * tarjeta guardada, es su token_id directo. Si eligio "nueva", tokeniza
 * contra Wompi (navegador->Wompi directo, nunca por nuestro backend) y la
 * guarda de inmediato (decision del usuario: toda tarjeta nueva se guarda
 * siempre, sin checkbox opcional) antes de usarla para pagar.
 */
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
    const addrRes = await api.post('orders/addresses/', {
      full_name:      addrData.full_name,
      address_line_1: addrData.address_line_1,
      address_line_2: addrData.address_line_2 || '',
      city:           addrData.city,
      state:          addrData.state,
      phone_number:   addrData.phone_number,
      country:        'CO',
    });

    // 3. Crear orden desde el carrito con metodo de pago seleccionado
    const orderRes = await api.post('orders/orders/create_from_cart/', {
      shipping_address_uuid: addrRes.data.uuid,
      payment_method:        selectedPaymentMethod.value,
    });

    // 4. Flujo condicional por metodo de pago
    if (selectedPaymentMethod.value === 'COD') {
      cartStore.reset();
      router.push(`/payment/result?status=COD_APPROVED&order_uuid=${orderRes.data.uuid}`);
    } else if (selectedPaymentMethod.value === 'NEQUI') {
      const nequiRes = await api.post('payment/nequi/initialize/', {
        order_uuid:   orderRes.data.uuid,
        phone_number: nequiPhone.value.trim(),
      });
      cartStore.reset();
      router.push(`/checkout/nequi-espera?tx=${nequiRes.data.uuid}`);
    } else if (isCardFlow) {
      // Backend crea la transaccion SINCRONA en Wompi (ADR-001 Sec.4) -- sin
      // abrir el widget completo. wompi_id/status ya vienen listos en la
      // respuesta; /payment/result hace su propio polling si sigue PENDING.
      const wompiRes = await api.post('payment/payments/initialize/', {
        order_uuid: orderRes.data.uuid,
        card_token: cardToken,
      });
      cartStore.reset();
      router.push({ path: '/payment/result', query: { tx: wompiRes.data.transaction_uuid } });
    } else {
      // PSE/Otros: flujo de siempre, sin cambios -- abre el widget completo.
      const wompiRes = await api.post('payment/payments/initialize/', {
        order_uuid: orderRes.data.uuid,
      });
      await openWompiWidget(wompiRes.data);
    }

  } catch (e) {
    const data = e.response?.data;
    const msg  = data?.detail || Object.values(data || {})[0]?.[0] || 'Error al procesar el pedido';
    toast.error(msg);
  } finally {
    if (isCardFlow) newCardRaw.value = defaultNewCard();
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
