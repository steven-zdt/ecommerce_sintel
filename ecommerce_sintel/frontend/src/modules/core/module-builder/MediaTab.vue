<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-image me-2"></i>Imagen del módulo</div>
    <div class="mb-grid">
      <div class="mb-field mb-field--full">
        <label class="mb-label">Imagen de fondo</label>
        <div
          class="mb-upload-zone"
          @click="$refs.bgImgInput.click()"
          @dragover.prevent="imageState.dragging = true"
          @dragleave="imageState.dragging = false"
          @drop.prevent="handleImgDrop"
          :class="imageState.dragging && 'mb-upload-zone--drag'"
        >
          <img v-if="imageState.preview && !imageState.remove" :src="imageState.preview" class="mb-upload-zone__preview" alt="">
          <div v-else class="mb-upload-zone__ph">
            <i class="bi bi-cloud-upload" style="font-size:2rem"></i>
            <span>Haz clic o arrastra imagen</span>
          </div>
          <input ref="bgImgInput" type="file" accept="image/*" class="d-none" @change="handleImgSelect">
        </div>
        <div v-if="imageState.preview && !imageState.remove" class="d-flex gap-2 mt-2">
          <button class="mb-btn-sm" @click.stop="$refs.bgImgInput.click()"><i class="bi bi-arrow-repeat me-1"></i>Cambiar</button>
          <button class="mb-btn-sm mb-btn-sm--danger" @click.stop="imageState.remove = true; imageState.preview = ''"><i class="bi bi-trash me-1"></i>Eliminar</button>
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Filtro de imagen</label>
        <select v-model="form.bg_filter" class="mb-select">
          <option value="none">Sin filtro</option>
          <option value="grayscale">Escala de grises</option>
          <option value="blur">Desenfoque</option>
          <option value="brightness">Brillo alto</option>
          <option value="sepia">Sepia</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

// `imageState` es el objeto reactivo del shell con la subida de imagen:
//   { file, preview, remove, dragging }
// El shell lo lee en save() (multipart) y lo repuebla en loadModule().
const props = defineProps({
  form:       { type: Object, required: true },
  imageState: { type: Object, required: true },
});

const bgImgInput = ref(null);

function handleImgSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  props.imageState.file    = file;
  props.imageState.preview = URL.createObjectURL(file);
  props.imageState.remove  = false;
}

function handleImgDrop(e) {
  props.imageState.dragging = false;
  const file = e.dataTransfer.files[0];
  if (!file || !file.type.startsWith('image/')) return;
  props.imageState.file    = file;
  props.imageState.preview = URL.createObjectURL(file);
  props.imageState.remove  = false;
}
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
/* ── Upload zone ─────────────────────────────────────────────────────────── */
.mb-upload-zone {
  border: 2px dashed #d1d5db; border-radius: 10px;
  background: #f8fafc; min-height: 120px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: border-color .15s, background .15s;
  position: relative; overflow: hidden;
}
.mb-upload-zone:hover         { border-color: #60a5fa; background: #eff6ff; }
.mb-upload-zone--drag         { border-color: #2563eb; background: #dbeafe; }
.mb-upload-zone__ph           { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; color: #94a3b8; font-size: 0.8rem; }
.mb-upload-zone__preview      { width: 100%; height: 120px; object-fit: cover; }
.mb-btn-sm {
  padding: 0.25rem 0.65rem; border: 1px solid #d1d5db; border-radius: 5px;
  background: #fff; font-size: 0.75rem; cursor: pointer; color: #374151;
}
.mb-btn-sm:hover          { background: #f1f5f9; }
.mb-btn-sm--danger        { color: #dc2626; }
.mb-btn-sm--danger:hover  { background: #fee2e2; border-color: #fca5a5; }
</style>
