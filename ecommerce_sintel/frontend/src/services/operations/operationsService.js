import useApi from '@/composables/useApi';

export const operationsService = {
  myOperations() {
    return useApi().get('operations/my/').then(r => r.data);
  },
  tasks() {
    return useApi().get('operations/tasks/').then(r => r.data);
  },
  transitionTask(uuid, status) {
    return useApi().post(`operations/tasks/${uuid}/transition/`, { status }).then(r => r.data);
  },
};
