/**
 * orderStore.js — Pinia store para el módulo administrativo de órdenes.
 */
import { defineStore } from 'pinia';
import { fetchOrder, fetchOrderTimeline } from '@/modules/orders/services/orderService';

export const useOrderStore = defineStore('orderStore', {
  state: () => ({
    order: null,
    timeline: [],
    loadingOrder: false,
    loadingTimeline: false,
    error: null,
  }),

  actions: {
    async loadOrder(uuid) {
      this.loadingOrder = true;
      this.error = null;
      try {
        const { data } = await fetchOrder(uuid);
        this.order = data;
        return data;
      } catch (err) {
        this.error = err;
        this.order = null;
        throw err;
      } finally {
        this.loadingOrder = false;
      }
    },

    async loadTimeline(uuid) {
      this.loadingTimeline = true;
      try {
        const { data } = await fetchOrderTimeline(uuid);
        this.timeline = Array.isArray(data) ? data : [];
        return this.timeline;
      } catch (err) {
        this.error = err;
        this.timeline = [];
        throw err;
      } finally {
        this.loadingTimeline = false;
      }
    },

    reset() {
      this.order = null;
      this.timeline = [];
      this.error = null;
      this.loadingOrder = false;
      this.loadingTimeline = false;
    },
  },
});
