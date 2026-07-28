import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useWishlistStore = defineStore('wishlist', {
  state: () => ({
    items: [],
    loaded: false,
    loading: false,
  }),

  getters: {
    isInWishlist: (state) => (variantUuid) =>
      state.items.some((i) => i.variant_uuid === variantUuid),
    findByVariant: (state) => (variantUuid) =>
      state.items.find((i) => i.variant_uuid === variantUuid),
  },

  actions: {
    async fetchWishlist() {
      const api = useApi();
      this.loading = true;
      try {
        const res = await api.get('cart/wishlist/');
        this.items = res.data?.results ?? res.data ?? [];
        this.loaded = true;
      } catch (e) {
        this.items = [];
        this.loaded = false;
        throw e;
      } finally {
        this.loading = false;
      }
    },

    async add(variantUuid) {
      const api = useApi();
      const res = await api.post('cart/wishlist/', { variant_uuid: variantUuid });
      this.items.push(res.data);
      return res.data;
    },

    async remove(itemUuid) {
      const api = useApi();
      await api.delete(`cart/wishlist/${itemUuid}/`);
      this.items = this.items.filter((i) => i.uuid !== itemUuid);
    },

    async toggle(variantUuid) {
      const existing = this.findByVariant(variantUuid);
      if (existing) {
        await this.remove(existing.uuid);
        return false;
      }
      await this.add(variantUuid);
      return true;
    },

    reset() {
      this.items = [];
      this.loaded = false;
      this.loading = false;
    },
  },
});
