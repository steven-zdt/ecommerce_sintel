/**
 * operationsAdmin.js — Pinia store para el panel de Operaciones
 * (OperationBoard.vue: tablero general; OperationDetail.vue: ticket
 * individual; DispatcherList.vue: CRUD de despachadores).
 *
 * Octavo incremento de la migracion a stores Pinia de modulos admin
 * (auditoria 2026-07-23, doc 13 P1-4). Ninguno de los 3 archivos tenia capa
 * de servicio previa -- todo llamaba a useApi() directo, asi que aqui el
 * store llama a useApi() directo tambien (a diferencia de ordersAdmin /
 * marketingAdmin, que delegaban en un service ya existente).
 *
 * El autocompletado de usuarios de DispatcherList.vue (`users/` con
 * `search=`) queda local al componente -- es una busqueda transitoria de
 * UI, no un dato que otro componente necesite compartir.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useOperationsAdminStore = defineStore('operationsAdmin', {
  state: () => ({
    ops: [],
    opsLoading: false,

    dispatchers: [],
    dispatchersLoading: false,

    currentTicket: null,
    ticketLoading: false,

    availableStaff: [],
    staffLoading: false,

    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    async fetchOps(filters = {}) {
      this.opsLoading = true;
      try {
        const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
        const { data } = await this._api().get('dashboard/operations/', { params });
        this.ops = data.results ?? data;
      } finally {
        this.opsLoading = false;
      }
    },

    async fetchDispatchers() {
      this.dispatchersLoading = true;
      try {
        const { data } = await this._api().get('dashboard/dispatchers/');
        this.dispatchers = data.results ?? data;
      } finally {
        this.dispatchersLoading = false;
      }
    },

    async createDispatcher(payload) {
      try {
        await this._api().post('dashboard/dispatchers/', payload);
        await this.fetchDispatchers();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      }
    },

    async deleteDispatcher(uuid) {
      try {
        await this._api().delete(`dashboard/dispatchers/${uuid}/`);
        this.dispatchers = this.dispatchers.filter((d) => d.uuid !== uuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      }
    },

    async fetchTicket(uuid) {
      this.ticketLoading = true;
      try {
        const { data } = await this._api().get(`dashboard/operations/${uuid}/`);
        this.currentTicket = data;
      } finally {
        this.ticketLoading = false;
      }
    },

    async fetchAvailableStaff(uuid) {
      this.staffLoading = true;
      try {
        const { data } = await this._api().get(`dashboard/operations/${uuid}/available-staff/`);
        this.availableStaff = data;
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.staffLoading = false;
      }
    },

    async _mutate(uuid, action) {
      this.actionLoading = true;
      try {
        await action();
        await this.fetchTicket(uuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    transition(uuid, status) {
      return this._mutate(uuid, () => this._api().post(`dashboard/operations/${uuid}/transition/`, { status }));
    },

    schedule(uuid, payload) {
      return this._mutate(uuid, () => this._api().post(`dashboard/operations/${uuid}/schedule/`, payload));
    },

    autoAssign(uuid) {
      return this._mutate(uuid, () => this._api().post(`dashboard/operations/${uuid}/auto-assign/`));
    },

    assign(uuid, payload) {
      return this._mutate(uuid, () => this._api().post(`dashboard/operations/${uuid}/assign/`, payload));
    },

    reviewDoc(uuid, docUuid, approved) {
      return this._mutate(uuid, () => this._api().post(`dashboard/operations/${uuid}/documents/${docUuid}/review/`, { approved }));
    },
  },
});
