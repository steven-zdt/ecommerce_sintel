/**
 * security.js — Pinia store para el panel de Seguridad (SecurityDashboardView.vue).
 *
 * Primer incremento de la migracion a stores Pinia de los modulos admin que
 * aun usaban useApi() directo (auditoria 2026-07-23, doc 13 P1-4). Modulo
 * elegido por ser el mas chico (1 vista, 122 LOC, solo lectura) -- sirve de
 * plantilla minima del patron ya establecido en rentingAdmin/catalog.js para
 * los modulos sin mutaciones (solo GETs, sin actionLoading).
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useSecurityAdminStore = defineStore('securityAdmin', {
  state: () => ({
    events: [],
    health: { db: true, redis: true, celery: true },
    loading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    async fetchEvents(filters = {}) {
      this.error = null;
      this.loading = true;
      try {
        const params = {};
        if (filters.event_type) params.event_type = filters.event_type;
        if (filters.severity) params.severity = filters.severity;
        const { data } = await this._api().get('dashboard/security-events/', { params });
        this.events = data.results ?? data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando eventos de seguridad.';
        this.events = [];
      } finally {
        this.loading = false;
      }
    },

    async fetchHealth() {
      try {
        const { data } = await this._api().get('dashboard/security-events/health/');
        this.health = data;
      } catch {
        this.health = { db: false, redis: false, celery: false };
      }
    },
  },
});
