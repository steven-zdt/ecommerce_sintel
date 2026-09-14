<template>
  <div
    id="communication-panel"
    ref="panelRef"
    class="comm-panel"
    :class="{ 'comm-panel--open': open }"
    role="dialog"
    aria-modal="false"
    aria-label="Centro de comunicación"
    :aria-hidden="open ? 'false' : 'true'"
    @keydown.escape="$emit('close')"
  >
    <div class="comm-panel-header">
      <div>
        <p class="comm-panel-title">Hablemos</p>
        <p class="comm-panel-subtitle">Elige cómo prefieres contactarnos</p>
      </div>
      <button
        type="button"
        class="comm-panel-close"
        aria-label="Cerrar centro de comunicación"
        @click="$emit('close')"
      >
        <i class="bi bi-x-lg"></i>
      </button>
    </div>

    <div class="comm-panel-body" role="menu" aria-label="Canales de contacto disponibles">
      <WhatsAppButton :ready="whatsAppReady" @click="$emit('whatsapp-click')" />

      <button
        v-for="item in supportChannels"
        :key="item.key"
        type="button"
        role="menuitem"
        class="comm-option-secondary"
        @click="$emit('support-click', item.key, item.prefill)"
      >
        <span class="comm-option-secondary-icon">
          <i :class="`bi ${item.icon}`"></i>
        </span>
        <span class="comm-option-secondary-text">
          <span class="comm-option-secondary-title">{{ item.label }}</span>
          <span class="comm-option-secondary-subtitle">{{ item.subtitle }}</span>
        </span>
        <i class="bi bi-chevron-right comm-option-secondary-chevron" aria-hidden="true"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import WhatsAppButton from './WhatsAppButton.vue';

const props = defineProps({
  open: { type: Boolean, default: false },
  whatsAppReady: { type: Boolean, default: false },
});
defineEmits(['close', 'whatsapp-click', 'support-click']);

const panelRef = ref(null);

// Las 3 activan el MISMO chat real de soporte (antes su propio boton
// flotante, ver SupportChatWidget.vue -- migrado aca 2026-07-31), cada una
// con un `channel` distinto (para el evento analitico) y un texto inicial
// distinto segun la intencion. `useCommunication.js::openSupportChat()`
// exige sesion iniciada -- CommunicationCenter.vue avisa si no la hay.
const supportChannels = [
  { key: 'ai_assistant', icon: 'bi-robot', label: 'Asistente IA', subtitle: 'Chatea con nuestro equipo', prefill: '' },
  { key: 'call', icon: 'bi-telephone-outbound', label: 'Solicitar llamada', subtitle: 'Te llamamos nosotros', prefill: 'Quisiera que me llamen, por favor. Mi número de contacto es: ' },
  { key: 'message', icon: 'bi-envelope', label: 'Enviar mensaje', subtitle: 'Déjanos tu consulta por escrito', prefill: '' },
];

// Al abrir, mueve el foco DENTRO del panel (primer elemento enfocable) --
// requisito de accesibilidad/navegacion por teclado. El retorno de foco al
// FloatingButton al cerrar lo maneja CommunicationCenter.vue, que es quien
// tiene ambas referencias.
watch(() => props.open, async (isOpen) => {
  if (!isOpen) return;
  await nextTick();
  const firstFocusable = panelRef.value?.querySelector('button:not(:disabled)');
  firstFocusable?.focus();
});
</script>

<style scoped>
/*
 * El panel vive SIEMPRE en el DOM (nunca v-if/<Transition>) -- deliberado.
 * Un intento anterior con <Transition name="comm-panel"> + v-if se rompio en
 * verificacion en vivo (2026-07-31): las clases enter-from/leave-from/
 * leave-active quedaban aplicadas simultaneamente y el elemento nunca se
 * desmontaba (Vue esperando un transitionend que nunca llegaba a limpiar el
 * estado), dejando un <div role="dialog"> invisible pero vivo en el DOM para
 * siempre tras el primer ciclo abrir/cerrar. Este patron (opacity + visibility
 * + pointer-events via clase) es mas simple y evita esa clase de bug por
 * completo -- `visibility:hidden` ya saca los botones de adentro del tab
 * order automaticamente en todos los navegadores, sin necesitar tabindex
 * manual.
 */
.comm-panel {
  position: absolute;
  bottom: calc(100% + 14px);
  right: 0;
  width: 320px;
  max-width: calc(100vw - 40px);
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
  border: 1px solid #e5e7eb;
  overflow: hidden;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(8px) scale(0.98);
  transition: opacity 0.18s ease, transform 0.18s ease, visibility 0s linear 0.18s;
}

.comm-panel--open {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: none;
  transition: opacity 0.18s ease, transform 0.18s ease, visibility 0s linear 0s;
}

@media (prefers-reduced-motion: reduce) {
  .comm-panel {
    transition: opacity 0s, visibility 0s;
  }
}

.comm-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 16px 12px;
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: #fff;
}

.comm-panel-title {
  margin: 0;
  font-weight: 700;
  font-size: 1rem;
}

.comm-panel-subtitle {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.85);
}

.comm-panel-close {
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.comm-panel-close:hover,
.comm-panel-close:focus-visible {
  background: rgba(255, 255, 255, 0.28);
}

.comm-panel-close:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.comm-panel-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/*
 * Mismo lenguaje visual de WhatsAppButton.vue para las 3 opciones que
 * migran al chat real de soporte -- duplicado deliberado (subset pequeno de
 * reglas, mismo criterio ya usado en otras decomposiciones del proyecto)
 * para no crear un componente extra solo por 3 filas sin logica propia mas
 * alla de un click con argumentos distintos.
 *
 * Nombre de clase `-secondary` (nunca `.comm-option` a secas): BUG REAL
 * encontrado y corregido en verificacion en vivo (2026-07-31) -- una version
 * anterior de este bloque se llamaba `.comm-option`, EL MISMO nombre que usa
 * WhatsAppButton.vue en su propio elemento raiz. Vue aplica el atributo de
 * scope del PADRE tambien a la raiz de un componente hijo usado directo en
 * su template (no solo el scope propio del hijo) -- esa regla se filtraba
 * tambien al boton de WhatsApp. Cualquier clase nueva en este archivo debe
 * evitar el prefijo exacto `comm-option` sin sufijo, para no repetir el bug.
 */
.comm-option-secondary {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.comm-option-secondary:hover,
.comm-option-secondary:focus-visible {
  background: #eff6ff;
  border-color: #93c5fd;
}

.comm-option-secondary:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.comm-option-secondary-icon {
  width: 40px;
  height: 40px;
  min-width: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  background: #eff6ff;
  color: #1e3a8a;
}

.comm-option-secondary-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.comm-option-secondary-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: #111827;
}

.comm-option-secondary-subtitle {
  font-size: 0.78rem;
  color: #6b7280;
}

.comm-option-secondary-chevron {
  margin-left: auto;
  color: #9ca3af;
  font-size: 0.8rem;
}

@media (max-width: 420px) {
  .comm-panel {
    width: calc(100vw - 32px);
    right: -4px;
  }
}
</style>
