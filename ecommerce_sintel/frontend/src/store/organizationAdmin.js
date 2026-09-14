/**
 * organizationAdmin.js — Pinia store para el panel de Organizacion
 * (OrganizationView.vue: 8 secciones -- empresa, branding, contacto, redes
 * sociales, correos, dominios, SEO, informacion legal).
 *
 * Cuarto incremento de la migracion a stores Pinia de modulos admin (auditoria
 * 2026-07-23, doc 13 P1-4; anteriores: security, notificationsAdmin, paymentAdmin).
 *
 * El store guarda unicamente los datos "de servidor" (lo que devuelve cada
 * GET) y las acciones de mutacion -- los formularios de edicion (draft antes
 * de guardar), previews de archivos y el estado de confirmacion de borrado
 * de una red social quedan como estado local del componente, igual criterio
 * que los 3 incrementos anteriores (son estado de UI, no datos del servidor).
 *
 * `actionLoading` es unico y compartido entre las 8 secciones a proposito --
 * asi se comportaba ya el `saving` original de OrganizationView.vue (un solo
 * ref reusado por los 8 botones "Guardar"), no se cambio ese comportamiento.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useOrganizationAdminStore = defineStore('organizationAdmin', {
  state: () => ({
    company: null,
    branding: null,
    contact: null,
    socialLinks: [],
    emailSettings: null,
    domainSettings: null,
    seoSettings: null,
    legalEntity: null,
    // White-label F8 (2026-08-14): documentos legales (Terminos/Privacidad/
    // Garantia/Devoluciones/Autorizacion) -- ver organization.LegalDocument.
    legalDocuments: [],

    loading: false,
    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    async fetchAll() {
      this.loading = true;
      try {
        const api = this._api();
        const [company, branding, contact, social, email, domains, seo, legal, legalDocs] = await Promise.all([
          api.get('organization/company/'),
          api.get('organization/branding/'),
          api.get('organization/contact/'),
          api.get('organization/social-links/'),
          api.get('organization/email-settings/'),
          api.get('organization/domain-settings/'),
          api.get('organization/seo-settings/'),
          api.get('organization/legal-entity/'),
          api.get('organization/legal-documents/'),
        ]);
        this.company = company.data ?? null;
        this.branding = branding.data ?? null;
        this.contact = contact.data ?? null;
        this.socialLinks = social.data ?? [];
        this.emailSettings = email.data ?? null;
        this.domainSettings = domains.data ?? null;
        this.seoSettings = seo.data ?? null;
        this.legalEntity = legal.data ?? null;
        this.legalDocuments = legalDocs.data ?? [];
      } catch {
        this.error = 'Error cargando la configuracion de Organizacion.';
      } finally {
        this.loading = false;
      }
    },

    async _save(action) {
      this.actionLoading = true;
      try {
        const response = await action();
        return { ok: true, data: response?.data };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    saveCompany(payload) {
      return this._save(() => this._api().patch('organization/company/update/', payload));
    },

    saveBranding(formData) {
      return this._save(() => this._api().patch('organization/branding/update/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }));
    },

    saveContact(payload) {
      return this._save(() => this._api().patch('organization/contact/update/', payload));
    },

    async createSocialLink(payload) {
      const res = await this._save(async () => {
        const { data } = await this._api().post('organization/social-links/', payload);
        this.socialLinks.push(data);
      });
      return res;
    },

    async deleteSocialLink(uuid) {
      try {
        await this._api().delete(`organization/social-links/${uuid}/`);
        this.socialLinks = this.socialLinks.filter((l) => l.uuid !== uuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      }
    },

    saveEmailSettings(payload) {
      return this._save(() => this._api().patch('organization/email-settings/update/', payload));
    },

    saveDomainSettings(payload) {
      return this._save(() => this._api().patch('organization/domain-settings/update/', payload));
    },

    saveSeoSettings(formData) {
      return this._save(() => this._api().patch('organization/seo-settings/update/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }));
    },

    saveLegalEntityInfo(payload) {
      return this._save(() => this._api().patch('organization/legal-entity/update/', payload));
    },

    async saveLegalDocument(docType, payload) {
      const res = await this._save(async () => {
        const { data } = await this._api().patch(`organization/legal-documents/${docType}/update/`, payload);
        const idx = this.legalDocuments.findIndex((d) => d.doc_type === docType);
        if (idx >= 0) this.legalDocuments[idx] = data;
        else this.legalDocuments.push(data);
      });
      return res;
    },
  },
});
