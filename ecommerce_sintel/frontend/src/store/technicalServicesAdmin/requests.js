/**
 * technicalServicesAdmin/requests.js -- Pinia store para la Fachada
 * Administrativa Unificada de Solicitudes de Servicio (Plan
 * "Fachada Administrativa Unificada", 2026-08-14).
 *
 * Mismo patron que rentingAdmin/requests.js: pega directo a
 * dashboard/technical-services/requests/ (BFF admin-only, no al endpoint
 * de cliente orders/service-orders/). Solo estado de UI -- las reglas de
 * negocio (que transicion es valida) viven en el backend
 * (ServiceOperationCommands via ServiceAdminRequestOrchestrator), este
 * store nunca las reimplementa.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useServiceRequestsAdminStore = defineStore('serviceRequestsAdmin', {
  state: () => ({
    requests: [],
    totalRequests: 0,
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

    async fetchRequests(params = {}) {
      this._clearError();
      this.loading = true;
      try {
        const query = new URLSearchParams(params).toString();
        const { data } = await this._api().get(`dashboard/technical-services/requests/?${query}`);
        this.requests = data.results ?? data;
        this.totalRequests = data.count ?? data.length;
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando solicitudes de servicio.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async fetchRequest(uuid) {
      this._clearError();
      try {
        const { data } = await this._api().get(`dashboard/technical-services/requests/${uuid}/`);
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando la solicitud.';
        return null;
      }
    },

    async planRequest(uuid, { scheduledDate, scheduledTime, estimatedDurationMinutes = null, notes = '' }) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/technical-services/requests/${uuid}/plan/`, {
          scheduled_date: scheduledDate, scheduled_time: scheduledTime,
          estimated_duration_minutes: estimatedDurationMinutes, notes,
        });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al planificar la solicitud.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async assignTechnician(uuid, technicianUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/technical-services/requests/${uuid}/assign/`, {
          technician_uuid: technicianUuid,
        });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al asignar el tecnico.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async scheduleRequest(uuid, { scheduledDate, scheduledTime, estimatedDurationMinutes = null }) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/technical-services/requests/${uuid}/schedule/`, {
          scheduled_date: scheduledDate, scheduled_time: scheduledTime,
          estimated_duration_minutes: estimatedDurationMinutes,
        });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al reprogramar la solicitud.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async notifyCustomer(uuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/technical-services/requests/${uuid}/notify/`);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al notificar al cliente.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async cancelRequest(uuid, reason = '') {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/technical-services/requests/${uuid}/cancel/`, { reason });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al cancelar la solicitud.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
