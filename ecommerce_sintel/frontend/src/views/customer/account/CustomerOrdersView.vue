<template>
  <CustomerAccountShell max-width="900px">
    <CustomerPageHeader title="Mis pedidos" subtitle="Consulta el estado y el historial de todas tus compras." />

    <CustomerSkeleton v-if="loading" :count="3" height="150px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchOrders" />

    <CustomerEmptyState
      v-else-if="orders.length === 0"
      icon="bi-bag"
      title="Aun no tienes pedidos"
      description="Explora nuestra tienda y realiza tu primera compra."
    >
      <template #action>
        <RouterLink to="/tienda" class="btn btn-primary">Ir a la tienda</RouterLink>
      </template>
    </CustomerEmptyState>

    <template v-else>
      <div class="orders-list">
        <CustomerCard v-for="order in orders" :key="order.id || order.uuid">
          <div class="order-row">
            <div class="order-main">
              <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                <span class="fw-semibold small">#{{ order.id || order.order_number }}</span>
                <CustomerStatusBadge enum-name="order-statuses" :value="order.status" />
                <span class="text-muted small">{{ fmtDate(order.created_at) }}</span>
              </div>
              <p class="text-muted small mb-1">
                {{ order.items_count || (order.items?.length ?? '?') }} articulo(s)
                <span v-if="order.payment_method"> &middot; {{ order.payment_method }}</span>
              </p>
              <div v-if="order.shipping_address" class="text-muted small">
                <i class="bi bi-geo-alt me-1"></i>
                {{ order.shipping_address.city || order.shipping_address.address_line1 }}
              </div>
            </div>
            <div class="order-side">
              <p class="fw-bold mb-1">${{ fmt(order.total_amount) }}</p>
              <CustomerButton variant="secondary" @click="viewOrder(order)">
                <i class="bi bi-eye me-1"></i>Ver detalle
              </CustomerButton>
            </div>
          </div>

          <div v-if="order.items?.length" class="order-items-preview">
            <div v-for="item in order.items.slice(0, 3)" :key="item.uuid" class="order-item-row">
              <span class="small text-secondary">{{ item.item_name }}</span>
              <span class="small fw-semibold">${{ fmt(parseFloat(item.price) * item.quantity) }}</span>
            </div>
            <div v-if="order.items.length > 3" class="small text-muted mt-1">
              +{{ order.items.length - 3 }} articulo(s) mas
            </div>
          </div>
        </CustomerCard>
      </div>

      <CustomerPagination :page="page" :total-pages="totalPages" @update:page="changePage" />
    </template>

    <!-- Detalle de pedido -->
    <CustomerOverlayPanel v-model="showDetail" :title="`Pedido #${selected?.id || selected?.order_number || ''}`">
      <template v-if="selected">
        <div class="row g-2 mb-4">
          <div class="col-6">
            <p class="text-muted small mb-0">Estado</p>
            <CustomerStatusBadge enum-name="order-statuses" :value="selected.status" />
          </div>
          <div class="col-6">
            <p class="text-muted small mb-0">Total</p>
            <p class="fw-bold mb-0">${{ fmt(selected.total_amount) }}</p>
          </div>
          <div class="col-6">
            <p class="text-muted small mb-0">Fecha</p>
            <p class="small mb-0">{{ fmtDate(selected.created_at) }}</p>
          </div>
          <div v-if="selected.payment_method" class="col-6">
            <p class="text-muted small mb-0">Metodo de pago</p>
            <p class="small mb-0">{{ selected.payment_method }}</p>
          </div>
        </div>

        <div v-if="selected.items?.length" class="mb-3">
          <p class="text-muted small fw-semibold mb-2">Articulos</p>
          <div v-for="item in selected.items" :key="item.uuid" class="modal-item-row">
            <div>
              <p class="small fw-semibold mb-0">{{ item.item_name }}</p>
              <p class="text-muted small mb-0">Cant: {{ item.quantity }}</p>
            </div>
            <p class="small fw-bold mb-0">${{ fmt(parseFloat(item.price) * item.quantity) }}</p>
          </div>
        </div>

        <div v-if="selected.shipping_address" class="mb-3">
          <p class="text-muted small fw-semibold mb-1">Direccion de envio</p>
          <p class="small mb-0">
            {{ selected.shipping_address.full_name }}<br>
            {{ selected.shipping_address.address_line_1 }}, {{ selected.shipping_address.city }}
          </p>
        </div>
        <div v-else-if="selected.service_detail" class="mb-3">
          <p class="text-muted small fw-semibold mb-1">Direccion del servicio</p>
          <p class="small mb-0">{{ selected.service_detail.address }}</p>
          <span class="badge bg-warning-subtle text-warning border small mt-1">
            Servicio tecnico - {{ selected.service_detail.priority }}
          </span>
        </div>

        <div class="order-timeline mt-3">
          <p class="text-muted small fw-semibold mb-3">Seguimiento del pedido</p>

          <ServiceTimeline v-if="selected.service_detail" :order="selected" />
          <template v-else-if="selected.shipment">
            <ShipmentTimeline :shipment="selected.shipment" />
            <CustomerButton
              v-if="selected.shipment.status === 'delivered' && !selected.shipment.customer_confirmed_at"
              variant="primary"
              class="mt-3"
              :loading="confirmingDelivery"
              @click="confirmDelivery"
            >
              <i class="bi bi-check2-circle me-1"></i>Confirmar que recibi mi pedido
            </CustomerButton>
            <p v-else-if="selected.shipment.customer_confirmed_at" class="text-success small mt-3 mb-0">
              <i class="bi bi-patch-check-fill me-1"></i>Confirmaste la recepcion de este pedido.
            </p>
          </template>

          <StatusTimeline
            v-else
            mode="steps"
            :steps="orderSteps"
            :active-index="activeStepIndex(selected.status)"
            :cancelled="selected.status === 'cancelled'"
          />
        </div>

        <CustomerButton variant="secondary" class="w-100 mt-4" @click="askForHelp(selected)">
          <i class="bi bi-headset me-1"></i>Necesitas ayuda con este pedido?
        </CustomerButton>
      </template>
    </CustomerOverlayPanel>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { ordersService } from '@/services/orders/ordersService';
import { formatCOP } from '@/utils/money';
import { useSupportContextStore } from '@/store/supportContext';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useEnums } from '@/composables/useEnums';
import ServiceTimeline from '@/components/customer/services/ServiceTimeline.vue';
import ShipmentTimeline from '@/components/customer/orders/ShipmentTimeline.vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerStatusBadge from '@/components/customer/account/CustomerStatusBadge.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';
import CustomerOverlayPanel from '@/components/customer/account/CustomerOverlayPanel.vue';
import CustomerPagination from '@/components/customer/account/CustomerPagination.vue';

const orderSteps = [
  { key: 'pending', label: 'Pedido recibido', icon: 'bi-receipt' },
  { key: 'processing', label: 'En proceso', icon: 'bi-hourglass-split' },
  { key: 'paid', label: 'Pago confirmado', icon: 'bi-credit-card' },
  { key: 'shipped', label: 'Enviado', icon: 'bi-truck' },
  { key: 'delivered', label: 'Entregado', icon: 'bi-check2-circle' },
];

const stepOrder = orderSteps.map(s => s.key);

function activeStepIndex(status) {
  if (status === 'cancelled') return stepOrder.indexOf('processing');
  const idx = stepOrder.indexOf(status);
  return idx === -1 ? 0 : idx;
}

const toast = useToast();
const { handleError } = useErrorHandler();
const enums = useEnums();
const supportContextStore = useSupportContextStore();

const loading = ref(true);
const loadError = ref(false);
const orders = ref([]);
const page = ref(1);
const totalPages = ref(1);
const pageSize = 10;
const selected = ref(null);
const showDetail = ref(false);
const confirmingDelivery = ref(false);

function askForHelp(order) {
  supportContextStore.requestHelp('ORDER', order.uuid);
  showDetail.value = false;
}

async function fetchOrders() {
  loading.value = true;
  loadError.value = false;
  try {
    const data = await ordersService.list({ page: page.value, page_size: pageSize });
    orders.value = data.results || data || [];
    const total = data.count || orders.value.length;
    totalPages.value = Math.max(1, Math.ceil(total / pageSize));
  } catch {
    loadError.value = true;
    toast.error('Error al cargar pedidos');
  } finally {
    loading.value = false;
  }
}

function changePage(p) {
  if (p < 1 || p > totalPages.value) return;
  page.value = p;
  fetchOrders();
}

async function viewOrder(order) {
  selected.value = order;
  showDetail.value = true;
  if (!order.service_detail && !order.shipping_address) {
    try {
      const data = await ordersService.serviceOrderDetail(order.uuid);
      selected.value = { ...order, ...data };
    } catch {
      // No es una orden de servicio o no accesible -- usar datos disponibles
    }
  }
}

async function confirmDelivery() {
  confirmingDelivery.value = true;
  try {
    const data = await ordersService.confirmDelivery(selected.value.uuid);
    selected.value = { ...selected.value, ...data };
    toast.success('Gracias por confirmar la recepcion de tu pedido.');
  } catch (e) {
    handleError(e, 'No fue posible confirmar la recepcion.');
  } finally {
    confirmingDelivery.value = false;
  }
}

const fmt = (val) => formatCOP(val);
const fmtDate = (d) => d ? new Date(d).toLocaleString('es-CO') : '-';

onMounted(() => {
  enums.ensure('order-statuses');
  fetchOrders();
});
</script>

<style scoped>
.orders-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.order-main { flex: 1; min-width: 200px; }
.order-side { text-align: right; }

.order-items-preview {
  border-top: 1px solid #f3f4f6;
  padding-top: 12px;
  margin-top: 12px;
}

.order-item-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}

.modal-item-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}
.modal-item-row:last-child { border-bottom: none; }

.order-timeline { border-top: 1px solid #f3f4f6; padding-top: 16px; }
</style>
