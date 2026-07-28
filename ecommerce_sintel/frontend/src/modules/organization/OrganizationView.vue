<template>
  <div class="org-view">
    <div class="org-header">
      <h1 class="org-title">Organizacion</h1>
      <p class="org-subtitle">Informacion institucional unica de la empresa — unico dueno de estos datos, el resto de modulos solo los consume.</p>
    </div>

    <div class="org-body">
      <!-- Tabs -->
      <ul class="org-tabs">
        <li v-for="s in sections" :key="s.id">
          <button
            class="org-tab-btn"
            :class="{ active: activeSection === s.id }"
            @click="activeSection = s.id"
          >
            <i :class="['bi', s.icon]"></i>
            {{ s.label }}
          </button>
        </li>
      </ul>

      <div class="org-panel">
        <!-- Empresa -->
        <section v-if="activeSection === 'company'">
          <h2 class="org-section-title">Empresa</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <BaseInput v-model="companyForm.trade_name" label="Nombre comercial" placeholder="Sintel" maxlength="150" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="companyForm.founded_year" type="number" label="Ano de fundacion" />
            </div>
            <div class="col-12">
              <BaseTextarea v-model="companyForm.description" label="Descripcion" :rows="3" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveCompany">Guardar</button>
        </section>

        <!-- Branding -->
        <section v-if="activeSection === 'branding'">
          <h2 class="org-section-title">Branding</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <BaseInput v-model="brandingForm.tagline" label="Eslogan" placeholder="Tu eslogan aqui" maxlength="300" />
            </div>
            <div class="col-md-3">
              <BaseUpload label="Logo" :preview-url="brandingPreview.logo" @file-selected="(f) => onFileSelected(f, 'logo')" />
            </div>
            <div class="col-md-3">
              <BaseUpload label="Favicon" :preview-url="brandingPreview.favicon" @file-selected="(f) => onFileSelected(f, 'favicon')" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveBranding">Guardar</button>
        </section>

        <!-- Contacto -->
        <section v-if="activeSection === 'contact'">
          <h2 class="org-section-title">Contacto</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <BaseInput v-model="contactForm.phone" label="Telefono" maxlength="100" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="contactForm.email" type="email" label="Email" maxlength="254" />
            </div>
            <div class="col-md-8">
              <BaseInput v-model="contactForm.address" label="Direccion" maxlength="500" />
            </div>
            <div class="col-md-4">
              <BaseInput v-model="contactForm.working_hours" label="Horario" maxlength="255" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveContact">Guardar</button>
        </section>

        <!-- Redes Sociales -->
        <section v-if="activeSection === 'social'">
          <h2 class="org-section-title">Redes Sociales</h2>
          <div class="org-social-list">
            <div v-for="link in socialLinks" :key="link.uuid" class="org-social-row"
              :class="{ 'bg-danger-subtle': confirmingDeleteUuid === link.uuid }">
              <template v-if="confirmingDeleteUuid === link.uuid">
                <span class="text-danger small flex-grow-1">¿Eliminar "{{ link.platform }}"?</span>
                <button class="org-btn-link text-danger" :disabled="saving" @click="deleteSocialLink(link)">Confirmar</button>
                <button class="org-btn-link" @click="cancelDeleteSocialLink">Cancelar</button>
              </template>
              <template v-else>
                <i :class="['bi', link.icon_class || 'bi-link-45deg']"></i>
                <span class="org-social-platform">{{ link.platform }}</span>
                <span class="org-social-url text-truncate">{{ link.url }}</span>
                <button class="org-btn-link text-danger" @click="askDeleteSocialLink(link)">Eliminar</button>
              </template>
            </div>
            <p v-if="!socialLinks.length" class="org-empty">Sin redes sociales configuradas.</p>
          </div>
          <div class="org-social-form">
            <BaseInput v-model="newSocialLink.platform" placeholder="Plataforma (ej. Instagram)" maxlength="100" />
            <BaseInput v-model="newSocialLink.url" placeholder="https://..." maxlength="500" />
            <BaseInput v-model="newSocialLink.icon_class" placeholder="bi-instagram" maxlength="100" />
            <button class="org-btn-primary" :disabled="saving" @click="createSocialLink">Agregar</button>
          </div>
        </section>

        <!-- Correos -->
        <section v-if="activeSection === 'email'">
          <h2 class="org-section-title">Correos</h2>
          <p class="org-hint">El password SMTP y demas credenciales de envio siguen en variables de entorno del servidor — solo los datos de negocio se editan aqui.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <BaseInput v-model="emailForm.default_from_email" type="email" label="Email remitente por defecto" maxlength="254" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="emailForm.frontend_base_url" label="URL base del frontend" maxlength="300" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="emailForm.admin_login_url" label="URL de login del panel admin" maxlength="300" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveEmailSettings">Guardar</button>
        </section>

        <!-- Dominios -->
        <section v-if="activeSection === 'domains'">
          <h2 class="org-section-title">Dominios</h2>
          <div class="row g-3">
            <div class="col-md-4">
              <BaseInput v-model="domainForm.primary_domain" label="Dominio principal" placeholder="sintel.net.co" maxlength="255" />
            </div>
            <div class="col-md-4">
              <BaseInput v-model="domainForm.admin_panel_domain" label="Dominio del panel admin" maxlength="255" />
            </div>
            <div class="col-md-4">
              <BaseInput v-model="domainForm.api_domain" label="Dominio de la API" maxlength="255" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveDomainSettings">Guardar</button>
        </section>

        <!-- SEO -->
        <section v-if="activeSection === 'seo'">
          <h2 class="org-section-title">SEO</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <BaseInput v-model="seoForm.meta_title" label="Meta titulo" maxlength="255" />
            </div>
            <div class="col-md-6">
              <BaseUpload label="Imagen Open Graph" :preview-url="seoPreview.og_image" @file-selected="(f) => onFileSelected(f, 'og_image')" />
            </div>
            <div class="col-12">
              <BaseTextarea v-model="seoForm.meta_description" label="Meta descripcion" :rows="2" maxlength="500" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveSeoSettings">Guardar</button>
        </section>

        <!-- Informacion Legal -->
        <section v-if="activeSection === 'legal'">
          <h2 class="org-section-title">Informacion Legal</h2>
          <div class="row g-3">
            <div class="col-md-6">
              <BaseInput v-model="legalForm.legal_name" label="Razon social" maxlength="255" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="legalForm.tax_id" label="NIT" maxlength="50" />
            </div>
            <div class="col-md-8">
              <BaseInput v-model="legalForm.fiscal_address" label="Direccion fiscal" maxlength="500" />
            </div>
            <div class="col-md-4">
              <BaseInput v-model="legalForm.legal_representative" label="Representante legal" maxlength="255" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="legalForm.city" label="Ciudad" maxlength="150" />
            </div>
            <div class="col-md-6">
              <BaseInput v-model="legalForm.department" label="Departamento" maxlength="150" />
            </div>
          </div>
          <button class="org-btn-primary mt-3" :disabled="saving" @click="saveLegalEntityInfo">Guardar</button>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useOrganizationAdminStore } from '@/store/organizationAdmin';
import BaseInput from '@/components/base/BaseInput.vue';
import BaseTextarea from '@/components/base/BaseTextarea.vue';
import BaseUpload from '@/components/base/BaseUpload.vue';

const toast = useToast();
const store = useOrganizationAdminStore();
const { actionLoading: saving, socialLinks } = storeToRefs(store);

const activeSection = ref('company');

const sections = [
  { id: 'company',  label: 'Empresa',          icon: 'bi-building' },
  { id: 'branding', label: 'Branding',          icon: 'bi-palette' },
  { id: 'contact',  label: 'Contacto',          icon: 'bi-telephone' },
  { id: 'social',   label: 'Redes Sociales',    icon: 'bi-share' },
  { id: 'email',    label: 'Correos',           icon: 'bi-envelope' },
  { id: 'domains',  label: 'Dominios',          icon: 'bi-globe' },
  { id: 'seo',      label: 'SEO',               icon: 'bi-search' },
  { id: 'legal',    label: 'Informacion Legal', icon: 'bi-file-earmark-text' },
];

const companyForm  = ref({ trade_name: '', description: '', founded_year: null });
const brandingForm = ref({ tagline: '', logo: null, favicon: null });
const brandingPreview = ref({ logo: null, favicon: null });
const contactForm  = ref({ phone: '', email: '', address: '', working_hours: '' });
const newSocialLink = ref({ platform: '', url: '', icon_class: '' });
const confirmingDeleteUuid = ref(null);
const emailForm  = ref({ default_from_email: '', frontend_base_url: '', admin_login_url: '' });
const domainForm = ref({ primary_domain: '', admin_panel_domain: '', api_domain: '' });
const seoForm    = ref({ meta_title: '', meta_description: '', og_image: null });
const seoPreview = ref({ og_image: null });
const legalForm  = ref({
  legal_name: '', tax_id: '', fiscal_address: '',
  legal_representative: '', city: '', department: '',
});

function onFileSelected(file, target) {
  const previewUrl = URL.createObjectURL(file);
  if (target === 'logo')      { brandingForm.value.logo = file;    brandingPreview.value.logo = previewUrl; }
  if (target === 'favicon')   { brandingForm.value.favicon = file; brandingPreview.value.favicon = previewUrl; }
  if (target === 'og_image')  { seoForm.value.og_image = file;     seoPreview.value.og_image = previewUrl; }
}

async function fetchAll() {
  await store.fetchAll();
  if (store.error) { toast.error(store.error); return; }
  const { company, branding, contact, emailSettings: email, domainSettings: domains, seoSettings: seo, legalEntity: legal } = store;
  if (company)  companyForm.value  = { trade_name: company.trade_name || '', description: company.description || '', founded_year: company.founded_year };
  if (branding) { brandingForm.value.tagline = branding.tagline || ''; brandingPreview.value.logo = branding.logo; brandingPreview.value.favicon = branding.favicon; }
  if (contact)  contactForm.value = { phone: contact.phone || '', email: contact.email || '', address: contact.address || '', working_hours: contact.working_hours || '' };
  if (email)   emailForm.value   = { default_from_email: email.default_from_email || '', frontend_base_url: email.frontend_base_url || '', admin_login_url: email.admin_login_url || '' };
  if (domains) domainForm.value  = { primary_domain: domains.primary_domain || '', admin_panel_domain: domains.admin_panel_domain || '', api_domain: domains.api_domain || '' };
  if (seo)      { seoForm.value.meta_title = seo.meta_title || ''; seoForm.value.meta_description = seo.meta_description || ''; seoPreview.value.og_image = seo.og_image; }
  if (legal)    legalForm.value  = {
    legal_name: legal.legal_name || '', tax_id: legal.tax_id || '',
    fiscal_address: legal.fiscal_address || '', legal_representative: legal.legal_representative || '',
    city: legal.city || '', department: legal.department || '',
  };
}

async function saveCompany() {
  const res = await store.saveCompany(companyForm.value);
  if (res.ok) toast.success('Empresa guardada.'); else toast.error('Error guardando Empresa.');
}

async function saveBranding() {
  const fd = new FormData();
  fd.append('tagline', brandingForm.value.tagline);
  if (brandingForm.value.logo)    fd.append('logo', brandingForm.value.logo);
  if (brandingForm.value.favicon) fd.append('favicon', brandingForm.value.favicon);
  const res = await store.saveBranding(fd);
  if (res.ok) toast.success('Branding guardado.'); else toast.error('Error guardando Branding.');
}

async function saveContact() {
  const res = await store.saveContact(contactForm.value);
  if (res.ok) toast.success('Contacto guardado.'); else toast.error('Error guardando Contacto.');
}

async function createSocialLink() {
  if (!newSocialLink.value.platform || !newSocialLink.value.url) {
    toast.error('Plataforma y URL son obligatorios.');
    return;
  }
  const res = await store.createSocialLink(newSocialLink.value);
  if (res.ok) {
    newSocialLink.value = { platform: '', url: '', icon_class: '' };
    toast.success('Red social agregada.');
  } else {
    toast.error('Error agregando red social.');
  }
}

function askDeleteSocialLink(link) {
  confirmingDeleteUuid.value = link.uuid;
}

function cancelDeleteSocialLink() {
  confirmingDeleteUuid.value = null;
}

async function deleteSocialLink(link) {
  const res = await store.deleteSocialLink(link.uuid);
  if (res.ok) toast.success('Red social eliminada.'); else toast.error('Error eliminando red social.');
  confirmingDeleteUuid.value = null;
}

async function saveEmailSettings() {
  const res = await store.saveEmailSettings(emailForm.value);
  if (res.ok) toast.success('Correos guardados.'); else toast.error('Error guardando Correos.');
}

async function saveDomainSettings() {
  const res = await store.saveDomainSettings(domainForm.value);
  if (res.ok) toast.success('Dominios guardados.'); else toast.error('Error guardando Dominios.');
}

async function saveSeoSettings() {
  const fd = new FormData();
  fd.append('meta_title', seoForm.value.meta_title);
  fd.append('meta_description', seoForm.value.meta_description);
  if (seoForm.value.og_image) fd.append('og_image', seoForm.value.og_image);
  const res = await store.saveSeoSettings(fd);
  if (res.ok) toast.success('SEO guardado.'); else toast.error('Error guardando SEO.');
}

async function saveLegalEntityInfo() {
  const res = await store.saveLegalEntityInfo(legalForm.value);
  if (res.ok) toast.success('Informacion legal guardada.'); else toast.error('Error guardando Informacion Legal.');
}

onMounted(fetchAll);
</script>

<style scoped>
.org-view { padding: 2rem; max-width: 1100px; }
.org-title { font-size: 1.5rem; font-weight: 700; margin-bottom: .25rem; }
.org-subtitle { color: #6b7280; font-size: .9rem; margin-bottom: 1.5rem; }
.org-body { display: flex; gap: 2rem; align-items: flex-start; }
.org-tabs { list-style: none; padding: 0; margin: 0; width: 220px; flex-shrink: 0; }
.org-tab-btn {
  display: flex; align-items: center; gap: .6rem; width: 100%;
  padding: .55rem .8rem; border: none; background: none; border-radius: 10px;
  color: #4b5563; font-size: .88rem; font-weight: 500; text-align: left;
  cursor: pointer; margin-bottom: .2rem; transition: all .15s;
}
.org-tab-btn:hover  { background: #f3f4f6; color: #111827; }
.org-tab-btn.active { background: #eff6ff; color: #1d4ed8; font-weight: 600; }
.org-panel { flex-grow: 1; background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 1.5rem; }
.org-section-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; }
.org-btn-primary {
  background: #1d4ed8; color: #fff; border: none; border-radius: 8px;
  padding: .55rem 1.2rem; font-size: .88rem; font-weight: 600; cursor: pointer;
}
.org-btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.org-btn-link { background: none; border: none; font-size: .8rem; cursor: pointer; }
.org-hint { font-size: .82rem; color: #6b7280; margin-bottom: 1rem; }
.org-empty { color: #9ca3af; font-size: .85rem; }
.org-social-list { margin-bottom: 1.25rem; }
.org-social-row {
  display: flex; align-items: center; gap: .75rem; padding: .5rem 0;
  border-bottom: 1px solid #f3f4f6; font-size: .85rem;
}
.org-social-platform { font-weight: 600; min-width: 100px; }
.org-social-url { flex-grow: 1; color: #6b7280; }
.org-social-form { display: flex; gap: .6rem; align-items: flex-start; }
.org-social-form .bi-field { flex: 1; }
</style>
