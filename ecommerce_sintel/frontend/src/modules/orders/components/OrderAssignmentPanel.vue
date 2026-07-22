<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h6 class="mb-0">Asignaciones</h6>
          <p class="small text-muted mb-0">Gestión rápida de logística.</p>
        </div>
      </div>

      <div class="mb-3">
        <div class="small text-muted mb-1">Centro de despacho</div>
        <div class="fw-semibold">{{ order.shipment?.dispatch_center || 'No asignado' }}</div>
        <button class="btn btn-sm btn-outline-primary mt-2">Asignar</button>
      </div>

      <div class="mb-3">
        <div class="small text-muted mb-1">Transportadora</div>
        <div class="fw-semibold">{{ order.shipment?.carrier || 'No asignada' }}</div>
        <button class="btn btn-sm btn-outline-primary mt-2">Asignar</button>
      </div>

      <div class="mb-3">
        <div class="small text-muted mb-1">Repartidor</div>
        <div class="fw-semibold">{{ order.shipment?.driver || 'No asignado' }}</div>
        <button class="btn btn-sm btn-outline-primary mt-2">Asignar</button>
      </div>

      <div class="mb-0">
        <div class="small text-muted mb-1">Estado del envío</div>
        <div class="fw-semibold">{{ order.shipment?.status || 'Sin shipment' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ order: { type: Object, required: true } });
</script>
