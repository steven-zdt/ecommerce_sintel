<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">Videos de demostracion: YouTube, Vimeo o archivo MP4 propio.</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openCreateForm" :disabled="showForm">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Video
      </button>
    </div>

    <div v-if="showForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">{{ editingItem ? 'Editar' : 'Nuevo' }} Video</h6>
      <div class="row g-2 mb-3">
        <div class="col-12">
          <label class="form-label small">Titulo</label>
          <input v-model="form.title" type="text" class="form-control form-control-sm" placeholder="Ej: Demostracion en campo">
        </div>
        <div class="col-12">
          <label class="form-label small">Origen</label>
          <select v-model="form.source_type" class="form-select form-select-sm">
            <option value="YOUTUBE">YouTube</option>
            <option value="VIMEO">Vimeo</option>
            <option value="MP4">Archivo MP4</option>
          </select>
        </div>
        <div v-if="form.source_type !== 'MP4'" class="col-12">
          <label class="form-label small">URL del video <span class="text-danger">*</span></label>
          <input v-model="form.video_url" type="url" class="form-control form-control-sm" placeholder="https://www.youtube.com/watch?v=...">
        </div>
        <div v-else class="col-12">
          <label class="form-label small">Archivo MP4 <span class="text-danger">*</span></label>
          <input ref="fileInputRef" type="file" accept="video/mp4" class="form-control form-control-sm" @change="onFileChange">
        </div>
        <div class="col-12">
          <label class="form-label small">Miniatura</label>
          <input type="file" accept="image/*" class="form-control form-control-sm" @change="onThumbnailChange">
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

    <div v-if="videos.length" class="row g-2">
      <div
        v-for="(video, idx) in videos"
        :key="video.uuid"
        class="col-6 col-md-4"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <div class="border rounded-3 overflow-hidden" :class="video.is_active ? 'bg-white' : 'bg-light opacity-60'">
          <div class="ratio ratio-16x9 bg-dark d-flex align-items-center justify-content-center">
            <img v-if="video.thumbnail" :src="video.thumbnail" class="w-100 h-100" style="object-fit:cover">
            <i v-else class="bi bi-play-circle text-white fs-1"></i>
          </div>
          <div class="p-2">
            <div class="fw-semibold small text-truncate">{{ video.title || video.source_type_display }}</div>
            <div class="text-muted mb-1" style="font-size:.7rem">{{ video.source_type_display }}</div>
            <div class="d-flex justify-content-between">
              <button type="button" class="btn btn-link p-0" @click="toggleActive(video)">
                <i :class="video.is_active ? 'bi bi-toggle-on text-success' : 'bi bi-toggle-off text-muted'"></i>
              </button>
              <div>
                <button type="button" class="btn btn-sm btn-light" @click="startEdit(video)"><i class="bi bi-pencil text-primary"></i></button>
                <button type="button" class="btn btn-sm btn-light" @click="remove(video)"><i class="bi bi-trash text-danger"></i></button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="!showForm" class="text-center py-4 text-muted">
      <i class="bi bi-camera-reels fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin videos registrados.</p>
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
const ENDPOINT = 'dashboard/rental-videos/';

const videos = ref([]);
const showForm = ref(false);
const editingItem = ref(null);
const saving = ref(false);
const fileInputRef = ref(null);
const dragIndex = ref(null);
const thumbnailFile = ref(null);

function emptyForm() {
  return { title: '', source_type: 'YOUTUBE', video_url: '', video_file: null };
}
const form = ref(emptyForm());

function onFileChange(e) {
  form.value.video_file = e.target.files[0] || null;
}
function onThumbnailChange(e) {
  thumbnailFile.value = e.target.files[0] || null;
}

async function fetchVideos() {
  if (!props.equipmentUuid) return;
  try {
    const res = await api.get(`${ENDPOINT}?equipment=${props.equipmentUuid}`);
    videos.value = res.data.results || res.data;
  } catch {
    toast.error('No se pudieron cargar los videos');
  }
}

function openCreateForm() {
  editingItem.value = null;
  form.value = emptyForm();
  thumbnailFile.value = null;
  showForm.value = true;
}
function startEdit(video) {
  editingItem.value = video;
  form.value = { title: video.title, source_type: video.source_type, video_url: video.video_url, video_file: null };
  thumbnailFile.value = null;
  showForm.value = true;
}
function cancelForm() {
  showForm.value = false;
  editingItem.value = null;
  form.value = emptyForm();
  thumbnailFile.value = null;
}

async function save() {
  if (form.value.source_type === 'MP4' && !form.value.video_file && !editingItem.value) {
    return toast.error('Selecciona un archivo MP4');
  }
  if (form.value.source_type !== 'MP4' && !form.value.video_url?.trim()) {
    return toast.error('Indica la URL del video');
  }
  saving.value = true;
  try {
    const fd = new FormData();
    if (!editingItem.value) fd.append('equipment', props.equipmentUuid);
    fd.append('title', form.value.title || '');
    fd.append('source_type', form.value.source_type);
    fd.append('video_url', form.value.video_url || '');
    if (form.value.video_file) fd.append('video_file', form.value.video_file);
    if (thumbnailFile.value) fd.append('thumbnail', thumbnailFile.value);

    if (editingItem.value) {
      await api.patch(`${ENDPOINT}${editingItem.value.uuid}/`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    } else {
      await api.post(ENDPOINT, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    }
    cancelForm();
    await fetchVideos();
    toast.success('Video guardado');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al guardar el video');
  } finally {
    saving.value = false;
  }
}

async function remove(video) {
  try {
    await api.delete(`${ENDPOINT}${video.uuid}/`);
    await fetchVideos();
    toast.success('Video eliminado');
  } catch {
    toast.error('No se pudo eliminar el video');
  }
}

async function toggleActive(video) {
  try {
    await api.post(`${ENDPOINT}${video.uuid}/toggle-active/`);
    await fetchVideos();
  } catch {
    toast.error('No se pudo cambiar el estado');
  }
}

function handleDragStart(index) { dragIndex.value = index; }
async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...videos.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  videos.value = reordered;
  try {
    await api.post(`${ENDPOINT}reorder/`, {
      equipment: props.equipmentUuid,
      ordered_uuids: reordered.map((v) => v.uuid),
    });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchVideos();
  }
}

watch(() => props.equipmentUuid, fetchVideos, { immediate: true });

defineExpose({ fetchVideos });
</script>
