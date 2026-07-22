import { defineStore } from 'pinia';

const blank = () => ({
  order:          null, // ServiceOrderSerializer payload (uuid, total_amount, service_detail, items, ...)
  serviceName:    '',
  variantSku:     '',
  priceInfo:      null, // price_info del variant seleccionado (labor_cost/material_cost/iva.../total)
  technicianName: '',
  durationHours:  null,
  phase:          'summary',  // summary | method | status
  paymentMethod:  'WOMPI',    // WOMPI | NEQUI | COD
  nequiPhone:     '',
  paymentStatus:  null,       // processing | approved | declined | pending | expired | cancelled
  txUuid:         '',
  wompiId:        '',
  pollTimedOut:   false,
});

export const useServiceCheckoutStore = defineStore('serviceCheckout', {
  state: () => ({ open: false, ...blank() }),
  actions: {
    openFor({ order, serviceName, variantSku, priceInfo, technicianName, durationHours }) {
      Object.assign(this.$state, blank());
      this.order          = order;
      this.serviceName     = serviceName || '';
      this.variantSku       = variantSku || '';
      this.priceInfo         = priceInfo || null;
      this.technicianName     = technicianName || '';
      this.durationHours       = durationHours ?? null;
      this.open = true;
    },
    setPhase(phase) { this.phase = phase; },
    setPaymentStatus(status, { txUuid = '', wompiId = '', pollTimedOut = false } = {}) {
      this.paymentStatus = status;
      if (txUuid) this.txUuid = txUuid;
      if (wompiId) this.wompiId = wompiId;
      this.pollTimedOut = pollTimedOut;
    },
    close() {
      this.open = false;
    },
    reset() {
      Object.assign(this.$state, { open: false, ...blank() });
    },
  },
});
