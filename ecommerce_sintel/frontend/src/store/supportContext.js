import { defineStore } from 'pinia';

/**
 * Contexto pendiente de adjuntar al chat de soporte (Customer Experience Hub).
 * Un boton "Necesitas ayuda con este pedido/alquiler?" setea esto y abre el widget;
 * SupportChatWidget.vue lo lee al conectar el WebSocket y lo limpia despues de usarlo.
 */
export const useSupportContextStore = defineStore('supportContext', {
  state: () => ({
    pending: null, // { type: 'ORDER' | 'RENTAL', uuid: string }
    openRequested: 0, // incrementa para forzar apertura del widget aunque ya este montado
  }),
  actions: {
    requestHelp(type, uuid) {
      this.pending = { type, uuid };
      this.openRequested += 1;
    },
    consume() {
      const ctx = this.pending;
      this.pending = null;
      return ctx;
    },
  },
});
