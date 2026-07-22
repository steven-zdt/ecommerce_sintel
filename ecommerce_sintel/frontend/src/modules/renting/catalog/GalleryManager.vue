<template>
  <div>
    <p class="text-muted small mb-3">
      Galeria avanzada: Principal, Galeria, Detalle, Instalacion, 360, Plano, Ejemplo.
      Arrastra para reordenar. La imagen "Principal" activa se usa como portada del producto.
    </p>

    <div class="card border-0 bg-light p-3 mb-3 rounded-3">
      <div class="row g-2 align-items-end">
        <div class="col-12">
          <label class="form-label small">Archivo <span class="text-danger">*</span></label>
          <input ref="fileInputRef" type="file" accept="image/*" class="form-control form-control-sm" @change="onFileChange">
        </div>
        <div class="col-6">
          <label class="form-label small">Tipo</label>
          <select v-model="uploadForm.image_type" class="form-select form-select-sm">
            <option v-for="opt in imageTypes" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small">Texto alternativo</label>
          <input v-model="uploadForm.alt_text" type="text" class="form-control form-control-sm" placeholder="Descripcion para accesibilidad/SEO">
        </div>
        <div class="col-12">
          <div class="form-check form-switch">
            <input v-model="uploadForm.is_primary" class="form-check-input" type="checkbox" id="imgPrimary">
            <label class="form-check-label small" for="imgPrimary">Marcar como principal</label>
          </div>
        </div>
      </div>
      <button type="button" class="btn btn-sm btn-primary mt-3" @click="upload" :disabled="uploading || !uploadForm.file">
        <span v-if="uploading" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-cloud-upload me-1"></i> Subir imagen
      </button>
    </div>

    <div v-if="images.length" class="row g-2">
      <div
        v-for="(img, idx) in images"
        :key="img.uuid"
        class="col-6 col-md-4 col-lg-3"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <div class="border rounded-3 overflow-hidden position-relative gallery-card">
          <span v-if="img.is_primary" class="badge bg-primary position-absolute top-0 start-0 m-1" style="font-size:.6rem">Principal</span>
          <span class="badge bg-dark-subtle text-dark position-absolute top-0 end-0 m-1" style="font-size:.6rem">{{ img.image_type_display }}</span>
          <img :src="img.image" class="w-100" style="height:110px;object-fit:cover" :alt="img.alt_text">
          <div class="d-flex justify-content-between p-1 bg-white">
            <button type="button" class="btn btn-sm btn-link p-0" title="Marcar como principal" @click="setPrimary(img)" :disabled="img.is_primary">
              <i class="bi bi-star-fill text-warning"></i>
            </button>
            <button type="button" class="btn btn-sm btn-link p-0 text-danger" title="Eliminar" @click="remove(img)">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="text-center py-4 text-muted">
      <i class="bi bi-images fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin imagenes en la galeria.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const api = useApi();
const toast = useToast();
const ENDPOINT = 'dashboard/equipment-images/';

const imageTypes = [
  { value: 'PRINCIPAL', label: 'Principal' },
  { value: 'GALERIA', label: 'Galeria' },
  { value: 'DETALLE', label: 'Detalle' },
  { value: 'INSTALACION', label: 'Instalacion' },
  { value: 'VISTA_360', label: '360' },
  { value: 'PLANO', label: 'Plano' },
  { value: 'EJEMPLO', label: 'Ejemplo' },
];

const images = ref([]);
const fileInputRef = ref(null);
const uploading = ref(false);
const uploadForm = ref({ file: null, image_type: 'GALERIA', alt_text: '', is_primary: false });
const dragIndex = ref(null);

function onFileChange(e) {
  uploadForm.value.file = e.target.files[0] || null;
}

async function fetchImages() {
  if (!props.equipmentUuid) return;
  try {
    const res = await api.get(`${ENDPOINT}?equipment=${props.equipmentUuid}`);
    images.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudo cargar la galeria');
  }
}

async function upload() {
  if (!uploadForm.value.file) return toast.error('Selecciona un archivo');
  uploading.value = true;
  try {
    const fd = new FormData();
    fd.append('equipment', props.equipmentUuid);
    fd.append('image', uploadForm.value.file);
    fd.append('image_type', uploadForm.value.image_type);
    fd.append('alt_text', uploadForm.value.alt_text || '');
    fd.append('is_primary', uploadForm.value.is_primary ? 'true' : 'false');
    await api.post(ENDPOINT, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    uploadForm.value = { file: null, image_type: 'GALERIA', alt_text: '', is_primary: false };
    if (fileInputRef.value) fileInputRef.value.value = '';
    await fetchImages();
    toast.success('Imagen subida');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al subir imagen');
  } finally {
    uploading.value = false;
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
  } catch {
    toast.error('No se pudo marcar como principal');
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
      equipment: props.equipmentUuid,
      ordered_uuids: reordered.map((i) => i.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchImages();
  }
}

watch(() => props.equipmentUuid, fetchImages, { immediate: true });

defineExpose({ fetchImages });
</script>

<style scoped>
.gallery-card { background: #fff; }
</style>
