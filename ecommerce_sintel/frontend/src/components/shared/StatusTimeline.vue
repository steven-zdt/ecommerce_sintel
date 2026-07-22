<template>
  <div v-if="cancelled" class="stl-cancelled">
    <i class="bi bi-x-circle-fill text-danger fs-4"></i>
    <span class="fw-semibold">{{ cancelledMessage }}</span>
  </div>

  <!-- mode="steps": secuencia fija de etapas conocidas, resalta la posicion actual -->
  <ol v-else-if="mode === 'steps'" class="stl-steps list-unstyled mb-0" :style="accentStyle">
    <li v-for="(step, index) in steps" :key="step.key" :class="{ complete: index <= activeIndex }">
      <span class="stl-dot"><i :class="index < activeIndex ? 'bi bi-check' : step.icon"></i></span>
      <div>
        <strong>{{ step.label }}</strong>
        <small v-if="index === activeIndex">Estado actual</small>
      </div>
    </li>
  </ol>

  <!-- mode="events" (default): lista de eventos ya ocurridos, cada uno con su propio color/fecha -->
  <ol v-else class="stl-events list-unstyled mb-0">
    <li v-for="event in events" :key="event.key" class="stl-event">
      <span class="stl-event-dot" :style="dotStyle(event.color)"><i :class="['bi', event.icon || 'bi-dot']"></i></span>
      <div class="stl-event-body">
        <div class="stl-event-label">{{ event.label }}</div>
        <div v-if="event.description" class="stl-event-desc">{{ event.description }}</div>
        <div v-if="event.date" class="stl-event-date">{{ formatDate(event.date) }}</div>
      </div>
    </li>
    <li v-if="!events.length" class="stl-empty">{{ emptyMessage }}</li>
  </ol>
</template>

<script setup>
import { computed } from 'vue';

// StatusTimeline -- interfaz normalizada que reemplaza los 7 timelines con
// logica de render solapada (ShipmentTimeline, RentalTimeline, ServiceTimeline,
// TrackingTimeline, OperationTimeline, UnifiedTimeline, OrderTimeline -- ver
// AUDITORIA/07_FRONTEND.md FE-M4). Dos variantes reales encontradas en el
// analisis, no una sola: "steps" (secuencia fija con posicion actual, sin
// fechas) y "events" (log de eventos ya ocurridos, cada uno con su fecha) --
// cada vista/composable adapta su propio modelo de datos a esta forma
// normalizada antes de pasarlo aqui (mismo patron que ya usaba
// OperationTimeline.vue al traducir hacia TrackingTimeline.vue).
const props = defineProps({
  mode: { type: String, default: 'events' }, // 'events' | 'steps'
  // mode="steps"
  steps: { type: Array, default: () => [] }, // [{ key, label, icon }]
  activeIndex: { type: Number, default: 0 },
  accentColor: { type: String, default: '#2563eb' },
  cancelled: { type: Boolean, default: false },
  cancelledMessage: { type: String, default: 'Este proceso fue cancelado.' },
  // mode="events"
  events: { type: Array, default: () => [] }, // [{ key, label, icon, color, date, description }]
  emptyMessage: { type: String, default: 'Sin eventos registrados.' },
});

const accentStyle = computed(() => ({ '--stl-accent': props.accentColor }));

function dotStyle(color) {
  if (!color) return {};
  return { background: `${color}22`, color };
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('es-CO', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return '';
  }
}
</script>

<style scoped>
.stl-cancelled {
  display: flex; align-items: center; gap: 10px;
  background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px;
  padding: 14px 16px; color: #7f1d1d;
}

/* mode="steps" */
.stl-steps { --stl-accent: #2563eb; }
.stl-steps li { display: flex; gap: .9rem; position: relative; padding-bottom: 1.35rem; color: #94a3b8; }
.stl-steps li:not(:last-child)::after {
  content: ''; position: absolute; left: 15px; top: 31px;
  width: 2px; height: calc(100% - 25px); background: #e2e8f0;
}
.stl-steps li.complete { color: #172033; }
.stl-steps li.complete:not(:last-child)::after { background: var(--stl-accent); }
.stl-dot { width: 32px; height: 32px; border-radius: 50%; background: #f1f5f9; display: grid; place-items: center; z-index: 1; flex: none; }
.complete .stl-dot { background: var(--stl-accent); color: #fff; }
.stl-steps strong, .stl-steps small { display: block; }
.stl-steps small { color: var(--stl-accent); font-size: .72rem; margin-top: .15rem; }

/* mode="events" */
.stl-event { display: flex; gap: 10px; position: relative; padding-bottom: 20px; }
.stl-event:not(:last-child)::after {
  content: ''; position: absolute; left: 13px; top: 28px;
  width: 2px; height: calc(100% - 20px); background: #e5e7eb;
}
.stl-event-dot {
  width: 26px; height: 26px; border-radius: 50%; background: #f1f5f9; color: #475569;
  display: grid; place-items: center; flex: none; font-size: 12px; z-index: 1;
}
.stl-event-body { padding-top: 2px; }
.stl-event-label { font-size: 13px; font-weight: 600; color: #111827; }
.stl-event-desc  { font-size: 12px; color: #6b7280; margin-top: 1px; }
.stl-event-date  { font-size: 11px; color: #9ca3af; margin-top: 1px; }
.stl-empty { color: #9ca3af; font-size: .875rem; text-align: center; padding: 12px 0; }
</style>
