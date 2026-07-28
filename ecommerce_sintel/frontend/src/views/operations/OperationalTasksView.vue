<template>
  <main class="tasks-view">
    <header class="tasks-header">
      <div>
        <p class="eyebrow">Operaciones</p>
        <h1>Mis tareas</h1>
      </div>
      <button class="icon-button" title="Actualizar tareas" :disabled="loading" @click="fetchTasks">
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </header>

    <div v-if="loading" class="state-block">
      <div class="spinner-border text-primary" role="status"></div>
    </div>
    <div v-else-if="!tasks.length" class="state-block">
      <i class="bi bi-clipboard2-check state-icon"></i>
      <p>No tienes tareas asignadas.</p>
    </div>

    <section v-else class="task-list">
      <article v-for="task in tasks" :key="task.uuid" class="task-item">
        <div class="task-topline">
          <span class="task-number">{{ task.ticket_number }}</span>
          <span class="status-badge" :class="statusClass(task.status)">
            {{ statusLabel(task.status) }}
          </span>
        </div>
        <h2>{{ typeLabel(task.operation_type) }}</h2>
        <p class="task-location">
          <i class="bi bi-geo-alt"></i>
          {{ [task.location_address, task.location_city].filter(Boolean).join(', ') || 'Ubicacion pendiente' }}
        </p>
        <p v-if="task.scheduled_date" class="task-schedule">
          <i class="bi bi-calendar3"></i>
          {{ task.scheduled_date }}
          <span v-if="task.scheduled_time_start"> · {{ task.scheduled_time_start.slice(0, 5) }}</span>
        </p>
        <button
          v-if="nextAction(task.status)"
          class="btn btn-primary action-button"
          :disabled="updating === task.uuid"
          @click="advance(task)"
        >
          <span v-if="updating === task.uuid" class="spinner-border spinner-border-sm"></span>
          <i v-else :class="['bi', nextAction(task.status).icon]"></i>
          {{ nextAction(task.status).label }}
        </button>
      </article>
    </section>
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { operationsService } from '@/services/operations/operationsService';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useEnums } from '@/composables/useEnums';

const toast = useToast();
const { handleError } = useErrorHandler();
const enums = useEnums();
const tasks = ref([]);
const loading = ref(true);
const updating = ref(null);

const ACTIONS = {
  SCHEDULED: { status: 'EN_ROUTE', label: 'Iniciar viaje', icon: 'bi-truck' },
  EN_ROUTE: { status: 'IN_PROGRESS', label: 'Iniciar trabajo', icon: 'bi-play-fill' },
  IN_PROGRESS: { status: 'COMPLETED', label: 'Completar tarea', icon: 'bi-check-lg' },
};
const nextAction = (status) => ACTIONS[status] || null;
const statusLabel = (status) => enums.label('operation-statuses', status, status);
const statusClass = (status) => enums.cssClass('operation-statuses', status, 'bg-secondary-subtle text-secondary border border-secondary-subtle');
const typeLabel = (type) => enums.label('operation-types', type, type);

async function fetchTasks() {
  loading.value = true;
  try {
    const data = await operationsService.tasks();
    tasks.value = data.results ?? data;
  } catch (error) {
    handleError(error, 'No fue posible cargar las tareas.');
  } finally {
    loading.value = false;
  }
}

async function advance(task) {
  const action = nextAction(task.status);
  if (!action) return;
  updating.value = task.uuid;
  try {
    await operationsService.transitionTask(task.uuid, action.status);
    toast.success('Estado actualizado.');
    await fetchTasks();
  } catch (error) {
    handleError(error, 'No fue posible actualizar la tarea.');
  } finally {
    updating.value = null;
  }
}

onMounted(() => {
  enums.preload(['operation-statuses', 'operation-types']);
  fetchTasks();
});
</script>

<style scoped>
.tasks-view { width: min(760px, 100%); margin: 0 auto; padding: 32px 20px 56px; }
.tasks-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.eyebrow { margin: 0 0 4px; color: #2563eb; font-size: .75rem; font-weight: 700; text-transform: uppercase; }
h1 { margin: 0; color: #111827; font-size: 1.75rem; }
.icon-button { width: 40px; height: 40px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; color: #374151; }
.state-block { min-height: 280px; display: grid; place-items: center; align-content: center; gap: 12px; color: #6b7280; }
.state-icon { font-size: 2rem; }
.task-list { border-top: 1px solid #e5e7eb; }
.task-item { padding: 20px 0; border-bottom: 1px solid #e5e7eb; }
.task-topline { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.task-number { color: #6b7280; font-size: .8rem; font-weight: 600; }
.task-item h2 { margin: 10px 0 12px; color: #111827; font-size: 1.05rem; }
.task-location, .task-schedule { margin: 6px 0; color: #4b5563; font-size: .9rem; }
.task-location i, .task-schedule i { width: 20px; color: #6b7280; }
.status-badge { padding: 4px 9px; border-radius: 8px; background: #e5e7eb; color: #374151; font-size: .75rem; font-weight: 700; }
.status-en_route, .status-in_progress { background: #fef3c7; color: #92400e; }
.status-completed { background: #dcfce7; color: #166534; }
.status-cancelled { background: #fee2e2; color: #991b1b; }
.action-button { width: 100%; min-height: 44px; margin-top: 18px; display: flex; align-items: center; justify-content: center; gap: 8px; }
@media (min-width: 640px) { .action-button { width: auto; min-width: 190px; } }
</style>
