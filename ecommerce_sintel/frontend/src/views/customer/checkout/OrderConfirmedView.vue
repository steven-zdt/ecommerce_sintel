<template>
  <div class="order-confirmed-page">

    <!-- Loading -->
    <div v-if="loading" class="text-center py-5 mt-5">
      <div class="spinner-border text-primary mb-3" style="width:3rem;height:3rem"></div>
      <p class="text-muted">Verificando tu pedido...</p>
    </div>

    <div v-else class="container py-5" style="max-width:680px">

      <!-- ── RENTAL COD CONFIRMADO ── -->
      <template v-if="isRentalCodApproved">
        <div class="text-center mb-4">
          <div class="status-icon status-ok mx-auto mb-3">
            <i class="bi bi-check-lg fs-2 text-white"></i>
          </div>
          <h1 class="h3 fw-bold mb-1">Reserva confirmada</h1>
          <p class="text-muted mb-0">Tu equipo ha sido reservado exitosamente.</p>
        </div>

        <div class="detail-card mb-4">
          <div class="detail-header">
            <span class="fw-semibold">Detalle del alquiler</span>
            <span class="badge bg-warning-subtle text-warning border border-warning-subtle">Contra entrega</span>
          </div>
          <div class="detail-row">
            <span class="text-muted small">Referencia</span>
            <code class="small">{{ rentalRequest?.uuid }}</code>
          </div>
          <div v-if="rentalRequest?.equipment_variant?.equipment_name" class="detail-row">
            <span class="text-muted small">Equipo</span>
            <span class="small fw-semibold">{{ rentalRequest.equipment_variant.equipment_name }}</span>
          </div>
          <div v-if="rentalRequest?.start_date" class="detail-row">
            <span class="text-muted small">Periodo</span>
            <span class="small">{{ rentalRequest.start_date }} &mdash; {{ rentalRequest.end_date }}</span>
          </div>
          <div class="detail-row">
            <span class="text-muted small">Total a pagar</span>
            <span class="fw-bold fs-6">${{ fmt(rentalRequest?.grand_total) }} COP</span>
          </div>
        </div>

        <div class="alert alert-warning d-flex align-items-start gap-3 mb-4">
          <i class="bi bi-cash-stack fs-5 flex-shrink-0 mt-1 text-warning"></i>
          <div>
            <strong>Pago contra entrega</strong>
            <p class="mb-0 small mt-1">
              Pagaras <strong>${{ fmt(rentalRequest?.grand_total) }} COP</strong>
              al momento de recibir o recoger el equipo.
            </p>
          </div>
        </div>

        <div class="d-flex flex-column flex-sm-row gap-2 justify-content-center">
          <RouterLink to="/mi-cuenta/pedidos" class="btn btn-primary px-4">
            <i class="bi bi-bag me-2"></i>Ver mis solicitudes
          </RouterLink>
          <RouterLink to="/alquiler" class="btn btn-outline-secondary px-4">Ver mas equipos</RouterLink>
        </div>
      </template>

      <!-- ── COD CONFIRMADO ── -->
      <template v-else-if="isCodApproved">
        <div class="text-center mb-4">
          <div class="status-icon status-ok mx-auto mb-3">
            <i class="bi bi-check-lg fs-2 text-white"></i>
          </div>
          <h1 class="h3 fw-bold mb-1">Orden confirmada</h1>
          <p class="text-muted mb-0">Tu pedido ha sido registrado exitosamente.</p>
        </div>

        <div class="detail-card mb-4">
          <div class="detail-header">
            <span class="fw-semibold">Resumen del pedido</span>
            <span class="badge bg-warning-subtle text-warning border border-warning-subtle">Contra entrega</span>
          </div>
          <div class="detail-row">
            <span class="text-muted small">N. de orden</span>
            <code class="small">{{ codOrder?.uuid }}</code>
          </div>
          <div class="detail-row">
            <span class="text-muted small">Total a pagar</span>
            <span class="fw-bold fs-6">${{ fmt(codOrder?.total_amount) }} COP</span>
          </div>
          <div v-if="codOrder?.shipping_address" class="detail-row align-items-start">
            <span class="text-muted small">Entrega en</span>
            <span class="small text-end" style="max-width:60%">
              {{ codOrder.shipping_address.address_line_1 }},
              {{ codOrder.shipping_address.city }}
            </span>
          </div>
          <!-- Items -->
          <div v-if="codOrder?.items?.length" class="border-top mt-1">
            <div v-for="item in codOrder.items" :key="item.sku" class="detail-row">
              <div>
                <div class="small fw-semibold">{{ item.item_name }}</div>
                <div class="text-muted" style="font-size:.78rem">SKU: {{ item.sku }} · x{{ item.quantity }}</div>
              </div>
              <span class="small fw-semibold">${{ fmt(parseFloat(item.price) * item.quantity) }}</span>
            </div>
          </div>
        </div>

        <!-- Banner informativo COD -->
        <div class="alert alert-warning d-flex align-items-start gap-3 mb-4">
          <i class="bi bi-truck fs-5 flex-shrink-0 mt-1 text-warning"></i>
          <div>
            <strong>Pago contra entrega</strong>
            <p class="mb-0 small mt-1">
              Prepararemos tu envio de inmediato. Pagaras
              <strong>${{ fmt(codOrder?.total_amount) }} COP</strong>
              al momento de recibir tus productos.
            </p>
          </div>
        </div>

        <div class="d-flex flex-column flex-sm-row gap-2 justify-content-center">
          <RouterLink to="/mi-cuenta/pedidos" class="btn btn-primary px-4">
            <i class="bi bi-bag me-2"></i>Ver mis pedidos
          </RouterLink>
          <RouterLink to="/tienda" class="btn btn-outline-secondary px-4">Ir a la tienda</RouterLink>
        </div>
      </template>

      <!-- ── WOMPI APROBADO ── -->
      <template v-else-if="isApproved">
        <div class="text-center mb-4">
          <div class="status-icon status-ok mx-auto mb-3">
            <i class="bi bi-check-lg fs-2 text-white"></i>
          </div>
          <h1 class="h3 fw-bold mb-1">Pago aprobado</h1>
          <p class="text-muted mb-0">Tu transaccion fue procesada exitosamente.</p>
        </div>

        <!-- Detalle solo cuando la API devolvio datos (guard contra data=null) -->
        <div v-if="data && data.order" class="detail-card mb-4">
          <div class="detail-header">
            <span class="fw-semibold">Resumen de la compra</span>
            <span class="badge" :class="approvedBadgeClass">{{ approvedBadgeLabel }}</span>
          </div>
          <div class="detail-row">
            <span class="text-muted small">N. de orden</span>
            <code class="small">{{ data.order.uuid }}</code>
          </div>
          <div v-if="data.wompi_id" class="detail-row">
            <span class="text-muted small">Referencia Wompi</span>
            <code class="small">{{ data.wompi_id }}</code>
          </div>
          <div class="detail-row">
            <span class="text-muted small">Total pagado</span>
            <span class="fw-bold text-success fs-6">${{ fmt(data.order.total_amount) }} COP</span>
          </div>
          <div class="detail-row">
            <span class="text-muted small">Fecha</span>
            <span class="small">{{ fmtDate(data.order.created_at) }}</span>
          </div>

          <div v-if="data.order.items?.length" class="border-top mt-1">
            <div v-for="item in data.order.items" :key="item.sku" class="detail-row">
              <div>
                <div class="small fw-semibold">{{ item.item_name }}</div>
                <div class="text-muted" style="font-size:.78rem">SKU: {{ item.sku }} · x{{ item.quantity }}</div>
              </div>
              <span class="small fw-semibold">${{ fmt(parseFloat(item.price) * item.quantity) }}</span>
            </div>
          </div>

          <div v-if="data.order.service_detail" class="border-top mt-1">
            <div class="detail-row align-items-start">
              <span class="text-muted small">Direccion</span>
              <span class="small text-end" style="max-width:55%">{{ data.order.service_detail.address }}</span>
            </div>
            <div v-if="data.order.service_detail.scheduled_at" class="detail-row">
              <span class="text-muted small">Fecha preferida</span>
              <span class="small">{{ fmtDate(data.order.service_detail.scheduled_at) }}</span>
            </div>
            <div class="detail-row">
              <span class="text-muted small">Prioridad</span>
              <span class="badge small" :class="servicePriorityClass(data.order.service_detail.priority)">
                {{ servicePriorityLabel(data.order.service_detail.priority) }}
              </span>
            </div>
            <div v-if="data.order.service_detail.contact_person" class="detail-row align-items-start">
              <span class="text-muted small">Encargado</span>
              <span class="small text-end">
                {{ data.order.service_detail.contact_person.full_name }}<br>
                <span class="text-muted" style="font-size:.78rem">{{ data.order.service_detail.contact_person.phone }}</span>
              </span>
            </div>
          </div>
        </div>

        <div class="d-flex flex-column flex-sm-row gap-2 justify-content-center">
          <RouterLink to="/mi-cuenta/pedidos" class="btn btn-primary px-4">
            <i class="bi bi-bag me-2"></i>Ver mis pedidos
          </RouterLink>
          <RouterLink to="/tienda" class="btn btn-outline-secondary px-4">
            <i class="bi bi-shop me-1"></i>Ir a la tienda
          </RouterLink>
        </div>
      </template>

      <!-- ── PENDIENTE (aun procesando Wompi) ── -->
      <template v-else-if="isPending">
        <div class="text-center mb-4">
          <div class="status-icon status-pending mx-auto mb-3">
            <i class="bi bi-hourglass-split fs-3 text-white"></i>
          </div>
          <h1 class="h3 fw-bold mb-1">Procesando tu pago</h1>
          <p class="text-muted mb-1">Tu transaccion esta siendo verificada por Wompi.</p>
          <p class="text-muted small">Esto puede tomar unos minutos. Recibiras una confirmacion en tu correo.</p>
        </div>
        <div v-if="data?.order" class="detail-card mb-4">
          <div class="detail-row">
            <span class="text-muted small">N. de orden</span>
            <code class="small">{{ data.order.uuid }}</code>
          </div>
          <div class="detail-row">
            <span class="text-muted small">Total</span>
            <span class="fw-bold">${{ fmt(data.order.total_amount) }} COP</span>
          </div>
        </div>
        <div class="d-flex flex-column flex-sm-row gap-2 justify-content-center flex-wrap">
          <RouterLink to="/mi-cuenta/pedidos" class="btn btn-primary px-4">
            <i class="bi bi-bag me-2"></i>Ver mis pedidos
          </RouterLink>
          <button class="btn btn-outline-secondary px-4" @click="retryFetch">
            <i class="bi bi-arrow-clockwise me-1"></i>Actualizar estado
          </button>
          <RouterLink to="/tienda" class="btn btn-outline-secondary px-4">
            <i class="bi bi-shop me-1"></i>Ir a la tienda
          </RouterLink>
        </div>
      </template>

      <!-- ── RECHAZADO / ERROR Wompi ── -->
      <template v-else>
        <div class="text-center mb-4">
          <div class="status-icon status-fail mx-auto mb-3">
            <i class="bi bi-x-lg fs-2 text-white"></i>
          </div>
          <h1 class="h3 fw-bold mb-1">Pago no completado</h1>
          <p class="text-muted mb-1">La transaccion fue {{ statusLabel }}.</p>
          <p class="text-muted small">Puedes intentar de nuevo con otro metodo de pago o volver a la tienda.</p>
        </div>
        <div v-if="txUuid && wompiStatus && wompiStatus !== 'PENDING'" class="detail-card mb-4">
          <div class="detail-row">
            <span class="text-muted small">Estado Wompi</span>
            <span class="badge bg-danger-subtle text-danger border border-danger-subtle small">{{ wompiStatus }}</span>
          </div>
        </div>
        <div class="d-flex flex-column flex-sm-row gap-2 justify-content-center flex-wrap">
          <RouterLink to="/tienda" class="btn btn-primary px-4">
            <i class="bi bi-shop me-2"></i>Ir a la tienda
          </RouterLink>
          <RouterLink to="/checkout" class="btn btn-outline-primary px-4">
            <i class="bi bi-arrow-clockwise me-2"></i>Volver al checkout
          </RouterLink>
          <RouterLink to="/mi-cuenta/pedidos" class="btn btn-outline-secondary px-4">
            <i class="bi bi-bag me-1"></i>Mis pedidos
          </RouterLink>
        </div>
      </template>

      <!-- Error de carga -->
      <div v-if="fetchError" class="alert alert-warning mt-4 small text-center">
        <i class="bi bi-exclamation-triangle me-2"></i>
        No se pudo cargar el detalle de la orden.
        <button class="btn btn-link btn-sm p-0 ms-1" @click="retryFetch">Reintentar</button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useCartStore } from '@/store/cart';
import { useAuthStore } from '@/store/auth';
import { useEnums } from '@/composables/useEnums';

const api       = useApi();
const route     = useRoute();
const cartStore = useCartStore();
const authStore = useAuthStore();
const enums     = useEnums();

const loading            = ref(true);
const data               = ref(null);
const fetchError         = ref(false);
const isCodApproved      = ref(false);
const codOrder           = ref(null);
const isRentalCodApproved = ref(false);
const rentalRequest      = ref(null);

const txUuid      = computed(() => route.query.tx || route.query.reference || '');
const wompiStatus = computed(() => (route.query.status || '').toUpperCase());

const isApproved = computed(() => {
  const s = data.value?.tx_status || wompiStatus.value;
  return s === 'APPROVED';
});
const isPending = computed(() => {
  if (isCodApproved.value || isRentalCodApproved.value) return false;
  const s = data.value?.tx_status || wompiStatus.value;
  return !s || s === 'PENDING';
});
const statusLabel = computed(() => {
  const raw = data.value?.tx_status || wompiStatus.value;
  const label = enums.label('payment-statuses', raw, 'No procesada');
  return String(label || 'No procesada').toLowerCase();
});

const approvedBadgeClass = computed(() => enums.cssClass('payment-statuses', 'APPROVED', 'bg-success-subtle text-success border border-success-subtle'));
const approvedBadgeLabel = computed(() => enums.label('payment-statuses', 'APPROVED', 'Aprobado'));

function servicePriorityClass(priority) {
  return enums.cssClass('service-priorities', priority, 'bg-warning-subtle text-warning border border-warning-subtle');
}

function servicePriorityLabel(priority) {
  return enums.label('service-priorities', priority, priority || 'Sin prioridad');
}

const fmt     = (val) => new Intl.NumberFormat('es-CO').format(Math.round(parseFloat(val) || 0));
const fmtDate = (d)   => d ? new Date(d).toLocaleString('es-CO', {
  year: 'numeric', month: 'short', day: 'numeric',
  hour: '2-digit', minute: '2-digit',
}) : '';

async function fetchCodOrder(orderUuid) {
  fetchError.value = false;
  try {
    const res = await api.get(`orders/orders/${orderUuid}/`);
    codOrder.value      = res.data;
    isCodApproved.value = true;
  } catch {
    fetchError.value = true;
  } finally {
    loading.value = false;
  }
}

async function fetchRentalRequest(rentalUuid) {
  fetchError.value = false;
  try {
    const res = await api.get(`renting/rental-requests/${rentalUuid}/`);
    rentalRequest.value       = res.data;
    isRentalCodApproved.value = true;
  } catch {
    fetchError.value = true;
  } finally {
    loading.value = false;
  }
}

async function fetchStatus() {
  if (!txUuid.value || !authStore.isAuthenticated) {
    loading.value = false;
    return;
  }
  fetchError.value = false;
  try {
    const res = await api.get(`payment/payments/transaction-status/?tx=${txUuid.value}`);
    data.value = res.data;
  } catch {
    fetchError.value = true;
  } finally {
    loading.value = false;
  }
}

function retryFetch() {
  loading.value = true;
  fetchStatus();
}

onMounted(() => {
  cartStore.reset();
  enums.preload(['payment-statuses', 'service-priorities']);

  if (route.query.status === 'RENTAL_COD_APPROVED' && route.query.rental_uuid) {
    fetchRentalRequest(route.query.rental_uuid);
  } else if (route.query.status === 'COD_APPROVED' && route.query.order_uuid) {
    fetchCodOrder(route.query.order_uuid);
  } else {
    fetchStatus();
  }
});
</script>

<style scoped>
.order-confirmed-page { min-height: 100vh; background: #f9fafb; }

.status-icon {
  width: 80px; height: 80px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.status-ok      { background: linear-gradient(135deg, #16a34a, #22c55e); box-shadow: 0 8px 24px rgba(22,163,74,.3); }
.status-pending { background: linear-gradient(135deg, #d97706, #f59e0b); box-shadow: 0 8px 24px rgba(217,119,6,.3); }
.status-fail    { background: linear-gradient(135deg, #dc2626, #ef4444); box-shadow: 0 8px 24px rgba(220,38,38,.3); }

.detail-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 18px;
  border-bottom: 1px solid #f3f4f6;
  gap: 12px;
}
.detail-row:last-child { border-bottom: none; }
</style>
