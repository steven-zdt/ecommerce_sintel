/**
 * aiProviderAdmin.js — Pinia store del panel de Proveedores de IA
 * (/panel/soporte/ia-config, plan maestro "CONFIGURACION DINAMICA DE MODELOS
 * LOCALES PARA CHAT SUPPORT", FASE 5, 2026-08-13). Mismo patron que
 * marketingAdmin.js (loading/actionLoading, _mutate helper, delega en la capa
 * de servicio).
 */
import { defineStore } from 'pinia';
import { aiProviderService } from '@/services/aiProvider/aiProviderService';

export const useAIProviderAdminStore = defineStore('aiProviderAdmin', {
  state: () => ({
    providers: [],
    channelConfig: null,
    mcpServers: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  actions: {
    async fetchAll() {
      this.loading = true;
      try {
        const [providers, channelConfig] = await Promise.all([
          aiProviderService.listProviders(),
          aiProviderService.getChannelConfig(),
        ]);
        this.providers = providers;
        this.channelConfig = channelConfig;
      } catch {
        this.error = 'Error al cargar proveedores de IA.';
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

    async createProvider(payload) {
      const res = await this._mutate(() => aiProviderService.createProvider(payload));
      if (res.ok) this.providers.push(res.data);
      return res;
    },

    async updateProvider(uuid, payload) {
      const res = await this._mutate(() => aiProviderService.updateProvider(uuid, payload));
      if (res.ok) {
        const idx = this.providers.findIndex((p) => p.uuid === uuid);
        if (idx !== -1) this.providers[idx] = res.data;
      }
      return res;
    },

    async deleteProvider(uuid) {
      const res = await this._mutate(() => aiProviderService.deleteProvider(uuid));
      if (res.ok) this.providers = this.providers.filter((p) => p.uuid !== uuid);
      return res;
    },

    async testConnection(uuid) {
      const res = await this._mutate(() => aiProviderService.testConnection(uuid));
      if (res.ok) {
        const idx = this.providers.findIndex((p) => p.uuid === uuid);
        if (idx !== -1) this.providers[idx] = res.data;
      }
      return res;
    },

    async discoverModels(uuid) {
      return this._mutate(() => aiProviderService.discoverModels(uuid));
    },

    async addModel(providerUuid, payload) {
      const res = await this._mutate(() => aiProviderService.addModel(providerUuid, payload));
      if (res.ok) {
        const provider = this.providers.find((p) => p.uuid === providerUuid);
        if (provider) provider.models.push(res.data);
      }
      return res;
    },

    async deleteModel(providerUuid, modelUuid) {
      const res = await this._mutate(() => aiProviderService.deleteModel(providerUuid, modelUuid));
      if (res.ok) {
        const provider = this.providers.find((p) => p.uuid === providerUuid);
        if (provider) provider.models = provider.models.filter((m) => m.uuid !== modelUuid);
      }
      return res;
    },

    // El backend valida el modelo (conectividad + disponibilidad) antes de activarlo. Si falla responde 409 con `report`;
    // el llamador puede reintentar con force=true tras confirmar con el admin.
    async setPrimary(modelUuid, force = false) {
      const res = await this._mutate(() => aiProviderService.setPrimary(modelUuid, 'support_chat', force));
      if (res.ok) this.channelConfig = res.data;
      return res;
    },

    async validateModel(modelUuid) {
      return this._mutate(() => aiProviderService.validateModel(modelUuid));
    },

    // PLAN_LLMDINAMICO sec. 16: "Probar conexion"/"Salud" persisten el estado; la fila del proveedor se refresca con el resultado.
    async checkHealth(uuid) {
      const res = await this._mutate(() => aiProviderService.checkHealth(uuid));
      if (res.ok) {
        const fresh = await aiProviderService.listProviders();
        this.providers = fresh;
      }
      return res;
    },

    async updateModelSettings(providerUuid, modelUuid, payload) {
      const res = await this._mutate(() => aiProviderService.updateModelSettings(providerUuid, modelUuid, payload));
      if (res.ok) {
        const provider = this.providers.find((p) => p.uuid === providerUuid);
        const idx = provider ? provider.models.findIndex((m) => m.uuid === modelUuid) : -1;
        if (idx !== -1) provider.models[idx] = res.data;
      }
      return res;
    },

    async detectCapabilities(providerUuid, modelUuid) {
      const res = await this._mutate(() => aiProviderService.detectCapabilities(providerUuid, modelUuid));
      if (res.ok) {
        const provider = this.providers.find((p) => p.uuid === providerUuid);
        const idx = provider ? provider.models.findIndex((m) => m.uuid === modelUuid) : -1;
        if (idx !== -1) provider.models[idx] = res.data;
      }
      return res;
    },

    async fetchProviderHistory(uuid) {
      return this._mutate(() => aiProviderService.getProviderHistory(uuid));
    },

    async rollbackProvider(uuid, version) {
      const res = await this._mutate(() => aiProviderService.rollbackProvider(uuid, version));
      if (res.ok) {
        const idx = this.providers.findIndex((p) => p.uuid === uuid);
        if (idx !== -1) this.providers[idx] = res.data;
      }
      return res;
    },

    async fetchMcpServers() {
      const res = await this._mutate(() => aiProviderService.listMcpServers());
      if (res.ok) this.mcpServers = res.data;
      return res;
    },

    async saveMcpServer(uuid, payload) {
      const res = await this._mutate(() => (uuid
        ? aiProviderService.updateMcpServer(uuid, payload)
        : aiProviderService.createMcpServer(payload)));
      if (res.ok) await this.fetchMcpServers();
      return res;
    },

    async deleteMcpServer(uuid) {
      const res = await this._mutate(() => aiProviderService.deleteMcpServer(uuid));
      if (res.ok) this.mcpServers = this.mcpServers.filter((s) => s.uuid !== uuid);
      return res;
    },

    async testMcpServer(uuid) {
      const res = await this._mutate(() => aiProviderService.testMcpServer(uuid));
      if (res.ok) await this.fetchMcpServers();
      return res;
    },

    async fetchChannelHistory() {
      return this._mutate(() => aiProviderService.getChannelHistory());
    },

    async rollbackChannel(version) {
      const res = await this._mutate(() => aiProviderService.rollbackChannel(version));
      if (res.ok) {
        this.channelConfig = res.data;
        // Restaurar un canal puede reactivar proveedores/modelos: recargar la lista para mostrar el estado real.
        this.providers = await aiProviderService.listProviders();
      }
      return res;
    },

    async setFallbackChain(modelUuids) {
      const res = await this._mutate(() => aiProviderService.setFallbackChain(modelUuids));
      if (res.ok) this.channelConfig = res.data;
      return res;
    },
  },
});
