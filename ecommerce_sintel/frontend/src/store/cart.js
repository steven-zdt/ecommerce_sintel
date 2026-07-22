import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [],
    totalFromApi: '0.00',
    totalItemsFromApi: 0,
    loading: false,
  }),

  getters: {
    itemCount: (state) =>
      state.totalItemsFromApi || state.items.reduce((sum, i) => sum + (i.quantity || 0), 0),
    total: (state) =>
      parseFloat(state.totalFromApi) ||
      state.items.reduce((sum, i) => sum + parseFloat(i.final_price || i.subtotal || 0), 0),
    isEmpty: (state) => state.items.length === 0,
  },

  actions: {
    async fetchCart() {
      const api = useApi();
      this.loading = true;
      try {
        const res = await api.get('cart/');
        this.items = res.data?.items ?? res.data ?? [];
        this.totalFromApi = res.data?.total ?? res.data?.total_cart_value ?? '0.00';
        this.totalItemsFromApi = res.data?.total_items ?? 0;
      } catch {
        this.items = [];
      } finally {
        this.loading = false;
      }
    },

    async addItem(variantUuid, quantity = 1) {
      const api = useApi();
      await api.post('cart/add_item/', { variant_uuid: variantUuid, quantity });
      await this.fetchCart();
    },

    async addServiceItem(serviceVariantUuid, quantity = 1) {
      const api = useApi();
      await api.post('cart/add_item/', { service_variant_uuid: serviceVariantUuid, quantity });
      await this.fetchCart();
    },

    async updateQuantity(variantUuid, serviceVariantUuid, quantity) {
      const api = useApi();
      const payload = { quantity };
      if (variantUuid) payload.variant_uuid = variantUuid;
      if (serviceVariantUuid) payload.service_variant_uuid = serviceVariantUuid;
      await api.post('cart/update_item/', payload);
      await this.fetchCart();
    },

    async removeItem(itemUuid) {
      const api = useApi();
      await api.post(`cart/remove-item/${itemUuid}/`);
      await this.fetchCart();
    },

    async clearCart() {
      const api = useApi();
      await api.post('cart/clear/');
      this.items = [];
      this.totalFromApi = '0.00';
      this.totalItemsFromApi = 0;
    },

    reset() {
      this.items = [];
      this.totalFromApi = '0.00';
      this.totalItemsFromApi = 0;
      this.loading = false;
    },
  },
});
