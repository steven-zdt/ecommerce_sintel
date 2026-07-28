<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Footer</h2>
        <p class="hcb-section-sub">Contacto, redes sociales y enlaces de navegacion.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" @click="openFooterGroupForm()">
        <i class="bi bi-plus-lg"></i> Nuevo grupo
      </button>
    </div>

    <div v-if="loadingFooter || loadingFooterGroups" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
    <template v-else>
      <!-- Contacto -->
      <div class="hcb-card-section">
        <h6 class="hcb-subsection-title"><i class="bi bi-telephone me-2"></i>Datos de contacto</h6>
        <div class="hcb-form-grid">
          <div class="hcb-field">
            <label class="hcb-label">Telefono</label>
            <input v-model="contactForm.phone" class="hcb-input" placeholder="+57 1 234 5678">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Email</label>
            <input v-model="contactForm.email" class="hcb-input" placeholder="info@sintel.com">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Direccion</label>
            <input v-model="contactForm.address" class="hcb-input" placeholder="Cra 7 # 123, Bogota">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Horario</label>
            <input v-model="contactForm.working_hours" class="hcb-input" placeholder="Lunes a Viernes 8-18h">
          </div>
        </div>
        <button class="hcb-btn hcb-btn--primary mt-3" :disabled="savingContact" @click="saveContact">
          <span v-if="savingContact" class="spinner-border spinner-border-sm me-1"></span>
          Guardar contacto
        </button>
      </div>

      <!-- Grupos (columnas) -->
      <div class="hcb-card-section mt-4">
        <h6 class="hcb-subsection-title"><i class="bi bi-columns-gap me-2"></i>Columnas de navegacion</h6>
        <p class="hcb-section-sub mb-3">Arrastra para reordenar. Maximo 6 columnas por fila en la Home publica (se ajusta solo).</p>
        <div v-if="!footerGroups.length" class="hcb-empty">Sin columnas. Crea la primera.</div>
        <div v-else class="hcb-fg-grid">
          <div
            v-for="(group, idx) in footerGroups"
            :key="group.uuid"
            :class="['hcb-fg-card', !group.is_active && 'hcb-fg-card--inactive', selectedGroupUuid === group.uuid && 'hcb-fg-card--selected']"
            draggable="true"
            @dragstart="handleGroupDragStart(idx)"
            @dragover.prevent
            @drop="handleGroupDrop(idx)"
            @click="selectGroup(group)"
          >
            <span class="hcb-drag-handle" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
            <div class="hcb-fg-card__icon">
              <IconRenderer :icon="group.icon_class" />
            </div>
            <div class="hcb-fg-card__body">
              <div class="hcb-fg-card__title">{{ group.title }}</div>
              <div class="hcb-fg-card__meta">{{ group.links_count }} enlace(s)</div>
            </div>
            <span :class="['hcb-chip', group.is_active ? 'hcb-chip--green' : 'hcb-chip--gray']">
              {{ group.is_active ? 'Activo' : 'Inactivo' }}
            </span>
            <div class="d-flex gap-1">
              <button class="hcb-icon-btn hcb-icon-btn--xs" @click.stop="openFooterGroupForm(group)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click.stop="deleteFooterGroup(group)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </div>

      <!-- Enlaces del grupo seleccionado -->
      <div v-if="selectedGroup" class="hcb-card-section mt-4">
        <div class="hcb-section-header">
          <h6 class="hcb-subsection-title mb-0">
            <IconRenderer :icon="selectedGroup.icon_class" extra-class="me-2" />
            Enlaces de "{{ selectedGroup.title }}"
          </h6>
          <button class="hcb-btn hcb-btn--primary hcb-btn--sm" @click="openFooterLinkForm()">
            <i class="bi bi-plus-lg"></i> Nuevo enlace
          </button>
        </div>
        <div v-if="!groupLinks.length" class="hcb-empty">Sin enlaces en este grupo. Agrega el primero.</div>
        <div v-else class="hcb-links-list">
          <div
            v-for="(link, idx) in groupLinks"
            :key="link.uuid"
            class="hcb-link-row"
            draggable="true"
            @dragstart="handleLinkDragStart(idx)"
            @dragover.prevent
            @drop="handleLinkDrop(idx)"
          >
            <span class="hcb-drag-handle" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
            <IconRenderer :icon="link.icon_class || 'bi-link'" extra-class="hcb-link-icon" />
            <div class="hcb-link-info">
              <span class="hcb-link-title">{{ link.title }}</span>
              <span class="hcb-chip hcb-chip--xs">{{ link.url }}</span>
              <span v-if="link.open_new_tab" class="hcb-chip hcb-chip--xs">Nueva pestana</span>
              <span :class="['hcb-chip hcb-chip--xs', link.is_active ? 'hcb-chip--green' : 'hcb-chip--gray']">
                {{ link.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </div>
            <div class="d-flex gap-1">
              <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openFooterLinkForm(link)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteFooterLink(link)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </div>

      <!-- Redes sociales -->
      <div class="hcb-card-section mt-4">
        <div class="hcb-section-header">
          <h6 class="hcb-subsection-title mb-0"><i class="bi bi-share me-2"></i>Redes sociales</h6>
          <button class="hcb-btn hcb-btn--primary hcb-btn--sm" @click="openSocialLinkForm()">
            <i class="bi bi-plus-lg"></i> Nueva red social
          </button>
        </div>
        <div v-if="!socialLinksFlat.length" class="hcb-empty">Sin redes sociales.</div>
        <div v-else class="hcb-links-list">
          <div v-for="link in socialLinksFlat" :key="link.uuid" class="hcb-link-row">
            <IconRenderer :icon="link.icon_class || 'bi-share'" extra-class="hcb-link-icon" />
            <div class="hcb-link-info">
              <span class="hcb-link-title">{{ link.title }}</span>
              <span class="hcb-chip hcb-chip--xs">{{ link.url }}</span>
            </div>
            <div class="d-flex gap-1">
              <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openSocialLinkForm(link)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteFooterLink(link)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <Teleport to="body">
      <!-- Modal Enlace Footer (nav, ligado al grupo seleccionado; o social) -->
      <BaseModal
        v-model="showFooterLinkModal"
        :title="editingFooterLink ? 'Editar enlace' : (footerLinkForm.category === 'social' ? 'Nueva red social' : `Nuevo enlace de '${selectedGroup?.title || ''}'`)"
      >
        <div class="hcb-form-grid">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo *</label>
            <input v-model="footerLinkForm.title" class="hcb-input" placeholder="Facebook">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">URL *</label>
            <input v-model="footerLinkForm.url" class="hcb-input" placeholder="https://...">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Icono (Bootstrap o atajo: telephone, camera...)</label>
            <div class="d-flex align-items-center gap-2">
              <IconRenderer :icon="normalizeIconInput(footerLinkForm.icon_class)" size="1.3rem" />
              <input v-model="footerLinkForm.icon_class" class="hcb-input" placeholder="bi-facebook">
            </div>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Orden</label>
            <input v-model.number="footerLinkForm.display_order" type="number" class="hcb-input" min="0">
          </div>
          <div class="hcb-field hcb-field--full d-flex gap-3">
            <div class="form-check form-switch">
              <input v-model="footerLinkForm.is_active" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Activo</label>
            </div>
            <div v-if="footerLinkForm.category === 'nav'" class="form-check form-switch">
              <input v-model="footerLinkForm.open_new_tab" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Abrir en nueva pestana</label>
            </div>
          </div>
        </div>
        <div v-if="footerLinkError" class="alert alert-danger small py-2 mt-2">{{ footerLinkError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeFooterLinkForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingFooterLink" @click="saveFooterLink">
            <span v-if="savingFooterLink" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingFooterLink ? 'Guardar cambios' : 'Crear enlace' }}
          </button>
        </template>
      </BaseModal>

      <!-- Modal Grupo del Footer -->
      <BaseModal v-model="showFooterGroupModal" :title="editingFooterGroup ? 'Editar columna' : 'Nueva columna'">
        <div class="hcb-form-grid">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo *</label>
            <input v-model="footerGroupForm.title" class="hcb-input" placeholder="Empresa">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Icono (Bootstrap o atajo: building, shop...)</label>
            <div class="d-flex align-items-center gap-2">
              <IconRenderer :icon="normalizeIconInput(footerGroupForm.icon_class)" size="1.3rem" />
              <input v-model="footerGroupForm.icon_class" class="hcb-input" placeholder="bi-building">
            </div>
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Descripcion (opcional)</label>
            <input v-model="footerGroupForm.description" class="hcb-input" placeholder="Texto breve de apoyo">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color de fondo</label>
            <div class="d-flex gap-2">
              <input v-model="footerGroupForm.background_color" type="color" class="hcb-color-input">
              <input v-model="footerGroupForm.background_color" class="hcb-input" placeholder="" style="flex:1">
            </div>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color de texto</label>
            <div class="d-flex gap-2">
              <input v-model="footerGroupForm.text_color" type="color" class="hcb-color-input">
              <input v-model="footerGroupForm.text_color" class="hcb-input" placeholder="" style="flex:1">
            </div>
          </div>
          <div class="hcb-field d-flex align-items-end">
            <div class="form-check form-switch">
              <input v-model="footerGroupForm.is_active" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Activo</label>
            </div>
          </div>
        </div>
        <div v-if="footerGroupError" class="alert alert-danger small py-2 mt-2">{{ footerGroupError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeFooterGroupForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingFooterGroup" @click="saveFooterGroup">
            <span v-if="savingFooterGroup" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingFooterGroup ? 'Guardar cambios' : 'Crear columna' }}
          </button>
        </template>
      </BaseModal>
    </Teleport>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import BaseModal from '@/components/base/BaseModal.vue';
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { normalizeIconInput } from '@/utils/iconShorthand';

const toast = useToast();
const store = useCoreAdminStore();
const {
  footerLinks, footerContact,
  footerLoading: loadingFooter, footerGroupsLoading: loadingFooterGroups,
  footerGroups,
} = storeToRefs(store);

// contactForm es v-model con el padre: el panel de preview compartido
// (CustomerFooter) necesita el borrador en vivo aunque el padre nunca lo
// edite directamente -- mismo criterio que BrandSection/CtaSection/
// BrandSliderSection (config).
const contactForm = defineModel('contactForm', {
  default: () => ({ phone: '', email: '', address: '', working_hours: '' }),
});

const showFooterLinkModal = ref(false);
const editingFooterLink = ref(null);
const savingFooterLink  = ref(false);
const footerLinkError   = ref('');
const savingContact     = ref(false);

const defaultFooterLinkForm = (category = 'nav') => ({
  title: '', url: '', category, group: null,
  icon_class: '', open_new_tab: false, is_active: true, display_order: 0,
});
const footerLinkForm = ref(defaultFooterLinkForm());

const socialLinksFlat = computed(() => footerLinks.value.filter((l) => l.category === 'social'));

async function fetchFooter() {
  await store.fetchFooter();
  const c = footerContact.value;
  if (c) {
    contactForm.value = { phone: c.phone || '', email: c.email || '', address: c.address || '', working_hours: c.working_hours || '' };
  }
}
async function saveContact() {
  savingContact.value = true;
  const res = await store.saveFooterContact(contactForm.value);
  if (res.ok) {
    toast.success('Contacto guardado.');
  } else {
    toast.error('Error al guardar contacto.');
  }
  savingContact.value = false;
}

// Enlaces de navegacion (ligados al grupo seleccionado) -- abre el mismo modal
// que las redes sociales, pero con category='nav' y el grupo implicito.
function openFooterLinkForm(link = null) {
  editingFooterLink.value = link;
  footerLinkError.value   = '';
  footerLinkForm.value = link ? {
    title: link.title, url: link.url, category: link.category, group: link.group,
    icon_class: link.icon_class || '', open_new_tab: link.open_new_tab || false,
    is_active: link.is_active, display_order: link.display_order ?? 0,
  } : { ...defaultFooterLinkForm('nav'), group: selectedGroupUuid.value };
  showFooterLinkModal.value = true;
}
function openSocialLinkForm(link = null) {
  editingFooterLink.value = link;
  footerLinkError.value   = '';
  footerLinkForm.value = link ? {
    title: link.title, url: link.url, category: 'social', group: null,
    icon_class: link.icon_class || '', open_new_tab: false,
    is_active: link.is_active, display_order: link.display_order ?? 0,
  } : defaultFooterLinkForm('social');
  showFooterLinkModal.value = true;
}
function closeFooterLinkForm() { showFooterLinkModal.value = false; editingFooterLink.value = null; }
async function saveFooterLink() {
  if (!footerLinkForm.value.title || !footerLinkForm.value.url) {
    footerLinkError.value = 'Titulo y URL son requeridos.'; return;
  }
  savingFooterLink.value = true; footerLinkError.value = '';
  const payload = { ...footerLinkForm.value, icon_class: normalizeIconInput(footerLinkForm.value.icon_class) };
  const res = editingFooterLink.value
    ? await store.updateFooterLink(editingFooterLink.value.uuid, payload)
    : await store.createFooterLink(payload);
  if (res.ok) {
    toast.success('Enlace guardado.');
    closeFooterLinkForm();
    await fetchFooter();
  } else {
    footerLinkError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingFooterLink.value = false;
}
async function deleteFooterLink(link) {
  if (!confirm(`Eliminar "${link.title}"?`)) return;
  const res = await store.deleteFooterLink(link.uuid);
  if (res.ok) {
    toast.success('Enlace eliminado.');
    await fetchFooter();
  } else {
    toast.error('No se pudo eliminar.');
  }
}

const linkDragIndex = ref(null);
function handleLinkDragStart(index) { linkDragIndex.value = index; }
async function handleLinkDrop(targetIndex) {
  const fromIndex = linkDragIndex.value;
  linkDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...groupLinks.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  // Actualizacion optimista: reordena localmente reasignando display_order
  // dentro de footerLinks para que groupLinks (computed) refleje el cambio ya.
  reordered.forEach((link, idx) => { link.display_order = idx; });
  const res = await store.reorderFooterLinks(reordered.map((l) => l.uuid));
  if (!res.ok) {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchFooter();
  }
}

// ── Grupos (columnas) ────────────────────────────────────────────────────────
const showFooterGroupModal = ref(false);
const editingFooterGroup  = ref(null);
const savingFooterGroup   = ref(false);
const footerGroupError    = ref('');
const selectedGroupUuid   = ref(null);
const groupDragIndex      = ref(null);

const defaultFooterGroupForm = () => ({
  title: '', icon_class: 'bi-folder', description: '',
  background_color: '', text_color: '', is_active: true, display_order: 0,
});
const footerGroupForm = ref(defaultFooterGroupForm());

const selectedGroup = computed(() => footerGroups.value.find((g) => g.uuid === selectedGroupUuid.value) || null);
const groupLinks = computed(() =>
  footerLinks.value
    .filter((l) => l.category === 'nav' && l.group === selectedGroupUuid.value)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
);

async function fetchFooterGroups() {
  await store.fetchFooterGroups();
  if (!selectedGroupUuid.value && footerGroups.value.length) selectedGroupUuid.value = footerGroups.value[0].uuid;
}
function selectGroup(group) { selectedGroupUuid.value = group.uuid; }
function openFooterGroupForm(group = null) {
  editingFooterGroup.value = group;
  footerGroupError.value   = '';
  footerGroupForm.value = group ? {
    title: group.title, icon_class: group.icon_class || 'bi-folder',
    description: group.description || '', background_color: group.background_color || '',
    text_color: group.text_color || '', is_active: group.is_active, display_order: group.display_order ?? 0,
  } : defaultFooterGroupForm();
  showFooterGroupModal.value = true;
}
function closeFooterGroupForm() { showFooterGroupModal.value = false; editingFooterGroup.value = null; }
async function saveFooterGroup() {
  if (!footerGroupForm.value.title.trim()) { footerGroupError.value = 'El titulo es requerido.'; return; }
  savingFooterGroup.value = true; footerGroupError.value = '';
  const payload = { ...footerGroupForm.value, icon_class: normalizeIconInput(footerGroupForm.value.icon_class) };
  const res = editingFooterGroup.value
    ? await store.updateFooterGroup(editingFooterGroup.value.uuid, payload)
    : await store.createFooterGroup(payload);
  if (res.ok) {
    toast.success('Columna guardada.');
    closeFooterGroupForm();
    await fetchFooterGroups();
  } else {
    footerGroupError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingFooterGroup.value = false;
}
async function deleteFooterGroup(group) {
  if (!confirm(`Eliminar columna "${group.title}" y desvincular sus enlaces?`)) return;
  const res = await store.deleteFooterGroup(group.uuid);
  if (res.ok) {
    toast.success('Columna eliminada.');
    if (selectedGroupUuid.value === group.uuid) selectedGroupUuid.value = null;
    await fetchFooterGroups();
  } else {
    toast.error('No se pudo eliminar.');
  }
}
function handleGroupDragStart(index) { groupDragIndex.value = index; }
async function handleGroupDrop(targetIndex) {
  const fromIndex = groupDragIndex.value;
  groupDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...footerGroups.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  footerGroups.value = reordered;
  const res = await store.reorderFooterGroups(reordered.map((g) => g.uuid));
  if (!res.ok) {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchFooterGroups();
  }
}
</script>
