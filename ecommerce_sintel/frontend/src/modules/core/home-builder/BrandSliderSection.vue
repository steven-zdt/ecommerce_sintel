<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Slider de Marcas / Clientes</h2>
        <p class="hcb-section-sub">Logos con desplazamiento horizontal continuo, entre el CTA final y el footer.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" @click="openBrandItemForm()">
        <i class="bi bi-plus-lg"></i> Nuevo logo
      </button>
    </div>

    <div v-if="loadingBrandConfig" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
    <div v-else class="hcb-form-grid mb-4">
      <div class="hcb-field hcb-field--full">
        <label class="hcb-label">Titulo de la seccion</label>
        <input v-model="brandConfigForm.title" class="hcb-input" placeholder="Marcas y clientes">
      </div>
      <div class="hcb-field hcb-field--full">
        <label class="hcb-label">Subtitulo</label>
        <input v-model="brandConfigForm.subtitle" class="hcb-input" placeholder="Empresas que confian en nosotros">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Velocidad (ms)</label>
        <input v-model.number="brandConfigForm.speed" type="number" class="hcb-input" min="500" step="100">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Direccion</label>
        <select v-model="brandConfigForm.direction" class="hcb-input">
          <option value="left">Izquierda</option>
          <option value="right">Derecha</option>
        </select>
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Logos visibles (desktop)</label>
        <input v-model.number="brandConfigForm.items_desktop" type="number" class="hcb-input" min="1" max="12">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Logos visibles (tablet)</label>
        <input v-model.number="brandConfigForm.items_tablet" type="number" class="hcb-input" min="1" max="10">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Logos visibles (mobile)</label>
        <input v-model.number="brandConfigForm.items_mobile" type="number" class="hcb-input" min="1" max="6">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Color de fondo</label>
        <div class="d-flex gap-2">
          <input v-model="brandConfigForm.background_color" type="color" class="hcb-color-input">
          <input v-model="brandConfigForm.background_color" class="hcb-input" placeholder="#ffffff" style="flex:1">
        </div>
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Padding superior</label>
        <select v-model="brandConfigForm.padding_top" class="hcb-input">
          <option value="none">Sin padding</option>
          <option value="sm">Pequeno</option>
          <option value="normal">Normal</option>
          <option value="lg">Grande</option>
          <option value="xl">Extra grande</option>
        </select>
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Padding inferior</label>
        <select v-model="brandConfigForm.padding_bottom" class="hcb-input">
          <option value="none">Sin padding</option>
          <option value="sm">Pequeno</option>
          <option value="normal">Normal</option>
          <option value="lg">Grande</option>
          <option value="xl">Extra grande</option>
        </select>
      </div>
      <div class="hcb-field hcb-field--full d-flex gap-4 flex-wrap">
        <div class="form-check form-switch">
          <input v-model="brandConfigForm.autoplay" class="form-check-input" type="checkbox">
          <label class="form-check-label small">Autoplay</label>
        </div>
        <div class="form-check form-switch">
          <input v-model="brandConfigForm.loop" class="form-check-input" type="checkbox">
          <label class="form-check-label small">Loop infinito</label>
        </div>
        <div class="form-check form-switch">
          <input v-model="brandConfigForm.pause_on_hover" class="form-check-input" type="checkbox">
          <label class="form-check-label small">Pausar al pasar el mouse</label>
        </div>
        <div class="form-check form-switch">
          <input v-model="brandConfigForm.is_visible" class="form-check-input" type="checkbox">
          <label class="form-check-label small">Visible en la Home</label>
        </div>
      </div>
      <div v-if="brandConfigError" class="hcb-field hcb-field--full">
        <div class="alert alert-danger small py-2 mb-0">{{ brandConfigError }}</div>
      </div>
      <div class="hcb-field hcb-field--full">
        <button class="hcb-btn hcb-btn--primary" :disabled="savingBrandConfig" @click="saveBrandConfig">
          <span v-if="savingBrandConfig" class="spinner-border spinner-border-sm me-1"></span>
          Guardar configuracion
        </button>
      </div>
    </div>

    <div v-if="loadingBrandItems" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
    <div v-else class="hcb-banners-list">
      <div
        v-for="(item, idx) in brandItems"
        :key="item.uuid"
        :class="['hcb-banner-row', !item.is_active && 'hcb-banner-row--inactive']"
        draggable="true"
        @dragstart="handleBrandItemDragStart(idx)"
        @dragover.prevent
        @drop="handleBrandItemDrop(idx)"
      >
        <span class="hcb-drag-handle" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
        <div class="hcb-banner-thumb">
          <img v-if="item.logo" :src="item.logo" alt="">
          <div v-else class="hcb-banner-placeholder"><i class="bi bi-image"></i></div>
        </div>
        <div class="hcb-banner-info">
          <div class="hcb-banner-title">{{ item.name }}</div>
          <div class="hcb-banner-meta">
            <span class="hcb-chip" :class="item.is_active ? 'hcb-chip--green' : 'hcb-chip--gray'">
              {{ item.is_active ? 'Activo' : 'Inactivo' }}
            </span>
            <span v-if="item.website" class="hcb-chip">{{ item.website }}</span>
          </div>
        </div>
        <div class="hcb-banner-actions">
          <button class="hcb-icon-btn" @click="openBrandItemForm(item)"><i class="bi bi-pencil"></i></button>
          <button class="hcb-icon-btn hcb-icon-btn--danger" @click="deleteBrandItem(item)"><i class="bi bi-trash"></i></button>
        </div>
      </div>
      <div v-if="!brandItems.length" class="hcb-empty">Sin logos. Crea el primero.</div>
    </div>

    <Teleport to="body">
      <BaseModal v-model="showBrandItemModal" :title="editingBrandItem ? 'Editar logo' : 'Nuevo logo'">
        <div class="hcb-form-grid">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Nombre *</label>
            <input v-model="brandItemForm.name" class="hcb-input" placeholder="Nombre de la marca">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Sitio web</label>
            <input v-model="brandItemForm.website" class="hcb-input" placeholder="https://...">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Orden</label>
            <input v-model.number="brandItemForm.display_order" type="number" class="hcb-input" min="0">
          </div>
          <div class="hcb-field d-flex align-items-end gap-3">
            <div class="form-check form-switch">
              <input v-model="brandItemForm.is_active" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Activo</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="brandItemForm.open_new_tab" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Abrir en nueva pestana</label>
            </div>
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Logo</label>
            <div v-if="brandItemLogoPreview && !brandItemRemoveLogo" class="hcb-media-current">
              <img :src="brandItemLogoPreview" class="hcb-media-current__img" alt="">
              <div class="hcb-media-current__actions">
                <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeBrandItemLogo">
                  <i class="bi bi-trash me-1"></i>Eliminar logo
                </button>
                <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.brandItemFileInput.click()">
                  <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                </button>
              </div>
            </div>
            <div v-else class="hcb-upload-area" @click="$refs.brandItemFileInput.click()">
              <i class="bi bi-cloud-upload"></i>
              <span>Haz clic para subir el logo</span>
            </div>
            <input ref="brandItemFileInput" type="file" accept="image/*" class="d-none" @change="handleBrandItemLogoSelect">
          </div>
        </div>
        <div v-if="brandItemError" class="alert alert-danger small py-2 mt-2">{{ brandItemError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeBrandItemForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingBrandItem" @click="saveBrandItem">
            <span v-if="savingBrandItem" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingBrandItem ? 'Guardar cambios' : 'Crear logo' }}
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
const {
  brandItems, brandItemsLoading: loadingBrandItems,
  brandSliderConfig, brandConfigLoading: loadingBrandConfig,
} = storeToRefs(store);

// ── Items ──────────────────────────────────────────────────────────────────────
const showBrandItemModal = ref(false);
const editingBrandItem   = ref(null);
const savingBrandItem    = ref(false);
const brandItemError     = ref('');
const brandItemFileInput = ref(null);
const brandItemSelectedFile = ref(null);
const brandItemLogoPreview  = ref('');
const brandItemRemoveLogo   = ref(false);
const brandItemDragIndex    = ref(null);

const defaultBrandItemForm = () => ({
  name: '', website: '', display_order: 0, is_active: true, open_new_tab: true,
});
const brandItemForm = ref(defaultBrandItemForm());

async function fetchBrandItems() {
  await store.fetchBrandItems();
}
function openBrandItemForm(item = null) {
  editingBrandItem.value      = item;
  brandItemError.value        = '';
  brandItemSelectedFile.value = null;
  brandItemRemoveLogo.value   = false;
  brandItemLogoPreview.value  = item?.logo || '';
  brandItemForm.value = item ? {
    name: item.name, website: item.website || '',
    display_order: item.display_order ?? 0,
    is_active: item.is_active, open_new_tab: item.open_new_tab,
  } : defaultBrandItemForm();
  showBrandItemModal.value = true;
}
function closeBrandItemForm() { showBrandItemModal.value = false; editingBrandItem.value = null; }
function removeBrandItemLogo() {
  brandItemRemoveLogo.value  = true;
  brandItemSelectedFile.value = null;
  brandItemLogoPreview.value = '';
}
function handleBrandItemLogoSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  brandItemSelectedFile.value = file;
  brandItemLogoPreview.value = URL.createObjectURL(file);
}
async function saveBrandItem() {
  if (!brandItemForm.value.name.trim()) { brandItemError.value = 'El nombre es requerido.'; return; }
  savingBrandItem.value = true; brandItemError.value = '';
  const fd = new FormData();
  Object.entries(brandItemForm.value).forEach(([k, v]) => fd.append(k, v));
  if (brandItemSelectedFile.value) fd.append('logo', brandItemSelectedFile.value);
  if (brandItemRemoveLogo.value) fd.append('remove_logo', 'true');
  const res = editingBrandItem.value
    ? await store.updateBrandItem(editingBrandItem.value.uuid, fd)
    : await store.createBrandItem(fd);
  if (res.ok) {
    toast.success(editingBrandItem.value ? 'Logo actualizado.' : 'Logo creado.');
    closeBrandItemForm();
    await fetchBrandItems();
  } else {
    brandItemError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingBrandItem.value = false;
}
async function deleteBrandItem(item) {
  if (!confirm(`Eliminar logo "${item.name}"?`)) return;
  const res = await store.deleteBrandItem(item.uuid);
  if (res.ok) {
    toast.success('Logo eliminado.');
    await fetchBrandItems();
  } else {
    toast.error('No se pudo eliminar.');
  }
}
function handleBrandItemDragStart(index) { brandItemDragIndex.value = index; }
async function handleBrandItemDrop(targetIndex) {
  const fromIndex = brandItemDragIndex.value;
  brandItemDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...brandItems.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  brandItems.value = reordered;
  const res = await store.reorderBrandItems(reordered.map((i) => i.uuid));
  if (!res.ok) {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchBrandItems();
  }
}

// ── Configuracion ──────────────────────────────────────────────────────────────
// brandConfigForm es v-model con el padre: el panel de preview compartido
// (HomeRenderer, pestaña 'brand_slider') lo necesita -- mismo criterio que
// contactForm/brandForm/ctaForm.
const savingBrandConfig  = ref(false);
const brandConfigError   = ref('');

const brandConfigForm = defineModel('brandConfigForm', {
  default: () => ({
    title: 'Marcas y clientes', subtitle: '',
    autoplay: true, speed: 3500, direction: 'left', loop: true, pause_on_hover: true,
    items_desktop: 6, items_tablet: 4, items_mobile: 2,
    background_color: '', padding_top: 'normal', padding_bottom: 'normal',
    is_visible: true,
  }),
});

async function fetchBrandConfig() {
  await store.fetchBrandSliderConfig();
  const data = brandSliderConfig.value;
  if (data) {
    brandConfigForm.value = {
      title: data.title || '', subtitle: data.subtitle || '',
      autoplay: data.autoplay, speed: data.speed, direction: data.direction,
      loop: data.loop, pause_on_hover: data.pause_on_hover,
      items_desktop: data.items_desktop, items_tablet: data.items_tablet, items_mobile: data.items_mobile,
      background_color: data.background_color || '',
      padding_top: data.padding_top, padding_bottom: data.padding_bottom,
      is_visible: data.is_visible,
    };
  }
}
async function saveBrandConfig() {
  savingBrandConfig.value = true; brandConfigError.value = '';
  const res = await store.updateBrandSliderConfig(brandConfigForm.value);
  if (res.ok) {
    toast.success('Configuracion actualizada.');
    await fetchBrandConfig();
  } else {
    brandConfigError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingBrandConfig.value = false;
}
</script>
