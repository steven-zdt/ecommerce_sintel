/**
 * auth.js — Pinia store para autenticación JWT
 *
 * Responsabilidades:
 * - Persistir access/refresh tokens en localStorage (o sessionStorage si el
 *   usuario no marco "Recordarme" en el login -- ver setTokens/setUser)
 * - Guardar datos del usuario autenticado
 * - Exponer helpers de rol (isAdmin, isCustomer)
 */
import { defineStore } from 'pinia';

// "Recordarme": localStorage persiste entre cierres del navegador, sessionStorage
// se limpia al cerrar la pestaña/ventana. Por defecto (remember=true) se mantiene
// el comportamiento historico (siempre localStorage).
function readPersisted(key) {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: readPersisted('sintel_access') || null,
    refreshToken: readPersisted('sintel_refresh') || null,
    user: JSON.parse(readPersisted('sintel_user') || 'null'),
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    isAdmin: (state) => state.user?.is_staff === true,
    isCustomer: (state) => !!state.user && state.user.is_staff !== true,
    fullName: (state) => {
      if (!state.user) return '';
      const first = state.user.first_name || '';
      const last = state.user.last_name || '';
      return `${first} ${last}`.trim() || state.user.email;
    },
    initials: (state) => {
      if (!state.user?.email) return '?';
      return state.user.email[0].toUpperCase();
    },
  },

  actions: {
    setTokens({ access, refresh }, remember = true) {
      this.accessToken = access;
      this.refreshToken = refresh;
      const storage = remember ? localStorage : sessionStorage;
      storage.setItem('sintel_access', access);
      if (refresh) storage.setItem('sintel_refresh', refresh);
      // Si se cambia de storage (ej. login previo sin "Recordarme"), limpiar el otro.
      const other = remember ? sessionStorage : localStorage;
      other.removeItem('sintel_access');
      other.removeItem('sintel_refresh');
    },

    setUser(userData, remember = true) {
      this.user = userData;
      const storage = remember ? localStorage : sessionStorage;
      storage.setItem('sintel_user', JSON.stringify(userData));
      const other = remember ? sessionStorage : localStorage;
      other.removeItem('sintel_user');
    },

    logout() {
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      localStorage.removeItem('sintel_access');
      localStorage.removeItem('sintel_refresh');
      localStorage.removeItem('sintel_user');
      sessionStorage.removeItem('sintel_access');
      sessionStorage.removeItem('sintel_refresh');
      sessionStorage.removeItem('sintel_user');
    },
  },
});
