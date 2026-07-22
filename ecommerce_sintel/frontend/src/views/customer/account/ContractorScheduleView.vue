<template>
  <div class="contractor-schedule">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>Mi Agenda</h1>
        <p class="subtitle">Gestiona tu disponibilidad semanal y tus horarios reservados.</p>
      </div>
      <button class="btn-primary" @click="showBulkModal = true">
        + Crear disponibilidad masiva
      </button>
    </div>

    <!-- Filtros -->
    <div class="filter-bar">
      <label>Desde
        <input type="date" v-model="startDate" @change="fetchSchedule" />
      </label>
      <label>Hasta
        <input type="date" v-model="endDate" @change="fetchSchedule" />
      </label>
      <div class="status-filters">
        <button
          v-for="f in statusFilters"
          :key="f.value"
          class="filter-chip"
          :class="{ active: activeFilter === f.value }"
          @click="toggleFilter(f.value)"
        >{{ f.label }}</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <span class="spinner"></span> Cargando agenda…
    </div>

    <!-- Empty -->
    <div v-else-if="filteredSlots.length === 0" class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      <p>No hay slots en este rango.</p>
    </div>

    <!-- Tabla de slots -->
    <div v-else class="table-container">
      <div v-for="group in groupedSlots" :key="group.date" class="day-section">
        <h3 class="day-title">{{ formatDayLabel(group.date) }}</h3>
        <div class="slots-list">
          <div
            v-for="slot in group.slots"
            :key="slot.id"
            class="slot-row"
            :class="slot.status"
          >
            <div class="slot-time-range">
              <span class="time">{{ slot.start_time.slice(0,5) }}</span>
              <span class="sep">–</span>
              <span class="time">{{ slot.end_time.slice(0,5) }}</span>
            </div>
            <span class="status-badge" :class="slot.status">{{ slot.status_display }}</span>
            <span class="slot-notes" v-if="slot.notes">{{ slot.notes }}</span>
            <!-- Acciones (solo si es propietario de ese slot) -->
            <div class="slot-actions" v-if="canEdit(slot)">
              <select
                class="status-select"
                :value="slot.status"
                @change="updateStatus(slot, $event.target.value)"
              >
                <option value="AVAILABLE">Disponible</option>
                <option value="BLOCKED">Bloqueado</option>
                <option value="VACATION">Vacaciones</option>
                <option value="SICK_LEAVE">Incapacidad</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Crear disponibilidad masiva -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showBulkModal" class="modal-overlay" @click.self="showBulkModal = false">
          <div class="modal-card">
            <div class="modal-header">
              <h2>Crear disponibilidad masiva</h2>
              <button class="btn-close" @click="showBulkModal = false">✕</button>
            </div>
            <div class="modal-body">
              <div class="form-grid">
                <label class="form-field">
                  Fecha inicio
                  <input type="date" v-model="bulkForm.start_date" :min="todayStr" />
                </label>
                <label class="form-field">
                  Fecha fin
                  <input type="date" v-model="bulkForm.end_date" :min="bulkForm.start_date" />
                </label>
                <label class="form-field">
                  Hora inicio turno
                  <input type="number" v-model.number="bulkForm.work_start_hour" min="0" max="23" />
                </label>
                <label class="form-field">
                  Hora fin turno
                  <input type="number" v-model.number="bulkForm.work_end_hour" min="1" max="24" />
                </label>
                <label class="form-field">
                  Duración de cada slot (horas)
                  <input type="number" v-model.number="bulkForm.slot_duration_hours" min="1" max="12" />
                </label>
                <label class="form-field checkbox-field">
                  <input type="checkbox" v-model="bulkForm.exclude_weekends" />
                  Excluir fines de semana
                </label>
                <label class="form-field full-width">
                  Notas (opcional)
                  <input type="text" v-model="bulkForm.notes" placeholder="Ej: Consultoría virtual" />
                </label>
              </div>
              <div v-if="bulkError" class="error-msg">{{ bulkError }}</div>
              <div v-if="bulkSuccess" class="success-msg">{{ bulkSuccess }}</div>
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" @click="showBulkModal = false">Cancelar</button>
              <button class="btn-primary" :disabled="bulkLoading" @click="submitBulkCreate">
                <span v-if="bulkLoading" class="spinner-sm"></span>
                <span v-else>Generar slots</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="toast" class="toast" :class="toast.type">{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useAuthStore } from '@/store/auth';

const { get, post, patch } = useApi();
const authStore = useAuthStore();

// ─── Estado ────────────────────────────────────────────────────────────────────
const loading  = ref(false);
const slots    = ref([]);
const toast    = ref(null);
const showBulkModal = ref(false);
const bulkLoading   = ref(false);
const bulkError     = ref('');
const bulkSuccess   = ref('');

const today   = new Date();
const todayStr = today.toISOString().slice(0, 10);
const plus60  = new Date(today); plus60.setDate(today.getDate() + 60);
const startDate = ref(todayStr);
const endDate   = ref(plus60.toISOString().slice(0, 10));

const statusFilters = [
  { value: null,                 label: 'Todos' },
  { value: 'AVAILABLE',         label: 'Disponibles' },
  { value: 'PENDING_RESERVATION', label: 'Pendientes' },
  { value: 'BOOKED',            label: 'Reservados' },
  { value: 'BLOCKED',           label: 'Bloqueados' },
  { value: 'VACATION',          label: 'Vacaciones' },
];
const activeFilter = ref(null);

const bulkForm = ref({
  start_date: todayStr,
  end_date:   plus60.toISOString().slice(0, 10),
  work_start_hour: 8,
  work_end_hour: 18,
  slot_duration_hours: 2,
  exclude_weekends: true,
  notes: '',
});

// ─── Computed ─────────────────────────────────────────────────────────────────
const filteredSlots = computed(() => {
  if (!activeFilter.value) return slots.value;
  return slots.value.filter(s => s.status === activeFilter.value);
});

const groupedSlots = computed(() => {
  const groups = {};
  filteredSlots.value.forEach(s => {
    if (!groups[s.date]) groups[s.date] = [];
    groups[s.date].push(s);
  });
  return Object.entries(groups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, slotList]) => ({ date, slots: slotList }));
});

// ─── Métodos ──────────────────────────────────────────────────────────────────
async function fetchSchedule() {
  loading.value = true;
  try {
    const params = new URLSearchParams({ start: startDate.value, end: endDate.value });
    const data = await get(`/auth/availability/my-schedule/?${params}`);
    slots.value = Array.isArray(data) ? data : (data.results ?? []);
  } catch (e) {
    showToast('Error al cargar la agenda.', 'error');
  } finally {
    loading.value = false;
  }
}

function toggleFilter(val) {
  activeFilter.value = activeFilter.value === val ? null : val;
}

function canEdit(slot) {
  return !['BOOKED', 'PENDING_RESERVATION'].includes(slot.status);
}

async function updateStatus(slot, newStatus) {
  try {
    const res = await patch(`/auth/availability/${slot.id}/update-status/`, { status: newStatus });
    const idx = slots.value.findIndex(s => s.id === slot.id);
    if (idx !== -1) slots.value[idx] = { ...slots.value[idx], ...res };
    showToast('Estado actualizado.', 'success');
  } catch (e) {
    const msg = e?.response?.data?.detail ?? 'Error al actualizar el slot.';
    showToast(msg, 'error');
  }
}

async function submitBulkCreate() {
  bulkError.value   = '';
  bulkSuccess.value = '';
  bulkLoading.value = true;
  try {
    const res = await post('/auth/availability/bulk-create/', bulkForm.value);
    bulkSuccess.value = `✅ ${res.detail ?? res.created + ' slots creados.'}`;
    await fetchSchedule();
  } catch (e) {
    const data = e?.response?.data;
    bulkError.value = data?.non_field_errors?.[0] ?? data?.detail ?? 'Error al crear la disponibilidad.';
  } finally {
    bulkLoading.value = false;
  }
}

function formatDayLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

function showToast(msg, type = 'info') {
  toast.value = { msg, type };
  setTimeout(() => { toast.value = null; }, 3500);
}

// ─── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(fetchSchedule);
</script>

<style scoped>
.contractor-schedule {
  max-width: 900px; margin: 0 auto; padding: 2rem 1rem;
  font-family: 'Inter', sans-serif;
}

/* Header */
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;
}
h1 { font-size: 1.75rem; font-weight: 700; color: #1e1b4b; margin: 0 0 .25rem; }
.subtitle { color: #64748b; margin: 0; }

/* Buttons */
.btn-primary {
  background: #6366f1; color: #fff; border: none; border-radius: 10px;
  padding: .65rem 1.5rem; font-size: .95rem; font-weight: 600;
  cursor: pointer; transition: background .2s; white-space: nowrap;
}
.btn-primary:hover:not(:disabled) { background: #4f46e5; }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.btn-secondary {
  background: #f1f5f9; color: #475569; border: 1.5px solid #e2e8f0;
  border-radius: 10px; padding: .65rem 1.5rem; font-size: .95rem;
  font-weight: 600; cursor: pointer; transition: background .2s;
}
.btn-secondary:hover { background: #e2e8f0; }

/* Filter bar */
.filter-bar {
  display: flex; gap: 1.5rem; margin-bottom: 1.5rem;
  flex-wrap: wrap; align-items: flex-end;
  background: #f8fafc; border-radius: 12px; padding: 1rem 1.5rem;
}
.filter-bar label { display: flex; flex-direction: column; gap: .3rem; font-size: .85rem; color: #475569; font-weight: 500; }
.filter-bar input {
  padding: .45rem .75rem; border: 1.5px solid #e2e8f0;
  border-radius: 8px; font-size: .9rem; color: #1e293b;
  outline: none; transition: border-color .2s;
}
.filter-bar input:focus { border-color: #6366f1; }
.status-filters { display: flex; gap: .5rem; flex-wrap: wrap; }
.filter-chip {
  padding: .35rem .85rem; border-radius: 20px; border: 1.5px solid #e2e8f0;
  background: #fff; font-size: .8rem; font-weight: 500; cursor: pointer;
  color: #64748b; transition: all .2s;
}
.filter-chip.active { background: #6366f1; border-color: #6366f1; color: #fff; }
.filter-chip:hover:not(.active) { border-color: #6366f1; color: #6366f1; }

/* Loading / Empty */
.loading-state {
  display: flex; align-items: center; justify-content: center;
  gap: .75rem; padding: 3rem; color: #64748b;
}
.spinner {
  width: 22px; height: 22px; border: 3px solid #e0e7ff;
  border-top-color: #6366f1; border-radius: 50%;
  animation: spin .8s linear infinite; flex-shrink: 0;
}
.empty-state {
  text-align: center; padding: 3.5rem 1rem; color: #94a3b8;
}
.empty-state svg { margin-bottom: 1rem; }

/* Day sections */
.day-section { margin-bottom: 1.75rem; }
.day-title {
  font-size: .95rem; font-weight: 600; color: #334155;
  text-transform: capitalize; margin: 0 0 .75rem;
  padding-bottom: .4rem; border-bottom: 1.5px solid #e2e8f0;
}
.slots-list { display: flex; flex-direction: column; gap: .6rem; }
.slot-row {
  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
  background: #fff; border: 1.5px solid #e2e8f0; border-radius: 10px;
  padding: .75rem 1rem; transition: border-color .2s;
}
.slot-row.BOOKED { border-color: #22c55e; background: #f0fdf4; }
.slot-row.PENDING_RESERVATION { border-color: #f59e0b; background: #fffbeb; }
.slot-row.BLOCKED { border-color: #94a3b8; background: #f8fafc; }
.slot-row.VACATION { border-color: #818cf8; background: #eef2ff; }
.slot-row.SICK_LEAVE { border-color: #f87171; background: #fef2f2; }

.slot-time-range { display: flex; align-items: center; gap: .4rem; min-width: 110px; }
.time { font-weight: 600; font-size: .95rem; color: #1e293b; }
.sep { color: #94a3b8; }

.status-badge {
  font-size: .75rem; font-weight: 600; padding: .2rem .65rem;
  border-radius: 20px; background: #e2e8f0; color: #475569;
}
.status-badge.AVAILABLE   { background: #dcfce7; color: #15803d; }
.status-badge.BOOKED      { background: #bbf7d0; color: #166534; }
.status-badge.PENDING_RESERVATION { background: #fef3c7; color: #92400e; }
.status-badge.BLOCKED     { background: #f1f5f9; color: #475569; }
.status-badge.VACATION    { background: #e0e7ff; color: #4338ca; }
.status-badge.SICK_LEAVE  { background: #fee2e2; color: #b91c1c; }

.slot-notes { font-size: .82rem; color: #94a3b8; flex: 1; font-style: italic; }
.slot-actions { margin-left: auto; }
.status-select {
  padding: .35rem .65rem; border: 1.5px solid #e2e8f0; border-radius: 8px;
  font-size: .85rem; background: #fff; cursor: pointer;
  color: #1e293b; outline: none;
}
.status-select:focus { border-color: #6366f1; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 300; padding: 1rem;
}
.modal-card {
  background: #fff; border-radius: 16px; width: 100%; max-width: 540px;
  box-shadow: 0 20px 60px rgba(0,0,0,.15); overflow: hidden;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0;
}
.modal-header h2 { margin: 0; font-size: 1.15rem; font-weight: 700; color: #1e1b4b; }
.btn-close {
  background: none; border: none; font-size: 1.1rem; cursor: pointer; color: #94a3b8;
}
.modal-body { padding: 1.5rem; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-field {
  display: flex; flex-direction: column; gap: .35rem;
  font-size: .85rem; color: #475569; font-weight: 500;
}
.form-field input[type="date"],
.form-field input[type="number"],
.form-field input[type="text"] {
  padding: .5rem .75rem; border: 1.5px solid #e2e8f0; border-radius: 8px;
  font-size: .9rem; color: #1e293b; outline: none;
  transition: border-color .2s; background: #f8fafc;
}
.form-field input:focus { border-color: #6366f1; background: #fff; }
.checkbox-field { flex-direction: row; align-items: center; gap: .5rem; padding-top: 1.4rem; }
.checkbox-field input { width: 16px; height: 16px; cursor: pointer; accent-color: #6366f1; }
.full-width { grid-column: 1 / -1; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: .75rem;
  padding: 1rem 1.5rem; border-top: 1px solid #e2e8f0; background: #f8fafc;
}

/* Messages */
.error-msg { margin-top: .75rem; color: #dc2626; background: #fef2f2; border-radius: 8px; padding: .6rem .75rem; font-size: .85rem; }
.success-msg { margin-top: .75rem; color: #15803d; background: #dcfce7; border-radius: 8px; padding: .6rem .75rem; font-size: .85rem; }

/* Toast */
.toast {
  position: fixed; bottom: 2rem; right: 2rem;
  padding: .75rem 1.25rem; border-radius: 10px;
  font-size: .9rem; font-weight: 500; z-index: 400;
  box-shadow: 0 4px 20px rgba(0,0,0,.15);
}
.toast.success { background: #15803d; color: #fff; }
.toast.error   { background: #dc2626; color: #fff; }
.toast.info    { background: #1e293b; color: #fff; }

/* Spinners */
.spinner-sm {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff; border-radius: 50%; animation: spin .8s linear infinite;
  display: inline-block;
}

/* Transitions */
.modal-enter-active, .modal-leave-active { transition: opacity .25s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.fade-enter-active, .fade-leave-active { transition: opacity .3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
