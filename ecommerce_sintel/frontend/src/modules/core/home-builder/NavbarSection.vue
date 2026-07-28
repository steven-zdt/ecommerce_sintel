<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Navbar</h2>
        <p class="hcb-section-sub">Links de navegacion principal visibles en todas las paginas.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" @click="openNavForm()"><i class="bi bi-plus-lg"></i> Nuevo enlace</button>
    </div>

    <div v-if="loadingNavbar" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
    <div v-else>
      <div class="hcb-nav-preview">
        <div class="hcb-nav-preview__bar">
          <span class="hcb-nav-preview__brand">{{ siteName || 'Sintel' }}</span>
          <div class="hcb-nav-preview__links">
            <span v-for="link in navbarLinks.filter(l => l.is_visible)" :key="link.uuid" class="hcb-nav-preview__link">
              <i v-if="link.icon_class" :class="['bi', link.icon_class, 'me-1']"></i>{{ link.label }}
            </span>
          </div>
        </div>
      </div>

      <div class="hcb-links-list mt-3">
        <div v-for="link in navbarLinks" :key="link.uuid" class="hcb-link-row">
          <i :class="['bi', link.icon_class || 'bi-link', 'hcb-link-icon']"></i>
          <div class="hcb-link-info">
            <span class="hcb-link-title">{{ link.label }}</span>
            <span class="hcb-chip hcb-chip--xs">{{ link.url }}</span>
            <span :class="['hcb-chip hcb-chip--xs', link.is_visible ? 'hcb-chip--green' : 'hcb-chip--gray']">
              {{ link.is_visible ? 'Visible' : 'Oculto' }}
            </span>
          </div>
          <div class="d-flex gap-1">
            <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openNavForm(link)"><i class="bi bi-pencil"></i></button>
            <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteNavLink(link)"><i class="bi bi-trash"></i></button>
          </div>
        </div>
        <div v-if="!navbarLinks.length" class="hcb-empty">Sin enlaces de navbar.</div>
      </div>
    </div>

    <Teleport to="body">
      <BaseModal v-model="showNavModal" :title="editingNavLink ? 'Editar enlace' : 'Nuevo enlace navbar'">
        <div class="hcb-form-grid">
          <div class="hcb-field">
            <label class="hcb-label">Etiqueta *</label>
            <input v-model="navForm.label" class="hcb-input" placeholder="Tienda">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL *</label>
            <input v-model="navForm.url" class="hcb-input" placeholder="/tienda">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Icono Bootstrap</label>
            <input v-model="navForm.icon_class" class="hcb-input" placeholder="bi-shop">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Orden</label>
            <input v-model.number="navForm.display_order" type="number" class="hcb-input" min="0">
          </div>
          <div class="hcb-field hcb-field--full d-flex gap-3">
            <div class="form-check form-switch">
              <input v-model="navForm.is_visible" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Visible</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="navForm.open_in_new_tab" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Abrir en nueva pestana</label>
            </div>
          </div>
        </div>
        <div v-if="navError" class="alert alert-danger small py-2 mt-2">{{ navError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeNavForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingNav" @click="saveNavLink">
            <span v-if="savingNav" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingNavLink ? 'Guardar cambios' : 'Crear enlace' }}
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

defineProps({
  // Nombre del sitio (borrador en vivo de BrandSection.vue) -- solo para el
  // mini-preview de esta seccion, no se persiste desde aqui.
  siteName: { type: String, default: '' },
});

const toast = useToast();
const store = useCoreAdminStore();
const { navbarLinks, navbarLoading: loadingNavbar } = storeToRefs(store);

const showNavModal   = ref(false);
const editingNavLink = ref(null);
const savingNav      = ref(false);
const navError       = ref('');

const defaultNavForm = () => ({ label: '', url: '', icon_class: '', display_order: 0, is_visible: true, open_in_new_tab: false });
const navForm = ref(defaultNavForm());

async function fetchNavbarLinks() {
  await store.fetchNavbarLinks();
}
function openNavForm(link = null) {
  editingNavLink.value = link; navError.value = '';
  navForm.value = link ? {
    label: link.label, url: link.url, icon_class: link.icon_class || '',
    display_order: link.display_order ?? 0,
    is_visible: link.is_visible, open_in_new_tab: link.open_in_new_tab,
  } : defaultNavForm();
  showNavModal.value = true;
}
function closeNavForm() { showNavModal.value = false; editingNavLink.value = null; }
async function saveNavLink() {
  if (!navForm.value.label || !navForm.value.url) { navError.value = 'Etiqueta y URL son requeridos.'; return; }
  savingNav.value = true; navError.value = '';
  const res = editingNavLink.value
    ? await store.updateNavLink(editingNavLink.value.uuid, navForm.value)
    : await store.createNavLink(navForm.value);
  if (res.ok) {
    toast.success('Enlace guardado.');
    closeNavForm();
    await fetchNavbarLinks();
  } else {
    navError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingNav.value = false;
}
async function deleteNavLink(link) {
  if (!confirm(`Eliminar "${link.label}"?`)) return;
  const res = await store.deleteNavLink(link.uuid);
  if (res.ok) {
    toast.success('Enlace eliminado.');
    await fetchNavbarLinks();
  } else {
    toast.error('No se pudo eliminar.');
  }
}
</script>
