<template>
  <CustomerAccountShell max-width="900px">
    <CustomerPageHeader title="Cotizaciones" subtitle="Historial de solicitudes de cotizacion.">
      <template #actions>
        <CustomerButton variant="primary" @click="$router.push('/cotizar')">
          <i class="bi bi-plus-circle me-1"></i>Nueva cotizacion
        </CustomerButton>
      </template>
    </CustomerPageHeader>

    <CustomerSkeleton v-if="loading" :count="3" height="110px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchQuotes" />

    <CustomerEmptyState
      v-else-if="quotes.length === 0"
      icon="bi-file-earmark-text"
      title="Aun no tienes cotizaciones"
      description="Solicita una cotizacion para productos, equipos o servicios."
    >
      <template #action>
        <RouterLink to="/cotizar" class="btn btn-primary">Solicitar cotizacion</RouterLink>
      </template>
    </CustomerEmptyState>

    <template v-else>
      <div class="quotes-list">
        <CustomerCard v-for="quote in quotes" :key="quote.uuid">
          <div class="d-flex align-items-start justify-content-between gap-3 flex-wrap">
            <div class="flex-grow-1">
              <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                <span class="fw-semibold small">#{{ quote.uuid.slice(0, 8) }}</span>
                <CustomerStatusBadge enum-name="quote-statuses" :value="quote.status" />
                <span class="badge bg-light text-muted border">{{ typeLabel(quote.quote_type) }}</span>
                <span class="text-muted small">{{ fmtDate(quote.created_at) }}</span>
              </div>
              <p class="quote-desc mb-0">{{ truncate(quote.description, 140) }}</p>
              <div v-if="quote.desired_date" class="mt-1">
                <span class="text-muted small">
                  <i class="bi bi-calendar3 me-1"></i>Fecha deseada: {{ fmtDate(quote.desired_date) }}
                </span>
              </div>
            </div>

            <div class="d-flex gap-2 flex-shrink-0">
              <CustomerButton v-if="quote.pdf_url" variant="icon" aria-label="Descargar PDF" @click="downloadPdf(quote)">
                <i class="bi bi-file-earmark-pdf"></i>
              </CustomerButton>
              <CustomerButton variant="secondary" @click="viewDetail(quote)">
                <i class="bi bi-eye me-1"></i>Ver detalle
              </CustomerButton>
            </div>
          </div>

          <div v-if="quote.response" class="quote-response mt-3">
            <div class="d-flex align-items-center gap-2 mb-1">
              <i class="bi bi-chat-left-text text-primary small"></i>
              <span class="text-muted small fw-semibold">Respuesta de Sintel</span>
            </div>
            <p class="small mb-0">{{ quote.response }}</p>
          </div>
        </CustomerCard>
      </div>

      <CustomerPagination :page="page" :total-pages="totalPages" @update:page="changePage" />
    </template>

    <CustomerOverlayPanel v-model="showDetail" title="Detalle de cotizacion">
      <template v-if="selected">
        <div class="row g-3 mb-3">
          <div class="col-sm-6">
            <p class="text-muted small mb-0">Estado</p>
            <CustomerStatusBadge enum-name="quote-statuses" :value="selected.status" />
          </div>
          <div class="col-sm-6">
            <p class="text-muted small mb-0">Tipo</p>
            <p class="fw-semibold mb-0">{{ typeLabel(selected.quote_type) }}</p>
          </div>
          <div class="col-sm-6">
            <p class="text-muted small mb-0">Fecha de solicitud</p>
            <p class="fw-semibold mb-0">{{ fmtDate(selected.created_at) }}</p>
          </div>
          <div v-if="selected.desired_date" class="col-sm-6">
            <p class="text-muted small mb-0">Fecha deseada</p>
            <p class="fw-semibold mb-0">{{ fmtDate(selected.desired_date) }}</p>
          </div>
        </div>
        <div class="mb-3">
          <p class="text-muted small mb-1">Descripcion</p>
          <div class="desc-box">{{ selected.description }}</div>
        </div>
        <div v-if="selected.response" class="mb-3">
          <p class="text-muted small mb-1">Respuesta</p>
          <div class="desc-box response-box">{{ selected.response }}</div>
        </div>
        <div v-if="selected.pdf_url" class="d-flex justify-content-end">
          <a :href="selected.pdf_url" target="_blank" class="btn btn-sm btn-outline-danger">
            <i class="bi bi-file-earmark-pdf me-2"></i>Descargar PDF
          </a>
        </div>
      </template>
    </CustomerOverlayPanel>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerStatusBadge from '@/components/customer/account/CustomerStatusBadge.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';
import CustomerOverlayPanel from '@/components/customer/account/CustomerOverlayPanel.vue';
import CustomerPagination from '@/components/customer/account/CustomerPagination.vue';

const api = useApi();
const toast = useToast();
const enums = useEnums();

const loading = ref(true);
const loadError = ref(false);
const quotes = ref([]);
const page = ref(1);
const totalPages = ref(1);
const pageSize = 10;
const selected = ref(null);
const showDetail = ref(false);

async function fetchQuotes() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await api.get('quotes/quotations/', { params: { page: page.value, page_size: pageSize } });
    quotes.value = res.data.results || res.data || [];
    const total = res.data.count || quotes.value.length;
    totalPages.value = Math.max(1, Math.ceil(total / pageSize));
  } catch {
    loadError.value = true;
    toast.error('Error al cargar cotizaciones');
  } finally {
    loading.value = false;
  }
}

function changePage(p) {
  if (p < 1 || p > totalPages.value) return;
  page.value = p;
  fetchQuotes();
}

function viewDetail(quote) {
  selected.value = quote;
  showDetail.value = true;
}

function downloadPdf(quote) {
  window.open(quote.pdf_url, '_blank');
}

const typeLabel = (t) => enums.label('quote-types', t, t);
const fmtDate = (d) => d ? new Date(d).toLocaleDateString('es-CO') : '-';
const truncate = (str, len) => str?.length > len ? str.slice(0, len) + '...' : (str || '');

onMounted(() => {
  enums.preload(['quote-statuses', 'quote-types']);
  fetchQuotes();
});
</script>

<style scoped>
.quotes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quote-desc { color: #374151; font-size: 0.9rem; line-height: 1.5; }
.quote-response {
  background: var(--acc-accent-bg, #eff6ff);
  border: 1px solid #bfdbfe;
  border-radius: var(--acc-radius-sm, 10px);
  padding: 12px;
}
.desc-box {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-wrap;
}
.response-box { background: var(--acc-accent-bg, #eff6ff); border-color: #bfdbfe; }
</style>
