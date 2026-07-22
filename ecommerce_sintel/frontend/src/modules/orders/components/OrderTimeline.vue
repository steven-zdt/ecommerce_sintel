<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h6 class="mb-0">Timeline de la Orden</h6>
          <p class="small text-muted mb-0">Visión vertical del ciclo completo.</p>
        </div>
      </div>

      <StatusTimeline mode="events" :events="normalized" empty-message="No hay eventos registrados todavía." />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';

const props = defineProps({
  timeline: { type: Array, default: () => [] }
});

const normalized = computed(() => props.timeline.map((event) => ({
  key: event.id,
  label: event.event_type || 'Evento',
  description: [event.comment || 'Sin comentario', event.location].filter(Boolean).join(' — '),
  date: event.created_at,
})));
</script>
