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
    prefillText: '', // texto inicial del input al abrir (2026-07-31, Centro de Comunicacion)
  }),
  actions: {
    requestHelp(type, uuid) {
      this.pending = { type, uuid };
      this.openRequested += 1;
    },
    /**
     * Abre el widget de soporte SIN contexto de orden/renta -- usado por el
     * Centro de Comunicacion (CommunicationPanel.vue) para migrar el viejo
     * boton flotante "Soporte" a una opcion del panel, y para las opciones
     * "Solicitar llamada"/"Enviar mensaje" (mismo canal real, distinto
     * texto inicial segun la intencion del usuario).
     */
    requestOpen(prefillText = '') {
      this.prefillText = prefillText;
      this.openRequested += 1;
    },
    consume() {
      const ctx = this.pending;
      this.pending = null;
      return ctx;
    },
    consumePrefill() {
      const text = this.prefillText;
      this.prefillText = '';
      return text;
    },
  },
});
