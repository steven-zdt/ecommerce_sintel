import useApi from '@/composables/useApi';

export const availabilityService = {
  check(equipmentUuid, params) {
    return useApi().get(`renting/equipment/${equipmentUuid}/check-availability/`, { params }).then(r => r.data);
  },
  get(equipmentUuid, params) {
    return useApi().get(`renting/equipment/${equipmentUuid}/availability/`, { params }).then(r => r.data);
  },
};
