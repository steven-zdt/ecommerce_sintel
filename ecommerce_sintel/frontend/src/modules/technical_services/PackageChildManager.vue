<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h6 class="fw-semibold small mb-0"><i :class="['bi', icon]" class="me-1"></i>{{ title }}</h6>
      <button class="btn btn-sm btn-outline-primary" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i>Agregar
      </button>
    </div>

    <div v-if="isCreating" class="card border-0 bg-white p-2 mb-2 rounded-3">
      <slot name="fields" :model="newItem" />
      <div class="d-flex justify-content-end gap-2 mt-2">
        <button class="btn btn-sm btn-light border" @click="cancelCreate">Cancelar</button>
        <button class="btn btn-sm btn-success" @click="handleCreate" :disabled="busy">
          <span v-if="busy" class="spinner-border spinner-border-sm me-1"></span>Guardar
        </button>
      </div>
    </div>

    <div v-if="loading && !items.length" class="text-center py-2">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>
    <div v-else-if="!items.length && !isCreating" class="text-muted small py-1">Sin elementos.</div>

    <div v-else class="d-flex flex-column gap-1">
      <div v-for="item in items" :key="item.uuid" class="d-flex align-items-center gap-2 bg-white border rounded-2 px-2 py-1">
        <template v-if="editingUuid === item.uuid">
          <div class="flex-grow-1">
            <slot name="fields" :model="editingModel" />
          </div>
          <div class="d-flex gap-1 flex-shrink-0">
            <button class="btn btn-sm btn-light border" @click="cancelEdit"><i class="bi bi-x-lg"></i></button>
            <button class="btn btn-sm btn-warning text-dark" @click="saveEdit" :disabled="busy">
              <span v-if="busy" class="spinner-border spinner-border-sm"></span>
              <i v-else class="bi bi-check-lg"></i>
            </button>
          </div>
        </template>
        <template v-else>
          <div class="flex-grow-1">
            <slot name="display" :item="item" />
          </div>
          <div class="d-flex gap-1 flex-shrink-0">
            <button class="btn btn-sm btn-light border" @click="startEdit(item)" title="Editar">
              <i class="bi bi-pencil text-primary" style="font-size:.72rem"></i>
            </button>
            <button class="btn btn-sm btn-light border" @click="handleRemove(item)" :disabled="busy" title="Eliminar">
              <i class="bi bi-trash text-danger" style="font-size:.72rem"></i>
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  packageUuid: { type: String, required: true },
  resource: { type: String, required: true },
  title: { type: String, required: true },
  icon: { type: String, default: 'bi-list-check' },
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyFields: { type: Function, required: true },
  fetch: { type: Function, required: true },
  create: { type: Function, required: true },
  update: { type: Function, required: true },
  remove: { type: Function, required: true },
});

const toast = useToast();
const busy = ref(false);
const isCreating = ref(false);
const newItem = ref({});
const editingUuid = ref(null);
const editingModel = ref({});

watch(() => props.packageUuid, () => {
  isCreating.value = false;
  editingUuid.value = null;
}, { immediate: true });

function beginCreate() {
  newItem.value = props.emptyFields();
  isCreating.value = true;
}
function cancelCreate() {
  isCreating.value = false;
}

async function handleCreate() {
  busy.value = true;
  try {
    const { ok, error } = await props.create(props.packageUuid, newItem.value);
    if (!ok) throw new Error(error);
    toast.success('Elemento agregado.');
    cancelCreate();
  } catch (e) {
    toast.error(e.message || 'Error al agregar.');
  } finally {
    busy.value = false;
  }
}

function startEdit(item) {
  editingUuid.value = item.uuid;
  editingModel.value = { ...item };
}
function cancelEdit() {
  editingUuid.value = null;
}

async function saveEdit() {
  busy.value = true;
  try {
    const { ok, error } = await props.update(editingUuid.value, props.packageUuid, editingModel.value);
    if (!ok) throw new Error(error);
    toast.success('Elemento actualizado.');
    editingUuid.value = null;
  } catch (e) {
    toast.error(e.message || 'Error al actualizar.');
  } finally {
    busy.value = false;
  }
}

async function handleRemove(item) {
  busy.value = true;
  try {
    const { ok, error } = await props.remove(item.uuid, props.packageUuid);
    if (!ok) throw new Error(error);
    toast.success('Elemento eliminado.');
  } catch (e) {
    toast.error(e.message || 'Error al eliminar.');
  } finally {
    busy.value = false;
  }
}
</script>
