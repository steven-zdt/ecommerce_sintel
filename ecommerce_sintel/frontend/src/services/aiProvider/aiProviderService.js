import useApi from '@/composables/useApi';

export const aiProviderService = {
  listProviders() {
    return useApi().get('dashboard/ai-providers/').then(r => r.data);
  },
  createProvider(payload) {
    return useApi().post('dashboard/ai-providers/', payload).then(r => r.data);
  },
  updateProvider(uuid, payload) {
    return useApi().patch(`dashboard/ai-providers/${uuid}/`, payload).then(r => r.data);
  },
  deleteProvider(uuid) {
    return useApi().delete(`dashboard/ai-providers/${uuid}/`).then(r => r.data);
  },
  testConnection(uuid) {
    return useApi().post(`dashboard/ai-providers/${uuid}/test-connection/`).then(r => r.data);
  },
  discoverModels(uuid) {
    return useApi().get(`dashboard/ai-providers/${uuid}/discover-models/`).then(r => r.data);
  },
  addModel(providerUuid, payload) {
    return useApi().post(`dashboard/ai-providers/${providerUuid}/models/`, payload).then(r => r.data);
  },
  deleteModel(providerUuid, modelUuid) {
    return useApi().delete(`dashboard/ai-providers/${providerUuid}/models/${modelUuid}/`).then(r => r.data);
  },
  getChannelConfig(channel = 'support_chat') {
    return useApi().get('dashboard/ai-channel-config/', { params: { channel } }).then(r => r.data);
  },
  setPrimary(modelUuid, channel = 'support_chat') {
    return useApi().post('dashboard/ai-channel-config/set-primary/', { model_uuid: modelUuid, channel }).then(r => r.data);
  },
  setFallbackChain(modelUuids, channel = 'support_chat') {
    return useApi().post('dashboard/ai-channel-config/set-fallback-chain/', { model_uuids: modelUuids, channel }).then(r => r.data);
  },
};
