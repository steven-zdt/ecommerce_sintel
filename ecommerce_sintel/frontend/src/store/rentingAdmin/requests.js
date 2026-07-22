/**
 * rentingAdmin/requests.js — Pinia store para Solicitudes de Renta (admin).
 *
 * Nota: a diferencia de catalog/pricing/taxonomy, estas acciones pegan a
 * renting/rental-requests/ (no a dashboard/): el permiso es por-accion
 * (IsAdminUser en cada @action), no por namespace de URL.
 * Dividido desde rentingAdmin.js (SPRINT 4, 2026-07-16) -- ver 12_CHECKLIST_IMPLEMENTACION.md.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useRentingRequestsAdminStore = defineStore('rentingRequestsAdmin', {
  state: () => ({
    rentalRequests: [],
    totalRentalRequests: 0,
    loading: false,
    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    _clearError() {
      this.error = null;
    },

    async fetchRentalRequests(params = {}) {
      this._clearError();
      this.loading = true;
      try {
        const query = new URLSearchParams(params).toString();
        const { data } = await this._api().get(`renting/rental-requests/?${query}`);
        this.rentalRequests = data.results ?? data;
        this.totalRentalRequests = data.count ?? data.length;
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando solicitudes de renta.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async approveRentalRequest(uuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/approve/`);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al aprobar la solicitud.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async rejectRentalRequest(uuid, reason = '') {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/reject/`, { reason });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al rechazar la solicitud.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async markDelivered(uuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/mark-delivered/`);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al marcar como entregado.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async markReturned(uuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/mark-returned/`);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al marcar como devuelto.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async releaseRentalPeriod(uuid, reason = '') {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/release-period/`, { reason });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al liberar el periodo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async extendRentalPeriod(uuid, newEndDate, reason = '') {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/extend/`, {
          new_end_date: newEndDate, reason,
        });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al extender la renta.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async registerReturnInspection(uuid, { hasDamage, conditionNotes = '', missingAccessories = '' }) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/rental-requests/${uuid}/return-inspection/`, {
          has_damage: hasDamage, condition_notes: conditionNotes, missing_accessories: missingAccessories,
        });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al registrar la inspeccion.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
