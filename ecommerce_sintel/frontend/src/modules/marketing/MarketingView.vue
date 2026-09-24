<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-4">
      <h4 class="fw-bold mb-0">Marketing e Inteligencia</h4>
      <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
        <router-link :to="{ name: 'home' }" class="btn btn-outline-secondary rounded-pill px-3">
          <i class="bi bi-globe2 me-1"></i> Ver Landing
        </router-link>
        <button class="btn btn-outline-primary rounded-pill px-3" @click="loadData">
          <i class="bi bi-arrow-clockwise me-1"></i> Sincronizar
        </button>
        <button v-if="activeTab === 'campaigns'" class="btn btn-primary rounded-pill px-3" @click="openCreate()">
          <i class="bi bi-plus-lg me-1"></i> Nueva Campaña
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-pills mb-4 bg-white p-1 rounded-pill shadow-sm border d-inline-flex">
      <li class="nav-item">
        <button 
          class="nav-link rounded-pill px-4" 
          :class="{ active: activeTab === 'campaigns' }" 
          @click="activeTab = 'campaigns'"
        >
          Campañas
        </button>
      </li>
      <li class="nav-item">
        <button 
          class="nav-link rounded-pill px-4" 
          :class="{ active: activeTab === 'offers' }" 
          @click="activeTab = 'offers'"
        >
          Ofertas Flash
        </button>
      </li>
      <li class="nav-item">
        <button 
          class="nav-link rounded-pill px-4" 
          :class="{ active: activeTab === 'agent' }" 
          @click="activeTab = 'agent'"
        >
          Agente IA
        </button>
      </li>
    </ul>

    <div class="marketing-actions card border-0 shadow-sm mb-4">
      <div class="card-body d-flex flex-wrap gap-2 align-items-center justify-content-between">
        <div>
          <div class="fw-semibold text-dark">Acciones de publicación</div>
          <div class="text-muted small">Lo que se administra aquí termina en Cache, API pública y Landing.</div>
        </div>
        <div class="d-flex gap-2 flex-wrap">
          <button class="btn btn-sm btn-outline-primary rounded-pill" @click="activeTab = 'campaigns'">
            <i class="bi bi-megaphone me-1"></i> Campañas
          </button>
          <button class="btn btn-sm btn-outline-warning rounded-pill" @click="activeTab = 'offers'">
            <i class="bi bi-lightning-charge me-1"></i> Ofertas
          </button>
          <button class="btn btn-sm btn-outline-success rounded-pill" @click="activeTab = 'agent'">
            <i class="bi bi-robot me-1"></i> Agente IA
          </button>
        </div>
      </div>
    </div>

    <!-- Sección Campañas -->
    <div v-if="activeTab === 'campaigns'" class="tab-content">
      <div class="card border-0 shadow-sm overflow-hidden">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="bg-light small text-uppercase fw-semibold">
              <tr>
                <th class="px-4 py-3">Título</th>
                <th class="py-3">Canales</th>
                <th class="py-3">Programada</th>
                <th class="py-3 text-center">Estado</th>
                <th class="py-3 text-center">Logs</th>
                <th class="py-3 text-end px-4">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="6" class="text-center py-5"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>
              <tr v-else-if="!campaigns.length"><td colspan="6" class="text-center py-5 text-muted">Sin campañas activas.</td></tr>
              <tr v-for="camp in campaigns" :key="camp.uuid">
                <td class="px-4">
                  <div class="fw-semibold text-dark">{{ camp.title }}</div>
                  <div class="text-muted smaller text-truncate" style="max-width: 200px;">{{ camp.content }}</div>
                </td>
                <td>
                  <div class="d-flex gap-1">
                    <span v-for="ch in camp.channels" :key="ch" class="badge bg-light text-dark border smaller">
                      {{ ch }}
                    </span>
                  </div>
                </td>
                <td>{{ formatDate(camp.scheduled_at) }}</td>
                <td class="text-center">
                  <span class="badge rounded-pill" :class="statusClass(camp)">
                    {{ statusLabel(camp) }}
                  </span>
                </td>
                <td class="text-center">
                  <span class="badge bg-secondary-subtle text-secondary rounded-circle" style="width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center;">
                    {{ camp.logs?.length || 0 }}
                  </span>
                </td>
                <td class="text-end px-4">
                  <div class="d-flex gap-2 justify-content-end">
                    <button class="btn btn-sm btn-outline-primary border" title="Previsualizar y enviar" @click="openDispatch(camp)"><i class="bi bi-send"></i></button>
                    <button class="btn btn-sm btn-light border" @click="openEdit(camp)"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger border" @click="deleteCampaign(camp)"><i class="bi bi-trash"></i></button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Sección Ofertas Flash -->
    <div v-if="activeTab === 'offers'" class="tab-content">
      <div class="card border-0 shadow-sm overflow-hidden">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="bg-light small text-uppercase fw-semibold">
              <tr>
                <th class="px-4 py-3">Oferta</th>
                <th class="py-3 text-center">Descuento</th>
                <th class="py-3">Desde</th>
                <th class="py-3">Hasta</th>
                <th class="py-3 text-center">Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="5" class="text-center py-5"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>
              <tr v-else-if="!offers.length"><td colspan="5" class="text-center py-5 text-muted">Sin ofertas flash.</td></tr>
              <tr v-for="off in offers" :key="off.uuid">
                <td class="px-4">
                  <div class="fw-semibold text-dark">{{ off.name }}</div>
                  <div class="text-muted smaller">{{ off.description }}</div>
                </td>
                <td class="text-center">
                  <span class="badge bg-danger text-white rounded-pill fw-bold fs-6">
                    {{ Math.floor(off.discount_percentage) }}%
                  </span>
                </td>
                <td>{{ formatDate(off.start_time) }}</td>
                <td>{{ formatDate(off.end_time) }}</td>
                <td class="text-center">
                  <span class="badge rounded-pill" :class="off.is_active ? 'bg-success text-white' : 'bg-secondary text-white'">
                    {{ off.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Sección Agente IA -->
    <div v-if="activeTab === 'agent'" class="tab-content">
      <div class="card border-0 shadow-sm overflow-hidden">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="bg-light small text-uppercase fw-semibold">
              <tr>
                <th class="px-4 py-3">Disparador</th>
                <th class="py-3">Proveedor LLM</th>
                <th class="py-3">Fecha Ejecución</th>
                <th class="py-3 text-center">Estado</th>
                <th class="py-3 text-end px-4">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="5" class="text-center py-5"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>
              <tr v-else-if="!agentRuns.length"><td colspan="5" class="text-center py-5 text-muted">No hay registros del agente.</td></tr>
              <tr v-for="run in agentRuns" :key="run.uuid">
                <td class="px-4">
                  <span class="badge bg-light text-dark border text-uppercase smaller">{{ run.triggered_by }}</span>
                </td>
                <td>
                  <div class="d-flex align-items-center">
                    <img v-if="run.llm_provider === 'gemini'" src="https://www.gstatic.com/lamda/images/favicon_v2_16x16.png" class="me-2" style="width: 16px;" />
                    <span class="text-capitalize">{{ run.llm_provider }}</span>
                  </div>
                </td>
                <td>{{ formatRelativeDate(run.created_at) }}</td>
                <td class="text-center">
                  <span class="badge rounded-pill bg-success-subtle text-success">
                    {{ run.status }}
                  </span>
                </td>
                <td class="text-end px-4">
                  <button class="btn btn-sm btn-outline-primary rounded-pill" @click="openDetail(run)">
                    Ver Decisión
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Offcanvas para Formularios y Detalles -->
    <SintelOffcanvas 
      v-model="showOffcanvas" 
      :title="offcanvasTitle"
      :width="offcanvasWidth"
      class="marketing-offcanvas"
    >
      <Transition name="fade" mode="out-in">
        <CampaignForm 
          v-if="offcanvasType === 'campaign'" 
          :key="`campaign-${mode}-${selected?.uuid}`"
          :campaign="selected" 
          :mode="mode"
          @saved="onCampaignSaved" 
        />
        <CampaignDispatchPanel
          v-else-if="offcanvasType === 'dispatch'"
          :key="`dispatch-${selected?.uuid}`"
          :campaign="selected"
          @sent="loadData"
        />
        <AgentRunDetail
          v-else-if="offcanvasType === 'agent'" 
          :key="`agent-${selected?.uuid}`"
          :run="selected" 
        />
      </Transition>
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, Transition } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useMarketingAdminStore } from '@/store/marketingAdmin';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import CampaignForm from './CampaignForm.vue';
import AgentRunDetail from './AgentRunDetail.vue';
import CampaignDispatchPanel from './CampaignDispatchPanel.vue';
const toast = useToast();
const activeTab = ref('campaigns');
const { show: showOffcanvas, mode, selected, openCreate, openEdit, openDetail } = useOffcanvas();
const store = useMarketingAdminStore();
const { campaigns, offers, agentRuns, loading } = storeToRefs(store);

const offcanvasType = ref('');

const offcanvasTitle = computed(() => {
  if (offcanvasType.value === 'dispatch') return 'Previsualizar y Enviar';
  if (offcanvasType.value === 'campaign') {
    return mode.value === 'create' ? 'Nueva Campaña' : 'Editar Campaña';
  }
  return 'Detalle de Ejecución IA';
});

const offcanvasWidth = computed(() => {
  // Hacer el offcanvas un poco más ancho para acomodar mejor el JSON
  return offcanvasType.value === 'agent' ? '640px' : '560px';
});

async function loadData() {
  await store.fetchAll();
  if (store.error) toast.error(store.error);
}

async function deleteCampaign(camp) {
  if (!confirm('¿Seguro que desea eliminar esta campaña?')) return;
  const res = await store.deleteCampaign(camp.uuid);
  if (res.ok) toast.success('Campaña eliminada.'); else toast.error('No se pudo eliminar la campaña.');
}

// openDetail() abre el offcanvas en modo 'detail'; el watcher de abajo decide el tipo segun
// esta bandera (mismo mecanismo que ya usa el tab activo).
let dispatchPending = false;
function openDispatch(camp) {
  dispatchPending = true;
  openDetail(camp);
}

const STATUS_LABELS = { DRAFT: 'Borrador', SCHEDULED: 'Programada', RUNNING: 'En envío', COMPLETED: 'Completada' };
const STATUS_CLASSES = {
  DRAFT: 'bg-secondary-subtle text-secondary',
  SCHEDULED: 'bg-info-subtle text-info',
  RUNNING: 'bg-warning-subtle text-warning',
  COMPLETED: 'bg-success-subtle text-success',
};
function statusLabel(camp) {
  return STATUS_LABELS[camp.status] || (camp.is_completed ? 'Completada' : 'Pendiente');
}
function statusClass(camp) {
  return STATUS_CLASSES[camp.status] || 'bg-info-subtle text-info';
}

function onCampaignSaved() {
  showOffcanvas.value = false;
  loadData();
}

// Sincronizar tipo de offcanvas con tab activo
watch([showOffcanvas, mode], ([isOpen, newMode]) => {
  if (isOpen && newMode) {
    // Detectar tipo basado en el tab activo al abrir offcanvas
    if (dispatchPending) {
      offcanvasType.value = 'dispatch';
      dispatchPending = false;
    } else if (activeTab.value === 'campaigns') {
      offcanvasType.value = 'campaign';
    } else if (activeTab.value === 'agent') {
      offcanvasType.value = 'agent';
    }
  }
}, { immediate: false });

function formatDate(dateStr) {
  if (!dateStr) return 'No definida';
  return new Date(dateStr).toLocaleString('es-CO', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatRelativeDate(dateStr) {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  if (diff < 3600000) return 'Hace unos minutos';
  return date.toLocaleDateString();
}

onMounted(loadData);
</script>

<style scoped>
.smaller { font-size: 0.75rem; }

.nav-pills .nav-link.active {
  background-color: var(--bs-primary);
  color: white;
}

.nav-pills .nav-link {
  color: var(--bs-gray-600);
}

.marketing-actions {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.marketing-offcanvas :deep(.offcanvas) {
  animation: slideInRight 0.3s ease-out;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease-in-out;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (max-width: 768px) {
  .marketing-offcanvas :deep(.offcanvas) {
    width: 90vw !important;
    max-width: 100% !important;
  }
}
</style>
