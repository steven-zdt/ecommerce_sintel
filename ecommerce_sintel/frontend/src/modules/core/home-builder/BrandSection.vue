<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Marca</h2>
        <p class="hcb-section-sub">Identidad visual del sitio: nombre, logo y eslogan.</p>
      </div>
    </div>

    <div v-if="loadingBrand" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
    <div v-else class="hcb-card-section">
      <!-- Preview live -->
      <div class="hcb-brand-preview">
        <div class="hcb-brand-preview__logo">
          <img v-if="brandPreviewLogo" :src="brandPreviewLogo" alt="Logo" class="hcb-brand-preview__img">
          <div v-else class="hcb-brand-preview__placeholder">
            <i class="bi bi-building"></i>
          </div>
        </div>
        <div>
          <div class="hcb-brand-preview__name">{{ brandForm.site_name || 'Nombre del sitio' }}</div>
          <div class="hcb-brand-preview__tagline">{{ brandForm.tagline || 'Tu eslogan aqui' }}</div>
        </div>
      </div>

      <div class="hcb-form-grid mt-4">
        <div class="hcb-field">
          <label class="hcb-label">Nombre del sitio</label>
          <input v-model="brandForm.site_name" class="hcb-input" placeholder="Sintel">
        </div>
        <div class="hcb-field">
          <label class="hcb-label">Eslogan</label>
          <input v-model="brandForm.tagline" class="hcb-input" placeholder="Tu plataforma de confianza">
        </div>
        <div class="hcb-field hcb-field--full">
          <label class="hcb-label">Logo</label>
          <div class="hcb-upload-area" @click="$refs.logoInput.click()" @dragover.prevent @drop.prevent="handleLogoDrop">
            <i class="bi bi-cloud-upload"></i>
            <span>Haz clic o arrastra el logo aqui</span>
            <span class="hcb-upload-hint">PNG, SVG, WEBP recomendado</span>
          </div>
          <input ref="logoInput" type="file" accept="image/*" class="d-none" @change="handleLogoSelect">
          <button v-if="brandForm.site_name" class="hcb-btn-link text-danger mt-1" @click="removeLogo">
            <i class="bi bi-trash me-1"></i>Eliminar logo
          </button>
        </div>
      </div>
      <button class="hcb-btn hcb-btn--primary mt-4" :disabled="savingBrand" @click="saveBrand">
        <span v-if="savingBrand" class="spinner-border spinner-border-sm me-1"></span>
        Guardar marca
      </button>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';

const toast = useToast();
const store = useCoreAdminStore();
const { brandLoading: loadingBrand } = storeToRefs(store);

// brandForm/brandPreviewLogo son v-model con el padre: el mini-preview de
// NavbarSection.vue Y el panel de preview compartido (para las pestañas
// 'brand' y 'navbar') necesitan este borrador aunque esta seccion no este
// montada -- unico caso realmente cross-tab de los 8 (ver HomeConfigView.vue).
const brandForm = defineModel('brandForm', { default: () => ({ site_name: 'Sintel', tagline: '' }) });
const brandPreviewLogo = defineModel('brandPreviewLogo', { default: '' });

const savingBrand = ref(false);
const logoInput   = ref(null);
const logoFile    = ref(null);

function handleLogoSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  logoFile.value = file;
  brandPreviewLogo.value = URL.createObjectURL(file);
}
function handleLogoDrop(e) {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  logoFile.value = file;
  brandPreviewLogo.value = URL.createObjectURL(file);
}
function removeLogo() { logoFile.value = null; brandPreviewLogo.value = ''; }
async function saveBrand() {
  savingBrand.value = true;
  const fd = new FormData();
  fd.append('site_name', brandForm.value.site_name);
  fd.append('tagline', brandForm.value.tagline);
  if (logoFile.value) fd.append('logo', logoFile.value);
  if (!logoFile.value && !brandPreviewLogo.value) fd.append('remove_logo', 'true');
  const res = await store.updateSiteBrand(fd);
  if (res.ok) {
    toast.success('Marca guardada.');
    logoFile.value = null;
  } else {
    toast.error('Error al guardar marca.');
  }
  savingBrand.value = false;
}
</script>
