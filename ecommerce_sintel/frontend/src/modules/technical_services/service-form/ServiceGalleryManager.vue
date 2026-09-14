<template>
  <div>
    <!-- Zona de carga multi-archivo -->
    <div
      class="upload-zone rounded-3 border-2 border-dashed d-flex flex-column align-items-center justify-content-center mb-3 p-4"
      :class="isDragging ? 'border-primary bg-primary-subtle' : 'border-secondary-subtle'"
      style="min-height:120px;cursor:pointer"
      @click="fileInput?.click()"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <i class="bi bi-cloud-upload fs-2 text-muted mb-2"></i>
      <p class="text-muted small mb-1">Arrastra una o varias imagenes aqui, o haz clic para seleccionar</p>
      <p class="text-muted" style="font-size:.72rem">JPG, PNG, WEBP — Max 5 MB c/u</p>
      <input ref="fileInput" type="file" accept="image/*" multiple class="d-none" @change="onFilesSelected">
    </div>

    <!-- Cola de pendientes por subir -->
    <div v-if="pendingFiles.length" class="mb-4 d-flex flex-column gap-2">
      <div v-for="(pf, idx) in pendingFiles" :key="pf.id" class="card border-0 bg-light p-3 rounded-3">
        <div class="d-flex gap-3">
          <img :src="pf.preview" class="rounded-2 object-fit-cover flex-shrink-0" style="width:64px;height:64px">
          <div class="flex-grow-1 min-w-0">
            <div class="small fw-semibold text-truncate mb-1">{{ pf.file.name }}</div>
            <input v-model="pf.caption" type="text" class="form-control form-control-sm mb-1" placeholder="Pie de foto (opcional)" maxlength="150">
            <textarea v-model="pf.description" class="form-control form-control-sm mb-1" rows="2" placeholder="Descripcion (opcional)"></textarea>
            <div class="form-check">
              <input v-model="pf.isPrimary" type="checkbox" class="form-check-input" :id="`pfPrimary-${pf.id}`" @change="onPendingPrimaryToggle(pf)">
              <label class="form-check-label smaller" :for="`pfPrimary-${pf.id}`">Imagen principal</label>
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-light border align-self-start flex-shrink-0" @click="removePending(idx)">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
      <div class="d-flex justify-content-end gap-2">
        <button type="button" class="btn btn-light border" @click="pendingFiles = []">Cancelar todo</button>
        <button type="button" class="btn btn-primary" :disabled="uploading" @click="uploadAllPending">
          <span v-if="uploading" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="bi bi-cloud-upload me-1"></i>Subir {{ pendingFiles.length }} imagen(es)
        </button>
      </div>
    </div>

    <!-- Galeria actual -->
    <div v-if="images.length" class="d-flex flex-column gap-2 mb-4">
      <div
        v-for="(img, idx) in images"
        :key="img.uuid"
        class="gallery-row d-flex gap-3 p-2 rounded-3 border"
        :class="img.is_primary ? 'border-warning border-2 bg-warning-subtle bg-opacity-25' : 'bg-white'"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <span class="drag-handle text-muted align-self-center" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
        <div class="position-relative flex-shrink-0" style="width:80px;height:80px">
          <img :src="img.image" :alt="img.alt_text || ''" class="w-100 h-100 rounded-2 object-fit-cover">
          <span v-if="img.is_primary" class="badge bg-warning text-dark position-absolute bottom-0 start-0 end-0 rounded-0 rounded-bottom-2" style="font-size:.6rem">
            Principal
          </span>
        </div>

        <div class="flex-grow-1 min-w-0">
          <template v-if="editingUuid !== img.uuid">
            <div class="fw-semibold small text-truncate">{{ img.caption || '(sin pie de foto)' }}</div>
            <div class="text-muted smaller text-truncate">{{ img.description || 'Sin descripcion' }}</div>
          </template>
          <template v-else>
            <input v-model="editForm.caption" type="text" class="form-control form-control-sm mb-1" placeholder="Pie de foto" maxlength="150">
            <textarea v-model="editForm.description" class="form-control form-control-sm mb-1" rows="2" placeholder="Descripcion"></textarea>
            <input v-model="editForm.alt_text" type="text" class="form-control form-control-sm" placeholder="Texto alternativo (accesibilidad)">
          </template>
        </div>

        <div class="d-flex flex-column gap-1 flex-shrink-0 align-self-center">
          <template v-if="editingUuid !== img.uuid">
            <button type="button" class="btn btn-sm btn-light border" :disabled="imgLoading" @click="startEdit(img)" title="Editar pie/descripcion">
              <i class="bi bi-pencil"></i>
            </button>
            <button v-if="!img.is_primary" type="button" class="btn btn-sm btn-light border" :disabled="imgLoading" @click="setPrimary(img)" title="Hacer principal">
              <i class="bi bi-star"></i>
            </button>
            <button type="button" class="btn btn-sm btn-light border" :disabled="imgLoading" @click="triggerReplace(img)" title="Reemplazar archivo">
              <i class="bi bi-arrow-repeat"></i>
            </button>
            <button type="button" class="btn btn-sm btn-light border text-danger" :disabled="imgLoading" @click="deleteImg(img)" title="Eliminar">
              <i class="bi bi-trash3"></i>
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn btn-sm btn-primary" :disabled="imgLoading" @click="saveEdit(img)">
              <i class="bi bi-check-lg"></i>
            </button>
            <button type="button" class="btn btn-sm btn-light border" @click="cancelEdit">
              <i class="bi bi-x-lg"></i>
            </button>
          </template>
        </div>
      </div>
    </div>

    <div v-else-if="!pendingFiles.length" class="text-center py-4 text-muted">
      <i class="bi bi-image fs-3 d-block mb-2 opacity-40"></i>
      <p class="small mb-0">Sin imagenes. Sube la primera imagen representativa del servicio.</p>
    </div>

    <input ref="replaceInput" type="file" accept="image/*" class="d-none" @change="onReplaceSelected">

    <div class="d-flex justify-content-end pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
/**
 * Plan "Rediseno ServiceForm + Content/Media" (2026-08-14) FASE 4 -- galeria
 * descriptiva real: multi-upload, preview, principal, caption/description/alt,
 * reorder (drag&drop, mismo patron que ContentBlocksTab.vue), delete, replace.
 * Reemplaza a ImagesTab.vue (single-upload, sin metadata) en el tab "Imagen".
 */
import { ref } from 'vue';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  // Array del padre (poblado desde item.images en su watcher) mutado in-place
  // aqui via push/splice/foreach -- mismo contrato que ImagesTab.vue.
  images: { type: Array, required: true },
  serviceUuid: { type: String, default: '' },
});
defineEmits(['close']);

const store = useTechnicalServicesStore();
const toast = useToast();

const imgLoading = ref(false);
const uploading = ref(false);
const isDragging = ref(false);
const fileInput = ref(null);
const replaceInput = ref(null);

// ─── Cola de subida multi-archivo ──────────────────────────────────────────
let pendingIdSeq = 0;
const pendingFiles = ref([]);

function addPendingFile(file) {
  pendingFiles.value.push({
    id: ++pendingIdSeq,
    file,
    preview: URL.createObjectURL(file),
    caption: '',
    description: '',
    isPrimary: !props.images.length && pendingFiles.value.length === 0,
  });
}

function onFilesSelected(e) {
  [...e.target.files].forEach(addPendingFile);
  e.target.value = '';
}

function onDrop(e) {
  isDragging.value = false;
  [...e.dataTransfer.files].filter((f) => f.type.startsWith('image/')).forEach(addPendingFile);
}

function removePending(idx) {
  pendingFiles.value.splice(idx, 1);
}

function onPendingPrimaryToggle(pf) {
  if (pf.isPrimary) {
    pendingFiles.value.forEach((p) => { if (p.id !== pf.id) p.isPrimary = false; });
  }
}

async function uploadAllPending() {
  uploading.value = true;
  try {
    for (const pf of pendingFiles.value) {
      const res = await store.uploadImage(props.serviceUuid, pf.file, '', pf.isPrimary, pf.caption, pf.description);
      if (!res.ok) throw new Error(res.error);
      props.images.push(res.data);
      if (pf.isPrimary) {
        props.images.forEach((img) => { img.is_primary = img.uuid === res.data.uuid; });
      }
    }
    toast.success(`${pendingFiles.value.length} imagen(es) subida(s) correctamente`);
    pendingFiles.value = [];
  } catch (e) {
    toast.error(e.message || 'Error al subir una de las imagenes');
  } finally {
    uploading.value = false;
  }
}

// ─── Acciones sobre imagenes existentes ────────────────────────────────────
async function deleteImg(img) {
  imgLoading.value = true;
  try {
    const res = await store.deleteImage(props.serviceUuid, img.uuid);
    if (!res.ok) throw new Error(res.error);
    const idx = props.images.findIndex((i) => i.uuid === img.uuid);
    if (idx !== -1) props.images.splice(idx, 1);
    if (img.is_primary && props.images.length) {
      props.images[0].is_primary = true;
    }
    toast.success('Imagen eliminada');
  } catch (e) {
    toast.error(e.message || 'Error al eliminar imagen');
  } finally {
    imgLoading.value = false;
  }
}

async function setPrimary(img) {
  imgLoading.value = true;
  try {
    const res = await store.setPrimaryImage(props.serviceUuid, img.uuid);
    if (!res.ok) throw new Error(res.error);
    props.images.forEach((i) => { i.is_primary = i.uuid === img.uuid; });
    toast.success('Imagen principal actualizada');
  } catch (e) {
    toast.error(e.message || 'Error al cambiar imagen principal');
  } finally {
    imgLoading.value = false;
  }
}

// ─── Edicion inline de metadata ────────────────────────────────────────────
const editingUuid = ref(null);
const editForm = ref({ caption: '', description: '', alt_text: '' });

function startEdit(img) {
  editingUuid.value = img.uuid;
  editForm.value = { caption: img.caption || '', description: img.description || '', alt_text: img.alt_text || '' };
}

function cancelEdit() {
  editingUuid.value = null;
}

async function saveEdit(img) {
  imgLoading.value = true;
  try {
    const res = await store.updateImageMetadata(props.serviceUuid, img.uuid, editForm.value);
    if (!res.ok) throw new Error(res.error);
    Object.assign(img, res.data);
    toast.success('Imagen actualizada');
    editingUuid.value = null;
  } catch (e) {
    toast.error(e.message || 'Error al actualizar la imagen');
  } finally {
    imgLoading.value = false;
  }
}

// ─── Reemplazar archivo ────────────────────────────────────────────────────
let replaceTargetImg = null;

function triggerReplace(img) {
  replaceTargetImg = img;
  replaceInput.value?.click();
}

async function onReplaceSelected(e) {
  const file = e.target.files[0];
  e.target.value = '';
  if (!file || !replaceTargetImg) return;
  imgLoading.value = true;
  try {
    const res = await store.replaceImageFile(props.serviceUuid, replaceTargetImg.uuid, file);
    if (!res.ok) throw new Error(res.error);
    Object.assign(replaceTargetImg, res.data);
    toast.success('Imagen reemplazada');
  } catch (e2) {
    toast.error(e2.message || 'Error al reemplazar la imagen');
  } finally {
    imgLoading.value = false;
    replaceTargetImg = null;
  }
}

// ─── Reordenar (drag&drop, mismo patron que ContentBlocksTab.vue) ─────────
const dragIndex = ref(null);

function handleDragStart(index) {
  dragIndex.value = index;
}

async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...props.images];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  props.images.splice(0, props.images.length, ...reordered);
  try {
    const res = await store.reorderImages(props.serviceUuid, reordered.map((i) => i.uuid));
    if (!res.ok) throw new Error(res.error);
    props.images.splice(0, props.images.length, ...res.data);
  } catch (e) {
    toast.error(e.message || 'No se pudo guardar el nuevo orden.');
  }
}
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
.object-fit-cover { object-fit: cover; }
.upload-zone { transition: border-color .2s, background .2s; }
.border-dashed { border-style: dashed !important; }
.drag-handle { cursor: grab; }
.gallery-row { transition: background-color .15s ease; }
</style>
