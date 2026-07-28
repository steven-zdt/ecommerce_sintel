/**
 * kycAdmin.js — Pinia store para el modulo KYC admin
 * (KycAdminList.vue: listado + KPIs; KycAdminDetail.vue: detalle de una
 * verificacion; KycVerificationPanel.vue: acciones de revision).
 *
 * Sexto incremento de la migracion a stores Pinia de modulos admin (auditoria
 * 2026-07-23, doc 13 P1-4).
 *
 * KycVerificationPanel.vue es un componente reusable (recibe `verification`
 * como prop, emite `changed`) consumido tanto por kyc/KycAdminDetail.vue como
 * por users/UserDetail.vue ("Dar de alta" con reviewable=false) -- el store
 * centraliza sus 6 acciones de mutacion para que ambos consumidores las
 * compartan sin duplicar la logica de kycService, sin que el store necesite
 * saber cual "verification" esta activa (eso lo sigue resolviendo cada padre
 * con su propio fetch/reload, via props/emit -- no se toco esa interfaz).
 */
import { defineStore } from 'pinia';
import { kycService } from '@/services/kyc/kycService';

export const useKycAdminStore = defineStore('kycAdmin', {
  state: () => ({
    items: [],
    totalCount: 0,
    nextPage: null,
    prevPage: null,
    listLoading: false,

    kpi: { by_status: {}, by_requested_type: {}, average_approval_seconds: null },

    currentVerification: null,
    detailLoading: false,

    actionLoading: false,
    error: null,
  }),

  actions: {
    async fetchList(params = {}) {
      this.listLoading = true;
      try {
        const data = await kycService.adminList(params);
        if (data.results !== undefined) {
          this.items = data.results;
          this.totalCount = data.count;
          this.nextPage = data.next ? extractPage(data.next) : null;
          this.prevPage = data.previous ? extractPage(data.previous) : null;
        } else {
          this.items = data;
          this.totalCount = data.length;
          this.nextPage = null;
          this.prevPage = null;
        }
      } catch {
        this.error = 'No se pudieron cargar las verificaciones';
      } finally {
        this.listLoading = false;
      }
    },

    async fetchKpis() {
      try {
        const data = await kycService.adminMetrics();
        this.kpi = {
          by_status: data.by_status || {},
          by_requested_type: data.by_requested_type || {},
          average_approval_seconds: data.average_approval_seconds,
        };
      } catch {
        // KPIs son un complemento visual -- si fallan, la lista sigue siendo util sin ellos.
      }
    },

    async fetchDetail(uuid) {
      this.detailLoading = true;
      try {
        this.currentVerification = await kycService.adminDetail(uuid);
      } finally {
        this.detailLoading = false;
      }
    },

    async _mutate(action) {
      this.actionLoading = true;
      try {
        await action();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    reviewDocument(verificationUuid, docUuid, payload) {
      return this._mutate(() => kycService.reviewDocument(verificationUuid, docUuid, payload));
    },

    approve(uuid) {
      return this._mutate(() => kycService.approve(uuid));
    },

    forceApprove(uuid, note) {
      return this._mutate(() => kycService.forceApprove(uuid, note));
    },

    reject(uuid, reason) {
      return this._mutate(() => kycService.reject(uuid, reason));
    },

    requestInfo(uuid, message) {
      return this._mutate(() => kycService.requestInfo(uuid, message));
    },

    block(uuid, reason) {
      return this._mutate(() => kycService.block(uuid, reason));
    },
  },
});

function extractPage(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/[?&]page=(\d+)/);
  return match ? Number(match[1]) : null;
}
