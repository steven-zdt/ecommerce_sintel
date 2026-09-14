<template>
  <div ref="rootRef" class="comm-center" @click.stop>
    <CommunicationPanel
      :open="isPanelOpen"
      :whats-app-ready="isWhatsAppReady"
      @close="handleClose"
      @whatsapp-click="openWhatsApp"
      @support-click="openSupportChat"
    />
    <FloatingButton ref="fabRef" :is-open="isPanelOpen" @toggle="togglePanel" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useCommunication } from '@/composables/useCommunication';
import FloatingButton from './FloatingButton.vue';
import CommunicationPanel from './CommunicationPanel.vue';

const {
  isPanelOpen,
  isWhatsAppReady,
  closePanel,
  togglePanel,
  openWhatsApp,
  openSupportChat,
} = useCommunication();

// Nota (2026-07-31): antes este widget se apilaba arriba de SupportChatWidget.vue
// cuando coexistian (ambos ocupaban bottom:24px/right:24px para clientes
// autenticados). Ya no hace falta -- SupportChatWidget.vue perdio su propio
// boton flotante (migrado a la opcion "Asistente IA"/"Solicitar llamada"/
// "Enviar mensaje" de este panel, ver useCommunication.js::openSupportChat).
// Su PANEL de chat, cuando se abre, vive en bottom:92px (ver su propio CSS)
// para no superponerse con el FAB de aca abajo.

const rootRef = ref(null);
const fabRef = ref(null);

function handleClose() {
  closePanel();
  // Devuelve el foco al boton que abrio el panel -- requisito de
  // accesibilidad, evita que el foco se "pierda" en el body tras cerrar.
  fabRef.value?.$el?.focus();
}

/**
 * Cierra el panel si el clic fue realmente afuera del widget.
 *
 * BUG REAL encontrado y corregido en la verificacion en vivo (2026-07-31):
 * el click que ABRE el panel tambien llega aca por bubbling nativo hasta
 * `document`. Ese mismo click hace que FloatingButton.vue re-renderice su
 * icono (v-if isOpen: bi-chat-dots-fill -> bi-x-lg), lo que DESTRUYE el
 * nodo <i> original ANTES de que el evento termine de burbujear. Para
 * cuando este handler se ejecuta, `event.target` apunta a un nodo ya
 * desconectado del documento -- `rootRef.value.contains(event.target)`
 * da `false` aunque el clic haya sido claramente adentro, y el panel se
 * cerraba en el mismo clic que lo abria (reproducido con el numero
 * institucional cargando correctamente pero el panel ya en `open:false`
 * para cuando se leia el prop). Fix real: `@click.stop` en la raiz
 * `.comm-center` (ver template) -- ningun clic interno del widget llega
 * nunca a `document`, evitando la carrera por completo en vez de intentar
 * "arreglar" la deteccion de target con `composedPath()`.
 */
function handleClickOutside(event) {
  if (!isPanelOpen.value) return;
  if (rootRef.value && !rootRef.value.contains(event.target)) {
    closePanel();
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside));
onUnmounted(() => document.removeEventListener('click', handleClickOutside));
</script>

<style scoped>
/* Esquina inferior derecha, discreto -- requisito 2. z-index por encima del
   contenido normal pero debajo de cualquier modal real (BaseModal.vue no
   documenta su propio z-index critico, 1050 es el valor estandar de
   Bootstrap para modales -- este widget se queda deliberadamente debajo). */
.comm-center {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 1030;
}

@media (max-width: 576px) {
  .comm-center {
    right: 16px;
    bottom: 16px;
  }
}
</style>
