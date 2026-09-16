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
      <div class="active-banner" :class="data.active.healthy ? 'ok' : 'fail'">
        Mecanismo activo: <strong>{{ data.active_connection_type }}</strong>
        &middot; {{ data.active.healthy ? 'Configurado y funcionando' : 'No configurado / con error' }}
        <span v-if="data.active_connection_type === 'REST'" class="hint">
          (REST no mantiene una sesion persistente que "conectar" -- el estado real relevante es
          "configurado y funcionando", no CONNECTED/DISCONNECTED como en una sesion QR)
        </span>
      </div>

      <div class="wa-cards">
        <div v-for="key in ['rest', 'qr']" :key="key" class="wa-card" :class="{ active: data.active_connection_type === key.toUpperCase() }">
          <div class="wa-card-header">
            <h4>{{ key.toUpperCase() }}</h4>
            <span class="badge" :class="statusClass(data[key].status)">{{ data[key].status }}</span>
          </div>
          <p v-if="key === 'qr'" class="wa-card-note">
            No existe ningun gateway QR real integrado hoy (ni Baileys, ni whatsapp-web.js, ni
            similar) -- este adapter cumple el mismo contrato que REST pero esta
            estructuralmente sin implementar a proposito. Integrarlo es una decision de producto
            (las librerias QR no son oficiales, riesgo real de baneo del numero por Meta).
          </p>
          <p v-else class="wa-card-note">
            Envuelve la integracion oficial de Meta Cloud API, la misma que ya usa produccion.
          </p>
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
import { ref, onMounted } from 'vue';
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
function statusClass(status) {
  if (status === 'CONNECTED') return 'bg-success';
  if (status === 'NOT_IMPLEMENTED') return 'bg-secondary';
  if (status === 'ERROR') return 'bg-danger';
  return 'bg-warning text-dark';
}

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
.active-banner.fail { background: #fee2e2; color: #991b1b; }
.active-banner .hint { display: block; font-size: 0.8rem; opacity: 0.8; margin-top: 4px; }
.wa-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.wa-card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; }
.wa-card.active { border-color: #2563eb; box-shadow: 0 0 0 1px #2563eb; }
.wa-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.wa-card-note { font-size: 0.8rem; color: #6b7280; margin-bottom: 12px; }
.wa-caps-table { width: 100%; font-size: 0.85rem; }
.wa-caps-table td { padding: 3px 0; }
.cap-yes { color: #166534; font-weight: 600; }
.cap-no { color: #9ca3af; }
</style>
