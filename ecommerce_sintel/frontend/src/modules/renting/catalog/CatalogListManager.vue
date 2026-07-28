<template>
  <div class="catalog-list-manager">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">{{ hint }}</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openCreateForm" :disabled="showForm">
        <i class="bi bi-plus-lg me-1"></i> Nuevo{{ genderSuffix }}
      </button>
    </div>

    <div v-if="showForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">{{ editingItem ? 'Editar' : 'Nuevo' }} {{ resourceLabel }}</h6>
      <div class="row g-2 mb-3">
        <div v-for="field in fields" :key="field.key" :class="field.col || 'col-12'">
          <label class="form-label small">
            {{ field.label }} <span v-if="field.required" class="text-danger">*</span>
          </label>
          <textarea
            v-if="field.type === 'textarea'"
            v-model="form[field.key]"
            class="form-control form-control-sm"
            rows="2"
            :placeholder="field.placeholder || ''"
          ></textarea>
          <div v-else-if="field.type === 'price'" class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="form[field.key]" type="number" step="0.01" min="0" class="form-control" :placeholder="field.placeholder || '0.00'">
          </div>
          <div v-else-if="field.type === 'icon'" class="input-group input-group-sm">
            <span class="input-group-text"><IconRenderer :icon="form[field.key]" /></span>
            <input v-model="form[field.key]" type="text" class="form-control" :placeholder="field.placeholder || 'bi-check-circle'">
          </div>
          <input
            v-else
            v-model="form[field.key]"
            type="text"
            class="form-control form-control-sm"
            :placeholder="field.placeholder || ''"
          >
        </div>
        <div class="col-6 d-flex align-items-end pb-1">
          <div class="form-check form-switch ms-1">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" :id="`${resource}Active`">
            <label class="form-check-label small" :for="`${resource}Active`">Activo</label>
          </div>
        </div>
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="save" :disabled="saving">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          {{ editingItem ? 'Guardar' : 'Agregar' }}
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="cancelForm">Cancelar</button>
      </div>
    </div>

    <div v-if="items.length" class="d-flex flex-column gap-2">
      <div
        v-for="(item, idx) in items"
        :key="item.uuid"
        class="catalog-row d-flex align-items-start gap-2 p-2 rounded-3 border"
        :class="item.is_active ? 'bg-white' : 'bg-light opacity-60'"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <span class="drag-handle text-muted" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
        <IconRenderer v-if="hasIconField" :icon="item[iconFieldKey]" extra-class="text-primary mt-1" />
        <div class="flex-grow-1 min-w-0">
          <div class="fw-semibold small text-truncate">{{ primaryText(item) }}</div>
          <div v-if="secondaryText(item)" class="text-muted" style="font-size:.75rem">{{ secondaryText(item) }}</div>
        </div>
        <div class="d-flex align-items-center gap-1 flex-shrink-0">
          <button type="button" class="btn btn-link p-0" :title="item.is_active ? 'Desactivar' : 'Activar'" @click="toggleActive(item)">
            <i :class="item.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"></i>
          </button>
          <button v-if="supportsDuplicate" type="button" class="btn btn-sm btn-light" title="Duplicar" @click="duplicate(item)">
            <i class="bi bi-files"></i>
          </button>
          <button type="button" class="btn btn-sm btn-light" title="Editar" @click="startEdit(item)">
            <i class="bi bi-pencil text-primary"></i>
          </button>
          <button type="button" class="btn btn-sm btn-light" title="Eliminar" @click="remove(item)">
            <i class="bi bi-trash text-danger"></i>
          </button>
        </div>
      </div>
    </div>
    <div v-else-if="!showForm" class="text-center py-4 text-muted">
      <i :class="['bi', emptyIcon, 'fs-3', 'd-block', 'mb-2', 'opacity-50']"></i>
      <p class="small mb-0">Sin {{ resourceLabelPlural.toLowerCase() }} registrados.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { formatCOP } from '@/utils/money';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import IconRenderer from '@/components/ui/IconRenderer.vue';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
  endpoint: { type: String, required: true },
  resource: { type: String, required: true },
  resourceLabel: { type: String, required: true },
  resourceLabelPlural: { type: String, required: true },
  hint: { type: String, default: '' },
  fields: { type: Array, required: true },
  primaryField: { type: String, default: null },
  secondaryField: { type: String, default: null },
  supportsDuplicate: { type: Boolean, default: true },
  emptyIcon: { type: String, default: 'bi-list-ul' },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const items = ref([]);
const showForm = ref(false);
const editingItem = ref(null);
const saving = ref(false);
const dragIndex = ref(null);

const genderSuffix = '';

const iconField = computed(() => props.fields.find((f) => f.type === 'icon'));
const hasIconField = computed(() => !!iconField.value);
const iconFieldKey = computed(() => iconField.value?.key);

const primaryKey = computed(() => props.primaryField || props.fields[0]?.key);
const secondaryKey = computed(() => props.secondaryField || props.fields.find((f) => f.key !== primaryKey.value && f.type !== 'icon')?.key);

function primaryText(item) {
  return item[primaryKey.value] ?? '';
}
function secondaryText(item) {
  const key = secondaryKey.value;
  if (!key) return '';
  const val = item[key];
  if (val === null || val === undefined || val === '') return '';
  const field = props.fields.find((f) => f.key === key);
  if (field?.type === 'price') return formatPrice(val);
  return val;
}


function formatPrice(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) return null;
  return formatCOP(number, { withSymbol: true });
}

function emptyForm() {
  const base = { is_active: true };
  for (const field of props.fields) {
    base[field.key] = field.type === 'price' ? null : '';
  }
  return base;
}

const form = ref(emptyForm());

async function fetchItems() {
  if (!props.equipmentUuid) return;
  try {
    const res = await api.get(`${props.endpoint}?equipment=${props.equipmentUuid}`);
    items.value = res.data.results || res.data;
  } catch {
    toast.error(`No se pudo cargar ${props.resourceLabelPlural.toLowerCase()}`);
  }
}

function openCreateForm() {
  editingItem.value = null;
  form.value = emptyForm();
  showForm.value = true;
}

function startEdit(item) {
  editingItem.value = item;
  const next = { is_active: item.is_active };
  for (const field of props.fields) {
    next[field.key] = item[field.key] ?? (field.type === 'price' ? null : '');
  }
  form.value = next;
  showForm.value = true;
}

function cancelForm() {
  showForm.value = false;
  editingItem.value = null;
  form.value = emptyForm();
}

async function save() {
  const requiredMissing = props.fields.find((f) => f.required && !String(form.value[f.key] ?? '').trim());
  if (requiredMissing) {
    toast.error(`${requiredMissing.label} es requerido`);
    return;
  }
  saving.value = true;
  try {
    if (editingItem.value) {
      await api.patch(`${props.endpoint}${editingItem.value.uuid}/`, { ...form.value });
      toast.success(`${props.resourceLabel} actualizado`);
    } else {
      await api.post(props.endpoint, { equipment: props.equipmentUuid, ...form.value });
      toast.success(`${props.resourceLabel} agregado`);
    }
    cancelForm();
    await fetchItems();
  } catch (e) {
    handleError(e, 'Error al guardar');
  } finally {
    saving.value = false;
  }
}

async function remove(item) {
  try {
    await api.delete(`${props.endpoint}${item.uuid}/`);
    await fetchItems();
    toast.success(`${props.resourceLabel} eliminado`);
  } catch {
    toast.error('No se pudo eliminar');
  }
}

async function toggleActive(item) {
  try {
    await api.post(`${props.endpoint}${item.uuid}/toggle-active/`);
    await fetchItems();
  } catch {
    toast.error('No se pudo cambiar el estado');
  }
}

async function duplicate(item) {
  try {
    await api.post(`${props.endpoint}${item.uuid}/duplicate/`);
    await fetchItems();
    toast.success(`${props.resourceLabel} duplicado`);
  } catch {
    toast.error('No se pudo duplicar');
  }
}

function handleDragStart(index) {
  dragIndex.value = index;
}

async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...items.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  items.value = reordered;
  try {
    await api.post(`${props.endpoint}reorder/`, {
      equipment: props.equipmentUuid,
      ordered_uuids: reordered.map((i) => i.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchItems();
  }
}

watch(() => props.equipmentUuid, fetchItems, { immediate: true });

defineExpose({ fetchItems });
</script>

<style scoped>
.drag-handle { cursor: grab; padding-top: .2rem; }
.catalog-row { transition: background-color .15s ease; }
</style>
