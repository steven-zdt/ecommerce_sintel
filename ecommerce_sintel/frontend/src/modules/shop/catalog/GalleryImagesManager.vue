<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">Galeria con tipo: principal, galeria, detalle o ejemplo de uso.</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openCreateForm" :disabled="showForm">
        <i class="bi bi-plus-lg me-1"></i> Nueva Imagen
      </button>
    </div>

    <div v-if="showForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Nueva Imagen</h6>
      <div class="row g-2 mb-3">
        <div class="col-12">
          <label class="form-label small">Archivo <span class="text-danger">*</span></label>
          <input ref="fileInputRef" type="file" accept="image/*" class="form-control form-control-sm" @change="onFileChange">
        </div>
        <div class="col-6">
          <label class="form-label small">Tipo</label>
          <select v-model="form.image_type" class="form-select form-select-sm">
            <option value="PRINCIPAL">Principal</option>
            <option value="GALERIA">Galeria</option>
            <option value="DETALLE">Detalle</option>
            <option value="EJEMPLO">Ejemplo</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small">Texto alternativo (SEO)</label>
          <input v-model="form.alt_text" type="text" class="form-control form-control-sm" placeholder="Descripcion de la imagen">
        </div>
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="save" :disabled="saving || !imageFile">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          Agregar
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="cancelForm">Cancelar</button>
      </div>
    </div>

    <div v-if="imagesLoading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>

    <div v-else-if="images.length" class="row g-2">
      <div
        v-for="(img, idx) in images"
        :key="img.uuid"
        class="col-6 col-md-4"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <div class="border rounded-3 overflow-hidden bg-white">
          <div class="ratio ratio-1x1 bg-light">
            <img :src="img.image" :alt="img.alt_text || 'imagen'" style="object-fit:cover">
          </div>
          <div class="p-2">
            <div class="d-flex align-items-center gap-1 flex-wrap mb-1">
              <span v-if="img.is_primary" class="badge bg-primary text-white" style="font-size:.65rem">
                <i class="bi bi-star-fill me-1"></i>Principal
              </span>
              <span class="badge bg-light text-dark border" style="font-size:.65rem">{{ img.image_type_display }}</span>
            </div>
            <div class="text-muted small text-truncate mb-1">{{ img.alt_text || '(sin descripcion)' }}</div>
            <div class="d-flex justify-content-between">
              <button v-if="!img.is_primary" type="button" class="btn btn-link p-0" title="Marcar como principal" @click="setPrimary(img)">
                <i class="bi bi-star text-primary"></i>
              </button>
              <span v-else></span>
              <button type="button" class="btn btn-sm btn-light" title="Eliminar" @click="remove(img)">
                <i class="bi bi-trash text-danger"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="!showForm" class="text-center py-4 text-muted">
      <i class="bi bi-images fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin imagenes en la galeria tipada.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const ENDPOINT = 'dashboard/product-catalog-images/';

const props = defineProps({
  productUuid: { type: String, required: true },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const images = ref([]);
const imagesLoading = ref(false);
const showForm = ref(false);
const saving = ref(false);
const fileInputRef = ref(null);
const dragIndex = ref(null);
const imageFile = ref(null);

function emptyForm() {
  return { image_type: 'GALERIA', alt_text: '' };
}
const form = ref(emptyForm());

function onFileChange(e) {
  imageFile.value = e.target.files[0] || null;
}

async function fetchImages() {
  if (!props.productUuid) return;
  imagesLoading.value = true;
  try {
    const res = await api.get(`${ENDPOINT}?product=${props.productUuid}`);
    images.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudieron cargar las imagenes de la galeria');
  } finally {
    imagesLoading.value = false;
  }
}

function openCreateForm() {
  form.value = emptyForm();
  imageFile.value = null;
  showForm.value = true;
}
function cancelForm() {
  showForm.value = false;
  form.value = emptyForm();
  imageFile.value = null;
  if (fileInputRef.value) fileInputRef.value.value = '';
}

async function save() {
  if (!imageFile.value) return toast.error('Selecciona un archivo');
  saving.value = true;
  try {
    const fd = new FormData();
    fd.append('product', props.productUuid);
    fd.append('image', imageFile.value);
    fd.append('image_type', form.value.image_type);
    fd.append('alt_text', form.value.alt_text || '');
    await api.post(ENDPOINT, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    cancelForm();
    await fetchImages();
    toast.success('Imagen agregada');
  } catch (e) {
    handleError(e, 'Error al subir la imagen');
  } finally {
    saving.value = false;
  }
}

async function remove(img) {
  try {
    await api.delete(`${ENDPOINT}${img.uuid}/`);
    await fetchImages();
    toast.success('Imagen eliminada');
  } catch {
    toast.error('No se pudo eliminar la imagen');
  }
}

async function setPrimary(img) {
  try {
    await api.post(`${ENDPOINT}${img.uuid}/set-primary/`);
    await fetchImages();
    toast.success('Imagen principal actualizada');
  } catch {
    toast.error('No se pudo establecer como principal');
  }
}

function handleDragStart(index) { dragIndex.value = index; }
async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...images.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  images.value = reordered;
  try {
    await api.post(`${ENDPOINT}reorder/`, {
      product: props.productUuid,
      ordered_uuids: reordered.map((i) => i.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchImages();
  }
}

watch(() => props.productUuid, fetchImages, { immediate: true });

defineExpose({ fetchImages });
</script>
