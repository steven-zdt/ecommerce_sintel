<template>
  <div class="support-dashboard">
    <div class="support-header">
      <h2>Chat de Soporte</h2>
      <span class="ws-badge" :class="wsReady ? 'online' : 'offline'">
        {{ wsReady ? 'En linea' : 'Desconectado' }}
      </span>
    </div>

    <!-- Analytics de conversaciones (Fase 9 AI Core -- Aprendizaje) -->
    <div class="row g-3 mb-3">
      <div class="col-sm-6 col-xl-3" v-for="kpi in analyticsKpis" :key="kpi.label">
        <div class="kpi-card h-100">
          <div class="kpi-icon" :style="{ background: kpi.color }">
            <i :class="['bi', kpi.icon]"></i>
          </div>
          <div>
            <div class="kpi-value">
              <template v-if="loadingAnalytics">
                <span class="placeholder-glow"><span class="placeholder col-6"></span></span>
              </template>
              <template v-else>{{ kpi.value }}</template>
            </div>
            <div class="kpi-label">{{ kpi.label }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="row g-3 mb-3" v-if="analytics">
      <div class="col-lg-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-bold py-2">
            <i class="bi bi-question-circle me-2 text-primary"></i>Preguntas mas frecuentes
          </div>
          <div class="card-body p-0">
            <div class="top-product-list">
              <div v-for="(item, idx) in analytics.intent_breakdown" :key="idx" class="top-product-item">
                <div class="product-rank">{{ idx + 1 }}</div>
                <div class="product-info">
                  <div class="product-name">{{ item.intent }}</div>
                </div>
                <div class="product-sales">
                  <span class="badge rounded-pill bg-light text-dark">{{ item.count }}</span>
                </div>
              </div>
              <div v-if="!analytics.intent_breakdown.length" class="p-3 text-center text-muted small">
                Sin datos en esta ventana.
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-bold py-2">
            <i class="bi bi-exclamation-triangle me-2 text-warning"></i>Problemas frecuentes (fallback)
          </div>
          <div class="card-body p-0">
            <div class="top-product-list">
              <div v-for="(item, idx) in analytics.frequent_issues" :key="idx" class="top-product-item">
                <div class="product-rank">{{ idx + 1 }}</div>
                <div class="product-info">
                  <div class="product-name">{{ item.intent }}</div>
                </div>
                <div class="product-sales">
                  <span class="badge rounded-pill bg-light text-dark">{{ item.fallback_count }}</span>
                </div>
              </div>
              <div v-if="!analytics.frequent_issues.length" class="p-3 text-center text-muted small">
                Sin fallbacks en esta ventana.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="support-columns">
      <!-- Panel izquierdo: lista de salas -->
      <div class="rooms-panel">
        <div class="rooms-toolbar">
          <input
            v-model="searchQuery"
            placeholder="Buscar por email..."
            class="search-input"
          />
        </div>

        <div class="rooms-list">
          <div v-if="loadingRooms && !rooms.length" class="text-center text-muted small py-4">
            <div class="spinner-border spinner-border-sm text-primary me-2"></div>Cargando chats...
          </div>
          <div
            v-else-if="filteredRooms.length === 0"
            class="empty-state"
          >
            No hay chats activos.
          </div>
          <div
            v-for="room in filteredRooms"
            :key="room.uuid"
            class="room-item"
            :class="{ active: selectedRoom?.uuid === room.uuid }"
            @click="selectRoom(room)"
          >
            <div class="room-user">{{ room.user_email }}</div>
            <div class="room-preview">{{ room.last_message || 'Sin mensajes' }}</div>
            <div class="room-meta">
              <span class="room-status" :class="room.status.toLowerCase()">{{ room.status }}</span>
              <span v-if="room.unread_count > 0" class="room-badge">{{ room.unread_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel derecho: mensajes -->
      <div class="messages-panel">
        <template v-if="selectedRoom">
          <div class="messages-header">
            <div>
              <strong>{{ selectedRoom.user_email }}</strong>
              <span class="room-id">&nbsp;#{{ selectedRoom.uuid.split('-')[0] }}</span>
              <span v-if="selectedRoom.csat_rating" class="csat-badge" :title="selectedRoom.csat_comment || ''">
                {{ '★'.repeat(selectedRoom.csat_rating) }}{{ '☆'.repeat(5 - selectedRoom.csat_rating) }}
              </span>
            </div>
            <button
              v-if="selectedRoom.status === 'OPEN'"
              class="close-room-btn"
              @click="closeRoom"
            >
              Cerrar chat
            </button>
          </div>

          <div class="messages-list" ref="messagesEl">
            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="chat-bubble"
              :class="msg.is_admin ? 'bubble-admin' : 'bubble-user'"
            >
              <small class="bubble-sender">
                {{ msg.is_admin ? msg.sender_email : selectedRoom.user_email }}
              </small>
              <p>{{ msg.message }}</p>
              <div v-if="msg.ai_metrics" class="ai-metrics">
                <span class="ai-metrics-badge">IA · {{ msg.ai_metrics.agent || 'sin agente' }}</span>
                <span v-if="msg.ai_metrics.intent" class="ai-metrics-badge">{{ msg.ai_metrics.intent }}</span>
                <span v-if="msg.ai_metrics.tools?.length" class="ai-metrics-badge">
                  {{ msg.ai_metrics.tools.map(t => t.tool).join(', ') }}
                </span>
                <span v-if="msg.ai_metrics.llm_tokens_in || msg.ai_metrics.llm_tokens_out" class="ai-metrics-badge">
                  {{ msg.ai_metrics.llm_tokens_in }}→{{ msg.ai_metrics.llm_tokens_out }} tokens
                </span>
                <span v-if="msg.ai_metrics.duration_ms != null" class="ai-metrics-badge">{{ msg.ai_metrics.duration_ms }} ms</span>
                <span v-if="msg.ai_metrics.handoff" class="ai-metrics-badge ai-metrics-warn">handoff: {{ msg.ai_metrics.handoff }}</span>
                <span v-if="msg.ai_metrics.needs_confirmation" class="ai-metrics-badge ai-metrics-warn">confirmacion pendiente</span>
                <span v-if="msg.ai_metrics.fallback_used" class="ai-metrics-badge ai-metrics-warn">fallback</span>
              </div>
              <small class="bubble-time">{{ formatTime(msg.created_at) }}</small>
            </div>
            <div v-if="messages.length === 0" class="empty-state">
              Sin mensajes aun.
            </div>
          </div>

          <div v-if="selectedRoom.status === 'OPEN'" class="messages-input">
            <input
              v-model="inputText"
              @keyup.enter="sendMessage"
              placeholder="Responder al cliente..."
              :disabled="!wsReady"
              class="msg-input"
            />
            <button
              @click="sendMessage"
              :disabled="!wsReady || !inputText.trim()"
              class="send-btn"
            >
              Enviar
            </button>
          </div>
          <div v-else class="closed-notice">Esta sala esta cerrada.</div>
        </template>

        <div v-else class="no-selection">
          Selecciona una sala para ver los mensajes.
        </div>
      </div>

      <!-- Panel de contexto: Customer 360 (Customer Experience Hub) -->
      <div class="context-panel">
        <Customer360Panel
          :user-uuid="selectedRoom?.user_uuid || ''"
          :room-contexts="selectedRoom?.contexts || []"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';
import { useAuthStore } from '@/store/auth';
import useApi from '@/composables/useApi';
import Customer360Panel from '@/components/support/Customer360Panel.vue';

const authStore = useAuthStore();
const api       = useApi();

const rooms        = ref([]);
const selectedRoom = ref(null);
const messages     = ref([]);
const inputText    = ref('');
const wsReady      = ref(false);
const messagesEl   = ref(null);
const searchQuery  = ref('');
const loadingRooms = ref(false);

const analytics        = ref(null);
const loadingAnalytics = ref(false);

const analyticsKpis = computed(() => {
  const a = analytics.value || {};
  return [
    { label: 'Conversaciones (30d)', value: a.total_conversations ?? '--', icon: 'bi-chat-dots-fill', color: 'linear-gradient(135deg,#0ea5e9,#0369a1)' },
    { label: 'Turnos IA', value: a.total_ai_turns ?? '--', icon: 'bi-robot', color: 'linear-gradient(135deg,#10b981,#047857)' },
    { label: 'Tasa de fallback', value: a.fallback_rate != null ? `${Math.round(a.fallback_rate * 100)}%` : '--', icon: 'bi-exclamation-triangle-fill', color: 'linear-gradient(135deg,#f59e0b,#b45309)' },
    { label: 'Tasa de escalamiento', value: a.handoff_rate != null ? `${Math.round(a.handoff_rate * 100)}%` : '--', icon: 'bi-person-lines-fill', color: 'linear-gradient(135deg,#8b5cf6,#5b21b6)' },
    { label: 'Tokens promedio (in/out)', value: a.avg_tokens_in != null ? `${a.avg_tokens_in}/${a.avg_tokens_out}` : '--', icon: 'bi-cpu-fill', color: 'linear-gradient(135deg,#2563eb,#1e3a8a)' },
    { label: 'Duracion promedio', value: a.avg_duration_ms != null ? `${(a.avg_duration_ms / 1000).toFixed(1)}s` : '--', icon: 'bi-stopwatch-fill', color: 'linear-gradient(135deg,#d97706,#b45309)' },
  ];
});

let ws = null;

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/';
const wsBase  = apiBase
  .replace('/api/v1/', '')
  .replace('http://', 'ws://')
  .replace('https://', 'wss://');

const filteredRooms = computed(() => {
  const q = searchQuery.value.toLowerCase();
  return q ? rooms.value.filter(r => r.user_email.toLowerCase().includes(q)) : rooms.value;
});

async function fetchAnalytics() {
  loadingAnalytics.value = true;
  try {
    const { data } = await api.get('dashboard/support/chats/analytics/');
    analytics.value = data;
  } catch (_) {
  } finally {
    loadingAnalytics.value = false;
  }
}

async function fetchRooms() {
  loadingRooms.value = true;
  try {
    const { data } = await api.get('dashboard/support/chats/');
    rooms.value = data;
  } catch (_) {
  } finally {
    loadingRooms.value = false;
  }
}

async function selectRoom(room) {
  selectedRoom.value = room;
  messages.value = [];
  try {
    const { data } = await api.get(`dashboard/support/chats/${room.uuid}/`);
    messages.value = data.messages || [];
    // Conserva user_uuid/contexts del detalle -- la lista (ChatRoomListSerializer) no los trae.
    selectedRoom.value = { ...room, ...data };
    const idx = rooms.value.findIndex(r => r.uuid === room.uuid);
    if (idx !== -1) rooms.value[idx].unread_count = 0;
    nextTick(scrollBottom);
  } catch (_) {}
}

function connectWs() {
  const url = `${wsBase}/ws/support/chat/?token=${authStore.accessToken}`;
  ws = new WebSocket(url);

  ws.onopen = () => { wsReady.value = true; };

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.type !== 'chat_message') return;

    const idx = rooms.value.findIndex(r => r.uuid === data.room_uuid);
    if (idx !== -1) {
      rooms.value[idx].last_message = data.message;
      if (selectedRoom.value?.uuid !== data.room_uuid) {
        rooms.value[idx].unread_count = (rooms.value[idx].unread_count || 0) + 1;
      }
    } else {
      fetchRooms();
    }

    if (selectedRoom.value?.uuid === data.room_uuid) {
      messages.value.push(data);
      nextTick(scrollBottom);
    }
  };

  ws.onclose = () => {
    wsReady.value = false;
    ws = null;
    setTimeout(connectWs, 3000);
  };

  ws.onerror = () => { ws?.close(); };
}

function sendMessage() {
  const text = inputText.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN || !selectedRoom.value) return;
  ws.send(JSON.stringify({ room_uuid: selectedRoom.value.uuid, message: text }));
  inputText.value = '';
}

async function closeRoom() {
  if (!selectedRoom.value) return;
  try {
    await api.post(`dashboard/support/chats/${selectedRoom.value.uuid}/close/`);
    rooms.value = rooms.value.filter(r => r.uuid !== selectedRoom.value.uuid);
    selectedRoom.value = null;
    messages.value = [];
  } catch (_) {}
}

function scrollBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('es-CO', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  } catch { return ''; }
}

onMounted(() => { fetchRooms(); fetchAnalytics(); connectWs(); });
onUnmounted(() => { if (ws) { ws.close(); ws = null; } });
</script>

<style scoped>
.support-dashboard {
  padding: 24px;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.support-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.support-header h2 { margin: 0; font-size: 20px; font-weight: 700; color: #111827; }

/* Analytics (Fase 9 AI Core -- Aprendizaje), estilo reusado de views/admin/DashboardView.vue */
.kpi-card {
  background: #fff; border-radius: 1rem; padding: 1rem 1.25rem;
  display: flex; align-items: center; gap: 1rem;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,.05); transition: transform .2s;
}
.kpi-card:hover { transform: translateY(-3px); }
.kpi-icon {
  width: 44px; height: 44px; border-radius: .875rem;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 1.2rem; flex-shrink: 0;
}
.kpi-value { font-size: 1.25rem; font-weight: 700; color: #1e293b; line-height: 1.2; }
.kpi-label { font-size: .75rem; color: #94a3b8; margin-top: .25rem; }

.top-product-list { background: #fff; max-height: 180px; overflow-y: auto; }
.top-product-item {
  display: flex; align-items: center; gap: 1rem; padding: .5rem 1.25rem;
  border-bottom: 1px solid #f1f5f9;
}
.product-rank {
  width: 22px; height: 22px; background: #f1f5f9; color: #64748b;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 0.7rem; font-weight: 700; flex-shrink: 0;
}
.product-info { flex-grow: 1; min-width: 0; }
.product-name { font-weight: 500; color: #1e293b; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.ws-badge {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: 600;
}
.ws-badge.online  { background: #d1fae5; color: #065f46; }
.ws-badge.offline { background: #fee2e2; color: #991b1b; }

.support-columns {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 16px;
  overflow: hidden;
  min-height: 0;
}

/* ── Context panel (Customer 360) ───────────────────────────── */
.context-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  min-height: 0;
}

/* ── Left panel ─────────────────────────────────────────────── */
.rooms-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rooms-toolbar { padding: 12px; border-bottom: 1px solid #f3f4f6; flex-shrink: 0; }
.search-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border 0.2s;
}
.search-input:focus { border-color: #1e40af; }

.rooms-list { flex: 1; overflow-y: auto; }

.room-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f9fafb;
  cursor: pointer;
  transition: background 0.15s;
}
.room-item:hover { background: #f3f4f6; }
.room-item.active { background: #eff6ff; border-left: 3px solid #1e40af; }

.room-user    { font-weight: 600; font-size: 13px; color: #111827; }
.room-preview { font-size: 12px; color: #6b7280; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.room-meta    { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }

.room-status         { font-size: 11px; text-transform: uppercase; font-weight: 600; }
.room-status.open    { color: #16a34a; }
.room-status.closed  { color: #9ca3af; }

.room-badge {
  background: #ef4444;
  color: #fff;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

/* ── Right panel ────────────────────────────────────────────── */
.messages-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.messages-header {
  padding: 14px 20px;
  border-bottom: 1px solid #f3f4f6;
  background: #f9fafb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.room-id { color: #9ca3af; font-size: 13px; }
.csat-badge { margin-left: 10px; color: #f59e0b; font-size: 14px; letter-spacing: 1px; }

.close-room-btn {
  background: #fee2e2;
  color: #991b1b;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}
.close-room-btn:hover { background: #fecaca; }

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.chat-bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
}
.bubble-admin { align-self: flex-start; background: #1e40af; color: #fff;    border-bottom-left-radius: 4px; }
.bubble-user  { align-self: flex-end;   background: #f3f4f6; color: #111827; border-bottom-right-radius: 4px; }

.bubble-sender { display: block; font-size: 11px; opacity: 0.7; margin-bottom: 3px; }
.bubble-time   { display: block; font-size: 11px; opacity: 0.6; margin-top: 4px; text-align: right; }

.ai-metrics { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.ai-metrics-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.15);
  color: inherit;
  opacity: 0.85;
}
.bubble-user .ai-metrics-badge { background: rgba(17, 24, 39, 0.08); }
.ai-metrics-warn { background: #f59e0b; color: #111827; opacity: 1; }

.messages-input {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #f3f4f6;
  flex-shrink: 0;
}
.msg-input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 14px;
  outline: none;
  transition: border 0.2s;
}
.msg-input:focus { border-color: #1e40af; }

.send-btn {
  background: #1e40af;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 9px 22px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.send-btn:hover:not(:disabled) { background: #1d4ed8; }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.closed-notice {
  padding: 14px 16px;
  background: #f9fafb;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  border-top: 1px solid #f3f4f6;
  flex-shrink: 0;
}

.no-selection {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 14px;
}

.empty-state {
  text-align: center;
  color: #9ca3af;
  padding: 32px;
  font-size: 13px;
}
</style>
