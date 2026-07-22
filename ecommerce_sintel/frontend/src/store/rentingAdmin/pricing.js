/**
 * rentingAdmin/pricing.js — Pinia store para Reglas de Costo de Renting.
 *
 * Dividido desde rentingAdmin.js (SPRINT 4, 2026-07-16) -- ver 12_CHECKLIST_IMPLEMENTACION.md.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useRentingPricingAdminStore = defineStore('rentingPricingAdmin', {
  state: () => ({
    costRules: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    // Regla arquitectonica: NO existen reglas globales en Renting -- el
    // listado SIEMPRE se filtra por equipo, nunca se pide el catalogo completo.
    async fetchCostRules(equipmentUuid) {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/rental-cost-rules/', {
          params: { equipment: equipmentUuid },
        });
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
        const { data } = await this._api().post('dashboard/rental-cost-rules/', payload);
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
        const { data } = await this._api().patch(`dashboard/rental-cost-rules/${uuid}/update/`, payload);
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
        await this._api().post(`dashboard/rental-cost-rules/${uuid}/deactivate/`);
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
          `dashboard/rental-cost-rules/${ruleUuid}/assign/`,
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
