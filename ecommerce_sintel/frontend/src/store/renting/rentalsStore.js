import { defineStore } from 'pinia';
import { bookingService } from '@/services/renting/bookingService';

export const useRentalsStore = defineStore('customerRentals', {
  state: () => ({ items: [], loading: false, error: '' }),
  actions: {
    async fetch() {
      this.loading = true; this.error = '';
      try { const data = await bookingService.list(); this.items = data.results || data || []; }
      catch { this.error = 'No pudimos cargar tus alquileres.'; }
      finally { this.loading = false; }
    },
  },
});
