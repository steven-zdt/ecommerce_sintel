<template>
  <BaseOperationBoard
    title="Operaciones de Tienda"
    subtitle="Picking, empaque, despacho y entrega de pedidos de producto."
    :cards="cards"
    :loading="loading"
    @refresh="load"
  >
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white d-flex gap-2 py-3 flex-wrap">
        <input v-model="filters.search" class="form-control" style="max-width:260px" placeholder="Buscar guia, orden o cliente" @keyup.enter="load">
        <select v-model="filters.status" class="form-select" style="max-width:220px" @change="load">
          <option value="">Todos los estados</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ s.replaceAll('_', ' ') }}</option>
        </select>
        <input v-model="filters.date_from" type="date" class="form-control" style="max-width:170px" @change="load">
        <input v-model="filters.date_to" type="date" class="form-control" style="max-width:170px" @change="load">
      </div>
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead><tr><th class="ps-4">Pedido</th><th>Cliente</th><th>Metodo envio</th><th>Transportista</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-if="loading"><td colspan="6" class="text-center py-5">Cargando...</td></tr>
            <tr v-else-if="!items.length"><td colspan="6" class="text-center py-5 text-muted">No hay pedidos con pago confirmado pendientes de operar.</td></tr>
            <tr v-for="sh in items" :key="sh.uuid">
              <td class="ps-4 fw-semibold">
                {{ sh.shipment_number }}
                <div class="small text-muted fw-normal">{{ sh.order?.items_count }} articulo(s) · ${{ fmt(sh.order?.total_amount) }}</div>
              </td>
              <td>{{ sh.order?.user_name }}</td>
              <td>{{ sh.shipping_method_display || 'Sin definir' }}</td>
              <td>{{ sh.dispatcher_name || 'Sin asignar' }}</td>
              <td><ShipmentStatusBadge :status="sh.status" /></td>
              <td><button class="btn btn-sm btn-outline-primary" @click="selectShipment(sh)">Gestionar</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selected" class="card border-0 shadow-sm mt-4 p-4">
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div>
          <h5 class="mb-1">Gestionar {{ selected.shipment_number }}</h5>
          <p class="text-muted small mb-0">Cliente: {{ selected.order?.user_name }} ({{ selected.order?.user_email }})</p>
        </div>
        <button class="btn-close" @click="selected = null"></button>
      </div>

      <div class="mb-3"><ShipmentStatusBadge :status="selected.status" /></div>

      <!-- Picking -->
      <div v-if="selected.order?.shipping_address" class="mb-3 p-3 rounded bg-light">
        <h6 class="fw-bold mb-1"><i class="bi bi-geo-alt me-1"></i>Direccion de entrega</h6>
        <p class="small mb-0">{{ selected.order.shipping_address.full_name }} · {{ selected.order.shipping_address.address_line_1 }}, {{ selected.order.shipping_address.city }}</p>
      </div>

      <!-- Empaque -->
      <div v-if="selected.status === 'PREPARING'" class="mb-3">
        <h6 class="fw-bold">Completar empaque</h6>
        <div class="row g-2">
          <div class="col-md-3"><input v-model="packing.package_type" class="form-control" placeholder="Tipo de embalaje"></div>
          <div class="col-md-3"><input v-model.number="packing.package_weight" type="number" step="0.01" class="form-control" placeholder="Peso (kg)"></div>
          <div class="col-md-3"><input v-model.number="packing.package_volume" type="number" step="0.01" class="form-control" placeholder="Volumen (m3)"></div>
          <div class="col-md-3"><input v-model="packing.package_dimensions" class="form-control" placeholder="Dimensiones"></div>
          <div class="col-12"><button class="btn btn-primary" :disabled="saving" @click="savePacking">Marcar como empacado</button></div>
        </div>
      </div>

      <!-- Programacion + asignacion de transportista -->
      <template v-if="selected.status === 'READY_FOR_DISPATCH' || selected.status === 'ASSIGNED'">
        <hr>
        <h6 class="fw-bold">Programacion logistica</h6>
        <div class="row g-2 mb-3">
          <div class="col-md-4">
            <select v-model="schedule.shipping_method" class="form-select">
              <option value="">Metodo de envio</option>
              <option v-for="m in SHIPPING_METHODS" :key="m.value" :value="m.value">{{ m.label }}</option>
            </select>
          </div>
          <div class="col-md-4"><input v-model="schedule.dispatch_scheduled_at" type="datetime-local" class="form-control"></div>
          <div class="col-md-4"><input v-model="schedule.route" class="form-control" placeholder="Ruta / zona"></div>
          <div class="col-12"><button class="btn btn-outline-primary btn-sm" :disabled="saving" @click="saveSchedule">Guardar programacion</button></div>
        </div>

        <h6 class="fw-bold">Asignar transportista</h6>
        <div class="row g-2">
          <div class="col-md-8">
            <select v-model="assignment.dispatcher_profile_uuid" class="form-select">
              <option value="">Seleccionar transportista disponible</option>
              <option v-for="d in availableDispatchers" :key="d.uuid" :value="d.uuid">{{ d.email }} · {{ d.vehicle_plate || 'sin placa' }}</option>
            </select>
          </div>
          <div class="col-md-4"><button class="btn btn-success w-100" :disabled="!assignment.dispatcher_profile_uuid || saving" @click="assignDispatcher">Asignar y notificar</button></div>
        </div>
      </template>

      <!-- Siguiente transicion -->
      <div v-if="nextAction" class="p-3 rounded bg-light d-flex align-items-center justify-content-between mt-3 mb-3">
        <div><div class="small text-muted">Siguiente paso</div><div class="fw-semibold">{{ nextAction.label }}</div></div>
        <button class="btn btn-primary" :disabled="saving" @click="runTransition(nextAction)">
          <i :class="['bi', nextAction.icon, 'me-2']"></i>{{ nextAction.button }}
        </button>
      </div>

      <div class="mt-4">
        <h6 class="fw-bold">Timeline operativo</h6>
        <div v-if="!timeline.length" class="text-muted small">Sin eventos registrados.</div>
        <div v-for="event in timeline" :key="event.id" class="border-start border-primary ps-3 py-2">
          <div class="fw-semibold small">{{ event.comment || event.event_type }}</div>
          <div class="text-muted smaller">{{ new Date(event.created_at).toLocaleString('es-CO') }}</div>
        </div>
      </div>
    </div>
  </BaseOperationBoard>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useToast } from '@/composables/useToast';
import { useOrdersAdminStore } from '@/store/ordersAdmin';
import ShipmentStatusBadge from '@/components/customer/orders/ShipmentStatusBadge.vue';
import BaseOperationBoard from '@/components/shared/BaseOperationBoard.vue';
import { formatCOP } from '@/utils/money';

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useOrdersAdminStore();
const {
  shipments: items, dispatchers, metrics, opsLoading: loading,
  timeline,
  actionLoading: saving,
} = storeToRefs(store);

const selected = ref(null);
const filters = reactive({ status: '', search: '', date_from: '', date_to: '' });
const packing = reactive({ package_type: '', package_weight: null, package_volume: null, package_dimensions: '' });
const schedule = reactive({ shipping_method: '', dispatch_scheduled_at: '', route: '' });
const assignment = reactive({ dispatcher_profile_uuid: '' });

const STATUSES = ['PREPARING', 'READY_FOR_DISPATCH', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'delivered', 'COMPLETED', 'FAILED_DELIVERY', 'LOST'];
const SHIPPING_METHODS = [
  { value: 'OWN_DELIVERY', label: 'Entrega propia' },
  { value: 'INTERNAL_DISPATCHER', label: 'Transportista interno' },
  { value: 'URBAN_COURIER', label: 'Mensajeria urbana' },
  { value: 'CARRIER_COMPANY', label: 'Empresa transportadora' },
  { value: 'CERTIFIED_MAIL', label: 'Correo certificado' },
  { value: 'STORE_PICKUP', label: 'Recogida en tienda' },
  { value: 'SCHEDULED_DELIVERY', label: 'Entrega programada' },
];

const transitionActions = {
  ASSIGNED: { endpoint: 'dispatch', label: 'Sacar el pedido de bodega', button: 'Despachar', icon: 'bi-box-arrow-up-right' },
  PICKED_UP: { endpoint: 'in-transit', label: 'El pedido esta en camino', button: 'Marcar en transito', icon: 'bi-truck' },
  IN_TRANSIT: { endpoint: 'out-for-delivery', label: 'El pedido entro en reparto final', button: 'Marcar en reparto', icon: 'bi-signpost-split' },
  OUT_FOR_DELIVERY: { endpoint: 'deliver', label: 'Confirmar entrega al cliente', button: 'Marcar entregado', icon: 'bi-check2-circle' },
  delivered: { endpoint: 'complete', label: 'Cerrar la operacion logistica', button: 'Completar pedido', icon: 'bi-lock' },
};

const nextAction = computed(() => transitionActions[selected.value?.status] || null);
const availableDispatchers = computed(() => dispatchers.value.filter(d => d.is_active && d.is_available));

const cards = computed(() => [
  { label: 'Pendientes de preparar', value: metrics.value.pending_preparation ?? 0 },
  { label: 'Pendientes de empacar', value: metrics.value.pending_packing ?? 0 },
  { label: 'Despachos de hoy', value: metrics.value.dispatches_today ?? 0 },
  { label: 'Entregas de hoy', value: metrics.value.deliveries_today ?? 0 },
  { label: 'Transportistas activos', value: metrics.value.dispatchers_active ?? 0 },
  { label: 'Atrasados', value: metrics.value.delayed ?? 0, danger: (metrics.value.delayed ?? 0) > 0 },
  { label: 'Tiempo promedio (h)', value: metrics.value.avg_fulfillment_hours ?? '-' },
  { label: 'SLA cumplido', value: metrics.value.sla_percentage != null ? `${metrics.value.sla_percentage}%` : '-' },
]);

const fmt = (val) => formatCOP(val);

function load() {
  return store.fetchOperations(filters);
}

function loadTimeline(orderUuid) {
  return store.fetchTimeline(orderUuid);
}

function selectShipment(sh) {
  selected.value = sh;
  Object.assign(packing, { package_type: sh.package_type || '', package_weight: sh.package_weight, package_volume: sh.package_volume, package_dimensions: sh.package_dimensions || '' });
  Object.assign(schedule, { shipping_method: sh.shipping_method || '', dispatch_scheduled_at: sh.dispatch_scheduled_at?.slice(0, 16) || '', route: sh.route || '' });
  Object.assign(assignment, { dispatcher_profile_uuid: '' });
  loadTimeline(sh.order.uuid);
}

async function execute(action, successMessage) {
  const res = await action();
  if (res.ok) {
    toast.success(successMessage);
    await load();
    const refreshed = items.value.find(i => i.order?.uuid === res.data.uuid);
    if (refreshed) selectShipment(refreshed);
  } else {
    handleError(res.error, 'No fue posible completar la accion.');
  }
}

async function savePacking() {
  await execute(() => store.pack(selected.value.order.uuid, packing), 'Empaque registrado.');
}

async function saveSchedule() {
  const payload = { ...schedule };
  if (payload.dispatch_scheduled_at) payload.dispatch_scheduled_at = new Date(payload.dispatch_scheduled_at).toISOString();
  await execute(() => store.scheduleDispatch(selected.value.order.uuid, payload), 'Programacion guardada.');
}

async function assignDispatcher() {
  await execute(() => store.assignDispatcher(selected.value.order.uuid, assignment), 'Transportista asignado y notificado.');
}

async function runTransition(action) {
  await execute(() => store.transition(selected.value.order.uuid, action.endpoint), 'Estado operativo actualizado.');
}

onMounted(load);
</script>
