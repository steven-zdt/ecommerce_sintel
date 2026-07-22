import useApi from '@/composables/useApi';

export const servicesService = {
  list(params = {}) {
    return useApi().get('services/services/', { params }).then(r => r.data);
  },
  categories() {
    return useApi().get('services/categories/').then(r => r.data);
  },
  levels() {
    return useApi().get('services/levels/').then(r => r.data);
  },
  detail(uuid) {
    return useApi().get(`services/services/${uuid}/`).then(r => r.data);
  },
  packages(uuid) {
    return useApi().get(`services/services/${uuid}/packages/`).then(r => r.data);
  },
  createOrder(payload) {
    return useApi().post('orders/service-orders/', payload).then(r => r.data);
  },
  uploadAttachment(orderUuid, file, docType = '') {
    const fd = new FormData();
    fd.append('file', file);
    if (docType) fd.append('doc_type', docType);
    return useApi().post(`orders/service-orders/${orderUuid}/attachments/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
};
