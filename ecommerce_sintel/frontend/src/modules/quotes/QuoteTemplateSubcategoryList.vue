<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h5 class="fw-bold mb-0">Subcategorías</h5>
      <button class="btn btn-primary btn-sm" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nueva Subcategoría
      </button>
    </div>

    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 20%">Categoría</th>
              <th class="py-3" style="width: 20%">Nombre</th>
              <th class="py-3">Descripción</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isCreating" class="bg-light-subtle">
              <td class="px-4">
                <select v-model="newSubcategory.category" class="form-select form-select-sm">
                  <option :value="null">-- Selecciona --</option>
                  <option v-for="cat in store.categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
                </select>
              </td>
              <td>
                <input v-model="newSubcategory.name" type="text" class="form-control form-control-sm" placeholder="CCTV" />
              </td>
              <td>
                <input v-model="newSubcategory.description" type="text" class="form-control form-control-sm" />
              </td>
              <td class="text-center">
                <div class="form-check form-switch d-flex justify-content-center">
                  <input v-model="newSubcategory.is_active" class="form-check-input" type="checkbox" role="switch" />
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

            <tr v-if="store.loading && !store.subcategories.length"><td colspan="5" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td></tr>
            <tr v-else-if="!store.subcategories.length && !isCreating"><td colspan="5" class="text-center py-5 text-muted">No hay subcategorías.</td></tr>

            <template v-for="sub in store.subcategories" :key="sub.uuid">
              <tr v-if="pendingDelete?.uuid === sub.uuid" class="bg-danger-subtle">
                <td colspan="5" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ sub.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="handleDelete(sub)" :disabled="store.actionLoading">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4 small text-muted">{{ sub.category_name }}</td>
                <td>
                  <InlineTextEditor
                    :model-value="sub.name"
                    :on-save="(value) => handleSave(sub, { name: value })"
                  />
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="sub.description"
                    :on-save="(value) => handleSave(sub, { description: value })"
                  />
                </td>
                <td class="text-center">
                  <InlineSwitch
                    :model-value="sub.is_active"
                    :on-save="(value) => handleSave(sub, { is_active: value })"
                  />
                </td>
                <td class="text-end px-4">
                  <TableRowActions
                    :item="sub"
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
import { ref, onMounted } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useToast } from '@/composables/useToast';

import InlineTextEditor from '@/modules/technical_services/InlineTextEditor.vue';
import InlineSwitch from '@/modules/technical_services/InlineSwitch.vue';
import TableRowActions from '@/modules/technical_services/TableRowActions.vue';

const store = useQuoteTemplateBuilderStore();
const toast = useToast();

const isCreating = ref(false);
const newSubcategory = ref({});
const pendingDelete = ref(null);

const rowActions = [
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

onMounted(() => {
  if (!store.categories.length) store.fetchCategories();
  store.fetchSubcategories();
});

const beginCreate = () => {
  newSubcategory.value = { category: null, name: '', description: '', is_active: true };
  isCreating.value = true;
};

const cancelCreate = () => {
  isCreating.value = false;
};

const handleCreate = async () => {
  if (!newSubcategory.value.category) {
    return toast.error('Selecciona una categoría.');
  }
  if (!newSubcategory.value.name) {
    return toast.error('El nombre es obligatorio.');
  }
  const { ok, error } = await store.createSubcategory(newSubcategory.value);
  if (ok) {
    toast.success('Subcategoría creada.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear la subcategoría.');
  }
};

const handleSave = async (sub, payload) => {
  const { ok, error } = await store.updateSubcategory(sub.uuid, payload);
  if (ok) {
    toast.success(`Subcategoría "${sub.name}" actualizada.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    store.fetchSubcategories();
    throw new Error(error);
  }
};

const handleDelete = async (sub) => {
  const { ok, error } = await store.deleteSubcategory(sub.uuid);
  if (ok) {
    toast.success(`Subcategoría "${sub.name}" eliminada.`);
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar.');
  }
};
</script>
