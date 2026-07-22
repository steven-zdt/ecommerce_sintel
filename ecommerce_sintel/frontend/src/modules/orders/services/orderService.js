/**
 * orderService.js — Cliente API para órdenes en el panel administrativo.
 */
import useApi from '@/composables/useApi';

const api = useApi();

export const fetchOrder = (uuid) => api.get(`orders/orders/${uuid}/`);
export const fetchOrders = (params = {}) => api.get('orders/orders/', { params });
export const fetchOrderTimeline = (uuid) => api.get(`orders/orders/${uuid}/timeline/`);

export const fetchShipmentAssignments = (uuid) => api.get(`orders/orders/${uuid}/`); // placeholder for future logistic APIs

export default {
  fetchOrder,
  fetchOrders,
  fetchOrderTimeline,
  fetchShipmentAssignments,
};
