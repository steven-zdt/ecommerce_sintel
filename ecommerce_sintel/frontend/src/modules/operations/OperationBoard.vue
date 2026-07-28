<template>
  <BaseOperationBoard title="Tablero de operaciones" :loading="loading" @refresh="fetchOps">
    <div class="board-header">
      <div class="filters">
        <select v-model="filters.status" class="form-select form-select-sm" @change="fetchOps">
          <option value="">Todos los estados</option>
          <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="filters.operation_type" class="form-select form-select-sm" @change="fetchOps">
          <option value="">Todos los tipos</option>
          <option v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <input v-model="filters.scheduled_date" type="date" class="form-control form-control-sm" @change="fetchOps" />
      </div>
    </div>

    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else-if="!ops.length" class="text-center py-5 text-muted">
      No hay operaciones para los filtros seleccionados.
    </div>

    <table v-else class="table table-hover align-middle">
      <thead class="table-light">
        <tr>
          <th>Ticket</th>
          <th>Tipo</th>
          <th>Estado</th>
          <th>Cliente</th>
          <th>Ciudad</th>
          <th>Fecha</th>
          <th>Asignados</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="op in ops" :key="op.uuid">
          <td class="fw-semibold">{{ op.ticket_number }}</td>
          <td><span class="badge text-bg-light">{{ typeLabel(op.operation_type) }}</span></td>
          <!-- [2026-07-12] effective_status (CORE v4 Fase 5 Paso 2) refleja el estado del
               ServiceOperation/RentalOperation/Shipment vinculado cuando existe -- fallback
               a op.status en tickets sin satelite todavia. Ver
               MIGRACION_CORE_V4_DOMINIOS_FASE5_PROPUESTA_OPERACIONES.md -->
          <td><span class="badge" :class="statusBadgeClass(op.effective_status)">{{ statusLabel(op.effective_status) }}</span></td>
          <td class="small">{{ op.customer_email }}</td>
          <td class="small">{{ op.location_city || '—' }}</td>
          <td class="small">{{ op.scheduled_date || '—' }}</td>
          <td class="small">
            <span v-for="a in op.assignees" :key="a.email" class="d-block">
              {{ a.email }} ({{ a.role }})
            </span>
            <span v-if="!op.assignees?.length" class="text-muted">—</span>
          </td>
          <td>
            <RouterLink :to="`/panel/operaciones/${op.uuid}`" class="btn btn-sm btn-outline-primary">
              Ver
            </RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </BaseOperationBoard>
</template>

<script setup>
import { reactive, onMounted, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useEnums } from '@/composables/useEnums';
import { useOperationsAdminStore } from '@/store/operationsAdmin';
import BaseOperationBoard from '@/components/shared/BaseOperationBoard.vue';

const enums   = useEnums();
const store   = useOperationsAdminStore();
const { ops, opsLoading: loading } = storeToRefs(store);

const filters = reactive({ status: '', operation_type: '', scheduled_date: '' });

const STATUS_OPTIONS = computed(() => {
  const catalog = [
    'CREATED', 'DOCS_PENDING', 'READY_TO_ASSIGN', 'ASSIGNED',
    'SCHEDULED', 'EN_ROUTE', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED',
  ];
  return catalog.map((value) => ({ value, label: enums.label('operation-statuses', value, value) }));
});

const TYPE_OPTIONS = computed(() => {
  const catalog = ['SHOP_DELIVERY', 'RENTAL', 'SERVICE'];
  return catalog.map((value) => ({ value, label: enums.label('operation-types', value, value) }));
});

function fetchOps() {
  return store.fetchOps(filters);
}

onMounted(fetchOps);
onMounted(() => {
  enums.preload(['operation-statuses', 'operation-types']);
});

const typeLabel   = (t) => enums.label('operation-types', t, t);
const statusLabel = (s) => enums.label('operation-statuses', s, s);
const statusBadgeClass = (s) => enums.cssClass('operation-statuses', s, 'bg-secondary-subtle text-secondary border border-secondary-subtle');
</script>

<style scoped>
.board-header { margin-bottom: 20px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.filters .form-select, .filters .form-control { max-width: 180px; }
</style>
