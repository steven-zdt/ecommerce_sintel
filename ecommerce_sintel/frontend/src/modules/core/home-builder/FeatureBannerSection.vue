<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Feature Banner</h2>
        <p class="hcb-section-sub">Secciones promocionales genericas (imagen + texto + botones), reutilizables para cualquier proposito comercial.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" @click="openSectionForm()">
        <i class="bi bi-plus-lg"></i> Nueva seccion
      </button>
    </div>

    <div v-if="loadingSections" class="hcb-loading"><div class="spinner-border text-primary"></div></div>

    <div v-else class="hcb-groups-list">
      <div v-for="section in sections" :key="section.uuid" class="hcb-group-block">
        <div class="hcb-group-header">
          <div class="hcb-group-header__left">
            <span class="hcb-group-name">{{ section.title || '(sin titulo)' }}</span>
            <span class="hcb-badge hcb-badge--gray">{{ section.blocks.length }} bloque(s)</span>
            <span :class="['hcb-chip', section.is_visible ? 'hcb-chip--green' : 'hcb-chip--gray']">
              {{ section.is_visible ? 'Visible' : 'Oculta' }}
            </span>
            <span class="hcb-chip">{{ THEME_LABELS[section.theme] || section.theme }}</span>
          </div>
          <div class="hcb-group-header__right">
            <button class="hcb-icon-btn hcb-icon-btn--sm" title="Agregar bloque" @click="openBlockForm(section)">
              <i class="bi bi-plus-lg"></i>
            </button>
            <button class="hcb-icon-btn hcb-icon-btn--sm" title="Configurar seccion" @click="openSectionForm(section)">
              <i class="bi bi-gear"></i>
            </button>
            <button class="hcb-icon-btn hcb-icon-btn--sm hcb-icon-btn--danger" title="Eliminar seccion" @click="deleteSection(section)">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>

        <div v-if="section.blocks.length" class="hcb-cards-grid">
          <div v-for="block in section.blocks" :key="block.uuid" class="hcb-card-thumb">
            <div class="hcb-card-thumb__icon" :style="{ background: (block.btn_primary_color || '#2563eb') + '18', color: block.btn_primary_color || '#2563eb' }">
              <i class="bi bi-window-stack"></i>
            </div>
            <div class="hcb-card-thumb__body">
              <div class="hcb-card-thumb__title">{{ block.title || '(sin titulo)' }}</div>
              <div class="hcb-card-thumb__meta">
                <span class="hcb-chip hcb-chip--xs">{{ LAYOUT_LABELS[block.layout_type] || block.layout_type }}</span>
                <span :class="['hcb-chip hcb-chip--xs', block.is_active ? 'hcb-chip--green' : 'hcb-chip--gray']">
                  {{ block.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
            </div>
            <div class="hcb-card-thumb__actions">
              <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openBlockForm(section, block)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteBlock(section, block)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
        <div v-else class="hcb-empty hcb-empty--sm">
          Sin bloques en esta seccion.
          <button class="hcb-btn hcb-btn--sm" @click="openBlockForm(section)">Agregar el primero</button>
        </div>
      </div>
      <div v-if="!sections.length" class="hcb-empty">Sin secciones de Feature Banner. Crea la primera.</div>
    </div>

    <Teleport to="body">
      <!-- Modal Seccion -->
      <BaseModal v-model="showSectionModal" :title="editingSection ? 'Configurar seccion' : 'Nueva seccion'">
        <div class="hcb-form-grid">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo</label>
            <input v-model="sectionForm.title" class="hcb-input" placeholder="Titulo de la seccion (opcional)">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Subtitulo</label>
            <input v-model="sectionForm.subtitle" class="hcb-input" placeholder="Subtitulo">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Descripcion</label>
            <textarea v-model="sectionForm.description" class="hcb-input" rows="2" placeholder="Texto de apoyo..."></textarea>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Tema</label>
            <select v-model="sectionForm.theme" class="hcb-select">
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="corporate">Corporate</option>
              <option value="minimal">Minimal</option>
              <option value="glass">Glass</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Orden</label>
            <input v-model.number="sectionForm.display_order" type="number" class="hcb-input" min="0">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Tipo de fondo</label>
            <select v-model="sectionForm.background_type" class="hcb-select">
              <option value="color">Color solido</option>
              <option value="gradient">Gradiente</option>
              <option value="image">Imagen</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Padding</label>
            <select v-model="sectionForm.padding" class="hcb-select">
              <option value="none">Sin padding</option>
              <option value="sm">Pequeno</option>
              <option value="normal">Normal</option>
              <option value="lg">Grande</option>
              <option value="xl">Extra grande</option>
            </select>
          </div>
          <div v-if="sectionForm.background_type === 'color'" class="hcb-field">
            <label class="hcb-label">Color de fondo</label>
            <div class="d-flex gap-2 align-items-center">
              <input type="color" v-model="sectionForm.background_color" class="hcb-color-input">
              <input v-model="sectionForm.background_color" class="hcb-input" style="flex:1" placeholder="#ffffff">
            </div>
          </div>
          <template v-if="sectionForm.background_type === 'gradient'">
            <div class="hcb-field">
              <label class="hcb-label">Gradiente desde</label>
              <div class="d-flex gap-2 align-items-center">
                <input type="color" v-model="sectionForm.background_gradient_from" class="hcb-color-input">
                <input v-model="sectionForm.background_gradient_from" class="hcb-input" style="flex:1">
              </div>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Gradiente hasta</label>
              <div class="d-flex gap-2 align-items-center">
                <input type="color" v-model="sectionForm.background_gradient_to" class="hcb-color-input">
                <input v-model="sectionForm.background_gradient_to" class="hcb-input" style="flex:1">
              </div>
            </div>
          </template>
          <div v-if="sectionForm.background_type === 'image'" class="hcb-field hcb-field--full">
            <label class="hcb-label">Imagen de fondo</label>
            <div v-if="sectionBgImagePreview && !sectionRemoveBgImage" class="hcb-media-current">
              <img :src="sectionBgImagePreview" class="hcb-media-current__img" alt="">
              <div class="hcb-media-current__actions">
                <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeSectionBgImage">
                  <i class="bi bi-trash me-1"></i>Eliminar imagen
                </button>
                <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.sectionBgImgInput.click()">
                  <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                </button>
              </div>
            </div>
            <div v-else class="hcb-upload-area" @click="$refs.sectionBgImgInput.click()">
              <i class="bi bi-image"></i>
              <span>Haz clic para subir imagen</span>
            </div>
            <input ref="sectionBgImgInput" type="file" accept="image/*" class="d-none" @change="handleSectionBgImageSelect">
          </div>
          <div class="hcb-field d-flex gap-3">
            <div class="form-check form-switch">
              <input v-model="sectionForm.overlay_enabled" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Overlay</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="sectionForm.is_visible" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Visible</label>
            </div>
          </div>
          <div v-if="sectionForm.overlay_enabled" class="hcb-field">
            <label class="hcb-label">Opacidad del overlay (%)</label>
            <input v-model.number="sectionForm.overlay_opacity" type="number" class="hcb-input" min="0" max="100">
          </div>
        </div>
        <div v-if="sectionError" class="alert alert-danger small py-2 mt-2">{{ sectionError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeSectionForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingSection" @click="saveSection">
            <span v-if="savingSection" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingSection ? 'Guardar cambios' : 'Crear seccion' }}
          </button>
        </template>
      </BaseModal>

      <!-- Modal Bloque -->
      <BaseModal v-model="showBlockModal" :title="editingBlock ? 'Editar bloque' : 'Nuevo bloque'" wide>
        <div class="hcb-form-grid">
          <div class="hcb-field">
            <label class="hcb-label">Layout</label>
            <select v-model="blockForm.layout_type" class="hcb-select">
              <option value="image_left">Imagen izquierda</option>
              <option value="image_right">Imagen derecha</option>
              <option value="fifty_fifty">50 / 50</option>
              <option value="sixty_forty">60 / 40</option>
              <option value="forty_sixty">40 / 60</option>
              <option value="full_image">Imagen completa (overlay)</option>
              <option value="text_centered">Texto centrado (sin imagen)</option>
            </select>
          </div>
          <div class="hcb-field d-flex gap-3">
            <div class="form-check form-switch">
              <input v-model="blockForm.is_active" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Activo</label>
            </div>
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo</label>
            <input v-model="blockForm.title" class="hcb-input" placeholder="Titulo principal">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo resaltado (color de acento)</label>
            <input v-model="blockForm.title_highlighted" class="hcb-input" placeholder="Palabra o frase destacada">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Descripcion</label>
            <textarea v-model="blockForm.description" class="hcb-input" rows="3"></textarea>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Orden</label>
            <input v-model.number="blockForm.display_order" type="number" class="hcb-input" min="0">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Texto alternativo de imagen</label>
            <input v-model="blockForm.image_alt" class="hcb-input">
          </div>

          <div v-if="blockForm.layout_type !== 'text_centered'" class="hcb-field hcb-field--full">
            <label class="hcb-label">Imagen</label>
            <div v-if="blockImagePreview && !blockRemoveImage" class="hcb-media-current">
              <img :src="blockImagePreview" class="hcb-media-current__img" alt="">
              <div class="hcb-media-current__actions">
                <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeBlockImage">
                  <i class="bi bi-trash me-1"></i>Eliminar imagen
                </button>
                <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.blockImgInput.click()">
                  <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                </button>
              </div>
            </div>
            <div v-else class="hcb-upload-area" @click="$refs.blockImgInput.click()">
              <i class="bi bi-image"></i>
              <span>Haz clic para subir imagen</span>
            </div>
            <input ref="blockImgInput" type="file" accept="image/*" class="d-none" @change="handleBlockImageSelect">
          </div>

          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Beneficios (icono + texto)</label>
            <div v-for="(b, i) in blockForm.benefits" :key="i" class="d-flex gap-2 mb-2">
              <input v-model="b.icon" class="hcb-input" style="width:110px" placeholder="bi-check-circle">
              <input v-model="b.text" class="hcb-input" style="flex:1" placeholder="Texto del beneficio">
              <button class="hcb-icon-btn hcb-icon-btn--sm hcb-icon-btn--danger" @click="blockForm.benefits.splice(i, 1)"><i class="bi bi-trash"></i></button>
            </div>
            <button class="hcb-btn hcb-btn--sm" @click="blockForm.benefits.push({ icon: 'bi-check-circle', text: '' })">
              <i class="bi bi-plus-lg me-1"></i>Agregar beneficio
            </button>
          </div>

          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Estadisticas (valor + etiqueta)</label>
            <div v-for="(s, i) in blockForm.stats" :key="i" class="d-flex gap-2 mb-2">
              <input v-model="s.value" class="hcb-input" style="width:110px" placeholder="+500">
              <input v-model="s.label" class="hcb-input" style="flex:1" placeholder="Etiqueta">
              <button class="hcb-icon-btn hcb-icon-btn--sm hcb-icon-btn--danger" @click="blockForm.stats.splice(i, 1)"><i class="bi bi-trash"></i></button>
            </div>
            <button class="hcb-btn hcb-btn--sm" @click="blockForm.stats.push({ value: '', label: '' })">
              <i class="bi bi-plus-lg me-1"></i>Agregar estadistica
            </button>
          </div>

          <div class="hcb-field">
            <label class="hcb-label">Badge - texto</label>
            <input v-model="blockForm.badge_text" class="hcb-input" placeholder="Nuevo, Popular...">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Badge - color</label>
            <div class="d-flex gap-2 align-items-center">
              <input type="color" v-model="blockForm.badge_color" class="hcb-color-input">
              <input v-model="blockForm.badge_color" class="hcb-input" style="flex:1">
            </div>
          </div>

          <div class="hcb-field--full"><hr class="my-1"><strong class="hcb-subsection-title">Boton primario</strong></div>
          <div class="hcb-field">
            <label class="hcb-label">Texto</label>
            <input v-model="blockForm.btn_primary_text" class="hcb-input">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Icono</label>
            <input v-model="blockForm.btn_primary_icon" class="hcb-input" placeholder="bi-arrow-right">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color</label>
            <div class="d-flex gap-2 align-items-center">
              <input type="color" v-model="blockForm.btn_primary_color" class="hcb-color-input">
              <input v-model="blockForm.btn_primary_color" class="hcb-input" style="flex:1">
            </div>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Estilo</label>
            <select v-model="blockForm.btn_primary_style" class="hcb-select">
              <option value="filled">Filled</option>
              <option value="outline">Outline</option>
              <option value="ghost">Ghost</option>
              <option value="minimal">Minimal</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Tipo de URL</label>
            <select v-model="blockForm.btn_primary_url_type" class="hcb-select">
              <option value="INTERNA">Interna (empieza con /)</option>
              <option value="EXTERNA">Externa (http/https)</option>
              <option value="ANCHOR">Ancla (empieza con #)</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL</label>
            <input v-model="blockForm.btn_primary_url" class="hcb-input" placeholder="/tienda">
          </div>
          <div v-if="blockForm.btn_primary_url_type === 'EXTERNA'" class="hcb-field">
            <label class="hcb-label">Apertura</label>
            <select v-model="blockForm.btn_primary_target" class="hcb-select">
              <option value="_self">Misma pestaña</option>
              <option value="_blank">Nueva pestaña</option>
            </select>
          </div>

          <div class="hcb-field--full"><hr class="my-1"><strong class="hcb-subsection-title">Boton secundario (opcional)</strong></div>
          <div class="hcb-field">
            <label class="hcb-label">Texto</label>
            <input v-model="blockForm.btn_secondary_text" class="hcb-input">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Icono</label>
            <input v-model="blockForm.btn_secondary_icon" class="hcb-input">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color</label>
            <div class="d-flex gap-2 align-items-center">
              <input type="color" v-model="blockForm.btn_secondary_color" class="hcb-color-input">
              <input v-model="blockForm.btn_secondary_color" class="hcb-input" style="flex:1">
            </div>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Estilo</label>
            <select v-model="blockForm.btn_secondary_style" class="hcb-select">
              <option value="filled">Filled</option>
              <option value="outline">Outline</option>
              <option value="ghost">Ghost</option>
              <option value="minimal">Minimal</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Tipo de URL</label>
            <select v-model="blockForm.btn_secondary_url_type" class="hcb-select">
              <option value="INTERNA">Interna (empieza con /)</option>
              <option value="EXTERNA">Externa (http/https)</option>
              <option value="ANCHOR">Ancla (empieza con #)</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL</label>
            <input v-model="blockForm.btn_secondary_url" class="hcb-input">
          </div>
          <div v-if="blockForm.btn_secondary_url_type === 'EXTERNA'" class="hcb-field">
            <label class="hcb-label">Apertura</label>
            <select v-model="blockForm.btn_secondary_target" class="hcb-select">
              <option value="_self">Misma pestaña</option>
              <option value="_blank">Nueva pestaña</option>
            </select>
          </div>
        </div>
        <div v-if="blockError" class="alert alert-danger small py-2 mt-2">{{ blockError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeBlockForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingBlock" @click="saveBlock">
            <span v-if="savingBlock" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingBlock ? 'Guardar cambios' : 'Crear bloque' }}
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
const { featureBannerSections: sections, featureBannerSectionsLoading: loadingSections } = storeToRefs(store);

const THEME_LABELS = { light: 'Light', dark: 'Dark', corporate: 'Corporate', minimal: 'Minimal', glass: 'Glass' };
const LAYOUT_LABELS = {
  image_left: 'Imagen izq.', image_right: 'Imagen der.', fifty_fifty: '50/50',
  sixty_forty: '60/40', forty_sixty: '40/60', full_image: 'Imagen completa', text_centered: 'Texto centrado',
};

async function fetchSections() {
  await store.fetchFeatureBannerSections();
}

// ── Seccion ──────────────────────────────────────────────────────────────────
const showSectionModal = ref(false);
const editingSection = ref(null);
const savingSection = ref(false);
const sectionError = ref('');
const sectionBgImageFile = ref(null);
const sectionBgImagePreview = ref('');
const sectionRemoveBgImage = ref(false);

const defaultSectionForm = () => ({
  title: '', subtitle: '', description: '', is_visible: true, display_order: 0, theme: 'light',
  background_type: 'color', background_color: '#ffffff', background_gradient_from: '#0f172a',
  background_gradient_to: '#1e3a8a', overlay_enabled: false, overlay_opacity: 45, padding: 'normal',
});
const sectionForm = ref(defaultSectionForm());

function openSectionForm(section = null) {
  editingSection.value = section;
  sectionError.value = '';
  sectionBgImageFile.value = null;
  sectionRemoveBgImage.value = false;
  sectionBgImagePreview.value = section?.background_image || '';
  sectionForm.value = section ? {
    title: section.title, subtitle: section.subtitle, description: section.description,
    is_visible: section.is_visible, display_order: section.display_order, theme: section.theme,
    background_type: section.background_type, background_color: section.background_color || '#ffffff',
    background_gradient_from: section.background_gradient_from || '#0f172a',
    background_gradient_to: section.background_gradient_to || '#1e3a8a',
    overlay_enabled: section.overlay_enabled, overlay_opacity: section.overlay_opacity, padding: section.padding,
  } : defaultSectionForm();
  showSectionModal.value = true;
}
function closeSectionForm() {
  showSectionModal.value = false;
  editingSection.value = null;
}
function handleSectionBgImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  sectionBgImageFile.value = file;
  sectionRemoveBgImage.value = false;
  sectionBgImagePreview.value = URL.createObjectURL(file);
}
function removeSectionBgImage() {
  sectionBgImageFile.value = null;
  sectionRemoveBgImage.value = true;
  sectionBgImagePreview.value = '';
}
async function saveSection() {
  savingSection.value = true; sectionError.value = '';
  const hasMedia = sectionBgImageFile.value || sectionRemoveBgImage.value;
  let sendPayload = sectionForm.value;
  if (hasMedia) {
    const fd = new FormData();
    Object.entries(sectionForm.value).forEach(([k, v]) => fd.append(k, v));
    if (sectionBgImageFile.value) fd.append('background_image', sectionBgImageFile.value);
    if (sectionRemoveBgImage.value) fd.append('remove_background_image', 'true');
    sendPayload = fd;
  }
  const res = editingSection.value
    ? await store.updateFeatureBannerSection(editingSection.value.uuid, sendPayload)
    : await store.createFeatureBannerSection(sendPayload);
  if (res.ok) {
    toast.success(editingSection.value ? 'Seccion actualizada.' : 'Seccion creada.');
    closeSectionForm();
    await fetchSections();
  } else {
    sectionError.value = res.error?.response?.data?.detail || 'Error al guardar la seccion.';
  }
  savingSection.value = false;
}
async function deleteSection(section) {
  if (!confirm(`Eliminar la seccion "${section.title || '(sin titulo)'}" y sus bloques?`)) return;
  const res = await store.deleteFeatureBannerSection(section.uuid);
  if (res.ok) {
    toast.success('Seccion eliminada.');
    await fetchSections();
  } else {
    toast.error('No se pudo eliminar la seccion.');
  }
}

// ── Bloque ───────────────────────────────────────────────────────────────────
const showBlockModal = ref(false);
const editingBlock = ref(null);
const editingBlockSection = ref(null);
const savingBlock = ref(false);
const blockError = ref('');
const blockImageFile = ref(null);
const blockImagePreview = ref('');
const blockRemoveImage = ref(false);

const defaultBlockForm = () => ({
  layout_type: 'image_left', title: '', title_highlighted: '', description: '',
  image_alt: '', benefits: [], stats: [], badge_text: '', badge_color: '#f59e0b',
  btn_primary_text: '', btn_primary_icon: 'bi-arrow-right', btn_primary_color: '#2563eb',
  btn_primary_style: 'filled', btn_primary_url: '', btn_primary_url_type: 'INTERNA', btn_primary_target: '_self',
  btn_secondary_text: '', btn_secondary_icon: '', btn_secondary_color: '#2563eb',
  btn_secondary_style: 'outline', btn_secondary_url: '', btn_secondary_url_type: 'INTERNA', btn_secondary_target: '_self',
  display_order: 0, is_active: true,
});
const blockForm = ref(defaultBlockForm());

function openBlockForm(section, block = null) {
  editingBlockSection.value = section;
  editingBlock.value = block;
  blockError.value = '';
  blockImageFile.value = null;
  blockRemoveImage.value = false;
  blockImagePreview.value = block?.image || '';
  blockForm.value = block ? {
    layout_type: block.layout_type, title: block.title, title_highlighted: block.title_highlighted,
    description: block.description, image_alt: block.image_alt,
    benefits: Array.isArray(block.benefits) ? block.benefits.map(b => ({ ...b })) : [],
    stats: Array.isArray(block.stats) ? block.stats.map(s => ({ ...s })) : [],
    badge_text: block.badge_text, badge_color: block.badge_color,
    btn_primary_text: block.btn_primary_text, btn_primary_icon: block.btn_primary_icon,
    btn_primary_color: block.btn_primary_color, btn_primary_style: block.btn_primary_style,
    btn_primary_url: block.btn_primary_url, btn_primary_url_type: block.btn_primary_url_type,
    btn_primary_target: block.btn_primary_target,
    btn_secondary_text: block.btn_secondary_text, btn_secondary_icon: block.btn_secondary_icon,
    btn_secondary_color: block.btn_secondary_color, btn_secondary_style: block.btn_secondary_style,
    btn_secondary_url: block.btn_secondary_url, btn_secondary_url_type: block.btn_secondary_url_type,
    btn_secondary_target: block.btn_secondary_target,
    display_order: block.display_order, is_active: block.is_active,
  } : defaultBlockForm();
  showBlockModal.value = true;
}
function closeBlockForm() {
  showBlockModal.value = false;
  editingBlock.value = null;
  editingBlockSection.value = null;
}
function handleBlockImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  blockImageFile.value = file;
  blockRemoveImage.value = false;
  blockImagePreview.value = URL.createObjectURL(file);
}
function removeBlockImage() {
  blockImageFile.value = null;
  blockRemoveImage.value = true;
  blockImagePreview.value = '';
}
async function saveBlock() {
  savingBlock.value = true; blockError.value = '';
  const payload = { ...blockForm.value, benefits: JSON.stringify(blockForm.value.benefits), stats: JSON.stringify(blockForm.value.stats) };
  if (!editingBlock.value) payload.section = editingBlockSection.value.uuid;
  const hasMedia = blockImageFile.value || blockRemoveImage.value;
  let sendPayload = payload;
  if (hasMedia) {
    const fd = new FormData();
    Object.entries(payload).forEach(([k, v]) => fd.append(k, v));
    if (blockImageFile.value) fd.append('image', blockImageFile.value);
    if (blockRemoveImage.value) fd.append('remove_image', 'true');
    sendPayload = fd;
  }
  const res = editingBlock.value
    ? await store.updateFeatureBannerBlock(editingBlock.value.uuid, sendPayload)
    : await store.createFeatureBannerBlock(sendPayload);
  if (res.ok) {
    toast.success(editingBlock.value ? 'Bloque actualizado.' : 'Bloque creado.');
    closeBlockForm();
    await fetchSections();
  } else {
    blockError.value = res.error?.response?.data?.detail || 'Error al guardar el bloque.';
  }
  savingBlock.value = false;
}
async function deleteBlock(section, block) {
  if (!confirm(`Eliminar el bloque "${block.title || '(sin titulo)'}"?`)) return;
  const res = await store.deleteFeatureBannerBlock(block.uuid);
  if (res.ok) {
    toast.success('Bloque eliminado.');
    await fetchSections();
  } else {
    toast.error('No se pudo eliminar el bloque.');
  }
}

// El fetch INICIAL lo dispara el padre (HomeConfigView.vue, onMounted), igual
// que el resto de secciones del Home Builder.
</script>
