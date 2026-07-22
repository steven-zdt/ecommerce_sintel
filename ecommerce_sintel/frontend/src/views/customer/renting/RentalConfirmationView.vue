<template>
  <main class="confirmation-page">
    <div class="container py-5">

      <RentalBookingSuccess :number="rental?.number || rental?.reference || shortId">

        <div v-if="loading" class="text-center my-4">
          <div class="spinner-border text-primary"></div>
        </div>

        <template v-else>
          <!-- Resumen compacto -->
          <div class="summary-card">
            <div>
              <span>Equipo</span>
              <strong>{{ equipmentName }}</strong>
            </div>
            <div>
              <span>Proyecto</span>
              <strong>{{ rental?.location_city || created?.project?.city || 'Por confirmar' }}</strong>
            </div>
            <div>
              <span>Costo estimado</span>
              <strong>{{ money(total) }}</strong>
            </div>
          </div>

          <!-- Acciones -->
          <div class="actions">
            <PaymentCTA icon="bi-shield-lock" @click="showPayment = true">Proceder al pago</PaymentCTA>
            <PaymentCTA v-if="editEquipmentUuid" variant="secondary" :to="editRoute">Editar solicitud</PaymentCTA>
            <RouterLink to="/alquiler" class="btn btn-link">
              Volver al catalogo
            </RouterLink>
          </div>
        </template>

      </RentalBookingSuccess>

      <!-- Panel de pago -- shell compartido, mismo que Services (ver
           PLAN_DE_ACCION_UI_SERVICES_PAYMENT.md, Paso 2). Un solo paso
           ("Metodo de pago"): el resumen ya se muestra arriba en la pagina
           y esta vista nunca queda esperando un estado -- pay() navega a
           /payment/result (Wompi/COD) o /checkout/nequi-espera (Nequi)
           exactamente igual que antes. -->
      <CheckoutModal
        :open="showPayment"
        phase="method"
        :steps="['Metodo de pago']"
        aria-label="Pago del alquiler"
        @close="showPayment = false"
      >
        <template #method>
          <PaymentMethodSelector
            v-model="method"
            v-model:nequi-phone="phone"
            :nequi-error="nequiError"
            :loading="paying"
            :allow-nequi="nequiEnabled"
            :hide-submit="method === 'WOMPI' && cardApiFlowEnabled"
            cod-label="Contra entrega"
            cod-description="Paga al recibir el equipo"
            cod-confirm-label="Confirmar reserva — contra entrega"
            @pay="pay"
          />

          <!-- Tarjeta vs PSE/Otros (mismo patron portado a Tienda y Servicios Tecnicos,
               ADR-001 Fase 3b): Tarjeta usa el flujo backend-directo, sin abrir el
               widget completo; PSE/Otros mantiene el widget (redireccion bancaria). -->
          <div v-if="method === 'WOMPI' && cardApiFlowEnabled" class="mt-3">
            <div class="btn-group w-100 mb-3" role="group">
              <button type="button" class="btn btn-sm"
                :class="wompiSubMethod === 'CARD' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
                @click="wompiSubMethod = 'CARD'">
                <i class="bi bi-credit-card-2-front me-1"></i>Tarjeta
              </button>
              <button type="button" class="btn btn-sm"
                :class="wompiSubMethod === 'WIDGET' ? 'btn-checkout-accent' : 'btn-outline-secondary'"
                @click="wompiSubMethod = 'WIDGET'">
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

                <button class="btn btn-checkout-accent w-100 mt-2" :disabled="paying || !cardStepValid" @click="pay">
                  <span v-if="paying" class="spinner-border spinner-border-sm me-2"></span>
                  Pagar
                </button>
              </div>
            </div>
          </div>
        </template>
      </CheckoutModal>

    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import RentalBookingSuccess from '@/components/customer/renting/RentalBookingSuccess.vue';
import { useBookingStore } from '@/store/renting/bookingStore';
import { bookingService } from '@/services/renting/bookingService';
import { paymentService } from '@/services/renting/paymentService';
import { useWompiWidget } from '@/composables/useWompiWidget';
import { useCardTokenization } from '@/composables/useCardTokenization';
import { useToast } from '@/composables/useToast';
import useApi from '@/composables/useApi';
import CheckoutModal from '@/components/shared/checkout/CheckoutModal.vue';
import PaymentMethodSelector from '@/components/shared/checkout/PaymentMethodSelector.vue';
import PaymentMethodCard from '@/components/shared/checkout/PaymentMethodCard.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';

const route  = useRoute();
const router = useRouter();
const store  = useBookingStore();
const api    = useApi();
const { openWompiWidget } = useWompiWidget();
const { tokenizeCard }    = useCardTokenization();
const toast  = useToast();

const rental      = ref(null);
const loading     = ref(true);
const showPayment = ref(false);
const method      = ref('WOMPI');
const phone       = ref('');
const paying      = ref(false);
// Kill-switch: Nequi Push se oculta del selector mientras no haya
// credenciales reales configuradas en el backend (ver
// payment/online/api/views.py:_is_nequi_configured). Fail-safe: ante
// cualquier duda (endpoint caido, red) se asume deshabilitado -- ya esta
// roto hoy, así que ocultarlo es la opcion segura, no al reves.
const nequiEnabled = ref(false);

// Tarjeta vs PSE/Otros (ADR-001 Fase 3b, portado desde CheckoutView.vue /
// ServiceCheckoutModal.vue -- Renting era la ultima superficie de checkout
// que seguia abriendo el widget completo tambien para tarjetas).
const wompiSubMethod     = ref('CARD');
const cardApiFlowEnabled = ref(false); // fail-safe: widget completo hasta confirmar el flag
const savedCards     = ref([]);
const loadingCards   = ref(false);
const cardsFetched   = ref(false);
const selectedCardId = ref('NEW');
const defaultNewCard = () => ({ number: '', exp_month: '', exp_year: '', cvc: '', card_holder: '' });
const newCardRaw     = ref(defaultNewCard());
const cardStepValid  = computed(() => selectedCardId.value !== 'NEW'
  || Object.values(newCardRaw.value).every((v) => String(v).trim() !== ''));

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

watch(method, (m) => { if (m === 'WOMPI') fetchSavedCards(); });

const created      = computed(() => store.created);
const shortId      = computed(() => String(route.params.uuid || '').slice(0, 8).toUpperCase());
const equipmentName = computed(() =>
  created.value?.equipment?.name ||
  rental.value?.equipment_variant?.equipment_name ||
  'Equipo reservado'
);
const total = computed(() =>
  rental.value?.grand_total ??
  created.value?.costs?.total ??
  0
);
const editEquipmentUuid = computed(() =>
  created.value?.equipment?.uuid || rental.value?.equipment_variant?.equipment_uuid || ''
);
const editRoute = computed(() => ({
  name: 'rental-request',
  params: { uuid: editEquipmentUuid.value },
}));

const money = (v) =>
  new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0);

const nequiError = ref(false);

async function pay() {
  nequiError.value = method.value === 'NEQUI' && !/^\d{10}$/.test(phone.value);
  if (nequiError.value) return;

  const isCardFlow = method.value === 'WOMPI' && wompiSubMethod.value === 'CARD' && cardApiFlowEnabled.value;
  if (isCardFlow && !cardStepValid.value) return;

  paying.value = true;

  try {
    // Tarjeta (backend-directo, ADR-001): tokenizar/resolver ANTES de llamar
    // a process-payment/ -- si falla, no queda ninguna Transaction huerfana.
    const cardToken = isCardFlow ? await resolveCardToken() : null;

    const payload = { payment_method: method.value };
    if (method.value === 'NEQUI') payload.phone_number = phone.value;
    if (isCardFlow) payload.card_token = cardToken;

    const data = await paymentService.process(route.params.uuid, payload);

    if (isCardFlow) {
      // El backend ya creo la transaccion de forma sincrona en Wompi -- sin
      // widget, /payment/result hace su propio polling con el wompi_id ya
      // disponible en la respuesta.
      router.push({ path: '/payment/result', query: { tx: data.transaction_uuid, id: data.wompi_id || undefined } });

    } else if (method.value === 'WOMPI') {
      // PSE/Otros: unico caso que aun abre el widget completo, porque el
      // banco exige esa redireccion. El callback de checkout.open() maneja
      // APPROVED/DECLINED/PENDING → todos redirigen a /payment/result?tx=<uuid>
      await openWompiWidget(data, { redirectPath: '/payment/result' });

    } else if (method.value === 'NEQUI') {
      router.push({
        name: 'nequi-pending',
        query: { tx: data.nequi_tx_uuid, rental_uuid: route.params.uuid },
      });

    } else {
      // Contra entrega
      router.push({
        path: '/payment/result',
        query: { status: 'RENTAL_COD_APPROVED', rental_uuid: route.params.uuid },
      });
    }
  } catch (e) {
    // 502 = fallo del proveedor de pago externo (Wompi/Nequi) contra su propio
    // gateway -- el "detail" en ese caso es un mensaje tecnico crudo (ej. "No
    // se pudo obtener token Nequi: 400") pensado para logs, no para el
    // cliente. Otros codigos (400, etc.) SI traen mensajes de validacion
    // utiles para el usuario y se muestran tal cual.
    const isGatewayFailure = e.response?.status === 502;
    const message = isGatewayFailure
      ? `No pudimos procesar el pago con ${method.value === 'NEQUI' ? 'Nequi' : 'el proveedor de pago'} en este momento. Intenta con otro metodo de pago.`
      : (e.response?.data?.detail || e?.message || 'No pudimos iniciar el pago.');
    toast.error(message);
  } finally {
    if (isCardFlow) newCardRaw.value = defaultNewCard();
    paying.value = false;
  }
}

onMounted(async () => {
  try {
    rental.value = await bookingService.detail(route.params.uuid);
  } catch {
    rental.value = created.value || null;
  } finally {
    loading.value = false;
  }
  try {
    const res = await api.get('payment/payments/feature-flags/');
    nequiEnabled.value = !!res.data.nequi_enabled;
    cardApiFlowEnabled.value = !!res.data.card_api_flow_enabled;
  } catch {
    nequiEnabled.value = false;
    cardApiFlowEnabled.value = false; // fail-safe, no fail-open
  }
  if (!cardApiFlowEnabled.value) wompiSubMethod.value = 'WIDGET';
});
</script>

<style scoped>
.confirmation-page { min-height: 100vh; background: #f8f8fb; }

.summary-card {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  text-align: left;
  background: #fff;
  border: 1px solid #e8e7ee;
  border-radius: 20px;
  padding: 1.25rem;
  margin: 1rem auto 1.5rem;
  box-shadow: 0 15px 40px rgba(30,20,60,.06);
}
.summary-card div {
  display: grid;
  gap: .3rem;
  padding: .4rem 1rem;
  border-right: 1px solid #eee;
}
.summary-card div:last-child { border: 0; }
.summary-card span { font-size: .72rem; text-transform: uppercase; color: #64748b; }

.actions { display: flex; justify-content: center; flex-wrap: wrap; gap: .7rem; }

/* El panel de pago (overlay/shell/selector de metodo) ahora vive en
   components/shared/checkout/ -- ver PLAN_DE_ACCION_UI_SERVICES_PAYMENT.md,
   Paso 2. Solo queda aqui el estilo de esta pagina de confirmacion. */

@media (max-width: 650px) {
  .summary-card { grid-template-columns: 1fr; }
  .summary-card div { border-right: 0; border-bottom: 1px solid #eee; }
}
</style>
