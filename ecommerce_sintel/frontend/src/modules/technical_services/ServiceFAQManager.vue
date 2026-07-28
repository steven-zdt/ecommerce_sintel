<template>
  <div class="service-faq-manager">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">Preguntas frecuentes mostradas en el detalle publico de este servicio.</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openCreateForm" :disabled="showForm">
        <i class="bi bi-plus-lg me-1"></i> Nueva
      </button>
    </div>

    <div v-if="showForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">{{ editingItem ? 'Editar' : 'Nueva' }} pregunta</h6>
      <div class="row g-2 mb-3">
        <div class="col-12">
          <label class="form-label small">Pregunta <span class="text-danger">*</span></label>
          <input v-model="form.question" type="text" class="form-control form-control-sm" placeholder="Ej: Cuanto dura la visita tecnica?">
        </div>
        <div class="col-12">
          <label class="form-label small">Respuesta <span class="text-danger">*</span></label>
          <textarea v-model="form.answer" class="form-control form-control-sm" rows="3" placeholder="Respuesta clara y breve"></textarea>
        </div>
        <div class="col-6 d-flex align-items-end pb-1">
          <div class="form-check form-switch ms-1">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" id="faqActive">
            <label class="form-check-label small" for="faqActive">Activo</label>
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

    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border spinner-border-sm text-primary"></span>
    </div>

    <div v-else-if="items.length" class="d-flex flex-column gap-2">
      <div
        v-for="(item, idx) in items"
        :key="item.uuid"
        class="faq-row d-flex align-items-start gap-2 p-2 rounded-3 border"
        :class="item.is_active ? 'bg-white' : 'bg-light opacity-60'"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <span class="drag-handle text-muted" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
        <div class="flex-grow-1 min-w-0">
          <div class="fw-semibold small text-truncate">{{ item.question }}</div>
          <div class="text-muted small text-truncate">{{ item.answer }}</div>
        </div>
        <div class="d-flex align-items-center gap-1 flex-shrink-0">
          <button type="button" class="btn btn-link p-0" :title="item.is_active ? 'Desactivar' : 'Activar'" @click="toggleActive(item)">
            <i :class="item.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"></i>
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
      <i class="bi bi-question-circle fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin preguntas frecuentes registradas.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

/**
 * Manager de ServiceFAQ -- unificacion con Renting (2026-07-18). Dedicado a
 * Technical Services (no una generalizacion de CatalogListManager.vue de
 * Renting): ese componente hardcodea el nombre de campo FK padre a
 * `equipment`, no reutilizable tal cual -- ver
 * technical_services/.AGENT/docs/PLAN_UNIFICACION_SERVICES_CON_RENTING.md,
 * Etapa 4.3. Mismo patron de interaccion (drag-reorder, toggle-active,
 * form inline), llamando directo a `dashboard/service-faqs/`.
 */
const props = defineProps({
  serviceUuid: { type: String, required: true },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const items = ref([]);
const loading = ref(false);
const showForm = ref(false);
const editingItem = ref(null);
const saving = ref(false);
const dragIndex = ref(null);

function emptyForm() {
  return { question: '', answer: '', is_active: true };
}
const form = ref(emptyForm());

async function fetchItems() {
  if (!props.serviceUuid) return;
  loading.value = true;
  try {
    const res = await api.get(`dashboard/service-faqs/?service=${props.serviceUuid}`);
    items.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudieron cargar las preguntas frecuentes');
  } finally {
    loading.value = false;
  }
}

function openCreateForm() {
  editingItem.value = null;
  form.value = emptyForm();
  showForm.value = true;
}

function startEdit(item) {
  editingItem.value = item;
  form.value = { question: item.question, answer: item.answer, is_active: item.is_active };
  showForm.value = true;
}

function cancelForm() {
  showForm.value = false;
  editingItem.value = null;
  form.value = emptyForm();
}

async function save() {
  if (!form.value.question.trim() || !form.value.answer.trim()) {
    toast.error('Pregunta y respuesta son requeridas');
    return;
  }
  saving.value = true;
  try {
    if (editingItem.value) {
      await api.patch(`dashboard/service-faqs/${editingItem.value.uuid}/`, { ...form.value });
      toast.success('Pregunta actualizada');
    } else {
      await api.post('dashboard/service-faqs/', { service: props.serviceUuid, ...form.value });
      toast.success('Pregunta agregada');
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
    await api.delete(`dashboard/service-faqs/${item.uuid}/`);
    await fetchItems();
    toast.success('Pregunta eliminada');
  } catch {
    toast.error('No se pudo eliminar');
  }
}

async function toggleActive(item) {
  try {
    await api.post(`dashboard/service-faqs/${item.uuid}/toggle-active/`);
    await fetchItems();
  } catch {
    toast.error('No se pudo cambiar el estado');
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
    await api.post('dashboard/service-faqs/reorder/', {
      service: props.serviceUuid,
      ordered_uuids: reordered.map((i) => i.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchItems();
  }
}

watch(() => props.serviceUuid, fetchItems, { immediate: true });
</script>

<style scoped>
.drag-handle { cursor: grab; padding-top: .2rem; }
.faq-row { transition: background-color .15s ease; }
</style>
