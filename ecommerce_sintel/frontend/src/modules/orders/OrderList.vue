<template>
  <div class="orders-module">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Gestión de Órdenes</h4>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>UUID Orden</th>
              <th>Cliente</th>
              <th>Fecha</th>
              <th>Total</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="text-center py-5">
                <div class="spinner-border text-primary spinner-border-sm me-2" role="status"></div>
                Cargando órdenes...
              </td>
            </tr>
            <tr v-else-if="orders.length === 0">
              <td colspan="6" class="text-center py-5 text-muted">No hay órdenes registradas.</td>
            </tr>
            <tr v-for="order in orders" :key="order.uuid">
              <td class="fw-bold text-primary font-monospace smaller">#{{ order.uuid?.slice(0, 8) }}</td>
              <td>
                <div class="fw-bold smaller text-dark">{{ order.user?.full_name || 'Consumidor Final' }}</div>
                <div class="text-muted smaller">{{ order.user?.email || 'N/A' }}</div>
              </td>
              <td class="smaller">{{ formatDate(order.created_at) }}</td>
              <td class="fw-bold text-primary">${{ formatNumber(order.total_amount) }}</td>
              <td>
                <span :class="['badge rounded-pill', getStatusClass(order.status)]">
                  {{ statusLabel(order.status) }}
                </span>
              </td>
              <td class="text-end">
                <router-link
                  :to="{ name: 'order-detail', params: { uuid: order.uuid } }"
                  class="btn btn-sm btn-light border shadow-sm"
                >
                  <i class="bi bi-eye text-primary"></i>
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useEnums } from '@/composables/useEnums';

const api = useApi();
const enums = useEnums();

const loading = ref(true);
const orders = ref([]);

const fetchOrders = async () => {
  loading.value = true;
  try {
    const response = await api.get('orders/orders/');
    orders.value = response.data.results || response.data;
  } catch (err) {
    console.error("Error al cargar órdenes:", err);
  } finally {
    loading.value = false;
  }
};

const formatNumber = (num) => new Intl.NumberFormat('es-CO').format(num);
const formatDate = (d) => new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

const getStatusClass = (status) => enums.cssClass('order-statuses', status, 'bg-secondary-subtle text-secondary');
const statusLabel    = (status) => enums.label('order-statuses', status, status);

onMounted(() => {
  enums.ensure('order-statuses');
  fetchOrders();
});
</script>

<style scoped>
.smaller { font-size: 0.85rem; }
</style>
