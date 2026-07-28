<template>
  <div>
    <p class="text-muted small mb-3">
      Metadatos para buscadores y redes sociales. El Schema.org (JSON-LD) del producto se
      genera automaticamente en el detalle publico a partir de estos mismos datos.
    </p>
    <div class="mb-3">
      <label class="form-label small fw-bold">Meta Titulo</label>
      <input v-model="form.meta_title" type="text" maxlength="70" class="form-control form-control-sm" placeholder="Titulo para buscadores (max 70 caracteres)">
      <div class="form-text" style="font-size:.7rem">{{ (form.meta_title || '').length }}/70</div>
    </div>
    <div class="mb-3">
      <label class="form-label small fw-bold">Meta Descripcion</label>
      <textarea v-model="form.meta_description" class="form-control form-control-sm" rows="3" placeholder="Descripcion breve para resultados de busqueda"></textarea>
    </div>
    <div class="mb-3">
      <label class="form-label small fw-bold">Palabras clave</label>
      <input v-model="form.meta_keywords" type="text" class="form-control form-control-sm" placeholder="alquiler, grua, construccion (separadas por coma)">
    </div>
    <div class="mb-3">
      <label class="form-label small fw-bold">Imagen OpenGraph</label>
      <input ref="fileInputRef" type="file" accept="image/*" class="form-control form-control-sm" @change="onFileChange">
      <img v-if="currentOgImage" :src="currentOgImage" class="mt-2 rounded border" style="max-height:120px">
    </div>
    <button type="button" class="btn btn-primary w-100" @click="save" :disabled="saving">
      <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
      <i v-else class="bi bi-floppy me-1"></i> Guardar SEO
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  equipment: { type: Object, required: true },
});
const emit = defineEmits(['updated']);

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const saving = ref(false);
const fileInputRef = ref(null);
const ogImageFile = ref(null);
const currentOgImage = ref('');
const form = ref({ meta_title: '', meta_description: '', meta_keywords: '' });

function syncFromEquipment(equipment) {
  form.value = {
    meta_title: equipment?.meta_title || '',
    meta_description: equipment?.meta_description || '',
    meta_keywords: equipment?.meta_keywords || '',
  };
  currentOgImage.value = equipment?.og_image || '';
}

function onFileChange(e) {
  ogImageFile.value = e.target.files[0] || null;
}

async function save() {
  saving.value = true;
  try {
    let data;
    if (ogImageFile.value) {
      const fd = new FormData();
      fd.append('meta_title', form.value.meta_title || '');
      fd.append('meta_description', form.value.meta_description || '');
      fd.append('meta_keywords', form.value.meta_keywords || '');
      fd.append('og_image', ogImageFile.value);
      const res = await api.patch(`dashboard/equipment/${props.equipment.uuid}/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      data = res.data;
    } else {
      const res = await api.patch(`dashboard/equipment/${props.equipment.uuid}/`, { ...form.value });
      data = res.data;
    }
    ogImageFile.value = null;
    if (fileInputRef.value) fileInputRef.value.value = '';
    syncFromEquipment(data);
    emit('updated', data);
    toast.success('SEO actualizado');
  } catch (e) {
    handleError(e, 'Error al guardar SEO');
  } finally {
    saving.value = false;
  }
}

watch(() => props.equipment, syncFromEquipment, { immediate: true, deep: false });
</script>
