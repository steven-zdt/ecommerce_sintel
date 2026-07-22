<template>
  <div class="p-3">
    <div class="d-flex align-items-center justify-content-between mb-4">
      <h4 class="fw-bold mb-0">Gestión de Categorías de Servicio</h4>
      <div class="d-flex align-items-center gap-2">
        <div class="btn-group btn-group-sm">
          <button class="btn" :class="viewMode === 'table' ? 'btn-primary' : 'btn-outline-secondary'" @click="viewMode = 'table'"><i class="bi bi-table"></i></button>
          <button class="btn" :class="viewMode === 'tree' ? 'btn-primary' : 'btn-outline-secondary'" @click="viewMode = 'tree'"><i class="bi bi-diagram-3"></i></button>
        </div>
        <button class="btn btn-primary" @click="beginCreate" :disabled="isCreating">
          <i class="bi bi-plus-lg me-1"></i> Nueva Categoría
        </button>
      </div>
    </div>

    <!-- Vista de Árbol -->
    <ServiceCategoryTree
      v-if="viewMode === 'tree'"
      :categories="store.categories"
      :loading="store.loading"
    />
    <!-- Vista de Tabla -->
    <div v-if="viewMode === 'table'" class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 30%">Nombre</th>
              <th class="py-3" style="width: 25%">Categoría Padre</th>
              <th class="py-3" style="width: 30%">Descripción</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <!-- Fila de Creación Rápida -->
            <tr v-if="isCreating" class="bg-light-subtle">
              <td class="px-4">
                <input v-model="newCategory.name" type="text" class="form-control form-control-sm" placeholder="Nombre de la categoría" />
              </td>
              <td>
                <select v-model="newCategory.parent" class="form-select form-select-sm">
                  <option :value="null">-- Sin padre --</option>
                  <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">{{ cat.text }}</option>
                </select>
              </td>
              <td>
                <input v-model="newCategory.description" type="text" class="form-control form-control-sm" placeholder="Descripción corta" />
              </td>
              <td class="text-center">
                <div class="form-check form-switch d-flex justify-content-center">
                  <input v-model="newCategory.is_active" class="form-check-input" type="checkbox" role="switch" />
                </div>
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
            <tr v-if="store.loading && !store.categories.length"><td colspan="5" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td></tr>
            <tr v-else-if="!store.categories.length && !isCreating"><td colspan="5" class="text-center py-5 text-muted">No hay categorías.</td></tr>
            
            <template v-for="category in store.categories" :key="category.uuid">
               <!-- Fila de confirmación de borrado -->
              <tr v-if="pendingDelete?.uuid === category.uuid" class="bg-danger-subtle">
                <td colspan="5" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ category.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="handleDelete(category)" :disabled="store.actionLoading">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4">
                  <InlineTextEditor
                    :model-value="category.name"
                    :on-save="(value) => handleSave(category, { name: value })"
                  />
                </td>
                <td>
                  <InlineSelectEditor
                    :model-value="category.parent"
                    :options="categoryOptions.filter(opt => opt.value !== category.uuid)"
                    placeholder="-- Sin padre --"
                    :on-save="(value) => handleSave(category, { parent: value })"
                  />
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="category.description"
                    :on-save="(value) => handleSave(category, { description: value })"
                  />
                </td>
                <td class="text-center">
                  <InlineSwitch
                    :model-value="category.is_active"
                    :on-save="(value) => handleSave(category, { is_active: value })"
                  />
                </td>
                <td class="text-end px-4">
                  <TableRowActions
                    :item="category"
                    :actions="rowActions"
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
import { ref, onMounted, computed } from 'vue';
import { useTechnicalServicesCatalogStore } from '@/store/technicalServicesAdmin/catalog';
import { useToast } from '@/composables/useToast';

import InlineTextEditor from './InlineTextEditor.vue';
import InlineSelectEditor from './InlineSelectEditor.vue';
import InlineSwitch from './InlineSwitch.vue';
import TableRowActions from './TableRowActions.vue';
import ServiceCategoryTree from './ServiceCategoryTree.vue';

const store = useTechnicalServicesCatalogStore();
const toast = useToast();

const isCreating = ref(false);
const newCategory = ref({});
const pendingDelete = ref(null);
const viewMode = ref('table');

const rowActions = [
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

const categoryOptions = computed(() =>
  store.categories.map(c => ({ value: c.uuid, text: c.name }))
);

onMounted(() => {
  store.fetchCategories();
});

const beginCreate = () => {
  newCategory.value = { name: '', description: '', parent: null, is_active: true };
  isCreating.value = true;
};

const cancelCreate = () => {
  isCreating.value = false;
};

const handleCreate = async () => {
  if (!newCategory.value.name) {
    return toast.error('El nombre es obligatorio.');
  }
  const { ok, error } = await store.createCategory(newCategory.value);
  if (ok) {
    toast.success('Categoría creada.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear la categoría.');
  }
};

const handleSave = async (category, payload) => {
  const { ok, error } = await store.updateCategory(category.uuid, payload);
  if (ok) {
    toast.success(`Categoría "${category.name}" actualizada.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    store.fetchCategories(); // Revert changes on error
    throw new Error(error);
  }
};

const handleDelete = async (category) => {
  const { ok, error } = await store.deleteCategory(category.uuid);
  if (ok) {
    toast.success(`Categoría "${category.name}" eliminada.`);
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar.');
  }
};

</script>