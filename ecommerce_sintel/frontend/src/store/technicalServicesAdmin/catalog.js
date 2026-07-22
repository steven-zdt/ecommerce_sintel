/**
 * technicalServicesAdmin/catalog.js — Pinia store para la taxonomia de
 * Technical Services: Categorias, Niveles y Reglas de Costo.
 *
 * Dividido desde technicalServicesAdmin.js (SPRINT 4, 2026-07-16) -- ver
 * 12_CHECKLIST_IMPLEMENTACION.md.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useTechnicalServicesCatalogStore = defineStore('technicalServicesCatalog', {
  state: () => ({
    categories: [],
    levels: [],
    costRules: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  getters: {
    activeCategories: (state) => state.categories.filter((c) => c.is_active),
    globalCostRules: (state) => state.costRules.filter((r) => r.applies_globally),
  },

  actions: {
    _api() {
      return useApi();
    },

    // ─── Categories ────────────────────────────────────────────────────────────

    async fetchCategories() {
      try {
        const { data } = await this._api().get('dashboard/service-categories/');
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
        const { data } = await this._api().post('dashboard/service-categories/', payload);
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
        const { data } = await this._api().patch(`dashboard/service-categories/${uuid}/`, payload);
        await this.fetchCategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: 'Error al actualizar categoría.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteCategory(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/service-categories/${uuid}/`);
        await this.fetchCategories();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: 'Error al eliminar categoría.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Levels ────────────────────────────────────────────────────────────────

    async fetchLevels() {
      try {
        const { data } = await this._api().get('dashboard/service-levels/');
        this.levels = data.results ?? data;
        return this.levels;
      } catch (err) {
        this.error = 'Error cargando niveles de servicio.';
        return [];
      }
    },

    async createLevel(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/service-levels/', payload);
        await this.fetchLevels();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear nivel.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateLevel(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/service-levels/${uuid}/`, payload);
        await this.fetchLevels();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar nivel.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteLevel(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/service-levels/${uuid}/`);
        await this.fetchLevels();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar nivel.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Cost Rules ────────────────────────────────────────────────────────────

    async fetchCostRules() {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/service-cost-rules/');
        this.costRules = data.results ?? data;
        return this.costRules;
      } catch (err) {
        this.error = 'Error cargando reglas de costo.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createCostRule(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/service-cost-rules/', payload);
        await this.fetchCostRules();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear regla de costo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateCostRule(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/service-cost-rules/${uuid}/update/`, payload);
        await this.fetchCostRules();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: 'Error al actualizar regla de costo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deactivateCostRule(uuid) {
      this.actionLoading = true;
      try {
        await this._api().post(`dashboard/service-cost-rules/${uuid}/deactivate/`);
        await this.fetchCostRules();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: 'Error al desactivar regla.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async assignCostRule(ruleUuid, variantUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(
          `dashboard/service-cost-rules/${ruleUuid}/assign/`,
          { variant_uuid: variantUuid }
        );
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al asignar regla.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
