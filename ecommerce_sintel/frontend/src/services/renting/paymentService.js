import useApi from '@/composables/useApi';

export const paymentService = {
  process(uuid, payload) {
    return useApi().post(`renting/rental-requests/${uuid}/process-payment/`, payload).then(r => r.data);
  },
};
