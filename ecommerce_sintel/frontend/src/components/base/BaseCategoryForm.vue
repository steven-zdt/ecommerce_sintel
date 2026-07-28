<template>
  <form @submit.prevent="submit">

    <ul v-if="hasSeo" class="nav nav-tabs nav-fill mb-3" style="font-size:.85rem">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'general' }" @click="tab = 'general'">
          <i class="bi bi-folder me-1"></i>General
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'seo' }" @click="tab = 'seo'">
          <i class="bi bi-search me-1"></i>SEO
        </button>
      </li>
    </ul>

    <div v-show="!hasSeo || tab === 'general'">
      <div class="mb-3">
        <label class="form-label small fw-bold">Nombre de la {{ entityLabel }} <span class="text-danger">*</span></label>
        <input v-model="form.name" type="text" class="form-control" required :placeholder="namePlaceholder">
      </div>

      <div class="mb-3">
        <label class="form-label small fw-bold">Descripcion</label>
        <textarea v-model="form.description" class="form-control" rows="3" placeholder="Descripcion..."></textarea>
      </div>

      <div v-if="hasImage" class="mb-3">
        <label class="form-label small fw-bold">Imagen de portada</label>
        <div v-if="imagePreview" class="mb-2 position-relative d-inline-block">
          <img :src="imagePreview" alt="Preview" class="rounded border" style="height:100px;width:100px;object-fit:cover;">
          <button type="button" class="btn btn-xs btn-danger position-absolute top-0 end-0 m-1 rounded-circle"
                  style="padding:2px 6px;font-size:.7rem" @click="clearImage" title="Eliminar imagen">
            <i class="bi bi-x"></i>
          </button>
        </div>
        <input ref="fileInput" type="file" class="form-control form-control-sm" accept="image/*" @change="onImageChange">
        <div class="form-text">Formatos: JPG, PNG, WebP. Max 2 MB.</div>
      </div>

      <div class="mb-3 form-check form-switch">
        <input v-model="form.is_active" class="form-check-input" type="checkbox" id="catActive">
        <label class="form-check-label small" for="catActive">{{ entityLabel }} Activa</label>
      </div>
    </div>

    <div v-if="hasSeo" v-show="tab === 'seo'">
      <div class="alert alert-info py-2 small mb-3">
        <i class="bi bi-info-circle me-1"></i>
        Optimiza esta categoria para motores de busqueda.
      </div>
      <div class="mb-3">
        <label class="form-label small fw-bold">Titulo SEO</label>
        <input v-model="form.meta_title" type="text" class="form-control" maxlength="70"
               placeholder="Titulo optimizado para buscadores">
        <div class="form-text d-flex justify-content-between">
          <span>Recomendado: 50-70 caracteres.</span>
          <span :class="form.meta_title.length > 60 ? 'text-warning' : 'text-muted'">{{ form.meta_title.length }}/70</span>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-bold">Meta Descripcion</label>
        <textarea v-model="form.meta_description" class="form-control" rows="3" maxlength="160"
                  placeholder="Descripcion breve para resultados de busqueda..."></textarea>
        <div class="form-text d-flex justify-content-between">
          <span>Recomendado: 120-160 caracteres.</span>
          <span :class="form.meta_description.length > 145 ? 'text-warning' : 'text-muted'">{{ form.meta_description.length }}/160</span>
        </div>
      </div>
    </div>

    <div class="d-flex gap-2 mt-4">
      <button type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? `Crear ${entityLabel}` : 'Guardar Cambios' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">
        Cancelar
      </button>
    </div>
  </form>
</template>

<script setup>
/**
 * BaseCategoryForm.vue -- fusion de modules/shop/CategoryForm.vue y
 * modules/renting/RentingCategoryForm.vue (Fase 2 §2.4 / Fase 7 §7.2 Paso 3).
 * `hasImage`/`hasSeo` reflejan una diferencia REAL de schema (verificado:
 * `shop.Category` tiene `image`/`meta_title`/`meta_description`,
 * `renting.RentingCategory` NO los tiene) -- no se fuerza paridad de campos
 * que el backend no soporta.
 */
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
  endpoint: { type: String, required: true }, // 'dashboard/categories' | 'dashboard/renting-categories'
  hasImage: { type: Boolean, default: false },
  hasSeo: { type: Boolean, default: false },
  entityLabel: { type: String, default: 'Categoria' },
  namePlaceholder: { type: String, default: 'Ej: Electronicos' },
});
const emit = defineEmits(['success', 'cancel']);

const api      = useApi();
const toast    = useToast();
const { handleError } = useErrorHandler();
const loading  = ref(false);
const tab      = ref('general');
const fileInput   = ref(null);
const imageFile   = ref(null);
const imagePreview = ref(null);

function emptyForm() {
  const base = { name: '', description: '', is_active: true };
  return props.hasSeo ? { ...base, meta_title: '', meta_description: '' } : base;
}
const form = ref(emptyForm());

function onImageChange(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  imageFile.value = file;
  imagePreview.value = URL.createObjectURL(file);
}

function clearImage() {
  imageFile.value = null;
  imagePreview.value = null;
  if (fileInput.value) fileInput.value.value = '';
}

watch(() => props.item, (val) => {
  tab.value = 'general';
  clearImage();
  if (val && props.mode === 'edit') {
    form.value = props.hasSeo
      ? {
          name: val.name, description: val.description || '', is_active: val.is_active,
          meta_title: val.meta_title || '', meta_description: val.meta_description || '',
        }
      : { name: val.name, description: val.description || '', is_active: val.is_active };
    if (props.hasImage && val.image) imagePreview.value = val.image;
  } else {
    form.value = emptyForm();
  }
}, { immediate: true });

async function submit() {
  loading.value = true;
  try {
    // uuid, no id -- los ViewSets admin de marca/categoria (shop y renting)
    // usan lookup_field='uuid'; usar el id entero produce un 500
    // ("no es un UUID valido") en cualquier edicion (bug real, 2026-07-27).
    const endpoint = props.mode === 'create' ? `${props.endpoint}/` : `${props.endpoint}/${props.item.uuid}/`;
    const method = props.mode === 'create' ? 'post' : 'patch';

    if (imageFile.value) {
      const fd = new FormData();
      Object.entries(form.value).forEach(([k, v]) => fd.append(k, v));
      fd.append('image', imageFile.value);
      await api[method](endpoint, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    } else {
      await api[method](endpoint, form.value);
    }

    toast.success(props.mode === 'create' ? `${props.entityLabel} creada` : `${props.entityLabel} actualizada`);
    emit('success');
  } catch (e) {
    handleError(e, 'Error al guardar');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.btn-xs { padding: 0.1rem 0.35rem; font-size: 0.75rem; line-height: 1.3; }
</style>
