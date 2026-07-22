import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

/**
 * Notificaciones recientes del usuario autenticado (admin o cliente, mismo
 * modelo de datos -- NotificationLog es un log personal, no un feed de
 * negocio aparte). Alimenta la campana del navbar.
 */
export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    recent: [],
    loading: false,
    lastOpenedAt: null,
  }),
  getters: {
    unseenCount(state) {
      if (!state.lastOpenedAt) return state.recent.length;
      return state.recent.filter(n => new Date(n.created_at) > state.lastOpenedAt).length;
    },
  },
  actions: {
    async fetchRecent() {
      this.loading = true;
      try {
        const api = useApi();
        const { data } = await api.get('notifications/logs/', { params: { page_size: 5 } });
        this.recent = data.results || data;
      } catch (_) {
        this.recent = [];
      } finally {
        this.loading = false;
      }
    },
    markOpened() {
      this.lastOpenedAt = new Date();
    },
  },
});
