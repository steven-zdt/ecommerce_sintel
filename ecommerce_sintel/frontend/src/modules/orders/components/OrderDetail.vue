<template>
  <div class="order-detail">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <div class="mt-2 text-muted small">Cargando detalles de la orden...</div>
    </div>

    <div v-else-if="!order" class="text-center py-5 text-danger">
      Error al cargar la orden.
    </div>

    <div v-else>
      <!-- Cabecera Rápida -->
      <div class="d-flex justify-content-between align-items-center mb-4 p-3 bg-light rounded border">
        <div>
          <div class="text-muted smaller text-uppercase fw-bold">ID Orden</div>
          <div class="font-monospace">{{ order.uuid }}</div>
        </div>
        <div class="text-end">
          <span :class="['badge rounded-pill px-3 py-2', getStatusClass(order.status)]">
            {{ statusLabel(order.status) }}
          </span>
        </div>
      </div>

      <!-- Datos del Cliente -->
      <div class="mb-4">
        <h6 class="fw-bold border-bottom pb-2 mb-3">Información del Cliente</h6>
        <div class="row g-3">
          <div class="col-sm-6">
            <div class="text-muted smaller">Nombre</div>
            <div class="fw-bold">{{ order.user?.full_name || 'N/A' }}</div>
          </div>
          <div class="col-sm-6">
            <div class="text-muted smaller">Email</div>
            <div class="fw-bold">{{ order.user?.email || 'N/A' }}</div>
          </div>
        </div>
      </div>

      <!-- Items -->
      <div class="mb-4">
        <h6 class="fw-bold border-bottom pb-2 mb-3">Artículos</h6>
        <div class="table-responsive">
          <table class="table table-sm table-borderless align-middle">
            <thead class="text-muted smaller border-bottom">
              <tr>
                <th>Producto</th>
                <th class="text-center">Cant.</th>
                <th class="text-end">Unitario</th>
                <th class="text-end">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in order.items" :key="item.id" class="border-bottom-dashed">
                <td class="py-2">
                  <div class="fw-bold small">{{ item.name_snapshot }}</div>
                  <div class="text-muted smaller">SKU: {{ item.sku_snapshot }}</div>
                </td>
                <td class="text-center small">{{ item.quantity }}</td>
                <td class="text-end small">${{ formatNumber(item.price_snapshot) }}</td>
                <td class="text-end fw-bold small">${{ formatNumber(item.subtotal) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="3" class="text-end pt-3 text-muted">Total de la Orden</td>
                <td class="text-end pt-3 h5 fw-bold text-primary">${{ formatNumber(order.total_amount) }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- Dirección (si existe) -->
      <div v-if="order.shipping_address" class="mb-4">
        <h6 class="fw-bold border-bottom pb-2 mb-3">Envío</h6>
        <div class="p-3 bg-light-subtle border rounded small">
          {{ order.shipping_address }}
        </div>
      </div>

      <div class="mt-4 pt-3 border-top d-grid gap-2">
        <router-link :to="`/panel/ordenes/${order.uuid}`" class="btn btn-outline-primary">
          <i class="bi bi-box-arrow-up-right me-1"></i> Ver en Detalle Completo
        </router-link>
        <button class="btn btn-light" @click="$emit('close')">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useEnums } from '@/composables/useEnums';

const props = defineProps({
  item: { type: Object, required: true }
});
defineEmits(['close']);

const api = useApi();
const enums = useEnums();
const loading = ref(true);
const order = ref(null);

const fetchOrder = async () => {
  loading.value = true;
  try {
    const response = await api.get(`orders/orders/${props.item.uuid}/`);
    order.value = response.data;
  } catch (err) {
    console.error("Error al cargar orden:", err);
  } finally {
    loading.value = false;
  }
};

const formatNumber = (num) => new Intl.NumberFormat('es-CO').format(num);

const getStatusClass = (status) => enums.cssClass('order-statuses', status, 'bg-secondary-subtle text-secondary');
const statusLabel    = (status) => enums.label('order-statuses', status, status);

onMounted(() => {
  enums.ensure('order-statuses');
  fetchOrder();
});
</script>

<style scoped>
.border-bottom-dashed { border-bottom: 1px dashed #e2e8f0; }
.smaller { font-size: 0.75rem; }
</style>
