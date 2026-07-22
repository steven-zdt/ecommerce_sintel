<template>
  <div class="pr-root">

    <!-- Loading -->
    <div v-if="loading" class="pr-loading">
      <div class="pr-loading-card">
        <div class="pr-loading-icon">
          <div class="spinner-border text-warning" role="status" style="width:2rem;height:2rem;"></div>
        </div>
        <div class="pr-loading-title">Verificando tu pago...</div>
        <p class="text-muted small mb-0">Por favor espera mientras procesamos la informacion</p>
      </div>
    </div>

    <!-- Error de carga -->
    <div v-else-if="fetchError && !result" class="pr-loading">
      <div class="pr-loading-card text-center">
        <i class="bi bi-exclamation-circle text-warning fs-1 mb-3 d-block"></i>
        <h3 class="fw-bold mb-2">No se pudo cargar la informacion</h3>
        <p class="text-muted small mb-4">Verifica tu conexion o intenta nuevamente.</p>
        <div class="d-flex gap-2 justify-content-center flex-wrap">
          <PaymentCTA size="md" icon="bi-arrow-clockwise" @click="load">Reintentar</PaymentCTA>
          <PaymentCTA size="md" variant="secondary" icon="bi-bag" to="/mi-cuenta/pedidos">Mis pedidos</PaymentCTA>
        </div>
      </div>
    </div>

    <!-- COD Renting -->
    <div v-else-if="isCodRenting" class="pr-body">
      <div class="container" style="max-width:680px">
        <PaymentHeader variant="warning" icon="bi-hourglass-split" title="Solicitud registrada"
          :subtitle="rentalData?.display_status || 'Tu solicitud está pendiente de validación por nuestro equipo'" class="mb-4">
          <template #badge><PaymentBadge css-class="bg-warning text-dark">Pago en sitio</PaymentBadge></template>
        </PaymentHeader>

        <PaymentCard icon="bi-box-seam" title="Detalle del alquiler" class="mb-4">
          <PaymentRow label="Referencia"><code class="small">{{ rentalData?.uuid }}</code></PaymentRow>
          <PaymentRow v-if="rentalData?.equipment_variant?.equipment_name" label="Equipo">
            <span class="fw-semibold">{{ rentalData.equipment_variant.equipment_name }}</span>
          </PaymentRow>
          <PaymentRow v-if="rentalData?.start_date" label="Periodo">
            <span>{{ rentalData.start_date }} — {{ rentalData.end_date }}</span>
          </PaymentRow>
          <PaymentRow label="Total a pagar" bold-label>
            <span class="fw-bold text-success fs-5">${{ fmt(rentalData?.grand_total) }} COP</span>
          </PaymentRow>
        </PaymentCard>

        <PaymentAlert variant="warning" icon="bi-cash-stack" title="Pago al momento de la entrega" class="mb-4">
          <p class="mb-0 mt-1 text-muted small">Tendras que pagar <strong>${{ fmt(rentalData?.grand_total) }} COP</strong> al recibir el equipo.</p>
        </PaymentAlert>

        <div class="pr-actions">
          <PaymentCTA icon="bi-bag" to="/mi-cuenta/pedidos">Ver mis solicitudes</PaymentCTA>
          <PaymentCTA variant="secondary" to="/alquiler">Ver mas equipos</PaymentCTA>
        </div>
      </div>
    </div>

    <!-- COD Orden regular / servicio -->
    <div v-else-if="isCodOrder" class="pr-body">
      <div class="container" style="max-width:680px">
        <PaymentHeader variant="success" icon="bi-check-lg" title="Orden confirmada"
          subtitle="Tu pedido ha sido registrado correctamente" class="mb-4">
          <template #badge><PaymentBadge css-class="bg-warning text-dark">Pago en sitio</PaymentBadge></template>
        </PaymentHeader>

        <PaymentCard icon="bi-receipt" title="Resumen del pedido" class="mb-4">
          <template #header-end><PaymentBadge css-class="bg-warning-subtle text-warning border border-warning-subtle">Contra entrega</PaymentBadge></template>
          <PaymentRow label="N. de orden"><code class="small">{{ codOrderData?.uuid }}</code></PaymentRow>
          <PaymentRow v-if="codOrderData?.tracking_number" label="Seguimiento">
            <code class="small">{{ codOrderData.tracking_number }}</code>
          </PaymentRow>
          <PaymentRow v-if="codOrderData?.shipping_address" label="Entrega en">
            <span class="text-end small" style="max-width:60%">{{ codOrderData.shipping_address.address_line_1 }}, {{ codOrderData.shipping_address.city }}</span>
          </PaymentRow>
          <template v-if="codOrderData?.items?.length">
            <PaymentRow v-for="item in codOrderData.items" :key="item.sku">
              <template #label>
                <div><div class="small fw-semibold">{{ item.item_name }}</div><div class="text-muted" style="font-size:.75rem">{{ item.sku }} · x{{ item.quantity }}</div></div>
              </template>
              <span class="small fw-semibold">${{ fmt(parseFloat(item.price) * item.quantity) }}</span>
            </PaymentRow>
          </template>
          <PaymentRow label="Total a pagar" bold-label>
            <span class="fw-bold text-success fs-5">${{ fmt(codOrderData?.total_amount) }} COP</span>
          </PaymentRow>
        </PaymentCard>

        <PaymentAlert variant="warning" icon="bi-truck" title="Pago contra entrega" class="mb-4">
          <p class="mb-0 mt-1 text-muted small">Pagaras <strong>${{ fmt(codOrderData?.total_amount) }} COP</strong> al momento de recibir tu pedido.</p>
        </PaymentAlert>

        <div class="pr-actions">
          <PaymentCTA icon="bi-bag" to="/mi-cuenta/pedidos">Ver mis pedidos</PaymentCTA>
          <PaymentCTA variant="secondary" icon="bi-shop" to="/tienda">Seguir comprando</PaymentCTA>
        </div>
      </div>
    </div>

    <!-- Wompi Renting -->
    <div v-else-if="result?.rental" class="pr-body">
      <div class="container" style="max-width:680px">
        <PaymentHeader :variant="statusVariant" :icon="statusIcon" :title="statusTitle" :subtitle="statusSubtitle" class="mb-4">
          <template #badge><PaymentBadge :css-class="statusBadgeClass">{{ statusBadgeLabel }}</PaymentBadge></template>
        </PaymentHeader>

        <PaymentCard icon="bi-box-seam" title="Detalle del alquiler" class="mb-4">
          <PaymentRow label="Referencia"><code class="small">{{ result.rental.uuid }}</code></PaymentRow>
          <PaymentRow v-if="result.rental.equipment_name" label="Equipo">
            <span class="fw-semibold">{{ result.rental.equipment_name }}</span>
          </PaymentRow>
          <PaymentRow v-if="result.rental.start_date" label="Periodo">
            <span>{{ result.rental.start_date }} — {{ result.rental.end_date }}</span>
          </PaymentRow>
          <PaymentRow v-if="result.rental.location_city" label="Ciudad">
            <span>{{ result.rental.location_city }}</span>
          </PaymentRow>
          <PaymentRow label="Total" bold-label>
            <span class="fw-bold fs-5" :class="isPaid ? 'text-success' : 'text-muted'">${{ fmt(result.rental.grand_total) }} COP</span>
          </PaymentRow>
        </PaymentCard>

        <PaymentAlert v-if="isPending && !isDeclined" variant="warning" spinner title="Pago en proceso" class="mb-4">
          <p class="mb-0 mt-1 text-muted small">Tu transaccion esta siendo verificada. Te notificaremos cuando se confirme.</p>
          <p v-if="pollTimedOut" class="mb-0 mt-1 text-muted small">Esto esta tomando mas de lo usual. Puedes cerrar esta pagina — te avisaremos por correo cuando se confirme.</p>
        </PaymentAlert>

        <PaymentAlert v-if="isDeclined" variant="danger" icon="bi-x-circle-fill" title="Pago no completado" class="mb-4">
          <p class="mb-0 mt-1 text-muted small">Verifica los datos de tu tarjeta o intenta con otro metodo de pago. No se realizo ningun cargo.</p>
        </PaymentAlert>

        <div class="pr-actions">
          <PaymentCTA v-for="step in result.next_steps" :key="step.path" :to="step.path" :variant="ctaVariant(step.variant)">
            {{ step.label }}
          </PaymentCTA>
        </div>
      </div>
    </div>

    <!-- Resultado Wompi -->
    <div v-else-if="result" class="pr-body">
      <div class="container" style="max-width:720px">

        <!-- Banner de estado -->
        <PaymentHeader :variant="statusVariant" :icon="statusIcon" :title="statusTitle" :subtitle="statusSubtitle" class="mb-4">
          <template #badge><PaymentBadge :css-class="statusBadgeClass">{{ statusBadgeLabel }}</PaymentBadge></template>
        </PaymentHeader>

        <!-- Card principal -->
        <PaymentCard icon="bi-receipt-cutoff" title="Comprobante de pago" :header-extra="fmtDatetime(result.payment.created_at)" class="mb-4">
          <PaymentSectionLabel label="Transaccion" />
          <PaymentRow label="Estado"><PaymentBadge :css-class="statusBadgeClass">{{ statusBadgeLabel }}</PaymentBadge></PaymentRow>
          <PaymentRow v-if="result.payment.wompi_id" label="ID Wompi">
            <code class="small text-muted">{{ result.payment.wompi_id }}</code>
          </PaymentRow>
          <PaymentRow label="Referencia"><code class="small">{{ result.payment.uuid }}</code></PaymentRow>
          <PaymentRow v-if="result.payment.payment_method_type" label="Metodo">
            <div class="d-flex align-items-center gap-2">
              <i :class="methodIcon(result.payment.payment_method_type)"></i>
              <span class="small">{{ methodLabel(result.payment.payment_method_type) }}</span>
            </div>
          </PaymentRow>
          <PaymentRow label="Fecha"><span class="small">{{ fmtDatetime(result.payment.created_at) }}</span></PaymentRow>
          <PaymentRow label="Valor pagado" bold-label>
            <span class="fw-bold fs-5" :class="isPaid ? 'text-success' : 'text-muted'">${{ fmt(result.payment.amount_cop) }} {{ result.payment.currency }}</span>
          </PaymentRow>

          <PaymentSectionLabel label="Orden" />
          <PaymentRow label="N. de orden"><code class="small">{{ result.order.uuid }}</code></PaymentRow>
          <PaymentRow v-if="result.order.tracking_number" label="Seguimiento">
            <code class="small text-primary">{{ result.order.tracking_number }}</code>
          </PaymentRow>
          <PaymentRow label="Estado de orden">
            <PaymentBadge :css-class="orderStatusClass(result.order.status)">{{ orderStatusLabel(result.order.status) }}</PaymentBadge>
          </PaymentRow>
          <PaymentRow label="Fecha"><span class="small">{{ fmtDatetime(result.order.created_at) }}</span></PaymentRow>

          <template v-if="result.order.items?.length">
            <PaymentSectionLabel :label="`Articulos (${result.order.items.length})`" />
            <PaymentRow v-for="item in result.order.items" :key="item.sku">
              <template #label>
                <div><div class="small fw-semibold">{{ item.item_name }}</div><div class="text-muted" style="font-size:.75rem">{{ item.sku }} · x{{ item.quantity }}</div></div>
              </template>
              <span class="small fw-semibold">${{ fmt(item.subtotal) }}</span>
            </PaymentRow>
            <PaymentRow label="Total" bold-label>
              <span class="fw-bold text-success fs-5">${{ fmt(result.order.total_amount) }} COP</span>
            </PaymentRow>
          </template>

          <PaymentSectionLabel label="Cliente" />
          <PaymentRow label="Correo"><span class="small">{{ result.customer.email }}</span></PaymentRow>
          <PaymentRow v-if="result.customer.full_name && result.customer.full_name !== result.customer.email" label="Nombre">
            <span class="small">{{ result.customer.full_name }}</span>
          </PaymentRow>

          <template v-if="result.shipping">
            <PaymentSectionLabel label="Envio" />
            <PaymentRow label="Direccion">
              <span class="small text-end" style="max-width:55%">{{ result.shipping.address_line_1 }}, {{ result.shipping.city }}</span>
            </PaymentRow>
            <PaymentRow v-if="result.shipping.department" label="Departamento">
              <span class="small">{{ result.shipping.department }}</span>
            </PaymentRow>
          </template>

          <template v-if="result.service">
            <PaymentSectionLabel label="Detalles del Servicio" />
            <PaymentRow label="Direccion">
              <span class="small text-end" style="max-width:55%">{{ result.service.address }}</span>
            </PaymentRow>
            <PaymentRow v-if="result.service.preferred_date" label="Fecha preferida">
              <span class="small">{{ fmtDate(result.service.preferred_date) }}</span>
            </PaymentRow>
            <PaymentRow v-if="result.service.preferred_time" label="Hora preferida">
              <span class="small">{{ result.service.preferred_time }}</span>
            </PaymentRow>
            <PaymentRow label="Prioridad">
              <PaymentBadge :css-class="priorityBadgeClass(result.service.priority)">{{ priorityLabel(result.service.priority) }}</PaymentBadge>
            </PaymentRow>
            <PaymentRow v-if="result.service.contact_person?.full_name" label="Encargado">
              <div class="text-end">
                <div class="small fw-semibold">{{ result.service.contact_person.full_name }}</div>
                <div class="text-muted" style="font-size:.72rem">{{ result.service.contact_person.phone }}</div>
              </div>
            </PaymentRow>

            <PaymentAlert v-if="isPaid" variant="info" icon="bi-info-circle-fill" title="Proximos pasos" class="mx-4 mb-3">
              <p class="mb-0 mt-1 text-muted">Nuestro equipo revisara la disponibilidad y te confirmara la fecha definitiva de la visita. Recibiras una notificacion por correo.</p>
            </PaymentAlert>
          </template>
        </PaymentCard>

        <!-- Estado pendiente: spinner + info -->
        <PaymentAlert v-if="isPending && !isDeclined" variant="warning" spinner title="Pago en proceso" class="mb-4">
          <p class="mb-0 mt-1 text-muted small">Tu transaccion esta siendo verificada. La orden continuara en proceso hasta que recibamos la confirmacion de pago. Recibiras una notificacion en tu correo.</p>
          <p v-if="pollTimedOut" class="mb-0 mt-1 text-muted small">Esto esta tomando mas de lo usual. Puedes cerrar esta pagina — te avisaremos por correo cuando se confirme.</p>
        </PaymentAlert>

        <!-- Estado rechazado: retry -->
        <PaymentAlert v-if="isDeclined" variant="danger" icon="bi-x-circle-fill" title="Pago no completado" class="mb-4">
          <p class="mb-0 mt-1 text-muted small">Verifica los datos de tu tarjeta o intenta con otro metodo de pago. No se realizo ningun cargo.</p>
        </PaymentAlert>

        <!-- Timeline -->
        <PaymentCard v-if="result.timeline?.length" icon="bi-clock-history" icon-class="text-secondary" title="Historial" class="mb-4">
          <PaymentTimeline :events="result.timeline" />
        </PaymentCard>

        <!-- Acciones -->
        <div class="pr-actions mb-4">
          <template v-if="result.next_steps?.length">
            <PaymentCTA v-for="step in result.next_steps" :key="step.path" :to="step.path" :variant="ctaVariant(step.variant)">
              {{ step.label }}
            </PaymentCTA>
          </template>
          <template v-else>
            <PaymentCTA icon="bi-shop" to="/tienda">Seguir comprando</PaymentCTA>
            <PaymentCTA variant="secondary" icon="bi-bag" to="/mi-cuenta/pedidos">Mis pedidos</PaymentCTA>
          </template>
          <PaymentCTA v-if="isPending" variant="secondary" icon="bi-arrow-clockwise" @click="load">Actualizar estado</PaymentCTA>
        </div>

        <!-- Legal footnote -->
        <PaymentFooter :reference-id="result.payment.uuid" class="mb-5" />

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useCartStore } from '@/store/cart';
import { useEnums } from '@/composables/useEnums';
import { usePaymentPolling } from '@/composables/usePaymentPolling';
import { mapPaymentStatus } from '@/utils/paymentStatus';
import PaymentHeader from '@/components/shared/checkout/PaymentHeader.vue';
import PaymentCard from '@/components/shared/checkout/PaymentCard.vue';
import PaymentRow from '@/components/shared/checkout/PaymentRow.vue';
import PaymentSectionLabel from '@/components/shared/checkout/PaymentSectionLabel.vue';
import PaymentAlert from '@/components/shared/checkout/PaymentAlert.vue';
import PaymentBadge from '@/components/shared/checkout/PaymentBadge.vue';
import PaymentTimeline from '@/components/shared/checkout/PaymentTimeline.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';
import PaymentFooter from '@/components/shared/checkout/PaymentFooter.vue';

const route     = useRoute();
const api       = useApi();
const cartStore = useCartStore();
const enums     = useEnums();

const loading    = ref(true);
const fetchError = ref(false);
const result     = ref(null);

// Polling mientras el pago esta PENDING (mismo patron que NequiPendingView.vue):
// el backend puede resolver el status real (via _sync_wompi_status) en cuanto se
// le consulta, pero la pantalla solo lo sabe si vuelve a preguntar.
// Mecanica del timer/timeout delegada a usePaymentPolling (ver
// PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 2, hallazgo 1).
const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS  = 120000;
const polling = usePaymentPolling({ intervalMs: POLL_INTERVAL_MS, timeoutMs: POLL_TIMEOUT_MS });
const pollTimedOut = polling.timedOut;

// COD flows
const isCodOrder   = ref(false);
const codOrderData = ref(null);
const isCodRenting = ref(false);
const rentalData   = ref(null);

// Status computed -- delegado a mapPaymentStatus (ver
// PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 13): mismo mapeo que ya
// existia inline (PENDING->pending, DECLINED/VOIDED/ERROR->declined,
// APPROVED->approved), ahora centralizado en la funcion pura compartida.
const mappedStatus = computed(() => mapPaymentStatus(result.value?.payment?.status, 'WOMPI'));
const isPaid = computed(() => mappedStatus.value === 'approved');
const isPending = computed(() => mappedStatus.value === 'pending');
const isDeclined = computed(() => mappedStatus.value === 'declined');

const statusVariant = computed(() => {
  if (isPaid.value)    return 'success';
  if (isPending.value) return 'warning';
  if (isDeclined.value) return 'danger';
  return 'secondary';
});

const statusIcon = computed(() => {
  if (isPaid.value)     return 'bi-check-lg';
  if (isPending.value)  return 'bi-hourglass-split';
  if (isDeclined.value) return 'bi-x-lg';
  return 'bi-question-lg';
});

const statusTitle = computed(() => {
  if (isPaid.value)     return 'Pago realizado correctamente';
  if (isPending.value)  return 'Pago en proceso';
  if (isDeclined.value) return 'Pago no completado';
  return 'Estado de pago';
});

const statusSubtitle = computed(() => {
  if (isPaid.value)     return 'Tu transaccion fue procesada y la orden ha sido confirmada';
  if (isPending.value)  return 'Estamos verificando tu pago — la orden continuara en proceso';
  if (isDeclined.value) return 'La transaccion fue rechazada — no se realizo ningun cargo';
  return '';
});

const statusBadgeClass = computed(() => {
  return enums.cssClass('payment-statuses', result.value?.payment?.status, 'bg-secondary text-white');
});

const statusBadgeLabel = computed(() => {
  return enums.label('payment-statuses', result.value?.payment?.status, result.value?.payment?.status || '');
});

// Helpers
function fmt(val) {
  return new Intl.NumberFormat('es-CO').format(Math.round(parseFloat(val) || 0));
}

function fmtDatetime(d) {
  if (!d) return '';
  return new Date(d).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fmtDate(d) {
  if (!d) return '';
  const [y, m, day] = d.split('-');
  return `${day}/${m}/${y}`;
}

function methodIcon(type) {
  return enums.icon('payment-methods', type, 'bi bi-wallet2 text-secondary');
}

function methodLabel(type) {
  return enums.label('payment-methods', type, type || 'Otro');
}

function orderStatusClass(s) {
  return enums.cssClass('order-statuses', s, 'bg-secondary-subtle text-secondary');
}

function orderStatusLabel(s) {
  return enums.label('order-statuses', s, s);
}

function priorityBadgeClass(p) {
  return enums.cssClass('service-priorities', p, 'bg-secondary-subtle text-secondary');
}

function priorityLabel(p) {
  return enums.label('service-priorities', p, p);
}

// next_steps[].variant llega del backend como clase Bootstrap cruda
// ("primary"/"outline-secondary", ver payment/online/api/views.py) -- se
// adapta al vocabulario primary/secondary de PaymentCTA sin tocar el backend.
function ctaVariant(v) {
  return v === 'primary' ? 'primary' : 'secondary';
}

// Carga principal
async function load() {
  loading.value    = true;
  fetchError.value = false;
  cartStore.reset();
  sessionStorage.removeItem('wompi_pending_tx');

  const q = route.query;

  // COD Renting
  if (q.status === 'RENTAL_COD_APPROVED' && q.rental_uuid) {
    try {
      const res = await api.get(`renting/rental-requests/${q.rental_uuid}/`);
      rentalData.value   = res.data;
      isCodRenting.value = true;
    } catch { fetchError.value = true; }
    loading.value = false;
    return;
  }

  // COD Order
  if (q.status === 'COD_APPROVED' && q.order_uuid) {
    try {
      const res = await api.get(`orders/orders/${q.order_uuid}/`);
      codOrderData.value = res.data;
      isCodOrder.value   = true;
    } catch { fetchError.value = true; }
    loading.value = false;
    return;
  }

  // Wompi transaction
  // ?tx  = our internal Transaction UUID (primary lookup key, always present)
  // ?id  = Wompi's own transaction ID (appended by a real redirect, or now also
  //        passed through by the widget callback) — used only as a hint so the
  //        backend can query Wompi's API even before the webhook has landed.
  const txWompiId = q.id || '';
  const txUuid    = q.tx || q.reference || '';

  if (!txWompiId && !txUuid) {
    fetchError.value = true;
    loading.value    = false;
    return;
  }

  const params = new URLSearchParams();
  if (txUuid) params.set('tx', txUuid);
  if (txWompiId) params.set('id', txWompiId);

  try {
    const res = await api.get(`payment/payments/confirmation/?${params.toString()}`);
    result.value = res.data;
  } catch {
    // Fallback al endpoint legacy usando nuestro UUID interno
    if (txUuid) {
      try {
        const legacy = await api.get(`payment/payments/transaction-status/?${params.toString()}`);
        result.value = _normalizeLegacy(legacy.data);
      } catch {
        fetchError.value = true;
      }
    } else {
      fetchError.value = true;
    }
  } finally {
    loading.value = false;
  }

  if (isPending.value) {
    startPolling(txUuid, txWompiId);
  } else {
    stopPolling();
  }
}

function startPolling(txUuid, txWompiId) {
  if (!txUuid) return;
  polling.start(async () => {
    try {
      const params = new URLSearchParams({ tx: txUuid });
      if (txWompiId) params.set('id', txWompiId);
      const res = await api.get(`payment/payments/transaction-status/?${params.toString()}`);
      if (res.data.tx_status && res.data.tx_status !== 'PENDING') {
        stopPolling();
        await load(); // refresca el payload completo con el estado final
      }
    } catch {
      // Sigue intentando hasta el timeout; un fallo puntual de red no detiene el polling.
    }
  });
}

function stopPolling() {
  polling.stop();
}

onUnmounted(stopPolling);

function _normalizeLegacy(d) {
  return {
    payment: {
      uuid:                d.transaction_uuid,
      wompi_id:            d.wompi_id,
      status:              d.tx_status,
      payment_method_type: null,
      amount_in_cents:     d.amount_in_cents,
      amount_cop:          String(d.amount_in_cents / 100),
      currency:            d.currency,
      created_at:          d.tx_created_at,
    },
    order: {
      uuid:            d.order?.uuid,
      status:          d.order?.status,
      total_amount:    d.order?.total_amount,
      tracking_number: d.order?.tracking_number,
      created_at:      d.order?.created_at,
      items:           d.order?.items || [],
    },
    customer:   { email: '', full_name: '' },
    shipping:   null,
    service:    d.order?.service_detail || null,
    timeline:   [],
    order_type: d.order?.service_detail ? 'service' : 'product',
    next_steps: [],
  };
}

onMounted(load);

onMounted(() => {
  enums.preload(['order-statuses', 'payment-methods', 'payment-statuses', 'service-priorities']);
});
</script>

<style scoped>
/* Root */
.pr-root { min-height: 100vh; background: #f5f7fa; }

/* Loading */
.pr-loading { display: flex; align-items: center; justify-content: center; min-height: 80vh; padding: 24px; }
.pr-loading-card { background: #fff; border-radius: 16px; padding: 40px 32px; text-align: center; max-width: 420px; width: 100%; box-shadow: 0 4px 20px rgba(0,0,0,.07); }
.pr-loading-icon { margin-bottom: 16px; }
.pr-loading-title { font-size: 1.15rem; font-weight: 700; color: #111; margin-bottom: 8px; }

/* Body */
.pr-body { padding: 40px 16px 80px; }

/* Actions */
.pr-actions { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
</style>
