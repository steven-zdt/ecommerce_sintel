/**
 * quotesAdmin/quotations.js — Pinia store para Solicitudes de Cotizacion
 * (Quotation generada desde el cuestionario, revisada en RequestViewer.vue).
 *
 * Dividido desde quotesAdmin.js (SPRINT 4, 2026-07-16) -- ver
 * 12_CHECKLIST_IMPLEMENTACION.md. La parte del Constructor de Plantillas
 * vive en quotesAdmin/templateBuilder.js.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useQuotationsAdminStore = defineStore('quotationsAdmin', {
  state: () => ({
    quotations: [],
    currentQuotation: null,
    loading: false,
    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    async fetchQuotations() {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/quotations/');
        this.quotations = data.results ?? data;
        return this.quotations;
      } catch (err) {
        this.error = 'Error cargando solicitudes.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async fetchQuotationDetail(uuid) {
      this.loading = true;
      try {
        const { data } = await this._api().get(`dashboard/quotations/${uuid}/`);
        this.currentQuotation = data;
        return data;
      } catch (err) {
        this.error = 'Solicitud no encontrada.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async changeQuotationStatus(uuid, newStatus, notes = '') {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/quotations/${uuid}/change-status/`, { status: newStatus, notes });
        this.currentQuotation = data;
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al cambiar el estado.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async addQuotationItem(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/quotations/${uuid}/add-item/`, payload);
        this.currentQuotation = data;
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al agregar el producto.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async addQuotationService(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/quotations/${uuid}/add-service/`, payload);
        this.currentQuotation = data;
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al agregar el servicio.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
