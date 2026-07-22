/**
 * timelineService.js — Cliente API para la línea de tiempo de órdenes.
 */
import useApi from '@/composables/useApi';

const api = useApi();

export const fetchTimeline = (orderUuid) => api.get(`orders/orders/${orderUuid}/timeline/`);

export default {
  fetchTimeline,
};
