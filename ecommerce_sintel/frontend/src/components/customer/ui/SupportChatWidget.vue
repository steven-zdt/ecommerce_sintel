<template>
  <div v-if="authStore.isAuthenticated && !authStore.isAdmin" class="support-chat-widget">
    <button class="chat-toggle-btn" :class="{ active: isOpen }" @click="toggleChat">
      <span v-if="!isOpen">Soporte</span>
      <span v-else>&times;</span>
      <span v-if="unreadCount > 0 && !isOpen" class="badge">{{ unreadCount }}</span>
    </button>

    <transition name="slide-up">
      <div v-if="isOpen" class="chat-panel glass">
        <div class="chat-header">
          <span>Soporte en Linea</span>
          <span class="status-dot" :class="wsReady ? 'online' : 'offline'"></span>
        </div>

        <div v-if="contexts.length" class="chat-context-bar">
          <span v-for="c in contexts" :key="c.uuid" class="context-chip">
            <i class="bi bi-paperclip"></i> {{ c.label }}
          </span>
        </div>

        <div class="chat-messages" ref="messagesEl">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="chat-bubble"
            :class="msg.is_admin ? 'bubble-admin' : 'bubble-user'"
          >
            <small class="bubble-sender">{{ msg.is_admin ? 'Soporte' : 'Yo' }}</small>
            <p>{{ msg.message }}</p>
            <small class="bubble-time">{{ formatTime(msg.created_at) }}</small>
          </div>
          <div v-if="messages.length === 0" class="empty-chat">
            Escribe un mensaje para iniciar el chat.
          </div>
        </div>

        <!-- CSAT: la sala se cerro -- ofrece calificar en vez del input normal -->
        <div v-if="showRatingPrompt" class="csat-prompt">
          <p class="csat-title">¿Como calificarias esta conversacion?</p>
          <div class="csat-stars">
            <button
              v-for="n in 5" :key="n"
              type="button"
              class="csat-star"
              :class="{ active: n <= csatRatingInput }"
              @click="csatRatingInput = n"
            >★</button>
          </div>
          <textarea
            v-model="csatCommentInput"
            class="csat-comment"
            placeholder="Comentario opcional..."
            rows="2"
          ></textarea>
          <div class="csat-actions">
            <button type="button" class="csat-skip" @click="dismissRatingPrompt">Ahora no</button>
            <button
              type="button"
              class="csat-submit"
              :disabled="!csatRatingInput || csatSending"
              @click="submitRating"
            >Enviar calificacion</button>
          </div>
        </div>
        <div v-else-if="csatSubmitted" class="csat-thanks">
          ¡Gracias por tu calificacion!
        </div>
        <div v-else class="chat-input-area">
          <input
            v-model="inputText"
            @keyup.enter="sendMessage"
            placeholder="Escribe un mensaje..."
            :disabled="!wsReady"
            class="chat-input"
          />
          <button
            @click="sendMessage"
            :disabled="!wsReady || !inputText.trim()"
            class="send-btn"
          >
            Enviar
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onUnmounted } from 'vue';
import { useAuthStore } from '@/store/auth';
import { useSupportContextStore } from '@/store/supportContext';
import useApi from '@/composables/useApi';

const authStore = useAuthStore();
const supportContextStore = useSupportContextStore();
const api = useApi();

const isOpen     = ref(false);
const messages   = ref([]);
const contexts   = ref([]);
const inputText  = ref('');
const wsReady    = ref(false);
const messagesEl = ref(null);
const unreadCount = ref(0);

// CSAT: la sala se cerro (room_closed via WS) -- ofrecer calificar.
const roomUuid        = ref(null);
const showRatingPrompt = ref(false);
const csatSubmitted    = ref(false);
const csatRatingInput  = ref(0);
const csatCommentInput = ref('');
const csatSending      = ref(false);

let ws = null;

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/';
const wsBase  = apiBase
  .replace('/api/v1/', '')
  .replace('http://', 'ws://')
  .replace('https://', 'wss://');

function connectWs() {
  if (ws) return;
  let url = `${wsBase}/ws/support/chat/?token=${authStore.accessToken}`;
  const pendingContext = supportContextStore.consume();
  if (pendingContext) {
    url += `&context_type=${pendingContext.type}&context_uuid=${pendingContext.uuid}`;
  }
  ws = new WebSocket(url);

  ws.onopen = () => { wsReady.value = true; };

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.type === 'history') {
      messages.value = data.messages;
      contexts.value = data.contexts || [];
      roomUuid.value = data.room_uuid || null;
      // CSAT: 'history' siempre corresponde a la sala OPEN actual
      // (ChatCommands.get_or_create_room crea una nueva si la anterior ya
      // fue calificada/cerrada) -- sin este reset, csatSubmitted quedaba en
      // true para siempre y el widget no volvia a mostrar el input de texto
      // en toda la sesion del navegador, incluso en una conversacion nueva.
      showRatingPrompt.value = false;
      csatSubmitted.value = false;
      csatRatingInput.value = 0;
      csatCommentInput.value = '';
      nextTick(scrollBottom);
    } else if (data.type === 'chat_message') {
      messages.value.push(data);
      if (!isOpen.value && data.is_admin) unreadCount.value += 1;
      nextTick(scrollBottom);
    } else if (data.type === 'room_closed') {
      showRatingPrompt.value = true;
      csatSubmitted.value = false;
    }
  };

  ws.onclose = () => {
    wsReady.value = false;
    ws = null;
    if (authStore.isAuthenticated) setTimeout(connectWs, 3000);
  };

  ws.onerror = () => { ws?.close(); };
}

function disconnectWs() {
  if (ws) { ws.close(); ws = null; }
  wsReady.value = false;
}

function toggleChat() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    unreadCount.value = 0;
    if (!ws) connectWs();
    nextTick(scrollBottom);
  }
}

function sendMessage() {
  const text = inputText.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ message: text }));
  inputText.value = '';
}

async function submitRating() {
  if (!roomUuid.value || !csatRatingInput.value || csatSending.value) return;
  csatSending.value = true;
  try {
    await api.post(`support/chats/${roomUuid.value}/rate/`, {
      rating: csatRatingInput.value,
      comment: csatCommentInput.value,
    });
    csatSubmitted.value = true;
    showRatingPrompt.value = false;
  } catch (_) {
    // Error silencioso (ej. ya calificada) -- no bloquea el cierre del widget.
    csatSubmitted.value = true;
    showRatingPrompt.value = false;
  } finally {
    csatSending.value = false;
  }
}

function dismissRatingPrompt() {
  showRatingPrompt.value = false;
}

function scrollBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

watch(() => authStore.isAuthenticated, (val) => { if (!val) disconnectWs(); });

// El boton "Necesitas ayuda con este pedido/alquiler?" (CustomerOrdersView, etc.) incrementa
// openRequested para forzar la apertura del widget con el contexto ya seteado en el store.
watch(() => supportContextStore.openRequested, (val) => {
  if (!val) return;
  isOpen.value = true;
  unreadCount.value = 0;
  disconnectWs();
  connectWs();
  nextTick(scrollBottom);
});

onUnmounted(disconnectWs);
</script>

<style scoped>
.support-chat-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.chat-toggle-btn {
  position: relative;
  background: #1e40af;
  color: #fff;
  border: none;
  border-radius: 50px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 24px rgba(30, 64, 175, 0.35);
  transition: background 0.2s, transform 0.15s;
}
.chat-toggle-btn:hover  { background: #1d4ed8; transform: translateY(-2px); }
.chat-toggle-btn.active { background: #374151; }

.badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #ef4444;
  color: #fff;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.glass {
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.14);
}

.chat-panel {
  width: 340px;
  height: 460px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  background: #1e40af;
  color: #fff;
  padding: 14px 16px;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.status-dot.online  { background: #4ade80; }
.status-dot.offline { background: #9ca3af; }

.chat-context-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(30, 64, 175, 0.06);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}
.context-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #eef2ff;
  color: #1e40af;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 600;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-chat {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  margin-top: 40px;
}

.chat-bubble {
  max-width: 82%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.45;
}
.bubble-user  { align-self: flex-end;   background: #1e40af; color: #fff;    border-bottom-right-radius: 4px; }
.bubble-admin { align-self: flex-start; background: #f3f4f6; color: #111827; border-bottom-left-radius: 4px; }

.bubble-sender { display: block; font-size: 10px; opacity: 0.7; margin-bottom: 2px; }
.bubble-time   { display: block; font-size: 10px; opacity: 0.6; margin-top: 2px; text-align: right; }

.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.95);
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
  transition: border 0.2s;
}
.chat-input:focus { border-color: #1e40af; }

.send-btn {
  background: #1e40af;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.send-btn:hover:not(:disabled) { background: #1d4ed8; }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.slide-up-enter-active,
.slide-up-leave-active { transition: all 0.25s ease; }
.slide-up-enter-from,
.slide-up-leave-to { opacity: 0; transform: translateY(16px); }

/* CSAT */
.csat-prompt {
  padding: 14px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.95);
  flex-shrink: 0;
}
.csat-title { margin: 0 0 8px; font-size: 13px; font-weight: 600; color: #111827; }
.csat-stars { display: flex; gap: 4px; margin-bottom: 8px; }
.csat-star {
  background: none; border: none; font-size: 22px; line-height: 1; cursor: pointer;
  color: #d1d5db; padding: 0;
}
.csat-star.active { color: #f59e0b; }
.csat-comment {
  width: 100%; border: 1px solid #d1d5db; border-radius: 8px; padding: 6px 10px;
  font-size: 12px; resize: none; outline: none; margin-bottom: 8px; font-family: inherit;
}
.csat-comment:focus { border-color: #1e40af; }
.csat-actions { display: flex; justify-content: flex-end; gap: 8px; }
.csat-skip {
  background: none; border: none; color: #6b7280; font-size: 12px; cursor: pointer;
}
.csat-submit {
  background: #1e40af; color: #fff; border: none; border-radius: 8px;
  padding: 7px 12px; font-size: 12px; cursor: pointer;
}
.csat-submit:disabled { opacity: 0.4; cursor: not-allowed; }
.csat-thanks {
  padding: 14px 16px; text-align: center; font-size: 13px; color: #059669;
  border-top: 1px solid rgba(0, 0, 0, 0.08); flex-shrink: 0;
}
</style>
