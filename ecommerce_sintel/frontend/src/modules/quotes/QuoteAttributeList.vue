<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h5 class="fw-bold mb-0">{{ title }}</h5>
      <button class="btn btn-primary btn-sm" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nuevo
      </button>
    </div>

    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 22%">Nombre</th>
              <th v-if="isInstallationType" class="py-3" style="width: 18%">Subcategoría</th>
              <th class="py-3" style="width: 12%">Icono</th>
              <th class="py-3">Descripción</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isCreating" class="bg-light-subtle">
              <td class="px-4">
                <input v-model="newItem.name" type="text" class="form-control form-control-sm" :placeholder="placeholder" />
              </td>
              <td v-if="isInstallationType">
                <select v-model="newItem.subcategory" class="form-select form-select-sm">
                  <option :value="null">-- Selecciona --</option>
                  <option v-for="sub in store.subcategories" :key="sub.uuid" :value="sub.uuid">{{ sub.category_name }} / {{ sub.name }}</option>
                </select>
              </td>
              <td>
                <input v-model="newItem.icon" type="text" class="form-control form-control-sm" placeholder="bi-tools" />
              </td>
              <td>
                <input v-model="newItem.description" type="text" class="form-control form-control-sm" />
              </td>
              <td class="text-center">
                <div class="form-check form-switch d-flex justify-content-center">
                  <input v-model="newItem.is_active" class="form-check-input" type="checkbox" role="switch" />
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

            <tr v-if="store.loading && !items.length"><td :colspan="colCount" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td></tr>
            <tr v-else-if="!items.length && !isCreating"><td :colspan="colCount" class="text-center py-5 text-muted">No hay registros.</td></tr>

            <template v-for="item in items" :key="item.uuid">
              <tr v-if="pendingDelete?.uuid === item.uuid" class="bg-danger-subtle">
                <td :colspan="colCount" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ item.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="handleDelete(item)" :disabled="store.actionLoading">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4">
                  <InlineTextEditor
                    :model-value="item.name"
                    :on-save="(value) => handleSave(item, { name: value })"
                  />
                </td>
                <td v-if="isInstallationType">
                  <InlineSelectEditor
                    :model-value="item.subcategory_uuid ?? null"
                    :options="subcategoryOptions"
                    placeholder="-- Selecciona --"
                    :on-save="(value) => handleSave(item, { subcategory: value })"
                  />
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="item.icon"
                    :on-save="(value) => handleSave(item, { icon: value })"
                  >
                    <template #default="{ value }">
                      <span class="editable-value"><i v-if="value" :class="['bi', value, 'me-1']"></i>{{ value || 'Sin icono' }}</span>
                    </template>
                  </InlineTextEditor>
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="item.description"
                    :on-save="(value) => handleSave(item, { description: value })"
                  />
                </td>
                <td class="text-center">
                  <InlineSwitch
                    :model-value="item.is_active"
                    :on-save="(value) => handleSave(item, { is_active: value })"
                  />
                </td>
                <td class="text-end px-4">
                  <TableRowActions
                    :item="item"
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

const props = defineProps({
  kind: { type: String, required: true }, // SERVICE_TYPE | INSTALLATION_TYPE | SYSTEM_TYPE
  title: { type: String, required: true },
  placeholder: { type: String, default: '' },
});

const store = useQuoteTemplateBuilderStore();
const toast = useToast();

const isInstallationType = computed(() => props.kind === 'INSTALLATION_TYPE');
const colCount = computed(() => (isInstallationType.value ? 6 : 5));

const items = computed(() => store.attributes.filter((a) => a.kind === props.kind));
const subcategoryOptions = computed(() =>
  store.subcategories.map((s) => ({ value: s.uuid, text: `${s.category_name} / ${s.name}` })),
);

const isCreating = ref(false);
const newItem = ref({});
const pendingDelete = ref(null);

const rowActions = [
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

onMounted(() => {
  store.fetchAttributes();
  if (isInstallationType.value && !store.subcategories.length) store.fetchSubcategories();
});

const beginCreate = () => {
  newItem.value = { kind: props.kind, name: '', subcategory: null, icon: '', description: '', is_active: true };
  isCreating.value = true;
};

const cancelCreate = () => {
  isCreating.value = false;
};

const handleCreate = async () => {
  if (!newItem.value.name) {
    return toast.error('El nombre es obligatorio.');
  }
  if (isInstallationType.value && !newItem.value.subcategory) {
    return toast.error('Selecciona a qué subcategoría pertenece.');
  }
  const { ok, error } = await store.createAttribute({ ...newItem.value, kind: props.kind });
  if (ok) {
    toast.success('Creado correctamente.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear.');
  }
};

const handleSave = async (item, payload) => {
  const { ok, error } = await store.updateAttribute(item.uuid, payload);
  if (ok) {
    toast.success(`"${item.name}" actualizado.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    store.fetchAttributes();
    throw new Error(error);
  }
};

const handleDelete = async (item) => {
  const { ok, error } = await store.deleteAttribute(item.uuid);
  if (ok) {
    toast.success(`"${item.name}" eliminado.`);
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar.');
  }
};
</script>
