<template>
  <StatusTimeline mode="events" :events="normalized" empty-message="Sin eventos de seguimiento aun." />
</template>

<script setup>
import { computed } from 'vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';

const props = defineProps({ events: { type: Array, default: () => [] } });

// NOTIFIED/READY agregados (F8, auditoria E2E): antes CUSTOMER_NOTIFIED/READY_TO_VISIT
// de Servicios Tecnicos caian en el generico NOTE ("Nota"), perdiendo la etiqueta
// especifica pese a tener su propio codigo real en ServiceOperationEvent -- ver
// OperationTimeline.vue. Aditivo puro: Renting nunca emite estos codigos, asi que
// no cambia nada de su timeline existente.
const MILESTONE_LABELS = {
  CREATED:       'Solicitud creada',
  DOCS_APPROVED: 'Documentos aprobados',
  ASSIGNED:      'Recurso asignado',
  SCHEDULED:     'Visita programada',
  NOTIFIED:      'Cliente notificado',
  READY:         'Listo para visita',
  EN_ROUTE:      'En camino',
  IN_PROGRESS:   'En progreso',
  COMPLETED:     'Completado',
  CANCELLED:     'Cancelado',
  NOTE:          'Nota',
};
const MILESTONE_ICONS = {
  CREATED:       'bi-file-earmark-check',
  DOCS_APPROVED: 'bi-patch-check',
  ASSIGNED:      'bi-person-check',
  SCHEDULED:     'bi-calendar-event',
  NOTIFIED:      'bi-envelope-check',
  READY:         'bi-calendar-check',
  EN_ROUTE:      'bi-truck',
  IN_PROGRESS:   'bi-hourglass-split',
  COMPLETED:     'bi-check2-circle',
  CANCELLED:     'bi-x-circle',
  NOTE:          'bi-sticky',
};
const MILESTONE_COLORS = {
  CREATED:       '#6b7280',
  DOCS_APPROVED: '#8b5cf6',
  ASSIGNED:      '#0ea5e9',
  SCHEDULED:     '#0ea5e9',
  NOTIFIED:      '#0ea5e9',
  READY:         '#0ea5e9',
  EN_ROUTE:      '#f59e0b',
  IN_PROGRESS:   '#f59e0b',
  COMPLETED:     '#16a34a',
  CANCELLED:     '#ef4444',
  NOTE:          '#6b7280',
};

const normalized = computed(() => props.events.map((ev) => ({
  key: ev.uuid,
  label: MILESTONE_LABELS[ev.milestone] ?? ev.milestone,
  icon: MILESTONE_ICONS[ev.milestone],
  color: MILESTONE_COLORS[ev.milestone],
  description: ev.description,
  date: ev.created_at,
})));
</script>
