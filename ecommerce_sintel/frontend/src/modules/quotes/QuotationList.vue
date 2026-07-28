<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-4">
      <h4 class="fw-bold mb-0">Cotizaciones</h4>
    </div>

    <!-- Filtros -->
    <div class="row g-3 mb-4">
      <div class="col-md-5">
        <div class="input-group">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input 
            v-model="search" 
            class="form-control border-start-0 ps-0" 
            placeholder="Buscar por cliente o ID..." 
          />
        </div>
      </div>
      <div class="col-md-3">
        <select v-model="filters.status" class="form-select" @change="loadPage()">
          <option value="">Todos los estados</option>
          <option value="BORRADOR">Borrador</option>
          <option value="RECIBIDA">Recibida</option>
          <option value="EN_REVISION">En revisión</option>
          <option value="PENDIENTE_INFORMACION">Pendiente información</option>
          <option value="COTIZADA">Cotizada</option>
          <option value="ENVIADA">Enviada</option>
          <option value="ACEPTADA">Aceptada</option>
          <option value="RECHAZADA">Rechazada</option>
          <option value="VENCIDA">Vencida</option>
          <option value="CANCELADA">Cancelada</option>
        </select>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3" style="width: 120px">ID</th>
              <th class="py-3">Cliente</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end">Total</th>
              <th class="py-3 text-center">Vence</th>
              <th class="py-3 text-center">Creada</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando cotizaciones...</span>
              </td>
            </tr>
            <tr v-else-if="!items.length">
              <td colspan="7" class="text-center py-5 text-muted">
                <i class="bi bi-file-earmark-text fs-2 d-block mb-2"></i>
                Sin registros.
              </td>
            </tr>
            <tr v-for="item in items" :key="item.uuid">
              <td class="px-4">
                <code class="text-primary small fw-bold">#{{ item.uuid.slice(0, 8) }}</code>
              </td>
              <td>
                <div class="fw-semibold text-dark">
                  {{ item.client_name }}
                  <i
                    v-if="item.attachments_count"
                    class="bi bi-file-earmark-text-fill text-primary ms-1 small"
                    :title="`${item.attachments_count} documento(s) adjunto(s)`"
                  ></i>
                </div>
                <div class="text-muted smaller">{{ item.client_email }}</div>
              </td>
              <td class="text-center">
                <span 
                  class="badge border rounded-pill fw-medium"
                  :class="enums.cssClass('quote-statuses', item.status, 'bg-light text-secondary')"
                >
                  {{ enums.label('quote-statuses', item.status, item.status) }}
                </span>
              </td>
              <td class="text-end fw-bold text-dark">
                {{ formatCurrency(item.total_amount) }}
              </td>
              <td class="text-center">
                <span class="text-muted smaller">{{ formatDate(item.valid_until) }}</span>
              </td>
              <td class="text-center">
                <span class="text-muted smaller">{{ formatRelativeDate(item.created_at) }}</span>
              </td>
              <td class="text-end px-4">
                <div class="d-flex gap-2 justify-content-end">
                  <button 
                    class="btn btn-sm btn-light border rounded-circle" 
                    title="Ver detalle"
                    @click="openDetail(item)"
                  >
                    <i class="bi bi-eye"></i>
                  </button>
                  <button 
                    class="btn btn-sm btn-outline-danger border rounded-circle" 
                    title="Descargar PDF"
                    @click="downloadPdf(item)"
                    :disabled="pdfLoading === item.uuid"
                  >
                    <span v-if="pdfLoading === item.uuid" class="spinner-border spinner-border-sm"></span>
                    <i v-else class="bi bi-file-pdf"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div class="card-footer bg-white border-0 d-flex justify-content-between align-items-center py-3 px-4">
        <div class="text-muted smaller">
          {{ totalCount }} registros encontrados
        </div>
        <div class="d-flex gap-2">
          <button 
            class="btn btn-sm btn-light border" 
            :disabled="!prevPage || loading" 
            @click="loadPage(prevPage)"
          >
            <i class="bi bi-chevron-left"></i>
          </button>
          <button 
            class="btn btn-sm btn-light border" 
            :disabled="!nextPage || loading" 
            @click="loadPage(nextPage)"
          >
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Offcanvas Detalle -->
    <SintelOffcanvas
      v-model="showDetail"
      :title="(selected?.template_name ? 'Solicitud' : 'Cotización') + ' #' + (selected?.uuid.slice(0, 8) || '')"
      width="720px"
    >
      <RequestViewer v-if="selected?.template_name" :uuid="selected.uuid" />
      <QuotationDetail v-else-if="selected" :quotation="selected" @download="downloadPdf" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, reactive } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useEnums } from '@/composables/useEnums';
import { formatCOP } from '@/utils/money';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import QuotationDetail from './QuotationDetail.vue';
import RequestViewer from './RequestViewer.vue';

const api = useApi();
const toast = useToast();
const { show: showDetail, selected, openDetail } = useOffcanvas();
const enums = useEnums();

const items = ref([]);
const loading = ref(true);
const pdfLoading = ref(null);
const search = ref('');
const totalCount = ref(0);
const nextPage = ref(null);
const prevPage = ref(null);

const filters = reactive({
  status: ''
});


async function loadPage(url = null) {
  loading.value = true;
  try {
    const endpoint = url || buildEndpoint();
    const { data } = await api.get(endpoint);
    
    if (data.results !== undefined) {
      items.value = data.results;
      totalCount.value = data.count;
      nextPage.value = data.next ? extractPath(data.next) : null;
      prevPage.value = data.previous ? extractPath(data.previous) : null;
    } else {
      items.value = data;
      totalCount.value = data.length;
    }
  } catch (err) {
    console.error('Error cargando cotizaciones:', err);
    toast.error('Error cargando las cotizaciones.');
  } finally {
    loading.value = false;
  }
}

function buildEndpoint() {
  const params = new URLSearchParams();
  if (search.value) params.append('search', search.value);
  if (filters.status) params.append('status', filters.status);
  
  return `quotes/quotations/?${params.toString()}`;
}

function extractPath(fullUrl) {
  if (!fullUrl) return null;
  const match = fullUrl.match(/\/api\/v1\/(.*)/);
  return match ? match[1] : fullUrl;
}

async function downloadPdf(quotation) {
  pdfLoading.value = quotation.uuid;
  try {
    const response = await api.get(`quotes/quotations/${quotation.uuid}/download_pdf/`, {
      responseType: 'blob',
    });
    const url = URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cotizacion-${quotation.uuid.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('PDF descargado con éxito.');
  } catch (err) {
    console.error('Error descargando PDF:', err);
    toast.error('No se pudo descargar el PDF.');
  } finally {
    pdfLoading.value = null;
  }
}

function formatCurrency(value) {
  return formatCOP(value, { withSymbol: true });
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
}

function formatRelativeDate(dateStr) {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 3600000) return 'Hace poco';
  if (diff < 86400000) return `Hace ${Math.floor(diff / 3600000)}h`;
  return formatDate(dateStr);
}

let debounceTimer = null;
watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    loadPage();
  }, 400);
});

onMounted(() => { loadPage(); enums.ensure('quote-statuses'); });
</script>

<style scoped>
.smaller {
  font-size: 0.75rem;
}
</style>
