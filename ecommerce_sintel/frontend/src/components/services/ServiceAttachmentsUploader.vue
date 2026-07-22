<template>
  <div class="sau-root">
    <!-- Drop zone -->
    <div
      class="sau-dropzone"
      :class="{ 'sau-dropzone--over': dragOver, 'sau-dropzone--full': atLimit }"
      @click="!atLimit && fileInput.click()"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="onDrop"
    >
      <i class="bi bi-cloud-arrow-up sau-dz-icon"></i>
      <div class="sau-dz-title">
        <span v-if="atLimit">Limite de {{ MAX_FILES }} archivos alcanzado</span>
        <span v-else>Arrastra archivos o <span class="sau-dz-link">haz clic para seleccionar</span></span>
      </div>
      <div class="sau-dz-hint">
        Fotos · PDF · Word · Excel · Planos · Videos cortos &mdash; max {{ MAX_FILES }} archivos / {{ MAX_TOTAL_MB }} MB total
      </div>
      <input
        ref="fileInput"
        type="file"
        multiple
        :accept="ACCEPT"
        class="d-none"
        @change="onInputChange"
      >
    </div>

    <!-- Total size bar -->
    <div v-if="files.length" class="sau-total-bar mt-2">
      <div class="d-flex justify-content-between align-items-center mb-1">
        <span class="sau-bar-label">{{ files.length }} archivo{{ files.length !== 1 ? 's' : '' }}</span>
        <span class="sau-bar-label">{{ fmtSize(totalBytes) }} / {{ MAX_TOTAL_MB }} MB</span>
      </div>
      <div class="progress sau-progress">
        <div
          class="progress-bar"
          :class="totalBytes > MAX_TOTAL_BYTES * 0.9 ? 'bg-danger' : 'bg-warning'"
          :style="{ width: Math.min(totalBytes / MAX_TOTAL_BYTES * 100, 100) + '%' }"
        ></div>
      </div>
    </div>

    <!-- File list -->
    <div v-if="files.length" class="sau-list mt-3">
      <div
        v-for="(entry, idx) in files"
        :key="entry.id"
        class="sau-item"
        :class="{ 'sau-item--dragging': dragIdx === idx }"
        draggable="true"
        @dragstart="onItemDragStart(idx)"
        @dragover.prevent="onItemDragOver(idx)"
        @drop.prevent="onItemDrop(idx)"
        @dragend="dragIdx = null"
      >
        <!-- Thumbnail / icon -->
        <div class="sau-thumb">
          <img v-if="entry.preview" :src="entry.preview" :alt="entry.file.name" class="sau-thumb-img" />
          <i v-else :class="fileIcon(entry.file)" class="sau-thumb-icon"></i>
        </div>

        <!-- Info -->
        <div class="sau-item-info">
          <div class="sau-item-name" :title="entry.file.name">{{ entry.file.name }}</div>
          <div class="sau-item-meta">
            <span>{{ fmtSize(entry.file.size) }}</span>
            <span class="sau-dot">·</span>
            <select
              v-model="entry.doc_type"
              class="sau-type-select"
              @change="emit('update:modelValue', files)"
            >
              <option value="">Tipo...</option>
              <option value="foto">Foto</option>
              <option value="plano">Plano</option>
              <option value="manual">Manual</option>
              <option value="pdf">Documento PDF</option>
              <option value="excel">Hoja de calculo</option>
              <option value="word">Documento Word</option>
              <option value="video">Video</option>
              <option value="otro">Otro</option>
            </select>
          </div>
        </div>

        <!-- Drag handle + delete -->
        <div class="sau-actions">
          <i class="bi bi-grip-vertical sau-drag-handle" title="Reordenar"></i>
          <button class="sau-del-btn" type="button" @click="remove(idx)" title="Eliminar">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Errors -->
    <div v-if="errors.length" class="sau-errors mt-2">
      <div v-for="(e, i) in errors" :key="i" class="sau-error-item">
        <i class="bi bi-exclamation-circle-fill me-1"></i>{{ e }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const MAX_FILES = 10;
const MAX_TOTAL_MB = 100;
const MAX_TOTAL_BYTES = MAX_TOTAL_MB * 1024 * 1024;
const ACCEPT = [
  'image/jpeg', 'image/png', 'image/gif', 'image/webp',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'video/mp4', 'video/quicktime', 'video/x-msvideo',
].join(',');

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
});
const emit = defineEmits(['update:modelValue']);

const fileInput = ref(null);
const dragOver  = ref(false);
const dragIdx   = ref(null);
const errors    = ref([]);

const files = ref(props.modelValue.map(f => wrapFile(f)));

let _idSeq = 0;
function wrapFile(file, existingId) {
  const entry = {
    id:       existingId ?? ++_idSeq,
    file,
    doc_type: '',
    preview:  null,
  };
  if (file.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = (e) => { entry.preview = e.target.result; };
    reader.readAsDataURL(file);
  }
  return entry;
}

const totalBytes = computed(() => files.value.reduce((s, e) => s + e.file.size, 0));
const atLimit    = computed(() => files.value.length >= MAX_FILES);

function addFiles(rawFiles) {
  errors.value = [];
  const incoming = Array.from(rawFiles);

  for (const f of incoming) {
    if (files.value.some(e => e.file.name === f.name && e.file.size === f.size)) continue;
    if (files.value.length >= MAX_FILES) {
      errors.value.push(`Maximo ${MAX_FILES} archivos. "${f.name}" no fue agregado.`);
      continue;
    }
    if (totalBytes.value + f.size > MAX_TOTAL_BYTES) {
      errors.value.push(`"${f.name}" supera el limite total de ${MAX_TOTAL_MB} MB.`);
      continue;
    }
    files.value.push(wrapFile(f));
  }
  emit('update:modelValue', files.value);
}

function remove(idx) {
  files.value.splice(idx, 1);
  emit('update:modelValue', files.value);
}

function onInputChange(e) {
  addFiles(e.target.files);
  e.target.value = '';
}

function onDrop(e) {
  dragOver.value = false;
  addFiles(e.dataTransfer.files);
}

function onItemDragStart(idx) { dragIdx.value = idx; }
function onItemDragOver(idx)  { dragIdx.value = idx; }
function onItemDrop(toIdx) {
  const fromIdx = dragIdx.value;
  if (fromIdx === null || fromIdx === toIdx) return;
  const [moved] = files.value.splice(fromIdx, 1);
  files.value.splice(toIdx, 0, moved);
  dragIdx.value = null;
  emit('update:modelValue', files.value);
}

function fileIcon(f) {
  if (f.type.startsWith('image/'))  return 'bi bi-file-earmark-image text-primary';
  if (f.type === 'application/pdf') return 'bi bi-file-earmark-pdf text-danger';
  if (f.type.includes('word'))      return 'bi bi-file-earmark-word text-primary';
  if (f.type.includes('excel') || f.type.includes('spreadsheet')) return 'bi bi-file-earmark-excel text-success';
  if (f.type.startsWith('video/'))  return 'bi bi-file-earmark-play text-warning';
  return 'bi bi-file-earmark text-secondary';
}

function fmtSize(bytes) {
  if (bytes < 1024)        return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>

<style scoped>
.sau-dropzone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  transition: all .18s;
  background: #fafafa;
}
.sau-dropzone:hover,
.sau-dropzone--over { border-color: #f59e0b; background: #fffbeb; }
.sau-dropzone--full { cursor: not-allowed; opacity: .6; }
.sau-dz-icon { font-size: 2rem; color: #9ca3af; display: block; margin-bottom: 6px; }
.sau-dz-title { font-size: .9rem; color: #374151; font-weight: 500; margin-bottom: 4px; }
.sau-dz-link { color: #d97706; font-weight: 600; text-decoration: underline; }
.sau-dz-hint { font-size: .72rem; color: #9ca3af; }

.sau-progress { height: 5px; border-radius: 3px; }
.sau-bar-label { font-size: .72rem; color: #6b7280; }

.sau-list { display: flex; flex-direction: column; gap: 8px; }
.sau-item {
  display: flex; align-items: center; gap: 10px;
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 10px; padding: 8px 10px;
  transition: box-shadow .15s;
}
.sau-item--dragging { box-shadow: 0 4px 18px rgba(0,0,0,.12); border-color: #f59e0b; }

.sau-thumb {
  width: 44px; height: 44px; flex-shrink: 0;
  border-radius: 7px; overflow: hidden;
  background: #f3f4f6;
  display: flex; align-items: center; justify-content: center;
}
.sau-thumb-img { width: 100%; height: 100%; object-fit: cover; }
.sau-thumb-icon { font-size: 1.4rem; }

.sau-item-info { flex: 1; min-width: 0; }
.sau-item-name { font-size: .83rem; font-weight: 600; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sau-item-meta { display: flex; align-items: center; gap: 4px; margin-top: 3px; }
.sau-item-meta span { font-size: .7rem; color: #6b7280; }
.sau-dot { color: #d1d5db; }
.sau-type-select {
  font-size: .7rem; color: #374151; border: 1px solid #e5e7eb;
  border-radius: 5px; padding: 1px 4px; background: #f9fafb;
  cursor: pointer;
}

.sau-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.sau-drag-handle { font-size: 1rem; color: #9ca3af; cursor: grab; padding: 4px; }
.sau-drag-handle:active { cursor: grabbing; }
.sau-del-btn {
  background: none; border: none; padding: 4px 6px;
  color: #9ca3af; border-radius: 6px; cursor: pointer;
  transition: color .15s, background .15s;
  font-size: .85rem;
}
.sau-del-btn:hover { color: #dc2626; background: #fee2e2; }

.sau-errors { }
.sau-error-item { font-size: .75rem; color: #dc2626; margin-bottom: 3px; }
</style>
