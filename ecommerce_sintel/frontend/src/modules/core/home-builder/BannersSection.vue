<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Banners</h2>
        <p class="hcb-section-sub">Carrusel hero de la pagina principal. Soporta imagen y video.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" @click="openBannerForm()">
        <i class="bi bi-plus-lg"></i> Nuevo banner
      </button>
    </div>

    <div v-if="loadingBanners" class="hcb-loading"><div class="spinner-border text-primary"></div></div>

    <div v-else class="hcb-banners-list">
      <div
        v-for="b in banners"
        :key="b.uuid"
        :class="['hcb-banner-row', !b.is_active && 'hcb-banner-row--inactive']"
      >
        <div class="hcb-banner-thumb">
          <img v-if="b.image" :src="b.image" alt="">
          <div v-else-if="b.video" class="hcb-banner-video-icon"><i class="bi bi-play-circle"></i></div>
          <div v-else class="hcb-banner-placeholder"><i class="bi bi-image"></i></div>
        </div>
        <div class="hcb-banner-info">
          <div class="hcb-banner-title">{{ b.title }}</div>
          <div class="hcb-banner-meta">
            <span class="hcb-chip" :class="b.is_active ? 'hcb-chip--green' : 'hcb-chip--gray'">
              {{ b.is_active ? 'Activo' : 'Inactivo' }}
            </span>
            <span class="hcb-chip">Orden {{ b.display_order }}</span>
            <span v-if="b.link_url" class="hcb-chip">{{ b.link_label || b.link_url }}</span>
          </div>
        </div>
        <div class="hcb-banner-actions">
          <button class="hcb-icon-btn" @click="openBannerForm(b)"><i class="bi bi-pencil"></i></button>
          <button class="hcb-icon-btn hcb-icon-btn--danger" @click="deleteBanner(b)"><i class="bi bi-trash"></i></button>
        </div>
      </div>
      <div v-if="!banners.length" class="hcb-empty">Sin banners. Crea el primero.</div>
    </div>

    <Teleport to="body">
      <BaseModal v-model="showBannerModal" :title="editingBanner ? 'Editar banner' : 'Nuevo banner'">
        <!-- Preview live del banner -->
        <div class="hcb-banner-live-preview">
          <img v-if="bannerMediaPreview && bannerMediaType === 'image' && !bannerRemoveMedia" :src="bannerMediaPreview" alt="" class="hcb-blp-img">
          <video v-else-if="bannerMediaPreview && bannerMediaType === 'video' && !bannerRemoveMedia" :src="bannerMediaPreview" class="hcb-blp-img" muted loop autoplay></video>
          <div v-else class="hcb-blp-placeholder" :style="bannerForm.background_color ? { background: bannerForm.background_color } : {}">
            <i class="bi bi-image" v-if="!bannerForm.background_color"></i>
            <span>{{ bannerForm.title || 'Titulo del banner' }}</span>
          </div>
          <div v-if="bannerForm.title" class="hcb-blp-overlay">
            <div v-if="bannerForm.eyebrow" class="hcb-blp-eyebrow">{{ bannerForm.eyebrow }}</div>
            <div class="hcb-blp-title">{{ bannerForm.title }}</div>
            <div v-if="bannerForm.subtitle" class="hcb-blp-subtitle">{{ bannerForm.subtitle }}</div>
            <div class="d-flex gap-2 flex-wrap mt-1">
              <button v-if="bannerForm.link_label" class="hcb-blp-cta">{{ bannerForm.link_label }}</button>
              <button v-if="bannerForm.cta_ghost_label" class="hcb-blp-cta hcb-blp-cta--ghost">{{ bannerForm.cta_ghost_label }}</button>
            </div>
          </div>
        </div>

        <div class="hcb-form-grid mt-3">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo *</label>
            <input v-model="bannerForm.title" class="hcb-input" placeholder="Titulo del banner">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Subtitulo</label>
            <input v-model="bannerForm.subtitle" class="hcb-input" placeholder="Descripcion breve">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Eyebrow (texto pequeño sobre el titulo)</label>
            <input v-model="bannerForm.eyebrow" class="hcb-input" placeholder="Sintel Technology">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL boton principal</label>
            <input v-model="bannerForm.link_url" class="hcb-input" placeholder="/tienda">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Texto boton principal</label>
            <input v-model="bannerForm.link_label" class="hcb-input" placeholder="Ver ahora">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Texto boton secundario</label>
            <input v-model="bannerForm.cta_ghost_label" class="hcb-input" placeholder="Solicitar cotizacion">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL boton secundario</label>
            <input v-model="bannerForm.cta_ghost_url" class="hcb-input" placeholder="/cotizar">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color de fondo</label>
            <div class="d-flex gap-2 align-items-center">
              <input v-model="bannerForm.background_color" type="color" class="hcb-color-input"
                title="Selecciona color de fondo (se usa si no hay imagen/video)">
              <input v-model="bannerForm.background_color" class="hcb-input" placeholder="#080d1a" style="flex:1">
              <button v-if="bannerForm.background_color" type="button" class="hcb-btn--sm hcb-btn--danger-sm"
                @click="bannerForm.background_color = ''" title="Quitar color">
                <i class="bi bi-x"></i>
              </button>
            </div>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Orden</label>
            <input v-model.number="bannerForm.display_order" type="number" class="hcb-input" min="0">
          </div>
          <div class="hcb-field d-flex align-items-end">
            <div class="form-check form-switch">
              <input v-model="bannerForm.is_active" class="form-check-input" type="checkbox">
              <label class="form-check-label">Activo</label>
            </div>
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Media (imagen o video)</label>
            <!-- Imagen/video actual con opcion de eliminar -->
            <div v-if="bannerMediaPreview && !bannerRemoveMedia" class="hcb-media-current">
              <img v-if="bannerMediaType === 'image'" :src="bannerMediaPreview" class="hcb-media-current__img" alt="">
              <video v-else :src="bannerMediaPreview" class="hcb-media-current__img" muted></video>
              <div class="hcb-media-current__actions">
                <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeBannerMedia">
                  <i class="bi bi-trash me-1"></i>Eliminar media
                </button>
                <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.bannerFileInput.click()">
                  <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                </button>
              </div>
            </div>
            <div
              v-else
              class="hcb-upload-area"
              :class="bannerIsDragging ? 'hcb-upload-area--dragging' : ''"
              @click="$refs.bannerFileInput.click()"
              @dragover.prevent="bannerIsDragging = true"
              @dragleave="bannerIsDragging = false"
              @drop.prevent="handleBannerDrop"
            >
              <i class="bi bi-cloud-upload"></i>
              <span>Haz clic o arrastra imagen/video</span>
            </div>
            <input ref="bannerFileInput" type="file" accept="image/*,video/*" class="d-none" @change="handleBannerSelect">
          </div>
        </div>
        <div v-if="bannerError" class="alert alert-danger small py-2 mt-2">{{ bannerError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeBannerForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingBanner" @click="saveBanner">
            <span v-if="savingBanner" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingBanner ? 'Guardar cambios' : 'Crear banner' }}
          </button>
        </template>
      </BaseModal>
    </Teleport>
  </section>
</template>

<script setup>
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import BaseModal from '@/components/base/BaseModal.vue';

const toast = useToast();
const store = useCoreAdminStore();
const { banners, bannersLoading: loadingBanners } = storeToRefs(store);

const showBannerModal = ref(false);
const editingBanner = ref(null);
const savingBanner  = ref(false);
const bannerError   = ref('');
const bannerFileInput = ref(null);
const bannerSelectedFile = ref(null);
const bannerMediaPreview = ref('');
const bannerMediaType   = ref('');
const bannerIsDragging  = ref(false);
const bannerRemoveMedia  = ref(false);

const defaultBannerForm = () => ({
  title: '', subtitle: '', eyebrow: '',
  link_url: '', link_label: '',
  background_color: '', cta_ghost_label: '', cta_ghost_url: '',
  display_order: 0, is_active: true,
});
const bannerForm = ref(defaultBannerForm());

async function fetchBanners() {
  await store.fetchBanners();
}
function openBannerForm(b = null) {
  editingBanner.value      = b;
  bannerError.value        = '';
  bannerSelectedFile.value = null;
  bannerRemoveMedia.value  = false;
  bannerMediaPreview.value = b?.image || b?.video || '';
  bannerMediaType.value    = b?.video ? 'video' : 'image';
  bannerForm.value = b ? {
    title: b.title, subtitle: b.subtitle || '', eyebrow: b.eyebrow || '',
    link_url: b.link_url || '', link_label: b.link_label || '',
    background_color: b.background_color || '',
    cta_ghost_label: b.cta_ghost_label || '', cta_ghost_url: b.cta_ghost_url || '',
    display_order: b.display_order ?? 0, is_active: b.is_active,
  } : defaultBannerForm();
  showBannerModal.value = true;
}
function removeBannerMedia() {
  bannerRemoveMedia.value  = true;
  bannerSelectedFile.value = null;
  bannerMediaPreview.value = '';
}
function closeBannerForm() { showBannerModal.value = false; editingBanner.value = null; }
function handleBannerSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  bannerSelectedFile.value = file;
  bannerMediaType.value = file.type.startsWith('video') ? 'video' : 'image';
  bannerMediaPreview.value = URL.createObjectURL(file);
}
function handleBannerDrop(e) {
  bannerIsDragging.value = false;
  const file = e.dataTransfer.files[0];
  if (!file) return;
  bannerSelectedFile.value = file;
  bannerMediaType.value = file.type.startsWith('video') ? 'video' : 'image';
  bannerMediaPreview.value = URL.createObjectURL(file);
}
async function saveBanner() {
  if (!bannerForm.value.title.trim()) { bannerError.value = 'El titulo es requerido.'; return; }
  savingBanner.value = true; bannerError.value = '';
  const fd = new FormData();
  Object.entries(bannerForm.value).forEach(([k, v]) => fd.append(k, v));
  if (bannerSelectedFile.value) {
    const key = bannerMediaType.value === 'video' ? 'video' : 'image';
    fd.append(key, bannerSelectedFile.value);
  }
  if (bannerRemoveMedia.value) {
    fd.append('remove_image', 'true');
    fd.append('remove_video', 'true');
  }
  const res = editingBanner.value
    ? await store.updateBanner(editingBanner.value.uuid, fd)
    : await store.createBanner(fd);
  if (res.ok) {
    toast.success(editingBanner.value ? 'Banner actualizado.' : 'Banner creado.');
    closeBannerForm();
    await fetchBanners();
  } else {
    bannerError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingBanner.value = false;
}
async function deleteBanner(b) {
  if (!confirm(`Eliminar banner "${b.title}"?`)) return;
  const res = await store.deleteBanner(b.uuid);
  if (res.ok) {
    toast.success('Banner eliminado.');
    await fetchBanners();
  } else {
    toast.error('No se pudo eliminar.');
  }
}
</script>
