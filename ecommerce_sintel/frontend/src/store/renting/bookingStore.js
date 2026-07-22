import { defineStore } from 'pinia';

const KEY = 'sintel:rental-booking:v2';
const blank = () => ({
  variantUuid: '',
  project: {
    address: '', city: '', department: '', neighborhood: '',
    roadType: 'Calle', roadNumber: '', roadSuffix: '', generator: '', plate: '', complement: '',
    projectType: '', company: '', activity: '', notes: '', conditions: [],
  },
  schedule: { startDate: '', endDate: '', quantity: 1, mode: 'days', deliveryTime: '', pickupTime: '', priority: 'LOW' },
  customer: { fullName: '', docType: 'CC', docNumber: '', email: '', phone: '' },
  termsAccepted: false,
});

export const useBookingStore = defineStore('rentalBooking', {
  state: () => ({ draft: blank(), step: 1, created: null }),
  actions: {
    restore() {
      try {
        const saved = JSON.parse(localStorage.getItem(KEY)) || {};
        if (saved.draft) {
          Object.assign(this.draft, saved.draft);
          Object.assign(this.draft.project, saved.draft.project || {});
          Object.assign(this.draft.schedule, saved.draft.schedule || {});
          Object.assign(this.draft.customer, saved.draft.customer || {});
        }
        if (saved.step >= 1 && saved.step <= 4) this.step = saved.step;
      } catch { /* El borrador es una mejora progresiva. */ }
    },
    persist() { localStorage.setItem(KEY, JSON.stringify({ draft: this.draft, step: this.step })); },
    clear() { this.draft = blank(); this.step = 1; this.created = null; localStorage.removeItem(KEY); },
  },
});
