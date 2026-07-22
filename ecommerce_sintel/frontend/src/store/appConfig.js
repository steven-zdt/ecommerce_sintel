import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useAppConfigStore = defineStore('appConfig', {
  state: () => ({
    brand: { site_name: 'Sintel', logo: null, tagline: '', uuid: null },
    navbarLinks: [],
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
        this.loaded = true;
      } catch {
        // usa defaults si la API falla
      }
    },

    reset() {
      this.brand = { site_name: 'Sintel', logo: null, tagline: '', uuid: null };
      this.navbarLinks = [];
      this.loaded = false;
    },
  },
});
