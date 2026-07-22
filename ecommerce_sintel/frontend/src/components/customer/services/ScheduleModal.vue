<template>
  <div v-if="modelValue" class="sm-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="sm-box">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="fw-bold mb-0">{{ isReschedule ? 'Reprogramar visita' : 'Planear visita' }}</h5>
        <button type="button" class="btn-close" @click="$emit('update:modelValue', false)"></button>
      </div>

      <div class="row g-2">
        <div class="col-6">
          <label class="form-label small">Fecha</label>
          <input v-model="form.scheduled_date" type="date" class="form-control">
        </div>
        <div class="col-6">
          <label class="form-label small">Hora</label>
          <input v-model="form.scheduled_time" type="time" class="form-control">
        </div>
        <div class="col-12">
          <label class="form-label small">Duracion estimada (minutos)</label>
          <input v-model.number="form.estimated_duration_minutes" type="number" min="1" class="form-control">
        </div>
        <div class="col-12" v-if="!isReschedule">
          <label class="form-label small">Observaciones</label>
          <textarea v-model="form.notes" class="form-control" rows="2"></textarea>
        </div>
      </div>

      <button
        class="btn btn-primary w-100 mt-3"
        :disabled="!form.scheduled_date || !form.scheduled_time || saving"
        @click="save"
      >
        {{ saving ? 'Guardando...' : 'Guardar programacion' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  isReschedule: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  initial: { type: Object, default: () => ({}) },
});
const emit = defineEmits(['update:modelValue', 'save']);

const form = reactive({
  scheduled_date: '',
  scheduled_time: '',
  estimated_duration_minutes: 60,
  notes: '',
});

watch(() => props.modelValue, (open) => {
  if (open) {
    Object.assign(form, {
      scheduled_date: props.initial.scheduled_date || '',
      scheduled_time: (props.initial.scheduled_time || '').slice(0, 5),
      estimated_duration_minutes: props.initial.estimated_duration_minutes || 60,
      notes: props.initial.notes || '',
    });
  }
});

function save() {
  emit('save', { ...form });
}
</script>

<style scoped>
.sm-overlay {
  position: fixed; inset: 0; z-index: 1060;
  background: rgba(15, 23, 42, .5);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.sm-box {
  background: #fff; border-radius: 16px; padding: 24px;
  width: 100%; max-width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}
</style>
