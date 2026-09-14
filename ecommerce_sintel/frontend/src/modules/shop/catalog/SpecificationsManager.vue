<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">{{ config.groupHint }}</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openGroupForm" :disabled="showGroupForm">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Grupo
      </button>
    </div>

    <div v-if="showGroupForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">{{ editingGroup ? 'Editar' : 'Nuevo' }} Grupo</h6>
      <div class="mb-3">
        <label class="form-label small">Nombre <span class="text-danger">*</span></label>
        <input v-model="groupForm.name" type="text" class="form-control form-control-sm" :placeholder="config.groupPlaceholder">
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="saveGroup" :disabled="savingGroup">
          <span v-if="savingGroup" class="spinner-border spinner-border-sm me-1"></span>
          {{ editingGroup ? 'Guardar' : 'Agregar' }}
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="cancelGroupForm">Cancelar</button>
      </div>
    </div>

    <div v-if="groups.length" class="d-flex flex-column gap-3">
      <div
        v-for="(group, gIdx) in groups"
        :key="group.uuid"
        class="border rounded-3 p-2"
        :class="group.is_active ? 'bg-white' : 'bg-light opacity-60'"
        draggable="true"
        @dragstart="handleGroupDragStart(gIdx)"
        @dragover.prevent
        @drop="handleGroupDrop(gIdx)"
      >
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="text-muted" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
          <span class="fw-semibold small flex-grow-1">{{ group.name }}</span>
          <button type="button" class="btn btn-link p-0" :title="group.is_active ? 'Desactivar' : 'Activar'" @click="toggleGroup(group)">
            <i :class="group.is_active ? 'bi bi-toggle-on text-success' : 'bi bi-toggle-off text-muted'"></i>
          </button>
          <button type="button" class="btn btn-sm btn-light" title="Editar grupo" @click="startEditGroup(group)"><i class="bi bi-pencil text-primary"></i></button>
          <button type="button" class="btn btn-sm btn-light" title="Eliminar grupo" @click="removeGroup(group)"><i class="bi bi-trash text-danger"></i></button>
        </div>

        <div class="ps-3 d-flex flex-column gap-1">
          <div
            v-for="(spec, sIdx) in group.specifications"
            :key="spec.uuid"
            class="d-flex align-items-center gap-2 p-1 rounded-2"
            :class="spec.is_active ? '' : 'opacity-50'"
            draggable="true"
            @dragstart="handleSpecDragStart(group, sIdx)"
            @dragover.prevent
            @drop="handleSpecDrop(group, sIdx)"
          >
            <span class="text-muted small" title="Arrastrar"><i class="bi bi-grip-vertical"></i></span>
            <span class="small flex-grow-1"><strong>{{ spec.name }}:</strong> {{ spec.value }}</span>
            <button type="button" class="btn btn-link p-0" @click="toggleSpec(spec)">
              <i :class="spec.is_active ? 'bi bi-toggle-on text-success' : 'bi bi-toggle-off text-muted'"></i>
            </button>
            <button type="button" class="btn btn-sm btn-light" @click="startEditSpec(group, spec)"><i class="bi bi-pencil text-primary small"></i></button>
            <button type="button" class="btn btn-sm btn-light" @click="removeSpec(group, spec)"><i class="bi bi-trash text-danger small"></i></button>
          </div>

          <div v-if="specForm.groupUuid === group.uuid" class="d-flex gap-2 align-items-end mt-1">
            <div class="flex-grow-1">
              <label class="form-label small mb-0">Nombre</label>
              <input v-model="specForm.name" type="text" class="form-control form-control-sm" :placeholder="config.namePlaceholder">
            </div>
            <div class="flex-grow-1">
              <label class="form-label small mb-0">Valor</label>
              <input v-model="specForm.value" type="text" class="form-control form-control-sm" :placeholder="config.valuePlaceholder">
            </div>
            <button type="button" class="btn btn-sm btn-primary" @click="saveSpec(group)" :disabled="savingSpec">Guardar</button>
            <button type="button" class="btn btn-sm btn-light border" @click="cancelSpecForm">Cancelar</button>
          </div>
          <button v-else type="button" class="btn btn-sm btn-outline-primary mt-1 align-self-start" @click="openSpecForm(group)">
            <i class="bi bi-plus-lg me-1"></i> Agregar especificacion
          </button>
        </div>
      </div>
    </div>
    <div v-else-if="!showGroupForm" class="text-center py-4 text-muted">
      <i class="bi bi-card-list fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin grupos de especificaciones registrados.</p>
    </div>
  </div>
</template>

<script setup>
// Generalizado 2026-08-05 (Sprint 5, auditoria transversal) -- antes existia una copia
// byte-identica de este componente por dominio (shop/renting/technical_services), variando
// solo endpoints/placeholders/nombre de prop. Mismo patron entity-type ya probado por
// ContentBlocksTab.vue (ver ese componente para el precedente) -- vive aqui (shop/catalog/)
// por el mismo motivo que ContentBlocksTab vive en shop/product-form/: convencion ya
// establecida de "el generico vive en su dominio de origen, los demas lo importan cruzado".
import { ref, computed, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const ENTITY_CONFIG = {
  product: {
    entityParam: 'product',
    groupsEndpoint: 'dashboard/product-specification-groups/',
    specsEndpoint: 'dashboard/product-specifications/',
    groupHint: 'Agrupa las especificaciones tecnicas por categoria (ej. Camara, Grabador).',
    groupPlaceholder: 'Ej: Camara',
    namePlaceholder: 'Ej: Resolucion',
    valuePlaceholder: 'Ej: 4MP',
  },
  equipment: {
    entityParam: 'equipment',
    groupsEndpoint: 'dashboard/rental-specification-groups/',
    specsEndpoint: 'dashboard/rental-specifications/',
    groupHint: 'Agrupa las especificaciones tecnicas por categoria (ej. Motor, Dimensiones).',
    groupPlaceholder: 'Ej: Motor',
    namePlaceholder: 'Ej: Cilindraje',
    valuePlaceholder: 'Ej: 2000cc',
  },
  service: {
    entityParam: 'service',
    groupsEndpoint: 'dashboard/service-specification-groups/',
    specsEndpoint: 'dashboard/service-specifications/',
    groupHint: 'Agrupa las especificaciones tecnicas por categoria (ej. General, Cobertura).',
    groupPlaceholder: 'Ej: General',
    namePlaceholder: 'Ej: Cobertura',
    valuePlaceholder: 'Ej: Nacional',
  },
};

const props = defineProps({
  entityType: { type: String, default: 'product', validator: (v) => ['product', 'equipment', 'service'].includes(v) },
  entityUuid: { type: String, required: true },
});

const config = computed(() => ENTITY_CONFIG[props.entityType]);

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const groups = ref([]);
const showGroupForm = ref(false);
const editingGroup = ref(null);
const savingGroup = ref(false);
const groupForm = ref({ name: '' });
const groupDragIndex = ref(null);

const specForm = ref({ groupUuid: null, uuid: null, name: '', value: '' });
const savingSpec = ref(false);
const specDrag = ref({ groupUuid: null, index: null });

async function fetchGroups() {
  if (!props.entityUuid) return;
  try {
    const res = await api.get(`${config.value.groupsEndpoint}?${config.value.entityParam}=${props.entityUuid}`);
    groups.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudieron cargar los grupos de especificaciones');
  }
}

function openGroupForm() {
  editingGroup.value = null;
  groupForm.value = { name: '' };
  showGroupForm.value = true;
}
function startEditGroup(group) {
  editingGroup.value = group;
  groupForm.value = { name: group.name };
  showGroupForm.value = true;
}
function cancelGroupForm() {
  showGroupForm.value = false;
  editingGroup.value = null;
  groupForm.value = { name: '' };
}

async function saveGroup() {
  if (!groupForm.value.name?.trim()) return toast.error('Nombre requerido');
  savingGroup.value = true;
  try {
    if (editingGroup.value) {
      await api.patch(`${config.value.groupsEndpoint}${editingGroup.value.uuid}/`, { name: groupForm.value.name });
    } else {
      await api.post(config.value.groupsEndpoint, { [config.value.entityParam]: props.entityUuid, name: groupForm.value.name });
    }
    cancelGroupForm();
    await fetchGroups();
  } catch (e) {
    handleError(e, 'Error al guardar el grupo');
  } finally {
    savingGroup.value = false;
  }
}

async function removeGroup(group) {
  try {
    await api.delete(`${config.value.groupsEndpoint}${group.uuid}/`);
    await fetchGroups();
    toast.success('Grupo eliminado');
  } catch {
    toast.error('No se pudo eliminar el grupo');
  }
}

async function toggleGroup(group) {
  try {
    await api.post(`${config.value.groupsEndpoint}${group.uuid}/toggle-active/`);
    await fetchGroups();
  } catch {
    toast.error('No se pudo cambiar el estado del grupo');
  }
}

function handleGroupDragStart(index) { groupDragIndex.value = index; }
async function handleGroupDrop(targetIndex) {
  const fromIndex = groupDragIndex.value;
  groupDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...groups.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  groups.value = reordered;
  try {
    await api.post(`${config.value.groupsEndpoint}reorder/`, {
      [config.value.entityParam]: props.entityUuid,
      ordered_uuids: reordered.map((g) => g.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden de grupos.');
    await fetchGroups();
  }
}

function openSpecForm(group) {
  specForm.value = { groupUuid: group.uuid, uuid: null, name: '', value: '' };
}
function startEditSpec(group, spec) {
  specForm.value = { groupUuid: group.uuid, uuid: spec.uuid, name: spec.name, value: spec.value };
}
function cancelSpecForm() {
  specForm.value = { groupUuid: null, uuid: null, name: '', value: '' };
}

async function saveSpec(group) {
  if (!specForm.value.name?.trim() || !specForm.value.value?.trim()) {
    return toast.error('Nombre y valor son requeridos');
  }
  savingSpec.value = true;
  try {
    if (specForm.value.uuid) {
      await api.patch(`${config.value.specsEndpoint}${specForm.value.uuid}/`, {
        name: specForm.value.name, value: specForm.value.value,
      });
    } else {
      await api.post(config.value.specsEndpoint, {
        [config.value.entityParam]: props.entityUuid, group: group.uuid,
        name: specForm.value.name, value: specForm.value.value,
      });
    }
    cancelSpecForm();
    await fetchGroups();
  } catch (e) {
    handleError(e, 'Error al guardar la especificacion');
  } finally {
    savingSpec.value = false;
  }
}

async function removeSpec(group, spec) {
  try {
    await api.delete(`${config.value.specsEndpoint}${spec.uuid}/`);
    await fetchGroups();
    toast.success('Especificacion eliminada');
  } catch {
    toast.error('No se pudo eliminar la especificacion');
  }
}

async function toggleSpec(spec) {
  try {
    await api.post(`${config.value.specsEndpoint}${spec.uuid}/toggle-active/`);
    await fetchGroups();
  } catch {
    toast.error('No se pudo cambiar el estado');
  }
}

function handleSpecDragStart(group, index) {
  specDrag.value = { groupUuid: group.uuid, index };
}
async function handleSpecDrop(group, targetIndex) {
  const { groupUuid, index: fromIndex } = specDrag.value;
  specDrag.value = { groupUuid: null, index: null };
  if (groupUuid !== group.uuid || fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...group.specifications];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  group.specifications = reordered;
  try {
    await api.post(`${config.value.specsEndpoint}reorder/`, {
      group: group.uuid,
      ordered_uuids: reordered.map((s) => s.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchGroups();
  }
}

watch(() => props.entityUuid, fetchGroups, { immediate: true });

defineExpose({ fetchGroups });
</script>
