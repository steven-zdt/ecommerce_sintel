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
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import BaseInput from '@/components/base/BaseInput.vue';
import BaseTextarea from '@/components/base/BaseTextarea.vue';
import BaseUpload from '@/components/base/BaseUpload.vue';

const api = useApi();
const toast = useToast();

const saving = ref(false);
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
const socialLinks   = ref([]);
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
  try {
    const [company, branding, contact, social, email, domains, seo, legal] = await Promise.all([
      api.get('organization/company/'),
      api.get('organization/branding/'),
      api.get('organization/contact/'),
      api.get('organization/social-links/'),
      api.get('organization/email-settings/'),
      api.get('organization/domain-settings/'),
      api.get('organization/seo-settings/'),
      api.get('organization/legal-entity/'),
    ]);
    if (company.data)  companyForm.value  = { trade_name: company.data.trade_name || '', description: company.data.description || '', founded_year: company.data.founded_year };
    if (branding.data) { brandingForm.value.tagline = branding.data.tagline || ''; brandingPreview.value.logo = branding.data.logo; brandingPreview.value.favicon = branding.data.favicon; }
    if (contact.data)  contactForm.value = { phone: contact.data.phone || '', email: contact.data.email || '', address: contact.data.address || '', working_hours: contact.data.working_hours || '' };
    socialLinks.value = social.data || [];
    if (email.data)   emailForm.value   = { default_from_email: email.data.default_from_email || '', frontend_base_url: email.data.frontend_base_url || '', admin_login_url: email.data.admin_login_url || '' };
    if (domains.data) domainForm.value  = { primary_domain: domains.data.primary_domain || '', admin_panel_domain: domains.data.admin_panel_domain || '', api_domain: domains.data.api_domain || '' };
    if (seo.data)      { seoForm.value.meta_title = seo.data.meta_title || ''; seoForm.value.meta_description = seo.data.meta_description || ''; seoPreview.value.og_image = seo.data.og_image; }
    if (legal.data)    legalForm.value  = {
      legal_name: legal.data.legal_name || '', tax_id: legal.data.tax_id || '',
      fiscal_address: legal.data.fiscal_address || '', legal_representative: legal.data.legal_representative || '',
      city: legal.data.city || '', department: legal.data.department || '',
    };
  } catch (err) {
    toast.error('Error cargando la configuracion de Organizacion.');
  }
}

async function saveCompany() {
  saving.value = true;
  try {
    await api.patch('organization/company/update/', companyForm.value);
    toast.success('Empresa guardada.');
  } catch (err) {
    toast.error('Error guardando Empresa.');
  } finally {
    saving.value = false;
  }
}

async function saveBranding() {
  saving.value = true;
  try {
    const fd = new FormData();
    fd.append('tagline', brandingForm.value.tagline);
    if (brandingForm.value.logo)    fd.append('logo', brandingForm.value.logo);
    if (brandingForm.value.favicon) fd.append('favicon', brandingForm.value.favicon);
    await api.patch('organization/branding/update/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    toast.success('Branding guardado.');
  } catch (err) {
    toast.error('Error guardando Branding.');
  } finally {
    saving.value = false;
  }
}

async function saveContact() {
  saving.value = true;
  try {
    await api.patch('organization/contact/update/', contactForm.value);
    toast.success('Contacto guardado.');
  } catch (err) {
    toast.error('Error guardando Contacto.');
  } finally {
    saving.value = false;
  }
}

async function createSocialLink() {
  if (!newSocialLink.value.platform || !newSocialLink.value.url) {
    toast.error('Plataforma y URL son obligatorios.');
    return;
  }
  saving.value = true;
  try {
    const { data } = await api.post('organization/social-links/', newSocialLink.value);
    socialLinks.value.push(data);
    newSocialLink.value = { platform: '', url: '', icon_class: '' };
    toast.success('Red social agregada.');
  } catch (err) {
    toast.error('Error agregando red social.');
  } finally {
    saving.value = false;
  }
}

function askDeleteSocialLink(link) {
  confirmingDeleteUuid.value = link.uuid;
}

function cancelDeleteSocialLink() {
  confirmingDeleteUuid.value = null;
}

async function deleteSocialLink(link) {
  try {
    await api.delete(`organization/social-links/${link.uuid}/`);
    socialLinks.value = socialLinks.value.filter(l => l.uuid !== link.uuid);
    toast.success('Red social eliminada.');
  } catch (err) {
    toast.error('Error eliminando red social.');
  } finally {
    confirmingDeleteUuid.value = null;
  }
}

async function saveEmailSettings() {
  saving.value = true;
  try {
    await api.patch('organization/email-settings/update/', emailForm.value);
    toast.success('Correos guardados.');
  } catch (err) {
    toast.error('Error guardando Correos.');
  } finally {
    saving.value = false;
  }
}

async function saveDomainSettings() {
  saving.value = true;
  try {
    await api.patch('organization/domain-settings/update/', domainForm.value);
    toast.success('Dominios guardados.');
  } catch (err) {
    toast.error('Error guardando Dominios.');
  } finally {
    saving.value = false;
  }
}

async function saveSeoSettings() {
  saving.value = true;
  try {
    const fd = new FormData();
    fd.append('meta_title', seoForm.value.meta_title);
    fd.append('meta_description', seoForm.value.meta_description);
    if (seoForm.value.og_image) fd.append('og_image', seoForm.value.og_image);
    await api.patch('organization/seo-settings/update/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    toast.success('SEO guardado.');
  } catch (err) {
    toast.error('Error guardando SEO.');
  } finally {
    saving.value = false;
  }
}

async function saveLegalEntityInfo() {
  saving.value = true;
  try {
    await api.patch('organization/legal-entity/update/', legalForm.value);
    toast.success('Informacion legal guardada.');
  } catch (err) {
    toast.error('Error guardando Informacion Legal.');
  } finally {
    saving.value = false;
  }
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
