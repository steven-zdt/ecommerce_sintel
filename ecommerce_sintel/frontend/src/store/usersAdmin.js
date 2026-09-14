/**
 * usersAdmin.js — Pinia store para el modulo de Usuarios admin
 * (UserList.vue: listado + toggle/eliminar; UserForm.vue: crear/editar;
 * UserDetail.vue: detalle + auditoria + grupos + acciones de cuenta).
 *
 * Noveno incremento de la migracion a stores Pinia de modulos admin
 * (auditoria 2026-07-23, doc 13 P1-4). Sin capa de servicio previa -- llama
 * a useApi() directo, mismo criterio que operationsAdmin.
 *
 * `actionLoading` es unico y compartido entre toggle/eliminar/crear/editar/
 * reset-password/reenviar-verificacion/guardar-grupos -- mismo criterio ya
 * establecido en los incrementos anteriores (organizationAdmin, kycAdmin):
 * un solo flag de mutacion en vez de uno por boton.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

function extractPath(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

export const useUsersAdminStore = defineStore('usersAdmin', {
  state: () => ({
    items: [],
    totalCount: 0,
    nextPage: null,
    prevPage: null,
    listLoading: false,

    currentDetail: null,
    detailLoading: false,

    auditLog: [],
    auditNext: null,
    auditLoading: false,

    timeline: [],
    timelineLoading: false,

    groupsCatalog: [],

    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    async fetchList(endpoint) {
      this.listLoading = true;
      try {
        const { data } = await this._api().get(endpoint);
        if (data.results !== undefined) {
          this.items = data.results;
          this.totalCount = data.count;
          this.nextPage = data.next ? extractPath(data.next) : null;
          this.prevPage = data.previous ? extractPath(data.previous) : null;
        } else {
          this.items = data;
          this.totalCount = data.length;
          this.nextPage = null;
          this.prevPage = null;
        }
      } catch {
        this.error = 'No se pudieron cargar los usuarios';
      } finally {
        this.listLoading = false;
      }
    },

    async _mutate(action) {
      this.actionLoading = true;
      try {
        const data = await action();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    createUser(payload) {
      return this._mutate(async () => (await this._api().post('users/', payload)).data);
    },

    patchUser(uuid, payload) {
      return this._mutate(async () => (await this._api().patch(`users/${uuid}/`, payload)).data);
    },

    deleteUser(uuid) {
      return this._mutate(() => this._api().delete(`users/${uuid}/erase/`));
    },

    async fetchDetail(uuid) {
      this.detailLoading = true;
      try {
        const { data } = await this._api().get(`users/${uuid}/`);
        this.currentDetail = data;
      } catch {
        this.error = 'No se pudo cargar el detalle del usuario.';
      } finally {
        this.detailLoading = false;
      }
    },

    async fetchAudit(uuid, url = null) {
      this.auditLoading = true;
      try {
        const { data } = await this._api().get(url || `users/${uuid}/audit-log/`);
        this.auditLog = url ? [...this.auditLog, ...data.results] : data.results;
        this.auditNext = data.next ? extractPath(data.next) : null;
      } finally {
        this.auditLoading = false;
      }
    },

    resetPassword(uuid) {
      return this._mutate(() => this._api().post(`users/${uuid}/reset-password/`));
    },

    resendVerification(uuid) {
      return this._mutate(() => this._api().post(`users/${uuid}/resend-verification/`));
    },

    // Lote 1 Identity Management (2026-08-07) -- acciones masivas + timeline unificado.
    bulkAction(uuids, action, reason = '') {
      return this._mutate(async () => (
        await this._api().post('users/bulk-action/', { uuids, action, reason })
      ).data);
    },

    async fetchTimeline(uuid) {
      this.timelineLoading = true;
      try {
        const { data } = await this._api().get(`users/${uuid}/timeline/`);
        this.timeline = data.results;
      } catch {
        this.error = 'No se pudo cargar el timeline del usuario.';
      } finally {
        this.timelineLoading = false;
      }
    },

    async fetchGroupsCatalog() {
      if (this.groupsCatalog.length > 0) return { ok: true };
      try {
        const { data } = await this._api().get('users/groups-catalog/');
        this.groupsCatalog = data;
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      }
    },

    saveGroups(uuid, groupIds) {
      return this._mutate(async () => (await this._api().put(`users/${uuid}/groups/`, { group_ids: groupIds })).data);
    },
  },
});
