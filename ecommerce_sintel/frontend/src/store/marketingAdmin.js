/**
 * marketingAdmin.js — Pinia store para el panel de Marketing
 * (MarketingView.vue: campañas/ofertas flash/agente IA; CampaignForm.vue:
 * crear/editar campaña).
 *
 * Septimo incremento de la migracion a stores Pinia de modulos admin
 * (auditoria 2026-07-23, doc 13 P1-4). Delega en la capa de servicio ya
 * existente (`services/marketing/marketingService.js`), mismo criterio que
 * ordersAdmin.js. `AgentRunDetail.vue` no se toco -- es un componente de
 * solo display (recibe `run` como prop, sin llamadas a la API).
 *
 * Los datos del formulario de campana (VeeValidate, via useFormValidation)
 * quedan locales al componente -- son un borrador de edicion, no datos de
 * servidor.
 */
import { defineStore } from 'pinia';
import { marketingService } from '@/services/marketing/marketingService';

export const useMarketingAdminStore = defineStore('marketingAdmin', {
  state: () => ({
    campaigns: [],
    offers: [],
    agentRuns: [],
    loading: false,

    actionLoading: false,
    error: null,
  }),

  actions: {
    async fetchAll() {
      this.loading = true;
      try {
        const [campData, offerData, agentData] = await Promise.all([
          marketingService.campaigns(),
          marketingService.offers(),
          marketingService.agentRuns(),
        ]);
        this.campaigns = campData.results ?? campData;
        this.offers = offerData.results ?? offerData;
        this.agentRuns = agentData.results ?? agentData;
      } catch {
        this.error = 'Error al cargar datos de marketing.';
      } finally {
        this.loading = false;
      }
    },

    async _mutate(action) {
      this.actionLoading = true;
      try {
        await action();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    createCampaign(payload) {
      return this._mutate(() => marketingService.createCampaign(payload));
    },

    updateCampaign(uuid, payload) {
      return this._mutate(() => marketingService.updateCampaign(uuid, payload));
    },

    async deleteCampaign(uuid) {
      try {
        await marketingService.deleteCampaign(uuid);
        this.campaigns = this.campaigns.filter((c) => c.uuid !== uuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      }
    },
  },
});
