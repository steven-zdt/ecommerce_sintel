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
          <CardOrWidgetPanel
            v-if="method === 'WOMPI' && cardApiFlowEnabled"
            v-model:sub-method="wompiSubMethod"
            v-model:selected-card-id="selectedCardId"
            :saved-cards="savedCards"
            :loading-cards="loadingCards"
            :new-card="newCardRaw"
            :card-step-valid="cardStepValid"
            :loading="paying"
            :card-api-flow-enabled="cardApiFlowEnabled"
            :widget-flow-enabled="widgetFlowEnabled"
            @update:new-card="({ field, value }) => newCardRaw[field] = value"
            @pay="pay"
          />
        </template>
      </CheckoutModal>

    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { formatCOP } from '@/utils/money';
import { useRoute, useRouter } from 'vue-router';
import RentalBookingSuccess from '@/components/customer/renting/RentalBookingSuccess.vue';
import { useBookingStore } from '@/store/renting/bookingStore';
import { bookingService } from '@/services/renting/bookingService';
import { paymentService } from '@/services/renting/paymentService';
import { useWompiWidget } from '@/composables/useWompiWidget';
import { useCardOrWidgetPayment } from '@/composables/useCardOrWidgetPayment';
import { useToast } from '@/composables/useToast';
import useApi from '@/composables/useApi';
import CheckoutModal from '@/components/shared/checkout/CheckoutModal.vue';
import PaymentMethodSelector from '@/components/shared/checkout/PaymentMethodSelector.vue';
import CardOrWidgetPanel from '@/components/shared/checkout/CardOrWidgetPanel.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';

const route  = useRoute();
const router = useRouter();
const store  = useBookingStore();
const api    = useApi();
const { openWompiWidget } = useWompiWidget();
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

// Tarjeta vs PSE/Otros -- estado y logica compartidos con CheckoutView.vue y
// ServiceCheckoutModal.vue via useCardOrWidgetPayment() (extraido en la
// auditoria 2026-07-22, plan hibrido Widget+API). No se usa el
// fetchFeatureFlags() propio del composable porque esta vista ya hace una
// sola llamada combinada (tambien necesita nequi_enabled) en el onMounted de
// abajo -- cardApiFlowEnabled sigue siendo un ref normal, asignable desde aqui.
const {
  wompiSubMethod, cardApiFlowEnabled, widgetFlowEnabled,
  savedCards, loadingCards, selectedCardId, newCardRaw, cardStepValid,
  fetchSavedCards, resolveCardToken, resetNewCard,
} = useCardOrWidgetPayment();

// immediate: true -- 'WOMPI' ya es el valor por defecto de `method` al montar
// esta vista, asi que un watch sin immediate nunca dispara (no hay cambio de
// valor que detectar) y las tarjetas guardadas jamas se cargaban (bug real,
// hallado en smoke test E2E 2026-07-22).
watch(method, (m) => { if (m === 'WOMPI') fetchSavedCards(); }, { immediate: true });

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
  formatCOP(v, { withSymbol: true });

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
    if (isCardFlow) resetNewCard();
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
  // Comodato no tiene paso de pago -- si el cliente vuelve a esta reserva mas
  // tarde (ej. desde "Mis alquileres"), redirige a la misma pantalla de
  // "pendiente de aprobacion" que ya usa el wizard al enviar la solicitud, en
  // vez de mostrar el CTA "Proceder al pago" (bug real, hallado en smoke test
  // 2026-07-22: esta vista no distinguia comercial_type y siempre asumia que
  // faltaba pagar).
  if (rental.value?.commercial_type === 'COMODATO') {
    router.replace({
      path: '/payment/result',
      query: { status: 'RENTAL_COD_APPROVED', rental_uuid: route.params.uuid },
    });
    return;
  }
  try {
    const res = await api.get('payment/payments/feature-flags/');
    nequiEnabled.value = !!res.data.nequi_enabled;
    cardApiFlowEnabled.value = !!res.data.card_api_flow_enabled;
    widgetFlowEnabled.value  = res.data.widget_flow_enabled !== false;
  } catch {
    nequiEnabled.value = false;
    cardApiFlowEnabled.value = false; // fail-safe, no fail-open
  }
  if (!cardApiFlowEnabled.value && widgetFlowEnabled.value) wompiSubMethod.value = 'WIDGET';
  else if (cardApiFlowEnabled.value && !widgetFlowEnabled.value) wompiSubMethod.value = 'CARD';
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
