<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Mano de Obra (Renta)</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nueva Mano de Obra
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Nombre</th>
              <th>Precio / Hora</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
              </td>
            </tr>
            <tr v-else-if="labors.length === 0">
              <td colspan="4" class="text-center py-5 text-muted">Sin mano de obra registrada.</td>
            </tr>
            <template v-for="lab in labors" :key="lab.uuid">
              <tr v-if="pendingDelete?.uuid === lab.uuid" class="bg-danger-subtle">
                <td colspan="4" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ lab.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(lab)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="fw-bold">{{ lab.name }}</td>
                <td>{{ formatCurrency(lab.price_per_hour) }}</td>
                <td>
                  <span :class="lab.is_active ? 'badge bg-success-subtle text-success' : 'badge bg-secondary-subtle text-secondary'">
                    {{ lab.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(lab)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = lab" title="Eliminar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nueva Mano de Obra' : 'Editar Mano de Obra'"
      :subtitle="mode === 'create' ? 'Servicio adicional para rentas' : `Modificando: ${selected?.name}`"
      width="400px"
    >
      <RentalLaborForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { formatCOP } from '@/utils/money';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import RentalLaborForm from './RentalLaborForm.vue';

const api = useApi();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const loading = ref(true);
const actionLoading = ref(false);
const labors = ref([]);
const pendingDelete = ref(null);

const fetchLabors = async () => {
  loading.value = true;
  try {
    const res = await api.get('dashboard/rental-labor/');
    labors.value = res.data.results || res.data;
  } catch {
    toast.error('Error al cargar mano de obra');
  } finally {
    loading.value = false;
  }
};

const executeDelete = async (lab) => {
  actionLoading.value = true;
  try {
    await api.delete(`dashboard/rental-labor/${lab.id}/`);
    toast.success(`"${lab.name}" eliminado`);
    await fetchLabors();
  } catch {
    toast.error('No se pudo eliminar');
  } finally {
    actionLoading.value = false;
    pendingDelete.value = null;
  }
};

function formatCurrency(value) {
  return formatCOP(value, { withSymbol: true });
}

const onFormSuccess = () => { close(); fetchLabors(); };
onMounted(fetchLabors);
</script>
