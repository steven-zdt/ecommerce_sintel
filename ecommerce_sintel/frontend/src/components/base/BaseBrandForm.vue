<template>
  <form @submit.prevent="submit">
    <div class="mb-3">
      <label class="form-label small fw-bold">Nombre de la Marca <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required :placeholder="namePlaceholder">
    </div>

    <div v-if="hasLogo" class="mb-3">
      <label class="form-label small fw-bold">Logo</label>
      <div v-if="logoPreview" class="mb-2 position-relative d-inline-block">
        <img :src="logoPreview" alt="Logo" class="rounded border bg-light"
             style="height:80px;width:80px;object-fit:contain;padding:6px;">
        <button type="button" class="btn btn-xs btn-danger position-absolute top-0 end-0 m-1 rounded-circle"
                style="padding:2px 6px;font-size:.7rem" @click="clearLogo" title="Quitar logo">
          <i class="bi bi-x"></i>
        </button>
      </div>
      <input ref="fileInput" type="file" class="form-control form-control-sm" accept="image/*" @change="onLogoChange">
      <div class="form-text">Formatos: JPG, PNG, SVG. Max 1 MB. Fondo transparente recomendado.</div>
    </div>

    <div v-if="hasActiveToggle" class="mb-3 form-check form-switch">
      <input v-model="form.is_active" class="form-check-input" type="checkbox" id="brandActive">
      <label class="form-check-label small" for="brandActive">Marca Activa</label>
    </div>

    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? 'Crear Marca' : 'Guardar Cambios' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">
        Cancelar
      </button>
    </div>
  </form>
</template>

<script setup>
/**
 * BaseBrandForm.vue -- fusion de modules/shop/BrandForm.vue y
 * modules/renting/RentingBrandForm.vue (Fase 2 §2.4 / Fase 7 §7.2 Paso 3 del
 * PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md). `hasLogo`/
 * `hasActiveToggle` reflejan una diferencia REAL de schema (verificado en
 * `shop.Brand` vs `renting.RentingBrand`: RentingBrand no tiene ni `logo` ni
 * `is_active` en el modelo) -- no se fuerza paridad de campos que el backend
 * no tiene, solo se deduplica el markup/logica que SI es identica.
 */
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
  endpoint: { type: String, required: true }, // 'dashboard/brands' | 'dashboard/renting-brands'
  hasLogo: { type: Boolean, default: false },
  hasActiveToggle: { type: Boolean, default: false },
  namePlaceholder: { type: String, default: 'Ej: Marca' },
});
const emit = defineEmits(['success', 'cancel']);

const api     = useApi();
const toast   = useToast();
const { handleError } = useErrorHandler();
const loading = ref(false);
const fileInput  = ref(null);
const logoFile   = ref(null);
const logoPreview = ref(null);

function emptyForm() {
  return props.hasActiveToggle ? { name: '', is_active: true } : { name: '' };
}
const form = ref(emptyForm());

function onLogoChange(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  logoFile.value = file;
  logoPreview.value = URL.createObjectURL(file);
}

function clearLogo() {
  logoFile.value = null;
  logoPreview.value = null;
  if (fileInput.value) fileInput.value.value = '';
}

watch(() => props.item, (val) => {
  clearLogo();
  if (val && props.mode === 'edit') {
    form.value = props.hasActiveToggle
      ? { name: val.name, is_active: val.is_active ?? true }
      : { name: val.name };
    if (props.hasLogo && val.logo) logoPreview.value = val.logo;
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

    if (logoFile.value) {
      const fd = new FormData();
      Object.entries(form.value).forEach(([k, v]) => fd.append(k, v));
      fd.append('logo', logoFile.value);
      await api[method](endpoint, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    } else {
      await api[method](endpoint, form.value);
    }

    toast.success(props.mode === 'create' ? 'Marca creada' : 'Marca actualizada');
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
