<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex flex-column flex-md-row justify-content-between gap-3 align-items-start">
        <div>
          <div class="text-uppercase text-muted small mb-1">Orden</div>
          <h2 class="h5 mb-1">#{{ order.uuid?.slice(0, 8) }}</h2>
          <div class="small text-muted">{{ order.uuid }}</div>
        </div>

        <div class="text-md-end">
          <span :class="['badge rounded-pill px-3 py-2', statusClass]">{{ statusLabel }}</span>
          <div class="mt-2">{{ order.payment_method || 'Método no definido' }}</div>
        </div>
      </div>

      <div class="row mt-4 gy-2 gy-md-0">
        <div class="col-md-2 col-6">
          <div class="text-muted small">Cliente</div>
          <div class="fw-semibold">{{ customerName }}</div>
        </div>
        <div class="col-md-2 col-6">
          <div class="text-muted small">Fecha</div>
          <div>{{ formattedDate }}</div>
        </div>
        <div class="col-md-2 col-6">
          <div class="text-muted small">Estado pago</div>
          <div>{{ paymentStatus }}</div>
        </div>
        <div class="col-md-2 col-6">
          <div class="text-muted small">Monto</div>
          <div class="fw-semibold text-primary">${{ formatCurrency(order.total_amount) }}</div>
        </div>
      </div>

      <div class="mt-4 d-flex flex-wrap gap-2">
        <button class="btn btn-primary btn-sm">Actualizar</button>
        <button class="btn btn-outline-secondary btn-sm">Editar</button>
        <button class="btn btn-outline-danger btn-sm">Cancelar</button>
        <button class="btn btn-outline-dark btn-sm">Imprimir</button>
        <button class="btn btn-outline-success btn-sm">Factura</button>
        <button class="btn btn-outline-secondary btn-sm">Más acciones</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useEnums } from '@/composables/useEnums';

const props = defineProps({
  order: { type: Object, required: true }
});

const enums = useEnums();
enums.ensure('order-statuses');

const customerName = computed(() => {
  const user = props.order.user;
  if (!user) return 'Consumidor Final';
  return [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email || 'Consumidor Final';
});

const formattedDate = computed(() => {
  if (!props.order.created_at) return 'N/D';
  return new Date(props.order.created_at).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
});

const statusLabel = computed(() => enums.label('order-statuses', props.order.status, props.order.status || 'Sin estado'));
const statusClass = computed(() => enums.cssClass('order-statuses', props.order.status, 'bg-secondary-subtle text-secondary'));
const paymentStatus = computed(() => (props.order.payment_method ? props.order.payment_method : 'Sin método'));
const formatCurrency = (value) => new Intl.NumberFormat('es-CO', { minimumFractionDigits: 0 }).format(value || 0);
</script>
