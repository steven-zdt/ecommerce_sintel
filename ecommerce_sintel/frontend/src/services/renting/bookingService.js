import useApi from '@/composables/useApi';

export const bookingService = {
  equipment(uuid) { return useApi().get(`renting/equipment/${uuid}/`).then(r => r.data); },
  create(payload) { return useApi().post('renting/rental-requests/', payload).then(r => r.data); },
  list(params = {}) { return useApi().get('renting/rental-requests/', { params }).then(r => r.data); },
  detail(uuid) { return useApi().get(`renting/rental-requests/${uuid}/`).then(r => r.data); },
  update(uuid, payload) { return useApi().patch(`renting/rental-requests/${uuid}/`, payload).then(r => r.data); },
  uploadAttachments(uuid, files) {
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    return useApi().post(`renting/rental-requests/${uuid}/attachments/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
};
