<template>
  <CustomerAccountShell max-width="900px">
    <RouterLink to="/mi-cuenta/operaciones" class="back-link">
      <i class="bi bi-arrow-left"></i> Mis operaciones
    </RouterLink>

    <CustomerSkeleton v-if="loading" :count="2" height="120px" />
    <CustomerErrorState v-else-if="error" :description="error" @retry="fetchTicket" />

    <template v-else-if="ticket">
      <CustomerCard class="ticket-header-card">
        <div class="ticket-header">
          <div>
            <h2 class="ticket-number">{{ ticket.ticket_number }}</h2>
            <CustomerStatusBadge enum-name="operation-statuses" :value="ticket.status" />
          </div>
          <div class="ticket-meta">
            <CustomerStatusBadge enum-name="operation-types" :value="ticket.operation_type" />
            <span v-if="ticket.scheduled_date" class="meta-date">
              <i class="bi bi-calendar3"></i> {{ formatDate(ticket.scheduled_date) }}
              <template v-if="ticket.scheduled_time_start">
                {{ ticket.scheduled_time_start }} &ndash; {{ ticket.scheduled_time_end }}
              </template>
            </span>
          </div>
        </div>
      </CustomerCard>

      <CustomerSection title="Seguimiento" icon="bi-clock-history">
        <TrackingTimeline :events="timeline" />
      </CustomerSection>

      <CustomerSection v-if="showDocUpload" title="Documentos requeridos" icon="bi-file-earmark-text">
        <DocumentUploader
          :ticket-uuid="ticket.uuid"
          :operation-type="ticket.operation_type"
          @uploaded="onDocUploaded"
        />
        <div class="doc-list" v-if="ticket.documents?.length">
          <div v-for="doc in ticket.documents" :key="doc.uuid" class="doc-row">
            <i class="bi bi-file-earmark-check"></i>
            <span>{{ docTypeLabel(doc.doc_type) }}</span>
            <span class="doc-status" :class="`doc--${doc.status.toLowerCase()}`">
              {{ doc.status }}
            </span>
          </div>
        </div>
      </CustomerSection>

      <CustomerSection v-if="canReview" title="Califica tu experiencia" icon="bi-star">
        <OperationReviewModal :ticket="ticket" @reviewed="fetchTicket" />
      </CustomerSection>
    </template>
  </CustomerAccountShell>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { useOperationTracking } from '@/composables/useOperationTracking';
import TrackingTimeline from '@/components/customer/ui/TrackingTimeline.vue';
import DocumentUploader from '@/components/customer/ui/DocumentUploader.vue';
import OperationReviewModal from '@/components/customer/ui/OperationReviewModal.vue';
import { useEnums } from '@/composables/useEnums';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerSection from '@/components/customer/account/CustomerSection.vue';
import CustomerStatusBadge from '@/components/customer/account/CustomerStatusBadge.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';

const route = useRoute();
const uuid = route.params.uuid;
const enums = useEnums();
enums.preload(['operation-statuses', 'operation-types']);

const { ticket, timeline, loading, error, fetchTicket } = useOperationTracking(uuid);

const showDocUpload = computed(() => ticket.value?.status === 'DOCS_PENDING');
const canReview = computed(() => ticket.value?.status === 'COMPLETED' && !ticket.value?.review);

async function onDocUploaded() {
  await fetchTicket();
}

const DOC_TYPE_LABELS = {
  ID_CARD: 'Cedula de identidad',
  RENTAL_CONTRACT: 'Contrato de alquiler',
  SERVICE_CONTRACT: 'Contrato de servicios',
  INVOICE: 'Factura',
  OTHER: 'Otro',
};
const docTypeLabel = (d) => DOC_TYPE_LABELS[d] ?? d;

function formatDate(d) {
  if (!d) return '';
  return new Date(d + 'T00:00:00').toLocaleDateString('es-CO', {
    weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
  });
}
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--acc-accent, #2563eb);
  text-decoration: none;
  font-size: 0.875rem;
  margin-bottom: 20px;
}
.back-link:hover { text-decoration: underline; }

.ticket-header-card { margin-bottom: 16px; }

.ticket-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
}

.ticket-number {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--acc-text, #111827);
  margin: 0 0 8px;
}

.ticket-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.meta-date {
  font-size: 0.82rem;
  color: var(--acc-muted, #6b7280);
}
.meta-date .bi { margin-right: 4px; }

.doc-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.doc-row {
  display: flex; align-items: center; gap: 10px;
  background: #f9fafb; border-radius: 8px; padding: 10px 14px;
  font-size: 0.875rem;
}
.doc-row .bi { color: #6b7280; }
.doc-status {
  margin-left: auto; font-size: 0.75rem; font-weight: 600; padding: 2px 8px;
  border-radius: 99px;
}
.doc--approved { background: #dcfce7; color: #166534; }
.doc--pending { background: #fef3c7; color: #92400e; }
.doc--rejected { background: #fee2e2; color: #991b1b; }
</style>
