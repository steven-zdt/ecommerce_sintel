<template>
  <div class="wa-status-view">
    <h2>Conexion de WhatsApp</h2>
    <p class="text-muted">
      Estado real del mecanismo de conexion usado por el chat de soporte por WhatsApp
      (<code>whatsapp/</code> -- arquitectura de dominio + Connection Adapter, ver
      <code>AUDITORIA/WHATSAPP_CONNECTION_ARCHITECTURE.md</code>).
    </p>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <template v-else-if="data">
      <div class="active-banner" :class="data.active.connected ? 'ok' : (data.active.configured ? 'warn' : 'fail')">
        Mecanismo activo: <strong>{{ connectionTypeLabel(data.active_connection_type) }}</strong>
        &middot; {{ activeSummary }}
      </div>

      <div class="wa-cards">
        <div
          v-for="key in ['meta_cloud_api', 'qr_web_session']"
          :key="key"
          class="wa-card"
          :class="{ active: data.active_connection_type === key.toUpperCase() }"
        >
          <div class="wa-card-header">
            <h4>{{ connectionTypeLabel(key.toUpperCase()) }}</h4>
            <span class="badge" :class="statusClass(key === 'qr_web_session' ? detailedStateClassSource : data[key].status)">
              {{ key === 'qr_web_session' ? detailedStateLabel : statusLabel(data[key]) }}
            </span>
          </div>

          <div v-if="key === 'qr_web_session'" class="wa-experimental-warning">
            <strong>EXPERIMENTAL &middot; TERCERO &middot; NO ES LA API OFICIAL DE META.</strong>
            Simula una sesion tipo WhatsApp Web via un mecanismo QR no oficial (Baileys). Ver
            <code>AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md</code> -- conectar el numero real de
            produccion es una decision de negocio explicita, ya tomada y documentada en
            <code>AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md</code>.
          </div>
          <p v-else class="wa-card-note">
            Integracion oficial de WhatsApp Business Platform (Meta Cloud API) -- la misma que ya
            usa produccion.
          </p>

          <!-- QR real (Fase 16) -- solo la tarjeta QR, solo si hay imagen vigente -->
          <div v-if="key === 'qr_web_session' && currentQrImage" class="wa-qr-box">
            <img :src="currentQrImage" alt="Codigo QR de WhatsApp" />
            <p class="wa-qr-hint">Escanea con WhatsApp &rarr; Dispositivos vinculados &rarr; Vincular dispositivo</p>
          </div>

          <!-- Acciones (Fase 16) -- solo la tarjeta QR, Meta no tiene sesion que abrir/cerrar -->
          <div v-if="key === 'qr_web_session'" class="wa-actions">
            <button
              class="btn btn-sm btn-primary"
              :disabled="actionLoading"
              @click="runAction('connect')"
            >Conectar</button>
            <button
              class="btn btn-sm btn-outline-secondary"
              :disabled="actionLoading"
              @click="runAction('reconnect')"
            >Reconectar</button>
            <button
              class="btn btn-sm btn-outline-danger"
              :disabled="actionLoading"
              @click="confirmDisconnect ? runAction('disconnect') : (confirmDisconnect = true)"
            >{{ confirmDisconnect ? 'Confirmar desconexion' : 'Desconectar' }}</button>
            <span v-if="actionLoading" class="spinner-border spinner-border-sm ms-2"></span>
          </div>

          <div class="wa-config-row">
            <span :class="data[key].configured ? 'cap-yes' : 'cap-no'">
              {{ data[key].configured ? 'Configurado' : 'No configurado' }}
            </span>
            <span :class="data[key].connected ? 'cap-yes' : 'cap-no'">
              {{ data[key].connected ? 'Conectado' : 'No conectado' }}
            </span>
          </div>

          <table class="wa-caps-table">
            <tbody>
              <tr v-for="(value, cap) in data[key].capabilities" :key="cap">
                <td>{{ capLabel(cap) }}</td>
                <td><span :class="value ? 'cap-yes' : 'cap-no'">{{ value ? 'Si' : 'No' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="text-center text-muted py-5">No se pudo cargar el estado de WhatsApp.</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/store/auth';
import { useAuth } from '@/composables/useAuth';

const api = useApi();
const toast = useToast();
const authStore = useAuthStore();
const { refreshAccessToken } = useAuth();

const data = ref(null);
const loading = ref(true);
const actionLoading = ref(false);
const confirmDisconnect = ref(false);

const CAP_LABELS = {
  send_text: 'Enviar texto',
  receive_text: 'Recibir texto',
  send_media: 'Enviar multimedia',
  receive_media: 'Recibir multimedia',
  webhook: 'Webhook',
  polling: 'Polling',
  qr_pairing: 'Emparejamiento QR',
  session_persistence: 'Sesion persistente',
  delivery_status: 'Estado de entrega',
};
function capLabel(key) {
  return CAP_LABELS[key] || key;
}

const CONNECTION_TYPE_LABELS = {
  META_CLOUD_API: 'Meta Cloud API (oficial)',
  QR_WEB_SESSION: 'QR Web Session (experimental)',
};
function connectionTypeLabel(type) {
  return CONNECTION_TYPE_LABELS[type] || type;
}

// FASE 19-21 de la mision anterior: nunca mostrar "Disconnected" cuando en
// realidad nunca se configuro nada. Union de vocabularios reales (Fase
// 16/17 de la migracion Baileys): ConnectionStatus (Port, 6 valores),
// WhatsAppSessionState (Django, 10 valores, en `session_state` de la carga
// inicial) y ConnectionState del gateway (8 valores, en los eventos WS
// vivos, ver whatsapp_gateway/src/state.ts) -- una sola tabla de labels
// para las 3 fuentes, en vez de 3 tablas separadas.
const STATUS_LABELS = {
  NOT_CONFIGURED: 'No configurado',
  NOT_IMPLEMENTED: 'No implementado (sin gateway real)',
  DISABLED: 'No configurado',
  DISCONNECTED: 'Desconectado',
  STARTING: 'Conectando...',
  QR_REQUIRED: 'Requiere QR',
  QR_READY: 'Requiere QR',
  SCANNING: 'Escaneando...',
  PAIRING: 'Emparejando...',
  AUTHENTICATING: 'Autenticando...',
  CONNECTED: 'Conectado',
  RECONNECTING: 'Reconectando...',
  LOGGED_OUT: 'Sesion cerrada',
  ERROR: 'Error',
  PAIRING_REQUIRED: 'Requiere emparejamiento',
};
function statusLabel(entry) {
  return STATUS_LABELS[entry.status] || entry.status;
}
function statusClass(statusValue) {
  if (statusValue === 'CONNECTED') return 'bg-success';
  if (['NOT_CONFIGURED', 'NOT_IMPLEMENTED', 'DISABLED', 'DISCONNECTED'].includes(statusValue)) return 'bg-secondary';
  if (statusValue === 'ERROR') return 'bg-danger';
  return 'bg-warning text-dark';
}

// Estado detallado en vivo de la tarjeta QR (Fase 16/17): arranca con
// `session_state` de la carga inicial (GET), se sobreescribe con cada
// evento `whatsapp_status` real que llega por WebSocket -- nunca hace
// polling (Fase 6 del plan: "no polling continuo").
const liveDetailedState = ref(null);
const detailedStateClassSource = computed(() => liveDetailedState.value || data.value?.qr_web_session?.session_state || data.value?.qr_web_session?.status);
const detailedStateLabel = computed(() => STATUS_LABELS[detailedStateClassSource.value] || detailedStateClassSource.value || '--');

const currentQrImage = ref(null);

const activeSummary = computed(() => {
  if (!data.value) return '';
  const active = data.value.active;
  if (active.connected) return 'Conectado y funcionando';
  if (active.configured) return 'Configurado, pero sin conexion activa';
  return 'No configurado -- sin credenciales ni gateway real';
});

async function load() {
  loading.value = true;
  try {
    const { data: resp } = await api.get('dashboard/whatsapp/connection-status/');
    data.value = resp;
    currentQrImage.value = resp.qr_web_session?.qr_image || null;
    liveDetailedState.value = resp.qr_web_session?.session_state || null;
  } catch {
    toast.error('Error al cargar el estado de WhatsApp');
  } finally {
    loading.value = false;
  }
}

async function runAction(action) {
  confirmDisconnect.value = false;
  actionLoading.value = true;
  try {
    const { data: resp } = await api.post('dashboard/whatsapp/session-action/', { action });
    liveDetailedState.value = resp.session_state || resp.status;
    toast.success(`Accion "${action}" aplicada -- estado: ${STATUS_LABELS[resp.status] || resp.status}`);
  } catch (err) {
    // Fase 16: nunca mostrar stack traces/errores internos -- solo el
    // mensaje ya sanitizado que la vista de Django devuelve (409/502/400).
    const message = err?.response?.data?.error || 'No se pudo ejecutar la accion.';
    toast.error(message);
  } finally {
    actionLoading.value = false;
  }
}

// ── WebSocket (Fase 17): reusa el mismo canal/grupo/heartbeat que ya usa
// el dashboard de soporte (support/consumers.py::SupportChatConsumer,
// grupo 'support_admins') -- "el heartbeat WebSocket existente de soporte
// debe mantenerse", nunca un consumer/ruta nueva. El frontend NUNCA habla
// con whatsapp_gateway/ directamente (regla dura de la Fase 17).
let ws = null;
let reconnectAttempts = 0;
const RECONNECT_BASE_MS = 3000;
const RECONNECT_MAX_MS = 30000;
function nextReconnectDelayMs() {
  const exp = Math.min(RECONNECT_BASE_MS * (2 ** reconnectAttempts), RECONNECT_MAX_MS);
  reconnectAttempts += 1;
  return exp * (0.5 + Math.random() * 0.5);
}

let heartbeatInterval = null;
let heartbeatTimeoutId = null;
const HEARTBEAT_INTERVAL_MS = 25000;
const HEARTBEAT_TIMEOUT_MS = 10000;
function stopHeartbeat() {
  if (heartbeatInterval) clearInterval(heartbeatInterval);
  if (heartbeatTimeoutId) clearTimeout(heartbeatTimeoutId);
  heartbeatInterval = null;
  heartbeatTimeoutId = null;
}
function startHeartbeat() {
  stopHeartbeat();
  heartbeatInterval = setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'ping' }));
    heartbeatTimeoutId = setTimeout(() => ws?.close(), HEARTBEAT_TIMEOUT_MS);
  }, HEARTBEAT_INTERVAL_MS);
}

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/';
const wsBase = apiBase.replace('/api/v1/', '').replace('http://', 'ws://').replace('https://', 'wss://');
let wsClosedByUs = false;

async function connectWs() {
  try {
    await refreshAccessToken();
  } catch {
    // Sesion admin realmente muerta -- no reintentar en loop silencioso,
    // mismo criterio que SupportDashboardView.vue::connectWs().
    return;
  }
  const url = `${wsBase}/ws/support/chat/?token=${authStore.accessToken}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    reconnectAttempts = 0;
    startHeartbeat();
  };

  ws.onmessage = (evt) => {
    let msg;
    try { msg = JSON.parse(evt.data); } catch { return; }
    if (msg.type === 'pong') {
      if (heartbeatTimeoutId) { clearTimeout(heartbeatTimeoutId); heartbeatTimeoutId = null; }
      return;
    }
    if (msg.type === 'whatsapp_status') {
      liveDetailedState.value = msg.status;
      if (data.value?.qr_web_session) {
        // Refleja tambien en el objeto principal para que 'connected'/'configured' del
        // resumen de arriba no queden desactualizados hasta el proximo GET.
        data.value.qr_web_session.status = msg.status;
      }
      if (msg.status === 'CONNECTED') currentQrImage.value = null;
      return;
    }
    if (msg.type === 'whatsapp_qr') {
      currentQrImage.value = msg.qr_image;
    }
  };

  ws.onclose = () => {
    stopHeartbeat();
    ws = null;
    if (!wsClosedByUs) setTimeout(connectWs, nextReconnectDelayMs());
  };

  ws.onerror = () => { ws?.close(); };
}

onMounted(() => {
  load();
  connectWs();
});

onUnmounted(() => {
  wsClosedByUs = true;
  stopHeartbeat();
  ws?.close();
});
</script>

<style scoped>
.wa-status-view { padding: 24px; max-width: 900px; }
.active-banner { padding: 12px 16px; border-radius: 10px; margin-bottom: 20px; font-size: 0.95rem; }
.active-banner.ok { background: #dcfce7; color: #166534; }
.active-banner.warn { background: #fef3c7; color: #92400e; }
.active-banner.fail { background: #fee2e2; color: #991b1b; }
.wa-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.wa-card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; }
.wa-card.active { border-color: #2563eb; box-shadow: 0 0 0 1px #2563eb; }
.wa-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.wa-card-note { font-size: 0.8rem; color: #6b7280; margin-bottom: 12px; }
.wa-experimental-warning {
  font-size: 0.78rem; color: #92400e; background: #fef3c7; border: 1px solid #fde68a;
  border-radius: 8px; padding: 8px 10px; margin-bottom: 12px; line-height: 1.4;
}
.wa-qr-box { text-align: center; margin-bottom: 14px; padding: 12px; border: 1px dashed #cbd5e1; border-radius: 10px; }
.wa-qr-box img { max-width: 220px; width: 100%; height: auto; }
.wa-qr-hint { font-size: 0.75rem; color: #6b7280; margin: 8px 0 0; }
.wa-actions { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.wa-config-row { display: flex; gap: 12px; margin-bottom: 10px; font-size: 0.85rem; font-weight: 600; }
.wa-caps-table { width: 100%; font-size: 0.85rem; }
.wa-caps-table td { padding: 3px 0; }
.cap-yes { color: #166534; font-weight: 600; }
.cap-no { color: #9ca3af; }
</style>
