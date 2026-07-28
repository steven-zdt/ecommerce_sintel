import { defineStore } from 'pinia';
import { availabilityService } from '@/services/renting/availabilityService';
import { extractErrorMessage } from '@/composables/useErrorHandler';

const FALLBACK = 'No pudimos verificar la disponibilidad.';

export const useAvailabilityStore = defineStore('rentalAvailability', {
  state: () => ({ checking: false, result: null, error: '' }),
  actions: {
    async check(uuid, params) {
      this.checking = true; this.error = '';
      try { this.result = await availabilityService.check(uuid, params); return this.result; }
      catch (error) { this.error = extractErrorMessage(error, FALLBACK); throw error; }
      finally { this.checking = false; }
    },
    async fetchAvailability(uuid, params) {
      this.checking = true; this.error = '';
      try { this.result = await availabilityService.get(uuid, params); return this.result; }
      catch (error) { this.error = extractErrorMessage(error, FALLBACK); throw error; }
      finally { this.checking = false; }
    },
  },
});
