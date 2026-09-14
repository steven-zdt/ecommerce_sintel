import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

// White-label F4 (2026-08-14): mapeo minimo tema->CSS custom properties.
// Solo sobreescribe las que el backend trae con valor -- '' se ignora, deja
// el default estatico de landing-design-system.css tal cual (fail-open, sin
// tocar visualmente Sintel hasta que un admin configure colores propios).
// No deriva variantes strong/soft (requeriria color math) -- gap conocido,
// ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_ARCHITECTURE_TARGET.md Fase 28.
const THEME_CSS_VAR_MAP = {
  primary_color: '--landing-primary',
  accent_color: '--landing-accent',
};

function applyTheme(theme) {
  if (!theme || typeof document === 'undefined') return;
  for (const [key, cssVar] of Object.entries(THEME_CSS_VAR_MAP)) {
    if (theme[key]) {
      document.documentElement.style.setProperty(cssVar, theme[key]);
    }
  }
}

export const useAppConfigStore = defineStore('appConfig', {
  state: () => ({
    brand: { site_name: '', logo: null, tagline: '', uuid: null },
    navbarLinks: [],
    // White-label F3 (2026-08-14): visibilidad de las 4 verticales core, consumido
    // por el guard de router en apps/admin/router.js. [] = "sin dato todavia" ->
    // el guard no oculta nada (fail-open) mientras el fetch esta en curso o si falla.
    modules: [],
    loaded: false,
  }),

  actions: {
    async fetchConfig() {
      if (this.loaded) return;
      const api = useApi();
      try {
        const res = await api.get('core/site-config/');
        this.brand = res.data.brand ?? this.brand;
        this.navbarLinks = res.data.navbar_links ?? [];
        this.modules = res.data.modules ?? [];
        applyTheme(res.data.theme);
        this.loaded = true;
      } catch {
        // usa defaults si la API falla
      }
    },

    reset() {
      this.brand = { site_name: '', logo: null, tagline: '', uuid: null };
      this.navbarLinks = [];
      this.modules = [];
      this.loaded = false;
    },
  },
});
