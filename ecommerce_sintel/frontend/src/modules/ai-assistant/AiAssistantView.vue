<template>
  <div class="ai-assistant-view">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <div>
        <h4 class="mb-0"><i class="bi bi-robot me-2"></i>Asistente IA</h4>
        <p class="text-muted small mb-0">
          Vertical piloto: Catalogo (productos, categorias, marcas, impuestos). Todo cambio de contenido
          queda como borrador hasta que lo confirmes; publicar o crear un impuesto siempre pide confirmacion.
        </p>
      </div>
      <button class="btn btn-outline-secondary btn-sm" :disabled="sending" @click="resetConversation">
        <i class="bi bi-arrow-repeat me-1"></i>Nueva conversacion
      </button>
    </div>

    <div class="card chat-card">
      <div class="chat-messages" ref="messagesEl">
        <div v-if="messages.length === 0" class="empty-state text-muted text-center py-5">
          <i class="bi bi-chat-dots fs-1 d-block mb-2 opacity-50"></i>
          Preguntale algo como <em>"listame los productos"</em> o
          <em>"creame un producto Hikvision de camaras 5MP, categoria CCTV, precio 350000"</em>.
        </div>

        <div v-for="(msg, i) in messages" :key="i" class="chat-row" :class="msg.role">
          <div class="chat-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'">
            <div v-if="msg.text" class="bubble-text">{{ msg.text }}</div>

            <div v-if="msg.agent" class="bubble-meta">
              <span class="badge text-bg-light border">{{ msg.agent }}</span>
              <span v-if="msg.handoff" class="badge text-bg-warning-subtle text-warning-emphasis border ms-1">
                derivado: {{ msg.handoff }}
              </span>
            </div>

            <div v-if="msg.toolResults && msg.toolResults.length" class="tool-results">
              <div v-for="(tr, j) in msg.toolResults" :key="j" class="tool-result-card">
                <div class="tool-result-header">
                  <i class="bi bi-tools me-1"></i>{{ tr.name }}
                  <span v-if="tr.response && tr.response.error" class="badge text-bg-danger ms-2">error</span>
                </div>
                <pre class="tool-result-body">{{ formatJson(tr.response) }}</pre>
              </div>
            </div>

            <div v-if="msg.confirmation" class="confirmation-card">
              <div class="confirmation-title">
                <i class="bi bi-exclamation-triangle-fill me-1"></i>
                Esta accion requiere tu confirmacion
              </div>
              <div v-if="msg.confirmation.hint" class="confirmation-hint">{{ msg.confirmation.hint }}</div>
              <div class="confirmation-actions">
                <button class="btn btn-sm btn-success" :disabled="sending" @click="answerConfirmation(true)">
                  <i class="bi bi-check-lg me-1"></i>Confirmar
                </button>
                <button class="btn btn-sm btn-outline-danger" :disabled="sending" @click="answerConfirmation(false)">
                  <i class="bi bi-x-lg me-1"></i>Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="sending" class="chat-row assistant">
          <div class="chat-bubble bubble-assistant bubble-loading">
            <span class="spinner-border spinner-border-sm me-2"></span>Pensando...
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <input
          v-model="inputText"
          type="text"
          class="form-control"
          placeholder="Escribe tu solicitud..."
          :disabled="sending || pendingConfirmation"
          @keyup.enter="sendMessage"
        />
        <button
          class="btn btn-primary ms-2"
          :disabled="sending || pendingConfirmation || !inputText.trim()"
          @click="sendMessage"
        >
          <i class="bi bi-send"></i>
        </button>
      </div>
      <div v-if="pendingConfirmation" class="chat-input-hint text-muted small px-3 pb-2">
        Responde "Confirmar" o "Cancelar" arriba antes de seguir la conversacion.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useErrorHandler } from '@/composables/useErrorHandler';

const api = useApi();
const { handleError } = useErrorHandler();

const messages = ref([]);
const inputText = ref('');
const sending = ref(false);
const pendingConfirmation = ref(false);
const messagesEl = ref(null);
const conversationId = ref('');

onMounted(() => {
  conversationId.value = `admin-${crypto.randomUUID()}`;
});

function resetConversation() {
  conversationId.value = `admin-${crypto.randomUUID()}`;
  messages.value = [];
  pendingConfirmation.value = false;
  inputText.value = '';
}

function formatJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch (_) {
    return String(value);
  }
}

async function scrollToBottom() {
  await nextTick();
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
  }
}

function pushAssistantMessage(data) {
  messages.value.push({
    role: 'assistant',
    text: data.response,
    agent: data.agent,
    handoff: data.handoff,
    toolResults: data.tool_results || [],
    confirmation: data.needs_confirmation ? (data.confirmation || {}) : null,
  });
  pendingConfirmation.value = !!data.needs_confirmation;
}

async function callAssistant(payload) {
  sending.value = true;
  try {
    const { data } = await api.post('dashboard/ai-assistant/chat/', payload);
    pushAssistantMessage(data);
  } catch (err) {
    handleError(err, 'No se pudo contactar al asistente. Intenta de nuevo.');
    messages.value.push({ role: 'assistant', text: 'No pude procesar tu solicitud. Intenta de nuevo en un momento.' });
    pendingConfirmation.value = false;
  } finally {
    sending.value = false;
    scrollToBottom();
  }
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || sending.value || pendingConfirmation.value) return;
  messages.value.push({ role: 'user', text });
  inputText.value = '';
  scrollToBottom();
  await callAssistant({ message: text, conversation_id: conversationId.value, confirm: null });
}

async function answerConfirmation(confirmed) {
  messages.value.push({ role: 'user', text: confirmed ? 'Confirmar' : 'Cancelar' });
  scrollToBottom();
  await callAssistant({ message: '', conversation_id: conversationId.value, confirm: confirmed });
}
</script>

<style scoped>
.chat-card {
  height: calc(100vh - 220px);
  min-height: 420px;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
}

.chat-row {
  display: flex;
  margin-bottom: 0.75rem;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-bubble {
  max-width: 75%;
  padding: 0.65rem 0.9rem;
  border-radius: 0.9rem;
  font-size: 0.925rem;
}

.bubble-user {
  background: var(--bs-primary, #0d6efd);
  color: #fff;
  border-bottom-right-radius: 0.25rem;
}

.bubble-assistant {
  background: #f1f3f5;
  color: #212529;
  border-bottom-left-radius: 0.25rem;
}

.bubble-loading {
  display: flex;
  align-items: center;
  color: #6c757d;
}

.bubble-text {
  white-space: pre-wrap;
}

.bubble-meta {
  margin-top: 0.4rem;
}

.tool-results {
  margin-top: 0.6rem;
}

.tool-result-card {
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  padding: 0.5rem 0.65rem;
  margin-top: 0.4rem;
}

.tool-result-header {
  font-size: 0.8rem;
  font-weight: 600;
  color: #495057;
}

.tool-result-body {
  margin: 0.35rem 0 0;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 220px;
  overflow-y: auto;
}

.confirmation-card {
  margin-top: 0.6rem;
  background: #fff8e1;
  border: 1px solid #ffe08a;
  border-radius: 0.5rem;
  padding: 0.6rem 0.75rem;
}

.confirmation-title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #7a5c00;
}

.confirmation-hint {
  font-size: 0.8rem;
  color: #7a5c00;
  margin: 0.25rem 0 0.5rem;
}

.confirmation-actions {
  display: flex;
  gap: 0.5rem;
}

.chat-input-area {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-top: 1px solid #dee2e6;
}
</style>
