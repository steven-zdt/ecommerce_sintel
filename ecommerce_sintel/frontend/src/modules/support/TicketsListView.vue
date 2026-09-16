<template>
  <div class="tickets-view">
    <div class="tickets-header">
      <h2>Tickets de Soporte</h2>
    </div>

    <div class="tickets-filters">
      <select v-model="filters.status" class="form-select form-select-sm" @change="load">
        <option value="">Todos los estados</option>
        <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <select v-model="filters.priority" class="form-select form-select-sm" @change="load">
        <option value="">Toda prioridad</option>
        <option v-for="opt in PRIORITY_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <div class="form-check form-check-sm assigned-check">
        <input id="assigned-to-me" v-model="filters.assigned_to_me" class="form-check-input" type="checkbox" @change="load" />
        <label class="form-check-label" for="assigned-to-me">Solo asignados a mi</label>
      </div>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>
    <div v-else class="table-responsive">
      <table class="table table-sm tickets-table">
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Cliente</th>
            <th>Asunto</th>
            <th>Prioridad</th>
            <th>Estado</th>
            <th>Asignado</th>
            <th>Creado</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.uuid">
            <td class="fw-semibold">{{ t.ticket_number }}</td>
            <td>{{ t.customer_email }}</td>
            <td class="text-truncate" style="max-width: 260px;" :title="t.subject">{{ t.subject || '-' }}</td>
            <td><span class="badge" :class="priorityClass(t.priority)">{{ priorityLabel(t.priority) }}</span></td>
            <td><span class="badge" :class="statusClass(t.status)">{{ statusLabel(t.status) }}</span></td>
            <td>{{ t.assigned_admin_email || '-' }}</td>
            <td>{{ formatDate(t.created_at) }}</td>
            <td>
              <RouterLink class="btn btn-sm btn-outline-primary" :to="`/panel/soporte?room=${t.room_uuid}`">
                Abrir chat
              </RouterLink>
            </td>
          </tr>
          <tr v-if="tickets.length === 0">
            <td colspan="8" class="text-center text-muted py-4">Sin tickets para estos filtros.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const api = useApi();
const toast = useToast();

const tickets = ref([]);
const loading = ref(false);
const filters = reactive({ status: '', priority: '', assigned_to_me: false });

// Mismos choices que support.models.SupportTicket (backend) -- ver
// SupportDashboardView.vue, mismo criterio, no se duplica una fuente de
// verdad de opciones distinta.
const STATUS_OPTIONS = [
  { value: 'NEW', label: 'Nuevo' },
  { value: 'OPEN', label: 'Abierto' },
  { value: 'IN_PROGRESS', label: 'En proceso' },
  { value: 'WAITING_CUSTOMER', label: 'Esperando cliente' },
  { value: 'RESOLVED', label: 'Resuelto' },
  { value: 'CLOSED', label: 'Cerrado' },
  { value: 'CANCELLED', label: 'Cancelado' },
];
const PRIORITY_OPTIONS = [
  { value: 'LOW', label: 'Baja' },
  { value: 'NORMAL', label: 'Normal' },
  { value: 'HIGH', label: 'Alta' },
  { value: 'URGENT', label: 'Urgente' },
];

function statusLabel(value) {
  return STATUS_OPTIONS.find(o => o.value === value)?.label || value || '';
}
function priorityLabel(value) {
  return PRIORITY_OPTIONS.find(o => o.value === value)?.label || value || '';
}
function statusClass(value) {
  if (value === 'NEW') return 'bg-primary';
  if (value === 'OPEN' || value === 'IN_PROGRESS') return 'bg-info text-dark';
  if (value === 'WAITING_CUSTOMER') return 'bg-warning text-dark';
  if (value === 'RESOLVED' || value === 'CLOSED') return 'bg-success';
  return 'bg-secondary';
}
function priorityClass(value) {
  if (value === 'URGENT') return 'bg-danger';
  if (value === 'HIGH') return 'bg-warning text-dark';
  if (value === 'LOW') return 'bg-secondary';
  return 'bg-info text-dark';
}
function formatDate(value) {
  return value ? new Date(value).toLocaleString('es-CO') : '-';
}

async function load() {
  loading.value = true;
  try {
    const { data } = await api.get('dashboard/support/chats/tickets/', {
      params: {
        status: filters.status || undefined,
        priority: filters.priority || undefined,
        assigned_to_me: filters.assigned_to_me || undefined,
      },
    });
    tickets.value = data;
  } catch {
    toast.error('Error al cargar los tickets');
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.tickets-view { padding: 24px; }
.tickets-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.tickets-filters { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.tickets-filters .form-select { max-width: 200px; }
.assigned-check { display: flex; align-items: center; gap: 6px; margin-left: 8px; }
.tickets-table { background: #fff; }
</style>
