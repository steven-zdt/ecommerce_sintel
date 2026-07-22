<template>
  <CustomerAccountShell max-width="900px">
    <CustomerPageHeader title="Mis operaciones" subtitle="Seguimiento de entregas, alquileres y servicios." />

    <CustomerSkeleton v-if="loading" :count="3" height="90px" />
    <CustomerErrorState v-else-if="loadError" @retry="loadOperations" />

    <CustomerEmptyState
      v-else-if="!operations.length"
      icon="bi-truck"
      title="Aun no tienes operaciones registradas"
      description="Cuando tengas una compra, alquiler o servicio en curso, aparecera aqui con su seguimiento."
    />

    <div v-else class="ops-list">
      <CustomerCard
        v-for="op in operations"
        :key="op.uuid"
        tag="RouterLink"
        :to="`/mi-cuenta/operaciones/${op.uuid}`"
        class="op-card"
      >
        <div class="op-card-row">
          <div class="op-card-badges">
            <CustomerStatusBadge enum-name="operation-types" :value="op.operation_type" />
            <CustomerStatusBadge enum-name="operation-statuses" :value="op.status" />
          </div>
          <div class="op-card-body">
            <p class="op-ticket">{{ op.ticket_number }}</p>
            <p v-if="op.scheduled_date" class="op-date">
              <i class="bi bi-calendar3 me-1"></i>{{ formatDate(op.scheduled_date) }}
            </p>
          </div>
          <i class="bi bi-chevron-right op-chevron"></i>
        </div>
      </CustomerCard>
    </div>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { operationsService } from '@/services/operations/operationsService';
import { useEnums } from '@/composables/useEnums';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerStatusBadge from '@/components/customer/account/CustomerStatusBadge.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';

const enums = useEnums();
const operations = ref([]);
const loading = ref(true);
const loadError = ref(false);

async function loadOperations() {
  loading.value = true;
  loadError.value = false;
  try {
    const data = await operationsService.myOperations();
    operations.value = data.results ?? data;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  enums.preload(['operation-statuses', 'operation-types']);
  loadOperations();
});

function formatDate(d) {
  if (!d) return '';
  return new Date(d + 'T00:00:00').toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}
</script>

<style scoped>
.ops-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.op-card {
  text-decoration: none;
  color: inherit;
}

.op-card-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.op-card-badges {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 140px;
}

.op-card-body { flex: 1; }

.op-ticket {
  font-weight: 600;
  font-size: 0.925rem;
  color: var(--acc-text, #111827);
  margin: 0 0 4px;
}

.op-date {
  font-size: 0.8rem;
  color: var(--acc-muted, #6b7280);
  margin: 0;
}

.op-chevron { color: #9ca3af; }
</style>
