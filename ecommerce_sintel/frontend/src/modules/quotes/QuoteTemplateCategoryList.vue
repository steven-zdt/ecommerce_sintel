<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h5 class="fw-bold mb-0">Categorías de Plantilla</h5>
      <button class="btn btn-primary btn-sm" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nueva Categoría
      </button>
    </div>

    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 22%">Nombre</th>
              <th class="py-3" style="width: 18%">Tipo de Servicio</th>
              <th class="py-3" style="width: 12%">Icono</th>
              <th class="py-3">Descripción</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isCreating" class="bg-light-subtle">
              <td class="px-4">
                <input v-model="newCategory.name" type="text" class="form-control form-control-sm" placeholder="Nombre de la categoría" />
              </td>
              <td>
                <select v-model="newCategory.service_type" class="form-select form-select-sm">
                  <option :value="null">-- Sin definir --</option>
                  <option v-for="opt in serviceTypeOptions" :key="opt.value" :value="opt.value">{{ opt.text }}</option>
                </select>
              </td>
              <td>
                <input v-model="newCategory.icon" type="text" class="form-control form-control-sm" placeholder="bi-camera-video" />
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

            <tr v-if="store.loading && !store.categories.length"><td colspan="6" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td></tr>
            <tr v-else-if="!store.categories.length && !isCreating"><td colspan="6" class="text-center py-5 text-muted">No hay categorías.</td></tr>

            <template v-for="category in store.categories" :key="category.uuid">
              <tr v-if="pendingDelete?.uuid === category.uuid" class="bg-danger-subtle">
                <td colspan="6" class="p-0">
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
                    :model-value="category.service_type?.uuid ?? null"
                    :options="serviceTypeOptions"
                    placeholder="-- Sin definir --"
                    :on-save="(value) => handleSave(category, { service_type: value })"
                  />
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="category.icon"
                    :on-save="(value) => handleSave(category, { icon: value })"
                  >
                    <template #default="{ value }">
                      <span class="editable-value"><i v-if="value" :class="['bi', value, 'me-1']"></i>{{ value || 'Sin icono' }}</span>
                    </template>
                  </InlineTextEditor>
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
import { ref, computed, onMounted } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useToast } from '@/composables/useToast';

import InlineTextEditor from '@/modules/technical_services/InlineTextEditor.vue';
import InlineSelectEditor from '@/modules/technical_services/InlineSelectEditor.vue';
import InlineSwitch from '@/modules/technical_services/InlineSwitch.vue';
import TableRowActions from '@/modules/technical_services/TableRowActions.vue';

const store = useQuoteTemplateBuilderStore();
const toast = useToast();

const isCreating = ref(false);
const newCategory = ref({});
const pendingDelete = ref(null);

const rowActions = [
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

const serviceTypeOptions = computed(() =>
  store.attributes.filter((a) => a.kind === 'SERVICE_TYPE').map((a) => ({ value: a.uuid, text: a.name })),
);

onMounted(() => {
  store.fetchCategories();
  store.fetchAttributes('SERVICE_TYPE');
});

const beginCreate = () => {
  newCategory.value = { name: '', service_type: null, icon: '', description: '', is_active: true };
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
    store.fetchCategories();
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
