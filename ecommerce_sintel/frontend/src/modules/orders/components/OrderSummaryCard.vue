<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-4 flex-column flex-lg-row gap-3">
        <div>
          <h6 class="mb-2">Resumen de Cliente</h6>
          <p class="mb-1"><span class="text-muted">Nombre:</span> {{ customerName }}</p>
          <p class="mb-1"><span class="text-muted">Email:</span> {{ order.user?.email || 'N/A' }}</p>
          <p class="mb-1"><span class="text-muted">Teléfono:</span> {{ order.user?.phone_number || order.shipping_address?.phone_number || 'N/A' }}</p>
        </div>
        <div>
          <h6 class="mb-2">Ubicación de envío</h6>
          <p class="mb-1">{{ order.shipping_address?.address_line_1 || 'N/D' }}</p>
          <p class="mb-1">{{ order.shipping_address?.city || 'N/D' }}, {{ order.shipping_address?.state || 'N/D' }}</p>
          <p class="mb-1">{{ order.shipping_address?.country || 'N/D' }}</p>
        </div>
      </div>

      <div class="row gy-3">
        <div class="col-sm-6 col-lg-4">
          <div class="small text-muted">Centro despacho</div>
          <div class="fw-semibold">{{ order.shipment?.dispatch_center || 'No asignado' }}</div>
        </div>
        <div class="col-sm-6 col-lg-4">
          <div class="small text-muted">Transportadora</div>
          <div class="fw-semibold">{{ order.shipment?.carrier || 'No asignada' }}</div>
        </div>
        <div class="col-sm-6 col-lg-4">
          <div class="small text-muted">Repartidor</div>
          <div class="fw-semibold">{{ order.shipment?.driver || 'No asignado' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({ order: { type: Object, required: true } });

const customerName = computed(() => {
  const user = props.order.user;
  if (!user) return 'Consumidor Final';
  return [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email || 'Consumidor Final';
});
</script>
