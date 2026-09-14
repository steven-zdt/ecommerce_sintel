<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">Pasos de como se presta el servicio, en orden.</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openCreateForm" :disabled="showForm">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Paso
      </button>
    </div>

    <div v-if="showForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">{{ editingItem ? 'Editar' : 'Nuevo' }} Paso</h6>
      <div class="row g-2 mb-3">
        <div class="col-3">
          <label class="form-label small">Numero</label>
          <input v-model.number="form.step_number" type="number" min="1" class="form-control form-control-sm">
        </div>
        <div class="col-9">
          <label class="form-label small">Titulo <span class="text-danger">*</span></label>
          <input v-model="form.title" type="text" class="form-control form-control-sm" placeholder="Ej: Diagnostico inicial">
        </div>
        <div class="col-12">
          <label class="form-label small">Descripcion</label>
          <textarea v-model="form.description" class="form-control form-control-sm" rows="2"></textarea>
        </div>
        <div class="col-6">
          <label class="form-label small">Tiempo estimado</label>
          <input v-model="form.estimated_time" type="text" class="form-control form-control-sm" placeholder="Ej: 30 min">
        </div>
        <div class="col-6">
          <label class="form-label small">Imagen</label>
          <input ref="fileInputRef" type="file" accept="image/*" class="form-control form-control-sm" @change="onFileChange">
        </div>
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="save" :disabled="saving || !form.title.trim()">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          {{ editingItem ? 'Guardar' : 'Agregar' }}
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="cancelForm">Cancelar</button>
      </div>
    </div>

    <div v-if="steps.length" class="d-flex flex-column gap-2">
      <div
        v-for="(step, idx) in steps"
        :key="step.uuid"
        class="d-flex align-items-center gap-2 p-2 rounded-3 border"
        :class="step.is_active ? 'bg-white' : 'bg-light opacity-60'"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <span class="text-muted" title="Arrastrar"><i class="bi bi-grip-vertical"></i></span>
        <span class="step-number">{{ step.step_number }}</span>
        <img v-if="step.image" :src="step.image" class="step-thumb" alt="">
        <div class="flex-grow-1 min-w-0">
          <div class="fw-semibold small text-truncate">{{ step.title }}</div>
          <div v-if="step.estimated_time" class="text-muted" style="font-size:.72rem">{{ step.estimated_time }}</div>
        </div>
        <button type="button" class="btn btn-link p-0" :title="step.is_active ? 'Desactivar' : 'Activar'" @click="toggleActive(step)">
          <i :class="step.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"></i>
        </button>
        <button type="button" class="btn btn-sm btn-light" title="Editar" @click="startEdit(step)"><i class="bi bi-pencil text-primary"></i></button>
        <button type="button" class="btn btn-sm btn-light" title="Eliminar" @click="remove(step)"><i class="bi bi-trash text-danger"></i></button>
      </div>
    </div>
    <div v-else-if="!showForm" class="text-center py-4 text-muted">
      <i class="bi bi-list-ol fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin pasos registrados.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  serviceUuid: { type: String, required: true },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const ENDPOINT = 'dashboard/service-process-steps/';

const steps = ref([]);
const showForm = ref(false);
const editingItem = ref(null);
const saving = ref(false);
const fileInputRef = ref(null);
const dragIndex = ref(null);
const imageFile = ref(null);

function emptyForm() {
  return { step_number: steps.value.length + 1, title: '', description: '', estimated_time: '' };
}
const form = ref(emptyForm());

function onFileChange(e) {
  imageFile.value = e.target.files[0] || null;
}

async function fetchSteps() {
  if (!props.serviceUuid) return;
  try {
    const res = await api.get(`${ENDPOINT}?service=${props.serviceUuid}`);
    steps.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudieron cargar los pasos del proceso');
  }
}

function openCreateForm() {
  editingItem.value = null;
  form.value = emptyForm();
  imageFile.value = null;
  showForm.value = true;
}
function startEdit(step) {
  editingItem.value = step;
  form.value = {
    step_number: step.step_number, title: step.title,
    description: step.description || '', estimated_time: step.estimated_time || '',
  };
  imageFile.value = null;
  showForm.value = true;
}
function cancelForm() {
  showForm.value = false;
  editingItem.value = null;
  form.value = emptyForm();
  imageFile.value = null;
}

async function save() {
  if (!form.value.title.trim()) return toast.error('El titulo es requerido');
  saving.value = true;
  try {
    const fd = new FormData();
    if (!editingItem.value) fd.append('service', props.serviceUuid);
    fd.append('step_number', form.value.step_number || 1);
    fd.append('title', form.value.title);
    fd.append('description', form.value.description || '');
    fd.append('estimated_time', form.value.estimated_time || '');
    if (imageFile.value) fd.append('image', imageFile.value);

    if (editingItem.value) {
      await api.patch(`${ENDPOINT}${editingItem.value.uuid}/`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    } else {
      await api.post(ENDPOINT, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    }
    cancelForm();
    await fetchSteps();
    toast.success('Paso guardado');
  } catch (e) {
    handleError(e, 'Error al guardar el paso');
  } finally {
    saving.value = false;
  }
}

async function remove(step) {
  try {
    await api.delete(`${ENDPOINT}${step.uuid}/`);
    await fetchSteps();
    toast.success('Paso eliminado');
  } catch {
    toast.error('No se pudo eliminar el paso');
  }
}

async function toggleActive(step) {
  try {
    await api.post(`${ENDPOINT}${step.uuid}/toggle-active/`);
    await fetchSteps();
  } catch {
    toast.error('No se pudo cambiar el estado');
  }
}

function handleDragStart(index) { dragIndex.value = index; }
async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...steps.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  steps.value = reordered;
  try {
    await api.post(`${ENDPOINT}reorder/`, {
      service: props.serviceUuid,
      ordered_uuids: reordered.map((s) => s.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchSteps();
  }
}

watch(() => props.serviceUuid, fetchSteps, { immediate: true });

defineExpose({ fetchSteps });
</script>

<style scoped>
.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 700;
  font-size: .78rem;
  flex-shrink: 0;
}
.step-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
}
</style>
