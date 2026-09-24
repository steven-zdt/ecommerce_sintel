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
        const data = await action();
        return { ok: true, data };
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

    // Fase 11-14 (2026-09-23): galeria de media. No tocan this.campaigns -- CampaignForm.vue
    // maneja su propio estado local de galeria (mismo criterio que items/benefits, que ya son
    // locales al formulario, ver docstring de marketingAdmin.js arriba).
    uploadCampaignMedia(campaignUuid, file, mediaType) {
      return this._mutate(() => marketingService.uploadCampaignMedia(campaignUuid, file, mediaType));
    },

    deleteCampaignMedia(campaignUuid, mediaUuid) {
      return this._mutate(() => marketingService.deleteCampaignMedia(campaignUuid, mediaUuid));
    },

    toggleCampaignMedia(campaignUuid, mediaUuid) {
      return this._mutate(() => marketingService.toggleCampaignMedia(campaignUuid, mediaUuid));
    },

    reorderCampaignMedia(campaignUuid, orderedUuids) {
      return this._mutate(() => marketingService.reorderCampaignMedia(campaignUuid, orderedUuids));
    },

    // Fase 17/22 (2026-09-24): preview y envio manual (endpoints preview/ y send/).
    previewCampaign(uuid) {
      return this._mutate(() => marketingService.previewCampaign(uuid));
    },

    sendCampaign(uuid, recipient) {
      return this._mutate(() => marketingService.sendCampaign(uuid, recipient));
    },
  },
});
