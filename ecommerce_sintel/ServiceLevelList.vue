<template>
  <div class="p-3">
    <div class="d-flex align-items-center justify-content-between mb-4">
      <h4 class="fw-bold mb-0">Gestión de Niveles de Servicio</h4>
      <button class="btn btn-primary" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Nivel
      </button>
    </div>

    <div class="card border-0 shadow-sm overflow-hidden" style="max-width: 800px;">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3">Nombre del Nivel</th>
              <th class="py-3 text-end px-4" style="width: 120px;">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <!-- Fila de Creación Rápida -->
            <tr v-if="isCreating" class="bg-light-subtle">
              <td class="px-4">
                <input 
                  v-model="newLevel.name" 
                  type="text" 
                  class="form-control form-control-sm" 
                  placeholder="Nombre del nuevo nivel" 
                  @keydown.enter="handleCreate"
                />
              </td>
              <td class="text-end px-4">
                <div class="d-flex gap-2 justify-content-end">
                  <button class="btn btn-sm btn-success" @click="handleCreate" :disabled="store.actionLoading">
                    <span v-if="store.actionLoading" class="spinner-border spinner-border-sm"></span>
                    <i v-else class="bi bi-check-lg"></i>
                  </button>
                  <button class="btn btn-sm btn-secondary" @click="cancelCreate"><i class="bi bi-x-lg"></i></button>
                </div>
              </td>
            </tr>

            <!-- Filas de Datos -->
            <tr v-if="store.loading && !store.levels.length"><td colspan="2" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td></tr>
            <tr v-else-if="!store.levels.length && !isCreating"><td colspan="2" class="text-center py-5 text-muted">No hay niveles de servicio.</td></tr>
            
            <template v-for="level in store.levels" :key="level.uuid">
               <!-- Fila de confirmación de borrado -->
              <tr v-if="pendingDelete?.uuid === level.uuid" class="bg-danger-subtle">
                <td colspan="2" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ level.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="handleDelete(level)" :disabled="store.actionLoading">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4">
                  <InlineTextEditor
                    :model-value="level.name"
                    :on-save="(value) => handleSave(level, { name: value })"
                  />
                </td>
                <td class="text-end px-4">
                  <TableRowActions
                    :item="level"
                    :actions="rowActions"
                    @duplicate="handleDuplicate"
                    @delete="pendingDelete = $event"
                  />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useTechnicalServicesAdminStore } from '@/stores/technicalServicesAdmin';
import { useToast } from '@/composables/useToast';

import InlineTextEditor from '@/components/ui/InlineTextEditor.vue';
import TableRowActions from '@/components/ui/TableRowActions.vue';

const store = useTechnicalServicesAdminStore();
const toast = useToast();

const isCreating = ref(false);
const newLevel = ref({ name: '' });
const pendingDelete = ref(null);

const rowActions = [
  { key: 'duplicate', label: 'Duplicar', icon: 'bi bi-copy' },
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

onMounted(() => {
  store.fetchLevels();
});

const beginCreate = () => {
  newLevel.value = { name: '' };
  isCreating.value = true;
};

const cancelCreate = () => {
  isCreating.value = false;
};

const handleCreate = async () => {
  if (!newLevel.value.name.trim()) {
    return toast.error('El nombre es obligatorio.');
  }
  const { ok, error } = await store.createLevel(newLevel.value);
  if (ok) {
    toast.success('Nivel creado.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear el nivel.');
  }
};

const handleSave = async (level, payload) => {
  const { ok, error } = await store.updateLevel(level.uuid, payload);
  if (ok) {
    toast.success(`Nivel "${level.name}" actualizado.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    store.fetchLevels(); // Revert changes on error
    throw new Error(error);
  }
};

const handleDuplicate = async (level) => {
  const { ok, error } = await store.duplicateLevel(level.uuid);
  if (ok) toast.success(`Nivel "${level.name}" duplicado.`);
  else toast.error(error || 'Error al duplicar.');
};

const handleDelete = async (level) => {
  const { ok, error } = await store.deleteLevel(level.uuid);
  if (ok) {
    toast.success(`Nivel "${level.name}" eliminado.`);
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar.');
  }
};
</script> 