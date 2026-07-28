<template>
  <div>
    <h6 class="fw-semibold mb-3">Configuración Logística</h6>

    <div class="card border-0 shadow-sm p-4">
      <div v-if="!config && !editing" class="text-center py-4 text-muted">
        <i class="bi bi-truck fs-2 d-block mb-2"></i>
        <p>Sin configuración logística.</p>
        <button class="btn btn-primary btn-sm" @click="startEdit">
          <i class="bi bi-plus-lg me-1"></i> Configurar Logística
        </button>
      </div>

      <div v-else-if="!editing">
        <!-- Vista de lectura -->
        <div class="row g-3 mb-3">
          <div class="col-sm-6 col-md-4" v-for="field in logisticsFields" :key="field.key">
            <div class="border rounded-3 p-3 bg-light">
              <div class="text-muted small mb-1">{{ field.label }}</div>
              <div class="fw-semibold">{{ formatCOP(config?.[field.key]) || '—' }}</div>
            </div>
          </div>
          <div class="col-12" v-if="config?.notes">
            <div class="border rounded-3 p-3 bg-light">
              <div class="text-muted small mb-1">Notas</div>
              <div>{{ config.notes }}</div>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-primary" @click="startEdit">
            <i class="bi bi-pencil me-1"></i> Editar
          </button>
          <button
            class="btn btn-sm btn-outline-danger"
            @click="deleteConfig"
            :disabled="store.actionLoading"
          >
            <i class="bi bi-trash me-1"></i> Eliminar
          </button>
        </div>
      </div>

      <!-- Formulario de edición -->
      <form v-else @submit.prevent="save">
        <div class="row g-3 mb-3">
          <div class="col-sm-6 col-md-4" v-for="field in logisticsFields" :key="field.key">
            <label class="form-label small fw-semibold">{{ field.label }}</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input
                v-model.number="form[field.key]"
                type="number"
                step="0.01"
                min="0"
                class="form-control"
                :placeholder="field.label"
              />
            </div>
          </div>
          <div class="col-12">
            <label class="form-label small fw-semibold">Notas</label>
            <textarea v-model="form.notes" class="form-control form-control-sm" rows="2" placeholder="Observaciones de logística..."></textarea>
          </div>
        </div>
        <div class="d-flex gap-2">
          <button type="submit" class="btn btn-sm btn-primary" :disabled="store.actionLoading">
            <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
            Guardar
          </button>
          <button type="button" class="btn btn-sm btn-light border" @click="editing = false">Cancelar</button>
        </div>
        <div v-if="error" class="alert alert-danger mt-3 py-2 small">{{ error }}</div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { formatCOP as formatCOPBase } from '@/utils/money';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const store = useRentingCatalogAdminStore();
const toast = useToast();

const editing = ref(false);
const error = ref(null);
const config = computed(() => store.logisticsConfig);

const logisticsFields = [
  { key: 'delivery_cost',     label: 'Costo de Entrega' },
  { key: 'pickup_cost',       label: 'Costo de Recogida' },
  { key: 'installation_cost', label: 'Instalación' },
  { key: 'calibration_cost',  label: 'Calibración' },
  { key: 'training_cost',     label: 'Capacitación' },
  { key: 'startup_cost',      label: 'Puesta en Marcha' },
];

const form = reactive({
  delivery_cost: null,
  pickup_cost: null,
  installation_cost: null,
  calibration_cost: null,
  training_cost: null,
  startup_cost: null,
  notes: '',
});

function formatCOP(value) {
  if (!value) return null;
  return formatCOPBase(value, { withSymbol: true });
}

function startEdit() {
  if (config.value) {
    Object.assign(form, { ...config.value });
  }
  editing.value = true;
  error.value = null;
}

async function save() {
  error.value = null;
  const result = await store.upsertLogisticsConfig(props.equipmentUuid, { ...form });
  if (result.ok) {
    toast.success('Configuración logística guardada.');
    editing.value = false;
  } else {
    error.value = result.error;
  }
}

async function deleteConfig() {
  const result = await store.deleteLogisticsConfig(props.equipmentUuid);
  if (result.ok) {
    toast.success('Configuración eliminada.');
  } else {
    toast.error(result.error);
  }
}

onMounted(() => store.fetchLogisticsConfig(props.equipmentUuid));
</script>
