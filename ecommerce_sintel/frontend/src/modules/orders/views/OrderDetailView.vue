<template>
  <div class="orders-detail-view">
    <div v-if="state.loadingOrder" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <div class="mt-3 text-muted">Cargando orden...</div>
    </div>

    <div v-else-if="state.error" class="alert alert-danger">
      No se pudo cargar la orden. Verifique la conexión o intente nuevamente.
    </div>

    <div v-else-if="!state.order" class="text-center py-5 text-muted">
      Orden no encontrada.
    </div>

    <div v-else>
      <OrderHeader :order="state.order" />

      <div class="row g-4">
        <div class="col-lg-8">
          <OrderTimeline :timeline="state.timeline" />
          <OrderProductsTable :items="state.order.items" />
          <OrderNotes :order="state.order" />
          <OrderHistory :order="state.order" />
        </div>

        <div class="col-lg-4">
          <OrderSummaryCard :order="state.order" />
          <OrderAssignmentPanel :order="state.order" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useOrderStore } from '@/store/orders/orderStore';
import OrderHeader from '../components/OrderHeader.vue';
import OrderSummaryCard from '../components/OrderSummaryCard.vue';
import OrderTimeline from '../components/OrderTimeline.vue';
import OrderProductsTable from '../components/OrderProductsTable.vue';
import OrderAssignmentPanel from '../components/OrderAssignmentPanel.vue';
import OrderNotes from '../components/OrderNotes.vue';
import OrderHistory from '../components/OrderHistory.vue';

const route = useRoute();
const orderStore = useOrderStore();
const orderUuid = route.params.uuid;

const loadOrder = async () => {
  if (!orderUuid) return;
  await orderStore.loadOrder(orderUuid);
  await orderStore.loadTimeline(orderUuid);
};

onMounted(loadOrder);

const state = {
  get order() {
    return orderStore.order;
  },
  get timeline() {
    return orderStore.timeline;
  },
  get loadingOrder() {
    return orderStore.loadingOrder;
  },
  get error() {
    return orderStore.error;
  },
};
</script>

<style scoped>
.orders-detail-view {
  padding: 1rem 0;
}
</style>
