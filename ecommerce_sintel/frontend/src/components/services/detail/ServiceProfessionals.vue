<template>
  <div v-if="technicians.length" class="sv-pro-grid">
    <article v-for="tech in technicians" :key="tech.uuid" class="sv-pro-card">
      <div class="sv-pro-avatar">
        <img v-if="tech.avatar" :src="tech.avatar" :alt="tech.full_name">
        <span v-else>{{ initials(tech.full_name) }}</span>
      </div>
      <div>
        <strong>{{ tech.full_name }}</strong>
        <span class="sv-pro-role"><i class="bi bi-patch-check-fill me-1"></i>Tecnico certificado</span>
      </div>
    </article>
  </div>
  <p v-else-if="!loading" class="sv-pro-empty">
    Nuestro equipo asigna un tecnico calificado segun disponibilidad al confirmar tu solicitud.
  </p>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';

const props = defineProps({
  serviceUuid: { type: String, required: true },
});

const api = useApi();
const technicians = ref([]);
const loading = ref(false);

function initials(name) {
  return (name || '').trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('');
}

async function fetchTechnicians() {
  if (!props.serviceUuid) return;
  loading.value = true;
  try {
    const res = await api.get(`services/services/${props.serviceUuid}/technicians/`);
    technicians.value = res.data.results || res.data;
  } catch {
    technicians.value = [];
  } finally {
    loading.value = false;
  }
}

watch(() => props.serviceUuid, fetchTechnicians, { immediate: true });
</script>

<style scoped>
.sv-pro-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: .75rem;
}
.sv-pro-card {
  display: flex; align-items: center; gap: .7rem;
  border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 14px;
  padding: .85rem;
}
.sv-pro-avatar {
  width: 48px; height: 48px; border-radius: 50%; overflow: hidden; flex-shrink: 0;
  background: #fef3c7; color: #92400e;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: .95rem;
}
.sv-pro-avatar img { width: 100%; height: 100%; object-fit: cover; }
.sv-pro-card strong { display: block; color: #0f172a; font-size: .88rem; font-weight: 800; }
.sv-pro-role { display: block; color: #0f766e; font-size: .74rem; font-weight: 700; margin-top: .15rem; }
.sv-pro-empty { color: #64748b; font-size: .88rem; }
</style>
