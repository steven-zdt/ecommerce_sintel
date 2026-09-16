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
            <span class="badge" :class="statusClass(data[key])">{{ statusLabel(data[key]) }}</span>
          </div>

          <div v-if="key === 'qr_web_session'" class="wa-experimental-warning">
            <strong>EXPERIMENTAL &middot; TERCERO &middot; NO ES LA API OFICIAL DE META.</strong>
            Simula una sesion tipo WhatsApp Web via un mecanismo QR no oficial (ej. Baileys/
            whatsapp-web.js). Hoy no hay ningun gateway real conectado -- ver
            <code>AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md</code>: bloqueado explicitamente
            para el numero de produccion real, por riesgo de perder tambien la integracion
            oficial (Meta Cloud API) que ya funciona en ese mismo numero.
          </div>
          <p v-else class="wa-card-note">
            Integracion oficial de WhatsApp Business Platform (Meta Cloud API) -- la misma que ya
            usa produccion.
          </p>

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
import { ref, onMounted, computed } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const api = useApi();
const toast = useToast();
const data = ref(null);
const loading = ref(true);

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

// FASE 19-21 de la mision: nunca mostrar "Disconnected" cuando en realidad
// nunca se configuro nada -- estados distintos, texto distinto.
const STATUS_LABELS = {
  NOT_CONFIGURED: 'No configurado',
  NOT_IMPLEMENTED: 'No implementado (sin gateway real)',
  CONNECTED: 'Conectado',
  DISCONNECTED: 'Desconectado',
  ERROR: 'Error',
  PAIRING_REQUIRED: 'Requiere emparejamiento',
};
function statusLabel(entry) {
  return STATUS_LABELS[entry.status] || entry.status;
}
function statusClass(entry) {
  if (entry.status === 'CONNECTED') return 'bg-success';
  if (entry.status === 'NOT_CONFIGURED' || entry.status === 'NOT_IMPLEMENTED') return 'bg-secondary';
  if (entry.status === 'ERROR') return 'bg-danger';
  return 'bg-warning text-dark';
}

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
  } catch {
    toast.error('Error al cargar el estado de WhatsApp');
  } finally {
    loading.value = false;
  }
}

onMounted(load);
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
.wa-config-row { display: flex; gap: 12px; margin-bottom: 10px; font-size: 0.85rem; font-weight: 600; }
.wa-caps-table { width: 100%; font-size: 0.85rem; }
.wa-caps-table td { padding: 3px 0; }
.cap-yes { color: #166534; font-weight: 600; }
.cap-no { color: #9ca3af; }
</style>
