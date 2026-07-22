/**
 * rentingAdmin/taxonomy.js — Pinia store para taxonomía de Renting.
 *
 * Responsabilidades: Categories, Brands, Labor (mano de obra).
 * Dividido desde rentingAdmin.js (SPRINT 4, 2026-07-16) -- ver 12_CHECKLIST_IMPLEMENTACION.md.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useRentingTaxonomyAdminStore = defineStore('rentingTaxonomyAdmin', {
  state: () => ({
    categories: [],
    brands: [],
    labor: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  getters: {
    activeCategories: (state) => state.categories.filter((c) => c.is_active),
  },

  actions: {
    _api() {
      return useApi();
    },

    // ─── Categories ───────────────────────────────────────────────────────────

    async fetchCategories() {
      try {
        const { data } = await this._api().get('dashboard/renting-categories/');
        this.categories = data.results ?? data;
        return this.categories;
      } catch (err) {
        this.error = 'Error cargando categorías.';
        return [];
      }
    },

    async createCategory(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/renting-categories/', payload);
        await this.fetchCategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear categoría.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateCategory(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/renting-categories/${uuid}/`, payload);
        await this.fetchCategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: 'Error al actualizar categoría.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Brands ───────────────────────────────────────────────────────────────

    async fetchBrands() {
      try {
        const { data } = await this._api().get('dashboard/renting-brands/');
        this.brands = data.results ?? data;
        return this.brands;
      } catch (err) {
        this.error = 'Error cargando marcas.';
        return [];
      }
    },

    async createBrand(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/renting-brands/', payload);
        await this.fetchBrands();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: 'Error al crear marca.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Labor ────────────────────────────────────────────────────────────────

    async fetchLabor() {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/rental-labor/');
        this.labor = data.results ?? data;
        return this.labor;
      } catch (err) {
        this.error = 'Error cargando mano de obra.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createLabor(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/rental-labor/', payload);
        await this.fetchLabor();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear mano de obra.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateLabor(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/rental-labor/${uuid}/`, payload);
        await this.fetchLabor();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: 'Error al actualizar mano de obra.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
