<template>
  <div>
    <p class="text-muted small mb-3">
      Costos predefinidos de transporte y puesta en marcha. Se pre-rellenaran en la solicitud del cliente.
    </p>

    <div class="row g-3 mb-3">
      <div class="col-6" v-for="field in logisticsFields" :key="field.key">
        <label class="form-label small fw-semibold">{{ field.label }}</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input
            v-model.number="logisticsForm[field.key]"
            type="number"
            min="0"
            step="0.01"
            class="form-control"
            placeholder="0"
          >
        </div>
      </div>
      <div class="col-12">
        <label class="form-label small fw-semibold">Notas internas</label>
        <textarea v-model="logisticsForm.notes" class="form-control form-control-sm" rows="2" placeholder="Observaciones de logistica..."></textarea>
      </div>
    </div>

    <div class="d-flex gap-2">
      <button type="button" class="btn btn-primary w-100" @click="saveLogistics" :disabled="logisticsLoading">
        <span v-if="logisticsLoading" class="spinner-border spinner-border-sm me-2"></span>
        <i v-else class="bi bi-floppy me-1"></i>
        {{ hasLogistics ? 'Actualizar Logistica' : 'Guardar Logistica' }}
      </button>
      <button
        v-if="hasLogistics"
        type="button"
        class="btn btn-outline-danger"
        @click="deleteLogistics"
        :disabled="logisticsLoading"
        title="Eliminar configuracion"
      >
        <i class="bi bi-trash"></i>
      </button>
    </div>

    <div v-if="hasLogistics" class="mt-3">
      <span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size:.72rem">
        <i class="bi bi-check-circle me-1"></i>Logistica configurada
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const logisticsLoading = ref(false);
const hasLogistics = ref(false);
const logisticsForm = reactive({
  delivery_cost: null, pickup_cost: null, installation_cost: null,
  calibration_cost: null, training_cost: null, startup_cost: null, notes: '',
});
const logisticsFields = [
  { key: 'delivery_cost', label: 'Costo Entrega' },
  { key: 'pickup_cost', label: 'Costo Recogida' },
  { key: 'installation_cost', label: 'Instalacion' },
  { key: 'calibration_cost', label: 'Calibracion' },
  { key: 'training_cost', label: 'Capacitacion' },
  { key: 'startup_cost', label: 'Puesta en Marcha' },
];

async function fetchLogistics() {
  try {
    const res = await api.get(`dashboard/equipment/${props.equipmentUuid}/logistics/`);
    if (res.data?.uuid) {
      hasLogistics.value = true;
      const d = res.data;
      Object.assign(logisticsForm, {
        delivery_cost: d.delivery_cost != null ? parseFloat(d.delivery_cost) : null,
        pickup_cost: d.pickup_cost != null ? parseFloat(d.pickup_cost) : null,
        installation_cost: d.installation_cost != null ? parseFloat(d.installation_cost) : null,
        calibration_cost: d.calibration_cost != null ? parseFloat(d.calibration_cost) : null,
        training_cost: d.training_cost != null ? parseFloat(d.training_cost) : null,
        startup_cost: d.startup_cost != null ? parseFloat(d.startup_cost) : null,
        notes: d.notes || '',
      });
    } else {
      hasLogistics.value = false;
    }
  } catch {
    hasLogistics.value = false;
  }
}

async function saveLogistics() {
  logisticsLoading.value = true;
  try {
    await api.put(`dashboard/equipment/${props.equipmentUuid}/logistics/`, { ...logisticsForm });
    hasLogistics.value = true;
    toast.success('Costos de logistica guardados');
  } catch (e) {
    handleError(e, 'Error al guardar logistica');
  } finally {
    logisticsLoading.value = false;
  }
}

async function deleteLogistics() {
  logisticsLoading.value = true;
  try {
    await api.delete(`dashboard/equipment/${props.equipmentUuid}/logistics/`);
    hasLogistics.value = false;
    Object.assign(logisticsForm, {
      delivery_cost: null, pickup_cost: null, installation_cost: null,
      calibration_cost: null, training_cost: null, startup_cost: null, notes: '',
    });
    toast.success('Configuracion de logistica eliminada');
  } catch {
    toast.error('Error al eliminar logistica');
  } finally {
    logisticsLoading.value = false;
  }
}

onMounted(fetchLogistics);
</script>
