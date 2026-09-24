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
  // Fase 11-14 (2026-09-23): galeria de media -- mismo patron FormData que
  // technical_services/servicesService.js (attachments de ordenes de servicio).
  uploadCampaignMedia(campaignUuid, file, mediaType) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('media_type', mediaType);
    return useApi().post(`marketing/campaigns/${campaignUuid}/media/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  deleteCampaignMedia(campaignUuid, mediaUuid) {
    return useApi().delete(`marketing/campaigns/${campaignUuid}/media/${mediaUuid}/`).then(r => r.data);
  },
  toggleCampaignMedia(campaignUuid, mediaUuid) {
    return useApi().post(`marketing/campaigns/${campaignUuid}/media/${mediaUuid}/toggle/`).then(r => r.data);
  },
  reorderCampaignMedia(campaignUuid, orderedUuids) {
    return useApi().post(`marketing/campaigns/${campaignUuid}/media/reorder/`, { ordered_uuids: orderedUuids }).then(r => r.data);
  },
  // Fase 17/22 (2026-09-24): preview real por canal y envio manual.
  previewCampaign(uuid) {
    return useApi().get(`marketing/campaigns/${uuid}/preview/`).then(r => r.data);
  },
  sendCampaign(uuid, recipient) {
    return useApi().post(`marketing/campaigns/${uuid}/send/`, recipient ? { recipient } : {}).then(r => r.data);
  },
};
