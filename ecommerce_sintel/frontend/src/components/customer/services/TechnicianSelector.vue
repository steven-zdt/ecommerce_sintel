<template>
  <div>
    <div v-if="loading" class="text-center text-muted small py-3">Buscando profesionales disponibles...</div>
    <div v-else-if="!candidates.length" class="text-muted small py-3">
      No hay profesionales disponibles para esta categoria en el horario planeado.
    </div>
    <div v-else class="d-flex flex-column gap-2">
      <TechnicianAvailabilityCard
        v-for="c in candidates"
        :key="c.uuid"
        :candidate="c"
        :selected="selectedUuid === c.uuid"
        @select="selectedUuid = c.uuid"
      />
    </div>
    <button
      class="btn btn-success w-100 mt-3"
      :disabled="!selectedUuid || assigning"
      @click="$emit('assign', selectedUuid)"
    >
      {{ assigning ? 'Asignando...' : 'Asignar y notificar' }}
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import TechnicianAvailabilityCard from './TechnicianAvailabilityCard.vue';

const props = defineProps({
  operationUuid: { type: String, required: true },
  assigning: { type: Boolean, default: false },
});
defineEmits(['assign']);

const api = useApi();
const candidates = ref([]);
const loading = ref(false);
const selectedUuid = ref('');

async function load() {
  if (!props.operationUuid) return;
  loading.value = true;
  selectedUuid.value = '';
  try {
    const { data } = await api.get(`service-operations/${props.operationUuid}/available-technicians/`);
    candidates.value = data;
  } finally {
    loading.value = false;
  }
}

watch(() => props.operationUuid, load, { immediate: true });
defineExpose({ reload: load });
</script>
