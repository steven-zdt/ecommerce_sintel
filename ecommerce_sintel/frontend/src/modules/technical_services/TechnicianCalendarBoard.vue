<template>
  <div>
    <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <h5 class="fw-bold mb-0 me-3">Agenda de Técnicos</h5>

      <div class="btn-group btn-group-sm">
        <button
          class="btn"
          :class="viewMode === 'day' ? 'btn-primary' : 'btn-outline-primary'"
          @click="setViewMode('day')"
        >Día</button>
        <button
          class="btn"
          :class="viewMode === 'week' ? 'btn-primary' : 'btn-outline-primary'"
          @click="setViewMode('week')"
        >Semana</button>
      </div>

      <div class="btn-group btn-group-sm">
        <button class="btn btn-light border" @click="navigate(-1)"><i class="bi bi-chevron-left"></i></button>
        <button class="btn btn-light border" @click="goToday">Hoy</button>
        <button class="btn btn-light border" @click="navigate(1)"><i class="bi bi-chevron-right"></i></button>
      </div>

      <span class="fw-semibold small text-muted">{{ rangeLabel }}</span>

      <div class="ms-auto d-flex align-items-center gap-2">
        <span class="small text-muted">Capacidad: {{ capacitySummary.free_hours ?? '—' }}h libres / {{ capacitySummary.capacity_hours ?? '—' }}h</span>
      </div>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border spinner-border-sm text-primary me-2"></div>
      <span class="text-muted">Cargando agenda...</span>
    </div>

    <div v-else-if="!feed.technicians.length" class="text-center text-muted py-5">
      <i class="bi bi-calendar-x fs-2 d-block mb-2"></i>
      Sin técnicos activos para mostrar.
    </div>

    <!-- Vista Día: linea de tiempo horizontal por tecnico -->
    <div v-else-if="viewMode === 'day'" class="card border-0 shadow-sm">
      <div class="timeline-header">
        <div class="timeline-tech-col"></div>
        <div class="timeline-track">
          <span v-for="h in hourMarks" :key="h" class="timeline-hour" :style="hourStyle(h)">{{ h }}:00</span>
        </div>
      </div>
      <div v-for="tech in feed.technicians" :key="tech.technician_id" class="timeline-row">
        <div class="timeline-tech-col">{{ tech.technician_name }}</div>
        <div class="timeline-track">
          <div v-if="tech.days[0].working_window" class="timeline-working-window" :style="blockStyle(tech.days[0].working_window.start, tech.days[0].working_window.end)"></div>
          <div
            v-for="(exc, i) in tech.days[0].exceptions"
            :key="'exc-' + i"
            class="timeline-block timeline-exception"
            :style="blockStyle(exc.start_time || '00:00', exc.end_time || '23:59')"
            :title="exc.exception_type_display + (exc.reason ? ': ' + exc.reason : '')"
          >{{ exc.exception_type_display }}</div>
          <div
            v-for="op in tech.days[0].operations"
            :key="op.uuid"
            class="timeline-block timeline-operation"
            :class="enums.cssClass('service-operation-statuses', op.status)"
            :style="blockStyle(op.start_time, op.end_time)"
            :title="`${op.customer_name} — ${op.status_display} (${op.start_time?.slice(0,5)}-${op.end_time?.slice(0,5)})`"
            @click="openReschedule(tech, tech.days[0].date, op)"
          >{{ op.customer_name }}</div>
        </div>
      </div>
    </div>

    <!-- Vista Semana: grilla compacta tecnico x dia -->
    <div v-else class="card border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-bordered align-top mb-0 week-table">
          <thead class="bg-light text-muted small text-uppercase">
            <tr>
              <th style="width:160px;">Técnico</th>
              <th v-for="day in feed.technicians[0]?.days || []" :key="day.date">
                {{ formatDayHeader(day.date) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tech in feed.technicians" :key="tech.technician_id">
              <td class="fw-semibold small">{{ tech.technician_name }}</td>
              <td v-for="day in tech.days" :key="day.date" class="week-cell">
                <div v-if="!day.working_window" class="text-muted small fst-italic">Sin horario</div>
                <div
                  v-for="exc in day.exceptions"
                  :key="'wexc-' + exc.exception_type + day.date"
                  class="week-chip bg-secondary-subtle text-secondary"
                >{{ exc.exception_type_display }}</div>
                <div
                  v-for="op in day.operations"
                  :key="op.uuid"
                  class="week-chip"
                  :class="enums.cssClass('service-operation-statuses', op.status)"
                  @click="openReschedule(tech, day.date, op)"
                >
                  {{ op.start_time?.slice(0,5) }} {{ op.customer_name }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ScheduleModal
      v-model="showReschedule"
      :is-reschedule="true"
      :saving="saving"
      :initial="rescheduleInitial"
      @save="saveReschedule"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useEnums } from '@/composables/useEnums';
import ScheduleModal from '@/components/customer/services/ScheduleModal.vue';

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const enums = useEnums();

const viewMode = ref('day');
const anchorDate = ref(new Date());
const loading = ref(false);
const saving = ref(false);
const feed = ref({ technicians: [] });
const capacitySummary = ref({});

const showReschedule = ref(false);
const rescheduleTarget = ref(null);
const rescheduleInitial = ref({});

const FRAME_START_HOUR = 6;
const FRAME_END_HOUR = 20;
const hourMarks = Array.from(
  { length: FRAME_END_HOUR - FRAME_START_HOUR + 1 },
  (_, i) => FRAME_START_HOUR + i,
);

function toDateStr(d) {
  return d.toISOString().slice(0, 10);
}

const rangeStart = computed(() => {
  if (viewMode.value === 'day') return new Date(anchorDate.value);
  const d = new Date(anchorDate.value);
  const dow = (d.getDay() + 6) % 7; // lunes=0
  d.setDate(d.getDate() - dow);
  return d;
});

const rangeEnd = computed(() => {
  const d = new Date(rangeStart.value);
  d.setDate(d.getDate() + (viewMode.value === 'day' ? 0 : 6));
  return d;
});

const rangeLabel = computed(() => {
  const opts = { day: 'numeric', month: 'short' };
  if (viewMode.value === 'day') return rangeStart.value.toLocaleDateString('es-CO', { ...opts, year: 'numeric' });
  return `${rangeStart.value.toLocaleDateString('es-CO', opts)} — ${rangeEnd.value.toLocaleDateString('es-CO', { ...opts, year: 'numeric' })}`;
});

function formatDayHeader(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric' });
}

function setViewMode(mode) {
  viewMode.value = mode;
}

function navigate(direction) {
  const step = viewMode.value === 'day' ? 1 : 7;
  const d = new Date(anchorDate.value);
  d.setDate(d.getDate() + direction * step);
  anchorDate.value = d;
}

function goToday() {
  anchorDate.value = new Date();
}

function timeToMinutes(t) {
  if (!t) return 0;
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

function blockStyle(startTime, endTime) {
  const frameStart = FRAME_START_HOUR * 60;
  const frameEnd = FRAME_END_HOUR * 60;
  const frameSpan = frameEnd - frameStart;
  const left = Math.max(0, ((timeToMinutes(startTime) - frameStart) / frameSpan) * 100);
  const width = Math.max(1, ((timeToMinutes(endTime) - timeToMinutes(startTime)) / frameSpan) * 100);
  return { left: `${left}%`, width: `${width}%` };
}

function hourStyle(hour) {
  const frameStart = FRAME_START_HOUR * 60;
  const frameEnd = FRAME_END_HOUR * 60;
  const left = (((hour * 60) - frameStart) / (frameEnd - frameStart)) * 100;
  return { left: `${left}%` };
}

async function load() {
  loading.value = true;
  try {
    const params = { start_date: toDateStr(rangeStart.value), end_date: toDateStr(rangeEnd.value) };
    const [calendarRes, summaryRes] = await Promise.all([
      api.get('services/technician-availability/calendar/', { params }),
      api.get('services/technician-availability/summary/', { params: { date: toDateStr(rangeStart.value) } }),
    ]);
    feed.value = calendarRes.data;
    capacitySummary.value = summaryRes.data;
  } catch (e) {
    handleError(e, 'No fue posible cargar la agenda.');
  } finally {
    loading.value = false;
  }
}

function openReschedule(tech, date, operation) {
  rescheduleTarget.value = operation;
  rescheduleInitial.value = {
    scheduled_date: date,
    scheduled_time: operation.start_time,
    estimated_duration_minutes: operation.estimated_duration_minutes,
  };
  showReschedule.value = true;
}

async function saveReschedule(form) {
  if (!rescheduleTarget.value) return;
  saving.value = true;
  try {
    await api.post(`service-operations/${rescheduleTarget.value.uuid}/reschedule/`, form);
    toast.success('Operación reprogramada.');
    showReschedule.value = false;
    await load();
  } catch (e) {
    handleError(e, 'No fue posible reprogramar.');
  } finally {
    saving.value = false;
  }
}

watch([viewMode, anchorDate], load);

onMounted(async () => {
  await Promise.all([enums.ensure('service-operation-statuses'), load()]);
});
</script>

<style scoped>
.timeline-header, .timeline-row {
  display: flex;
  border-bottom: 1px solid #f1f5f9;
}
.timeline-tech-col {
  width: 160px;
  flex-shrink: 0;
  padding: 10px 12px;
  font-weight: 600;
  font-size: 0.85rem;
  border-right: 1px solid #f1f5f9;
}
.timeline-track {
  position: relative;
  flex: 1;
  min-height: 44px;
}
.timeline-hour {
  position: absolute;
  top: 0;
  font-size: 0.7rem;
  color: #94a3b8;
  transform: translateX(-4px);
}
.timeline-header {
  min-height: 24px;
}
.timeline-working-window {
  position: absolute;
  top: 4px;
  bottom: 4px;
  background: #f0fdf4;
  border: 1px dashed #bbf7d0;
  border-radius: 4px;
}
.timeline-block {
  position: absolute;
  top: 6px;
  bottom: 6px;
  border-radius: 6px;
  padding: 2px 6px;
  font-size: 0.7rem;
  overflow: hidden;
  white-space: nowrap;
  cursor: pointer;
}
.timeline-exception {
  background: repeating-linear-gradient(45deg, #e2e8f0, #e2e8f0 6px, #f1f5f9 6px, #f1f5f9 12px);
  color: #64748b;
  cursor: default;
}
.week-table td, .week-table th { vertical-align: top; }
.week-cell { min-width: 130px; }
.week-chip {
  display: block;
  border-radius: 6px;
  padding: 2px 6px;
  font-size: 0.72rem;
  margin-bottom: 3px;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
