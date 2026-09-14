<template>
  <div>
    <!-- Formulario subir imagen(es) -->
    <div class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Subir imagenes</h6>
      <div class="mb-2">
        <label class="form-label smaller mb-1 fw-semibold">Archivo(s) <span class="text-danger">*</span></label>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          multiple
          class="form-control form-control-sm"
          @change="uploadFiles = Array.from($event.target.files)"
        >
        <div v-if="uploadFiles.length > 1" class="form-text smaller">
          {{ uploadFiles.length }} archivos seleccionados.
        </div>
      </div>
      <div class="mb-2">
        <label class="form-label smaller mb-1">Texto alternativo (SEO)</label>
        <input v-model="uploadAltText" type="text" class="form-control form-control-sm"
               placeholder="Descripcion de la imagen">
        <div v-if="uploadFiles.length > 1" class="form-text smaller">
          Se aplica a todas las imagenes de esta subida.
        </div>
      </div>
      <button type="button" class="btn btn-sm btn-primary"
              @click="uploadImages" :disabled="actionLoading || !uploadFiles.length">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-cloud-upload me-1"></i>
        {{ uploadFiles.length > 1 ? `Subir ${uploadFiles.length} imagenes` : 'Subir imagen' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="imagesLoading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>

    <!-- Sin imagenes -->
    <div v-else-if="!productImages.length" class="text-center py-4 text-muted">
      <i class="bi bi-images fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin imagenes. Sube la primera.</p>
    </div>

    <!-- Lista de imagenes -->
    <div v-else class="d-flex flex-column gap-2">
      <div v-for="img in productImages" :key="img.uuid"
           class="d-flex align-items-center gap-2 p-2 rounded-3 border"
           :class="img.is_primary ? 'border-primary bg-primary-subtle' : 'bg-white'">

        <img :src="img.image" :alt="img.alt_text || 'imagen'"
             class="rounded-2 object-fit-cover flex-shrink-0"
             style="width:56px;height:56px;border:1px solid #e5e7eb">

        <div class="flex-grow-1 min-w-0">
          <div class="d-flex align-items-center gap-1 flex-wrap">
            <span v-if="img.is_primary"
                  class="badge bg-primary text-white" style="font-size:.65rem">
              <i class="bi bi-star-fill me-1"></i>Principal
            </span>
            <span class="text-muted small text-truncate">{{ img.alt_text || '(sin descripcion)' }}</span>
          </div>
        </div>

        <div class="d-flex gap-1 flex-shrink-0">
          <button v-if="!img.is_primary"
                  type="button"
                  class="btn btn-sm btn-outline-primary py-0 px-2"
                  style="font-size:.75rem"
                  @click="setPrimaryImage(img)"
                  :disabled="actionLoading"
                  title="Establecer como principal">
            <i class="bi bi-star"></i>
          </button>
          <button type="button"
                  class="btn btn-sm btn-outline-danger py-0 px-2"
                  style="font-size:.75rem"
                  @click="deleteImage(img)"
                  :disabled="actionLoading"
                  title="Eliminar imagen">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Footer Imagenes -->
    <div class="d-flex justify-content-end mt-4 pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useShopAdminStore } from '@/store/shopAdmin';

const props = defineProps({
  productUuid: { type: String, required: true },
});
defineEmits(['close']);

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useShopAdminStore();
const { productImages, imagesLoading, actionLoading } = storeToRefs(store);

const uploadFiles = ref([]);
const uploadAltText = ref('');
const fileInputRef = ref(null);

async function fetchImages() {
  if (!props.productUuid) return;
  await store.fetchProductImages(props.productUuid);
  if (store.error) toast.error(store.error);
}

async function uploadImages() {
  if (!uploadFiles.value.length) return toast.error('Selecciona al menos una imagen');
  const files = uploadFiles.value;
  const noExistingImages = !productImages.value.length;
  let successCount = 0;
  let firstError = null;

  for (let i = 0; i < files.length; i++) {
    const fd = new FormData();
    fd.append('image', files[i]);
    fd.append('alt_text', uploadAltText.value || '');
    // Solo la primera imagen de la primera subida (cuando el producto aun no
    // tiene ninguna) se marca principal -- mismo criterio que el flujo de 1
    // archivo, extendido a la subida multiple sin marcar mas de una.
    if (noExistingImages && i === 0) fd.append('is_primary', 'true');

    const res = await store.uploadProductImage(props.productUuid, fd);
    if (res.ok) {
      successCount++;
    } else if (!firstError) {
      firstError = res.error;
    }
  }

  uploadFiles.value = [];
  uploadAltText.value = '';
  if (fileInputRef.value) fileInputRef.value.value = '';
  await fetchImages();

  if (successCount) {
    toast.success(successCount > 1 ? `${successCount} imagenes subidas` : 'Imagen subida');
  }
  if (firstError) {
    handleError(firstError, successCount ? 'Algunas imagenes no se pudieron subir' : 'Error al subir imagen');
  }
}

async function deleteImage(img) {
  const res = await store.deleteProductImage(props.productUuid, img.uuid);
  if (res.ok) {
    await fetchImages();
    toast.success('Imagen eliminada');
  } else {
    toast.error('Error al eliminar imagen');
  }
}

async function setPrimaryImage(img) {
  const res = await store.setPrimaryImage(props.productUuid, img.uuid);
  if (res.ok) {
    await fetchImages();
    toast.success('Imagen principal actualizada');
  } else {
    toast.error('Error al establecer imagen principal');
  }
}

onMounted(fetchImages);
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
</style>
