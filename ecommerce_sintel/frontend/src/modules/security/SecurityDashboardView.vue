<template>
  <div class="security-dashboard">
    <div class="sec-header">
      <h2>Centro de Seguridad</h2>
      <div class="health-banner">
        <span class="health-pill" :class="health.db ? 'ok' : 'fail'">DB {{ health.db ? 'OK' : 'FALLO' }}</span>
        <span class="health-pill" :class="health.redis ? 'ok' : 'fail'">Redis {{ health.redis ? 'OK' : 'FALLO' }}</span>
        <span class="health-pill" :class="health.celery ? 'ok' : 'fail'">Celery {{ health.celery ? 'OK' : 'FALLO' }}</span>
      </div>
    </div>

    <div class="sec-filters">
      <select v-model="filters.event_type" class="form-select form-select-sm" @change="load">
        <option value="">Todos los tipos</option>
        <option value="LOGIN_SUCCESS">Login exitoso</option>
        <option value="LOGIN_FAILED">Login fallido</option>
        <option value="KYC_REJECTED">KYC rechazado</option>
        <option value="KYC_BLOCKED">KYC bloqueado</option>
        <option value="RATE_LIMIT_HIT">Limite de tasa</option>
        <option value="FILE_REJECTED">Archivo rechazado</option>
      </select>
      <select v-model="filters.severity" class="form-select form-select-sm" @change="load">
        <option value="">Toda severidad</option>
        <option value="INFO">Info</option>
        <option value="WARNING">Advertencia</option>
        <option value="CRITICAL">Critico</option>
      </select>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>
    <div v-else class="table-responsive">
      <table class="table table-sm sec-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Tipo</th>
            <th>Severidad</th>
            <th>Usuario</th>
            <th>IP</th>
            <th>Ruta</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ev in events" :key="ev.uuid">
            <td>{{ formatDate(ev.created_at) }}</td>
            <td>{{ ev.event_type }}</td>
            <td><span class="badge" :class="severityClass(ev.severity)">{{ ev.severity }}</span></td>
            <td>{{ ev.user_email || '-' }}</td>
            <td>{{ ev.ip_address || '-' }}</td>
            <td class="text-truncate" style="max-width: 220px;">{{ ev.path }}</td>
          </tr>
          <tr v-if="events.length === 0">
            <td colspan="6" class="text-center text-muted py-4">Sin eventos registrados.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import useApi from '@/composables/useApi';

const api = useApi();
const events = ref([]);
const loading = ref(false);
const health = ref({ db: true, redis: true, celery: true });
const filters = reactive({ event_type: '', severity: '' });

function severityClass(sev) {
  if (sev === 'CRITICAL') return 'bg-danger';
  if (sev === 'WARNING') return 'bg-warning text-dark';
  return 'bg-secondary';
}

function formatDate(value) {
  return new Date(value).toLocaleString('es-CO');
}

async function load() {
  loading.value = true;
  try {
    const params = {};
    if (filters.event_type) params.event_type = filters.event_type;
    if (filters.severity) params.severity = filters.severity;
    const { data } = await api.get('dashboard/security-events/', { params });
    events.value = data.results || data;
  } catch (_) {
    events.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadHealth() {
  try {
    const { data } = await api.get('dashboard/security-events/health/');
    health.value = data;
  } catch (_) {
    health.value = { db: false, redis: false, celery: false };
  }
}

onMounted(() => {
  load();
  loadHealth();
});
</script>

<style scoped>
.security-dashboard { padding: 24px; }
.sec-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.health-banner { display: flex; gap: 8px; }
.health-pill { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.health-pill.ok { background: #dcfce7; color: #166534; }
.health-pill.fail { background: #fee2e2; color: #991b1b; }
.sec-filters { display: flex; gap: 10px; margin-bottom: 12px; max-width: 400px; }
.sec-table { background: #fff; }
</style>
