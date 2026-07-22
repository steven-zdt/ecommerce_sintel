<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h5 class="fw-bold mb-0">Tipos de Equipo</h5>
      <button class="btn btn-primary btn-sm" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Tipo
      </button>
    </div>

    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 25%">Nombre</th>
              <th class="py-3" style="width: 15%">Icono</th>
              <th class="py-3">Descripción</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isCreating" class="bg-light-subtle">
              <td class="px-4">
                <input v-model="newType.name" type="text" class="form-control form-control-sm" placeholder="Camara IP" />
              </td>
              <td>
                <input v-model="newType.icon" type="text" class="form-control form-control-sm" placeholder="bi-camera-video" />
              </td>
              <td>
                <input v-model="newType.description" type="text" class="form-control form-control-sm" />
              </td>
              <td class="text-center">
                <div class="form-check form-switch d-flex justify-content-center">
                  <input v-model="newType.is_active" class="form-check-input" type="checkbox" role="switch" />
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

            <tr v-if="store.loading && !store.equipmentTypes.length"><td colspan="5" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td></tr>
            <tr v-else-if="!store.equipmentTypes.length && !isCreating"><td colspan="5" class="text-center py-5 text-muted">No hay tipos de equipo.</td></tr>

            <template v-for="type in store.equipmentTypes" :key="type.uuid">
              <tr v-if="pendingDelete?.uuid === type.uuid" class="bg-danger-subtle">
                <td colspan="5" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ type.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="handleDelete(type)" :disabled="store.actionLoading">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4">
                  <InlineTextEditor
                    :model-value="type.name"
                    :on-save="(value) => handleSave(type, { name: value })"
                  />
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="type.icon"
                    :on-save="(value) => handleSave(type, { icon: value })"
                  >
                    <template #default="{ value }">
                      <span class="editable-value"><i v-if="value" :class="['bi', value, 'me-1']"></i>{{ value || 'Sin icono' }}</span>
                    </template>
                  </InlineTextEditor>
                </td>
                <td>
                  <InlineTextEditor
                    :model-value="type.description"
                    :on-save="(value) => handleSave(type, { description: value })"
                  />
                </td>
                <td class="text-center">
                  <InlineSwitch
                    :model-value="type.is_active"
                    :on-save="(value) => handleSave(type, { is_active: value })"
                  />
                </td>
                <td class="text-end px-4">
                  <TableRowActions
                    :item="type"
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
const newType = ref({});
const pendingDelete = ref(null);

const rowActions = [
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

onMounted(() => {
  store.fetchEquipmentTypes();
});

const beginCreate = () => {
  newType.value = { name: '', icon: '', description: '', is_active: true };
  isCreating.value = true;
};

const cancelCreate = () => {
  isCreating.value = false;
};

const handleCreate = async () => {
  if (!newType.value.name) {
    return toast.error('El nombre es obligatorio.');
  }
  const { ok, error } = await store.createEquipmentType(newType.value);
  if (ok) {
    toast.success('Tipo de equipo creado.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear el tipo de equipo.');
  }
};

const handleSave = async (type, payload) => {
  const { ok, error } = await store.updateEquipmentType(type.uuid, payload);
  if (ok) {
    toast.success(`Tipo "${type.name}" actualizado.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    store.fetchEquipmentTypes();
    throw new Error(error);
  }
};

const handleDelete = async (type) => {
  const { ok, error } = await store.deleteEquipmentType(type.uuid);
  if (ok) {
    toast.success(`Tipo "${type.name}" eliminado.`);
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar.');
  }
};
</script>
