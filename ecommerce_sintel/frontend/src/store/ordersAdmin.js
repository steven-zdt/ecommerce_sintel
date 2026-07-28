/**
 * ordersAdmin.js — Pinia store para el panel de Ordenes admin
 * (OrderList.vue: listado; ShopOperationBoard.vue: tablero operativo de
 * picking/empaque/despacho/entrega).
 *
 * Quinto incremento de la migracion a stores Pinia de modulos admin (auditoria
 * 2026-07-23, doc 13 P1-4; anteriores: security, notificationsAdmin,
 * paymentAdmin, organizationAdmin).
 *
 * A diferencia de los 4 incrementos previos, este modulo ya tenia una capa de
 * servicio (`services/orders/ordersService.js`, SPRINT 4) que envuelve
 * `useApi()` por endpoint -- el store delega ahi en vez de llamar a useApi()
 * directo, para no duplicar las rutas de la API en dos lugares. La unica
 * excepcion es `dashboard/dispatchers/`, que el componente original ya
 * llamaba directo (no via ordersService) -- se preserva igual aqui.
 *
 * El item de shipment seleccionado y los 3 formularios de accion (empaque,
 * programacion, asignacion) quedan como estado local del componente --
 * mismo criterio que los incrementos anteriores (son borradores de UI, no
 * datos de servidor).
 *
 * `order`/`orderLoading`/`fetchOrder` agregados en el cierre de FE-H5 residual
 * (2026-07-27): `OrderDetailView.vue` (`/panel/ordenes/:uuid`) tenia su PROPIO
 * store paralelo (`store/orders/orderStore.js`, `useOrderStore`) que nunca se
 * toco en el quinto incremento de P1-4 porque no aparecio en el grep de
 * `useApi()` (llamaba a traves de otro service, `modules/orders/services/
 * orderService.js`). Se consolido aqui y se eliminaron ambos archivos
 * duplicados (`orderStore.js`, `orderService.js`, mas `timelineService.js`
 * que ya estaba huerfano) -- un solo store/servicio de ordenes para todo el
 * dominio, sin duplicar rutas de API en dos lugares.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';
import { ordersService } from '@/services/orders/ordersService';

export const useOrdersAdminStore = defineStore('ordersAdmin', {
  state: () => ({
    orders: [],
    ordersLoading: false,

    order: null,
    orderLoading: false,

    shipments: [],
    dispatchers: [],
    metrics: {},
    opsLoading: false,

    timeline: [],
    timelineLoading: false,

    actionLoading: false,
    error: null,
  }),

  actions: {
    async fetchOrder(uuid) {
      this.orderLoading = true;
      try {
        this.order = await ordersService.detail(uuid);
      } catch (err) {
        this.error = 'Error al cargar la orden.';
        this.order = null;
      } finally {
        this.orderLoading = false;
      }
    },

    async fetchOrders(params = {}) {
      this.ordersLoading = true;
      try {
        const data = await ordersService.list(params);
        this.orders = data.results ?? data;
      } catch (err) {
        this.error = 'Error al cargar órdenes.';
      } finally {
        this.ordersLoading = false;
      }
    },

    async fetchOperations(filters = {}) {
      this.opsLoading = true;
      try {
        const [data, dispatcherResponse, metrics] = await Promise.all([
          ordersService.operations(filters),
          useApi().get('dashboard/dispatchers/'),
          ordersService.operationsDashboard(),
        ]);
        this.shipments = data.results ?? data;
        this.dispatchers = dispatcherResponse.data.results ?? dispatcherResponse.data;
        this.metrics = metrics;
      } finally {
        this.opsLoading = false;
      }
    },

    async fetchTimeline(orderUuid) {
      this.timelineLoading = true;
      try {
        this.timeline = await ordersService.timeline(orderUuid);
      } finally {
        this.timelineLoading = false;
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

    pack(uuid, payload) {
      return this._mutate(() => ordersService.pack(uuid, payload));
    },

    scheduleDispatch(uuid, payload) {
      return this._mutate(() => ordersService.scheduleDispatch(uuid, payload));
    },

    assignDispatcher(uuid, payload) {
      return this._mutate(() => ordersService.assignDispatcher(uuid, payload));
    },

    transition(uuid, action) {
      return this._mutate(() => ordersService.transition(uuid, action));
    },
  },
});
