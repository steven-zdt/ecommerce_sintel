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
                <span class="badge bg-light text-muted border">{{ typeLabel(quote) }}</span>
                <span class="text-muted small">{{ fmtDate(quote.created_at) }}</span>
              </div>
              <p class="quote-desc mb-0">{{ summaryLine(quote) }}</p>
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
              <span class="text-muted small fw-semibold">Respuesta de {{ brandName }}</span>
            </div>
            <p class="small mb-0">{{ quote.response }}</p>
          </div>
        </CustomerCard>
      </div>

      <CustomerPagination :page="page" :total-pages="totalPages" @update:page="changePage" />
    </template>

    <CustomerOverlayPanel v-model="showDetail" title="Detalle de cotizacion">
      <CustomerSkeleton v-if="loadingDetail" :count="2" height="60px" />
      <template v-else-if="selected">
        <div class="row g-3 mb-3">
          <div class="col-sm-6">
            <p class="text-muted small mb-0">Estado</p>
            <CustomerStatusBadge enum-name="quote-statuses" :value="selected.status" />
          </div>
          <div class="col-sm-6">
            <p class="text-muted small mb-0">Tipo</p>
            <p class="fw-semibold mb-0">{{ typeLabel(selected) }}</p>
          </div>
          <div class="col-sm-6">
            <p class="text-muted small mb-0">Fecha de solicitud</p>
            <p class="fw-semibold mb-0">{{ fmtDate(selected.created_at) }}</p>
          </div>
        </div>

        <template v-if="!selected.is_custom">
          <div class="mb-3">
            <p class="text-muted small mb-1">Items cotizados</p>
            <div class="desc-box">
              <div v-for="item in allQuoteItems(selected)" :key="item.uuid" class="d-flex justify-content-between">
                <span>{{ item.name }} <span class="text-muted">x{{ item.quantity }}</span></span>
                <span>${{ fmtMoney(item.subtotal) }}</span>
              </div>
            </div>
          </div>
          <div class="d-flex justify-content-between fw-semibold mb-3">
            <span>Total</span>
            <span>${{ fmtMoney(selected.total_amount) }}</span>
          </div>
        </template>
        <template v-else>
          <div class="mb-3">
            <p class="text-muted small mb-1">Detalle de la solicitud</p>
            <div class="desc-box">
              <div v-if="selected.project_name">Proyecto: {{ selected.project_name }}</div>
              <div v-if="selected.company">Empresa: {{ selected.company }}</div>
              <div v-if="selected.phone">Telefono: {{ selected.phone }}</div>
              <div v-if="selected.address">Direccion: {{ selected.address }}, {{ selected.city }}</div>
              <div v-if="selected.template_name">Plantilla: {{ selected.template_name }}</div>
              <div v-if="!selected.project_name && !selected.company && !selected.phone && !selected.address">
                {{ selected.notes || 'Sin informacion adicional.' }}
              </div>
            </div>
          </div>
        </template>
        <div v-if="selected.notes && !selected.is_custom" class="mb-3">
          <p class="text-muted small mb-1">Notas</p>
          <div class="desc-box">{{ selected.notes }}</div>
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
import { ref, computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';
import { useAppConfigStore } from '@/store/appConfig';
import { formatCOP } from '@/utils/money';
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
// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado.
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'la plataforma');

const loading = ref(true);
const loadError = ref(false);
const quotes = ref([]);
const page = ref(1);
const totalPages = ref(1);
const pageSize = 10;
const selected = ref(null);
const showDetail = ref(false);
const loadingDetail = ref(false);

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

async function viewDetail(quote) {
  // El endpoint de lista usa un serializer liviano (sin items/services/rental_items
  // ni los campos del cuestionario) -- hay que pedir el detalle completo antes de
  // mostrar el panel, o "Items cotizados"/"Detalle de la solicitud" salen vacios.
  showDetail.value = true;
  selected.value = quote;
  loadingDetail.value = true;
  try {
    const res = await api.get(`quotes/quotations/${quote.uuid}/`);
    selected.value = res.data;
  } catch {
    toast.error('Error al cargar el detalle de la cotizacion');
  } finally {
    loadingDetail.value = false;
  }
}

function downloadPdf(quote) {
  window.open(quote.pdf_url, '_blank');
}

// El modelo Quotation no tiene un campo `quote_type` -- solo `is_custom`
// distingue las 2 modalidades reales (ver quotes/CLAUDE.md: catalogo/legado
// con precio inmediato vs cuestionario tecnico revisado por un asesor).
const typeLabel = (q) => (q.is_custom ? 'Cuestionario tecnico' : 'Catalogo');
const fmtDate = (d) => d ? new Date(d).toLocaleDateString('es-CO') : '-';
const fmtMoney = (v) => formatCOP(v);

function allQuoteItems(quote) {
  const products = (quote.items || []).map(i => ({ uuid: i.uuid, name: i.product_name, quantity: i.quantity, subtotal: i.subtotal }));
  const services = (quote.services || []).map(s => ({ uuid: s.uuid, name: s.service_name, quantity: 1, subtotal: s.subtotal }));
  const rentals = (quote.rental_items || []).map(r => ({ uuid: r.uuid, name: r.equipment_name, quantity: r.computed_days, subtotal: r.subtotal }));
  return [...products, ...services, ...rentals];
}

function summaryLine(quote) {
  // El listado usa el serializer liviano: solo total_amount/template_name estan
  // disponibles aqui (items/company/etc. se piden aparte en viewDetail al abrir
  // el panel de detalle).
  if (!quote.is_custom) {
    return `Total cotizado: $${fmtMoney(quote.total_amount)}`;
  }
  return quote.template_name || 'Solicitud de cotizacion personalizada en revision.';
}

onMounted(() => {
  enums.preload(['quote-statuses']);
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
