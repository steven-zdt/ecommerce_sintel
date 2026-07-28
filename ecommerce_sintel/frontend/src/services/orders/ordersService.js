import useApi from '@/composables/useApi';

export const ordersService = {
  list(params = {}) {
    return useApi().get('orders/orders/', { params }).then(r => r.data);
  },
  detail(uuid) {
    return useApi().get(`orders/orders/${uuid}/`).then(r => r.data);
  },
  createFromCart(payload) {
    return useApi().post('orders/orders/create_from_cart/', payload).then(r => r.data);
  },
  timeline(uuid) {
    return useApi().get(`orders/orders/${uuid}/timeline/`).then(r => r.data);
  },
  pack(uuid, payload) {
    return useApi().post(`orders/orders/${uuid}/pack/`, payload).then(r => r.data);
  },
  scheduleDispatch(uuid, payload) {
    return useApi().post(`orders/orders/${uuid}/schedule-dispatch/`, payload).then(r => r.data);
  },
  assignDispatcher(uuid, payload) {
    return useApi().post(`orders/orders/${uuid}/assign-dispatcher/`, payload).then(r => r.data);
  },
  transition(uuid, action) {
    return useApi().post(`orders/orders/${uuid}/${action}/`).then(r => r.data);
  },
  operationsDashboard() {
    return useApi().get('orders/orders/operations-dashboard/').then(r => r.data);
  },
  operations(params = {}) {
    return useApi().get('orders/orders/operations/', { params }).then(r => r.data);
  },
  confirmDelivery(uuid) {
    return useApi().post(`orders/orders/${uuid}/confirm-delivery/`).then(r => r.data);
  },
  serviceOrderDetail(uuid) {
    return useApi().get(`orders/service-orders/${uuid}/`).then(r => r.data);
  },

  // Direcciones de envio del cliente (orders/addresses/)
  addresses: {
    list() {
      return useApi().get('orders/addresses/').then(r => r.data);
    },
    create(payload) {
      return useApi().post('orders/addresses/', payload).then(r => r.data);
    },
    update(uuid, payload) {
      return useApi().patch(`orders/addresses/${uuid}/`, payload).then(r => r.data);
    },
    setDefault(uuid) {
      return useApi().post(`orders/addresses/${uuid}/set-default/`).then(r => r.data);
    },
    delete(uuid) {
      return useApi().delete(`orders/addresses/${uuid}/`).then(r => r.data);
    },
  },
};
