import useApi from '@/composables/useApi';

export const marketingService = {
  dashboard() {
    return useApi().get('marketing/dashboard/').then(r => r.data);
  },
  campaigns() {
    return useApi().get('marketing/campaigns/').then(r => r.data);
  },
  offers() {
    return useApi().get('marketing/offers/').then(r => r.data);
  },
  agentRuns() {
    return useApi().get('marketing/agent-runs/').then(r => r.data);
  },
  createCampaign(payload) {
    return useApi().post('marketing/campaigns/', payload).then(r => r.data);
  },
  updateCampaign(uuid, payload) {
    return useApi().patch(`marketing/campaigns/${uuid}/`, payload).then(r => r.data);
  },
  deleteCampaign(uuid) {
    return useApi().delete(`marketing/campaigns/${uuid}/`).then(r => r.data);
  },
};
