/**
 * paymentAdmin.js — Pinia store para el panel de Transacciones de Pago
 * (PaymentTransactionsAdminView.vue: Wompi/Nequi/COD + feature flags + resync).
 *
 * Tercer incremento de la migracion a stores Pinia de modulos admin (auditoria
 * 2026-07-23, doc 13 P1-4; anteriores: store/security.js, store/notificationsAdmin.js).
 *
 * El tab activo, el filtro de estado y la pagina actual quedan como estado
 * local del componente (interaccion de UI, no datos del servidor) -- mismo
 * criterio que los 2 incrementos anteriores. El store solo guarda lo que
 * viene de la API: las 3 listas de transacciones, los feature flags, y el
 * historial de eventos de la transaccion expandida.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

const ENDPOINT_BY_TAB = {
  wompi: 'dashboard/payment-transactions/',
  nequi: 'dashboard/payment-transactions/nequi/',
  cod:   'dashboard/payment-transactions/cod/',
};

export const usePaymentAdminStore = defineStore('paymentAdmin', {
  state: () => ({
    wompiTx: [],
    nequiTx: [],
    codTx: [],
    totalCount: 0,
    loading: false,

    cardApiFlowEnabled: true,
    widgetFlowEnabled: true,
    flagLoading: false,

    transactionEvents: [],
    historyLoading: false,

    actionLoading: false,
    error: null,
  }),

  getters: {
    totalPages: (state) => Math.ceil(state.totalCount / 25),
  },

  actions: {
    _api() {
      return useApi();
    },

    async fetchTransactions(tab, page = 1, status = '') {
      this.loading = true;
      try {
        const params = { page };
        if (status) params.status = status;
        const { data } = await this._api().get(ENDPOINT_BY_TAB[tab], { params });
        const results = data.results ?? data;
        if (tab === 'wompi') this.wompiTx = results;
        else if (tab === 'nequi') this.nequiTx = results;
        else this.codTx = results;
        this.totalCount = data.count ?? results.length;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error al cargar las transacciones';
      } finally {
        this.loading = false;
      }
    },

    async fetchFeatureFlags() {
      try {
        const { data } = await this._api().get('dashboard/payment-transactions/feature-flags/');
        this.cardApiFlowEnabled = !!data.card_api_flow_enabled;
        this.widgetFlowEnabled = data.widget_flow_enabled !== false;
      } catch (err) {
        this.error = err.response?.data?.detail || 'No se pudo cargar el estado del flag de pagos';
      }
    },

    async toggleCardApiFlow(checked) {
      this.flagLoading = true;
      try {
        const { data } = await this._api().patch('dashboard/payment-transactions/feature-flags/', {
          card_api_flow_enabled: checked,
        });
        this.cardApiFlowEnabled = !!data.card_api_flow_enabled;
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.flagLoading = false;
      }
    },

    async toggleWidgetFlow(checked) {
      this.flagLoading = true;
      try {
        const { data } = await this._api().patch('dashboard/payment-transactions/feature-flags/', {
          widget_flow_enabled: checked,
        });
        this.widgetFlowEnabled = data.widget_flow_enabled !== false;
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.flagLoading = false;
      }
    },

    async resyncTransaction(uuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/payment-transactions/${uuid}/resync/`);
        const idx = this.wompiTx.findIndex((t) => t.uuid === uuid);
        if (idx !== -1) Object.assign(this.wompiTx[idx], data);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    async fetchTransactionEvents(uuid) {
      this.historyLoading = true;
      this.transactionEvents = [];
      try {
        const { data } = await this._api().get(`dashboard/payment-transactions/${uuid}/events/`);
        this.transactionEvents = data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'No se pudo cargar el historial de la transaccion';
      } finally {
        this.historyLoading = false;
      }
    },
  },
});
