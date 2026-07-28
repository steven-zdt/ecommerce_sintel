/**
 * notificationsAdmin.js — Pinia store para el panel de Notificaciones admin
 * (NotificationsAdminView.vue: plantillas + logs de envio).
 *
 * No confundir con store/notifications.js (useNotificationsStore) -- ese es
 * el feed personal de la campana del navbar (NotificationLog del usuario
 * autenticado), un dominio completamente distinto que ya existia con ese
 * nombre. Este store es para el CRUD de plantillas + logs de TODOS los
 * envios, solo visible en el panel admin.
 *
 * Segundo incremento de la migracion a stores Pinia de modulos admin (auditoria
 * 2026-07-23, doc 13 P1-4; primer incremento fue store/security.js).
 *
 * Dos recursos de lectura independientes (templates/logs, cada uno en su
 * propia pestana) mantienen loading flags separados a proposito -- un solo
 * flag compartido parpadearia de forma incorrecta ya que ambos se cargan en
 * paralelo al montar la vista (si uno termina antes que el otro, un flag
 * unico ocultaria el spinner del que todavia esta cargando).
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useNotificationsAdminStore = defineStore('notificationsAdmin', {
  state: () => ({
    templates: [],
    templatesLoading: false,

    logs: [],
    logsTotalCount: 0,
    logsPagination: { next: null, previous: null },
    logsLoading: false,

    actionLoading: false,
    error: null,
  }),

  getters: {
    logsTotalPages: (state) => Math.ceil(state.logsTotalCount / 25),
  },

  actions: {
    _api() {
      return useApi();
    },

    async fetchTemplates() {
      this.templatesLoading = true;
      try {
        const { data } = await this._api().get('dashboard/notification-templates/');
        this.templates = data.results ?? data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error al cargar las plantillas';
      } finally {
        this.templatesLoading = false;
      }
    },

    async updateTemplate(uuid, payload) {
      this.actionLoading = true;
      try {
        await this._api().patch(`dashboard/notification-templates/${uuid}/`, payload);
        await this.fetchTemplates();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    async fetchLogs(page = 1, filters = {}) {
      this.logsLoading = true;
      try {
        const params = { page };
        if (filters.status) params.status = filters.status;
        if (filters.channel) params.channel = filters.channel;
        if (filters.template_slug) params.template_slug = filters.template_slug;
        const { data } = await this._api().get('dashboard/notification-logs/', { params });
        this.logs = data.results ?? data;
        this.logsTotalCount = data.count ?? this.logs.length;
        this.logsPagination = { next: data.next, previous: data.previous };
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error al cargar los logs';
      } finally {
        this.logsLoading = false;
      }
    },
  },
});
