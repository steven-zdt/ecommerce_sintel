/**
 * technicalServicesAdmin/services.js — Pinia store para el CRUD de
 * Technical Services: entidad Service + Imagenes + Variantes.
 *
 * Dividido desde technicalServicesAdmin.js (SPRINT 4, 2026-07-16) -- ver
 * 12_CHECKLIST_IMPLEMENTACION.md. Paquetes vive en ./packages.js, taxonomia
 * (Categorias/Niveles/Reglas de costo) en ./catalog.js.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useTechnicalServicesStore = defineStore('technicalServices', {
  state: () => ({
    services: [],
    totalServices: 0,
    currentService: null,
    variants: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  getters: {
    activeServices: (state) => state.services.filter((s) => s.is_active),
  },

  actions: {
    _api() {
      return useApi();
    },

    _clearError() {
      this.error = null;
    },

    // ─── Services ──────────────────────────────────────────────────────────────

    async fetchServices(params = {}) {
      this._clearError();
      this.loading = true;
      try {
        const query = new URLSearchParams(params).toString();
        const { data } = await this._api().get(`dashboard/services/?${query}`);
        this.services = data.results ?? data;
        this.totalServices = data.count ?? data.length;
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando servicios.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async fetchServiceDetail(uuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get(`dashboard/services/${uuid}/`);
        this.currentService = data;
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Servicio no encontrado.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async createService(payload) {
      this._clearError();
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/services/', payload);
        await this.fetchServices(); // invalidar caché
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear servicio.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateService(uuid, payload) {
      this._clearError();
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/services/${uuid}/`, payload);
        await this.fetchServices();
        if (this.currentService?.uuid === uuid) {
          this.currentService = data;
        }
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al actualizar servicio.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteService(uuid) {
      this._clearError();
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/services/${uuid}/`);
        await this.fetchServices();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar servicio.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async duplicateService(uuid) {
      this._clearError();
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/services/${uuid}/duplicate/`);
        await this.fetchServices();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al duplicar servicio.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Images ────────────────────────────────────────────────────────────────

    async uploadImage(serviceUuid, file, altText = '', isPrimary = false) {
      this.actionLoading = true;
      try {
        const fd = new FormData();
        fd.append('image', file);
        if (altText) fd.append('alt_text', altText);
        fd.append('is_primary', isPrimary ? 'true' : 'false');
        const { data } = await this._api().post(
          `dashboard/services/${serviceUuid}/add_image/`,
          fd,
          { headers: { 'Content-Type': 'multipart/form-data' } },
        );
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al subir imagen.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteImage(serviceUuid, imageUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/services/${serviceUuid}/delete_image/${imageUuid}/`);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar imagen.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async setPrimaryImage(serviceUuid, imageUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(
          `dashboard/services/${serviceUuid}/set_primary/${imageUuid}/`,
        );
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al establecer imagen principal.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Variants ──────────────────────────────────────────────────────────────

    async fetchVariants(serviceUuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/service-variants/', {
          params: { service: serviceUuid },
        });
        this.variants = data.results ?? data;
        return this.variants;
      } catch (err) {
        this.error = 'Error cargando variantes.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createVariant(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/service-variants/', payload);
        if (payload.service) {
          await this.fetchVariants(payload.service);
        }
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear variante.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateVariant(variantUuid, serviceUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/service-variants/${variantUuid}/`, payload);
        if (serviceUuid) {
          await this.fetchVariants(serviceUuid);
        }
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar variante.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteVariant(variantUuid, serviceUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/service-variants/${variantUuid}/`);
        if (serviceUuid) {
          await this.fetchVariants(serviceUuid);
        }
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar variante.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async fetchVariantsPriceHistory(variantUuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get(`dashboard/service-variants/${variantUuid}/price_history/`);
        return data;
      } catch (err) {
        this.error = 'Error al cargar el historial de precios.';
        return [];
      } finally {
        this.loading = false;
      }
    },
  },
});
