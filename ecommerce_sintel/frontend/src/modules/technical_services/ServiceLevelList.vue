<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Niveles de Servicio</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Nivel
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3">Nombre</th>
              <th class="py-3">Slug</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="3" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando niveles...</span>
              </td>
            </tr>
            <tr v-else-if="levels.length === 0">
              <td colspan="3" class="text-center py-5 text-muted">
                <i class="bi bi-bar-chart-steps fs-2 d-block mb-2"></i>
                Sin niveles registrados.
              </td>
            </tr>
            <template v-for="lvl in levels" :key="lvl.uuid">
              <tr v-if="pendingDelete?.uuid === lvl.uuid" class="bg-danger-subtle">
                <td colspan="3" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar nivel <strong>{{ lvl.name }}</strong>? Esta acción es permanente.</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(lvl)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4 fw-semibold text-dark">{{ lvl.name }}</td>
                <td><code class="small text-muted">{{ lvl.slug }}</code></td>
                <td class="text-end px-4">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(lvl)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = lvl" title="Eliminar">
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
      :title="mode === 'create' ? 'Nuevo Nivel' : 'Editar Nivel'"
      :subtitle="mode === 'create' ? 'Define un nivel de complejidad de servicio' : `Modificando: ${selected?.name}`"
      width="380px"
    >
      <ServiceLevelForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useTechnicalServicesCatalogStore } from '@/store/technicalServicesAdmin/catalog';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import ServiceLevelForm from './ServiceLevelForm.vue';

const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const store = useTechnicalServicesCatalogStore();
const { levels, loading, actionLoading } = storeToRefs(store);
const pendingDelete = ref(null);

// Niveles: solo endpoint público (IsAdminUser en escritura, AllowAny en lectura)
const fetchLevels = async () => {
  store.loading = true;
  try {
    await store.fetchLevels();
  } catch {
    toast.error('Error al cargar niveles');
  } finally {
    store.loading = false;
  }
};

const executeDelete = async (lvl) => {
  const res = await store.deleteLevel(lvl.uuid);
  if (res.ok) {
    toast.success(`Nivel "${lvl.name}" eliminado`);
    await fetchLevels();
  } else {
    toast.error(res.error || 'No se pudo eliminar el nivel');
  }
  pendingDelete.value = null;
};

const onFormSuccess = () => { close(); fetchLevels(); };
onMounted(fetchLevels);
</script>
