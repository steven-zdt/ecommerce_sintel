<template>
  <div v-if="modelValue" class="tal-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="tal-box">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="fw-bold mb-0">Agenda del profesional</h5>
        <button type="button" class="btn-close" @click="$emit('update:modelValue', false)"></button>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small">Desde</label>
          <input v-model="dateFrom" type="date" class="form-control form-control-sm" @change="load">
        </div>
        <div class="col-6">
          <label class="form-label small">Hasta</label>
          <input v-model="dateTo" type="date" class="form-control form-control-sm" @change="load">
        </div>
      </div>

      <div v-if="loading" class="text-center text-muted small py-4">Cargando agenda...</div>
      <div v-else-if="!slots.length" class="text-center text-muted small py-4">
        Sin franjas registradas en este rango.
      </div>
      <div v-else class="tal-list">
        <div v-for="slot in slots" :key="slot.uuid" class="tal-row">
          <div>
            <div class="fw-semibold small">{{ slot.date }}</div>
            <div class="text-muted small">{{ slot.start_time.slice(0,5) }} - {{ slot.end_time.slice(0,5) }}</div>
          </div>
          <span class="badge" :class="STATUS_CLASS[slot.status] || 'bg-secondary-subtle text-secondary'">
            {{ slot.status_display }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  profileUuid: { type: String, default: '' },
});
defineEmits(['update:modelValue']);

const api = useApi();
const slots = ref([]);
const loading = ref(false);

const today = new Date();
const in14 = new Date(Date.now() + 14 * 86400000);
const dateFrom = ref(today.toISOString().slice(0, 10));
const dateTo = ref(in14.toISOString().slice(0, 10));

const STATUS_CLASS = {
  AVAILABLE: 'bg-success-subtle text-success',
  PENDING_RESERVATION: 'bg-warning-subtle text-warning',
  BOOKED: 'bg-primary-subtle text-primary',
  BLOCKED: 'bg-secondary-subtle text-secondary',
  VACATION: 'bg-info-subtle text-info',
  SICK_LEAVE: 'bg-danger-subtle text-danger',
};

async function load() {
  if (!props.profileUuid) return;
  loading.value = true;
  try {
    const { data } = await api.get('service-operations/technician-agenda/', {
      params: { profile_uuid: props.profileUuid, date_from: dateFrom.value, date_to: dateTo.value },
    });
    slots.value = data;
  } finally {
    loading.value = false;
  }
}

watch(() => [props.modelValue, props.profileUuid], ([open]) => { if (open) load(); });
</script>

<style scoped>
.tal-overlay {
  position: fixed; inset: 0; z-index: 1060;
  background: rgba(15, 23, 42, .5);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.tal-box {
  background: #fff; border-radius: 16px; padding: 24px;
  width: 100%; max-width: 480px; max-height: 85vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}
.tal-list { display: flex; flex-direction: column; gap: 6px; }
.tal-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border: 1px solid #f3f4f6; border-radius: 8px; }
</style>
