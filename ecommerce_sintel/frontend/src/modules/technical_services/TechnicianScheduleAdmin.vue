<template>
  <div>
    <h5 class="fw-bold mb-3">Horarios y Ausencias de Técnicos</h5>

    <!-- Tablero de carga operativa (Fase 6) -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-2" v-for="kpi in kpiCards" :key="kpi.label">
        <div class="card border-0 shadow-sm p-3 text-center h-100">
          <div class="fs-4 fw-bold">{{ kpi.value }}</div>
          <div class="small text-muted">{{ kpi.label }}</div>
        </div>
      </div>
    </div>

    <div class="card border-0 shadow-sm p-3 mb-4">
      <label class="form-label fw-semibold">Técnico</label>
      <select v-model="selectedTechnicianUuid" class="form-select" @change="onTechnicianChange">
        <option value="">-- Selecciona un técnico --</option>
        <option v-for="t in technicians" :key="t.technician_uuid" :value="t.technician_uuid">
          {{ t.technician_name }}
        </option>
      </select>
    </div>

    <div v-if="selectedTechnicianUuid">
      <div class="card border-0 shadow-sm mb-4">
        <div class="card-header bg-white fw-semibold">Horario laboral semanal</div>
        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead class="bg-light text-muted small text-uppercase">
              <tr>
                <th class="px-3">Día</th>
                <th class="text-center">Activo</th>
                <th>Hora inicio</th>
                <th>Hora fin</th>
                <th class="text-end px-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="day in WEEKDAYS" :key="day.value">
                <td class="px-3 fw-semibold">{{ day.label }}</td>
                <td class="text-center">
                  <input type="checkbox" class="form-check-input" v-model="scheduleForm[day.value].is_active">
                </td>
                <td>
                  <input type="time" class="form-control form-control-sm" v-model="scheduleForm[day.value].start_time" style="max-width:120px;">
                </td>
                <td>
                  <input type="time" class="form-control form-control-sm" v-model="scheduleForm[day.value].end_time" style="max-width:120px;">
                </td>
                <td class="text-end px-3">
                  <button class="btn btn-sm btn-primary" :disabled="savingDay === day.value" @click="saveDay(day.value)">
                    <span v-if="savingDay === day.value" class="spinner-border spinner-border-sm me-1"></span>
                    Guardar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card border-0 shadow-sm">
        <div class="card-header bg-white d-flex justify-content-between align-items-center">
          <span class="fw-semibold">Ausencias y horas extra</span>
          <button class="btn btn-sm btn-outline-primary" @click="showNewException = !showNewException">
            <i class="bi bi-plus-lg me-1"></i>Nueva
          </button>
        </div>

        <div v-if="showNewException" class="card-body border-bottom action-form">
          <div class="row g-2">
            <div class="col-md-4">
              <label class="form-label small text-muted">Tipo</label>
              <select v-model="exceptionForm.exception_type" class="form-select form-select-sm">
                <option value="VACATION">Vacaciones</option>
                <option value="PERMIT">Permiso</option>
                <option value="SICK_LEAVE">Incapacidad</option>
                <option value="TRAINING">Capacitación</option>
                <option value="MAINTENANCE">Mantenimiento (bloqueo manual)</option>
                <option value="EXTRA_HOURS">Horas extra</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label small text-muted">Desde</label>
              <input type="date" class="form-control form-control-sm" v-model="exceptionForm.start_date">
            </div>
            <div class="col-md-4">
              <label class="form-label small text-muted">Hasta</label>
              <input type="date" class="form-control form-control-sm" v-model="exceptionForm.end_date">
            </div>
            <div class="col-md-4">
              <label class="form-label small text-muted">
                Hora inicio <span v-if="exceptionForm.exception_type === 'EXTRA_HOURS'" class="text-danger">*</span>
              </label>
              <input type="time" class="form-control form-control-sm" v-model="exceptionForm.start_time">
            </div>
            <div class="col-md-4">
              <label class="form-label small text-muted">
                Hora fin <span v-if="exceptionForm.exception_type === 'EXTRA_HOURS'" class="text-danger">*</span>
              </label>
              <input type="time" class="form-control form-control-sm" v-model="exceptionForm.end_time">
            </div>
            <div class="col-12">
              <p v-if="exceptionForm.exception_type === 'EXTRA_HOURS'" class="small text-success mb-1">
                <i class="bi bi-plus-circle me-1"></i>Suma disponibilidad extra ese rango de fechas (no requiere horario base).
              </p>
              <p v-else class="small text-muted mb-1">Deja las horas vacías para bloquear el día completo.</p>
              <label class="form-label small text-muted">Motivo</label>
              <textarea class="form-control form-control-sm" rows="2" v-model="exceptionForm.reason"></textarea>
            </div>
          </div>
          <div class="mt-3">
            <button class="btn btn-sm btn-primary" :disabled="savingException" @click="createException">
              <span v-if="savingException" class="spinner-border spinner-border-sm me-1"></span>
              Guardar
            </button>
            <button class="btn btn-sm btn-light border ms-2" @click="showNewException = false">Cancelar</button>
          </div>
        </div>

        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead class="bg-light text-muted small text-uppercase">
              <tr>
                <th class="px-3">Tipo</th>
                <th>Rango</th>
                <th>Motivo</th>
                <th class="text-end px-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loadingExceptions">
                <td colspan="4" class="text-center py-3">
                  <div class="spinner-border spinner-border-sm text-primary"></div>
                </td>
              </tr>
              <tr v-else-if="!exceptions.length">
                <td colspan="4" class="text-center text-muted py-3">Sin ausencias registradas.</td>
              </tr>
              <tr v-for="exc in exceptions" :key="exc.uuid">
                <td class="px-3">
                  <span class="badge" :class="exc.exception_type === 'EXTRA_HOURS' ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
                    {{ exc.exception_type_display }}
                  </span>
                </td>
                <td class="small">
                  {{ exc.start_date }} — {{ exc.end_date }}
                  <span v-if="exc.start_time" class="text-muted">({{ exc.start_time.slice(0,5) }}-{{ exc.end_time.slice(0,5) }})</span>
                </td>
                <td class="small text-muted">{{ exc.reason || '—' }}</td>
                <td class="text-end px-3">
                  <button class="btn btn-sm btn-outline-danger" :disabled="deletingUuid === exc.uuid" @click="deleteException(exc.uuid)">
                    Liberar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const api = useApi();
const toast = useToast();

const WEEKDAYS = [
  { value: 0, label: 'Lunes' },
  { value: 1, label: 'Martes' },
  { value: 2, label: 'Miércoles' },
  { value: 3, label: 'Jueves' },
  { value: 4, label: 'Viernes' },
  { value: 5, label: 'Sábado' },
  { value: 6, label: 'Domingo' },
];

const technicians = ref([]);
const selectedTechnicianUuid = ref('');
const scheduleForm = reactive(
  Object.fromEntries(WEEKDAYS.map((d) => [d.value, { is_active: false, start_time: '07:00', end_time: '18:00' }])),
);
const savingDay = ref(null);

const exceptions = ref([]);
const loadingExceptions = ref(false);
const showNewException = ref(false);
const savingException = ref(false);
const deletingUuid = ref(null);
const exceptionForm = reactive({
  exception_type: 'VACATION', start_date: '', end_date: '', start_time: '', end_time: '', reason: '',
});

const capacitySummary = ref({});
const kpiCards = computed(() => [
  { label: 'Técnicos disponibles', value: capacitySummary.value.technicians_available ?? '—' },
  { label: 'Técnicos ocupados', value: capacitySummary.value.technicians_busy ?? '—' },
  { label: 'Horas disponibles', value: capacitySummary.value.free_hours ?? '—' },
  { label: 'Horas ocupadas', value: capacitySummary.value.occupied_hours ?? '—' },
  { label: 'Capacidad (h)', value: capacitySummary.value.capacity_hours ?? '—' },
]);

async function loadTechnicians() {
  const { data } = await api.get('services/technician-availability/technicians/');
  technicians.value = data;
}

async function loadCapacitySummary() {
  const today = new Date().toISOString().slice(0, 10);
  const { data } = await api.get('services/technician-availability/summary/', { params: { date: today } });
  capacitySummary.value = data;
}

async function loadSchedule() {
  WEEKDAYS.forEach((d) => { scheduleForm[d.value] = { is_active: false, start_time: '07:00', end_time: '18:00' }; });
  const { data } = await api.get('services/working-schedules/', { params: { technician: selectedTechnicianUuid.value } });
  const results = data.results ?? data;
  for (const s of results) {
    scheduleForm[s.weekday] = {
      is_active: s.is_active,
      start_time: s.start_time.slice(0, 5),
      end_time: s.end_time.slice(0, 5),
    };
  }
}

async function loadExceptions() {
  loadingExceptions.value = true;
  try {
    const { data } = await api.get('services/working-exceptions/', { params: { technician: selectedTechnicianUuid.value } });
    exceptions.value = data.results ?? data;
  } finally {
    loadingExceptions.value = false;
  }
}

async function onTechnicianChange() {
  if (!selectedTechnicianUuid.value) return;
  await Promise.all([loadSchedule(), loadExceptions()]);
}

async function saveDay(weekday) {
  savingDay.value = weekday;
  try {
    const form = scheduleForm[weekday];
    await api.post('services/working-schedules/', {
      technician: selectedTechnicianUuid.value,
      weekday,
      start_time: form.start_time,
      end_time: form.end_time,
      is_active: form.is_active,
    });
    toast.success('Horario guardado.');
    await loadCapacitySummary();
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'No fue posible guardar el horario.');
  } finally {
    savingDay.value = null;
  }
}

async function createException() {
  savingException.value = true;
  try {
    await api.post('services/working-exceptions/', {
      technician: selectedTechnicianUuid.value,
      exception_type: exceptionForm.exception_type,
      start_date: exceptionForm.start_date,
      end_date: exceptionForm.end_date,
      start_time: exceptionForm.start_time || null,
      end_time: exceptionForm.end_time || null,
      reason: exceptionForm.reason,
    });
    toast.success('Registrado correctamente.');
    showNewException.value = false;
    Object.assign(exceptionForm, { exception_type: 'VACATION', start_date: '', end_date: '', start_time: '', end_time: '', reason: '' });
    await Promise.all([loadExceptions(), loadCapacitySummary()]);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'No fue posible registrar.');
  } finally {
    savingException.value = false;
  }
}

async function deleteException(uuid) {
  deletingUuid.value = uuid;
  try {
    await api.delete(`services/working-exceptions/${uuid}/`);
    toast.success('Liberado correctamente.');
    await Promise.all([loadExceptions(), loadCapacitySummary()]);
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'No fue posible liberar.');
  } finally {
    deletingUuid.value = null;
  }
}

onMounted(async () => {
  await Promise.all([loadTechnicians(), loadCapacitySummary()]);
});
</script>

<style scoped>
.action-form { background: #f9fafb; }
</style>
