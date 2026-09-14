<template>
  <div class="c360">
    <div v-if="loading" class="text-center text-muted small py-4">Cargando contexto del cliente...</div>
    <template v-else-if="data">
      <div class="c360-profile">
        <div class="c360-avatar">{{ initials }}</div>
        <div class="min-w-0">
          <div class="c360-name text-truncate">{{ fullName }}</div>
          <div class="c360-email text-truncate">{{ data.user.email }}</div>
        </div>
      </div>

      <div class="c360-badges">
        <span v-if="data.profile" class="badge" :class="enums.cssClass('user-types', data.profile.user_type)">
          {{ enums.label('user-types', data.profile.user_type, data.profile.user_type) }}
        </span>
        <span v-if="data.kyc" class="badge" :class="enums.cssClass('kyc-verification-statuses', data.kyc.status)">
          KYC: {{ enums.label('kyc-verification-statuses', data.kyc.status, data.kyc.status) }}
        </span>
      </div>

      <!-- Contexto pinneado de la sala activa -->
      <template v-if="pinnedOrders.length || pinnedRentals.length">
        <h6 class="c360-section-title">Sobre esta conversación</h6>
        <div class="c360-cards">
          <OrderContextCard v-for="o in pinnedOrders" :key="'o-' + o.uuid" :order="o" />
          <PaymentContextCard v-for="o in pinnedOrders" :key="'p-' + o.uuid" :order="o" />
          <RentalContextCard v-for="r in pinnedRentals" :key="'r-' + r.uuid" :rental="r" />
        </div>
      </template>

      <h6 class="c360-section-title">Pedidos recientes</h6>
      <div v-if="data.orders.length" class="c360-cards">
        <OrderContextCard v-for="o in data.orders.slice(0, 3)" :key="o.uuid" :order="o" />
      </div>
      <p v-else class="text-muted small">Sin pedidos.</p>

      <h6 class="c360-section-title">Alquileres recientes</h6>
      <div v-if="data.rentals.length" class="c360-cards">
        <RentalContextCard v-for="r in data.rentals.slice(0, 3)" :key="r.uuid" :rental="r" />
      </div>
      <p v-else class="text-muted small">Sin alquileres.</p>

      <h6 class="c360-section-title">Cotizaciones recientes</h6>
      <div v-if="data.quotations.length" class="c360-cards">
        <QuotationContextCard v-for="q in data.quotations.slice(0, 3)" :key="q.uuid" :quotation="q" />
      </div>
      <p v-else class="text-muted small">Sin cotizaciones.</p>

      <h6 class="c360-section-title">Ordenes de operación</h6>
      <div v-if="data.operations.length" class="c360-cards">
        <OperationContextCard v-for="t in data.operations.slice(0, 3)" :key="t.uuid" :operation="t" />
      </div>
      <p v-else class="text-muted small">Sin ordenes de operación.</p>

      <h6 class="c360-section-title">Timeline</h6>
      <UnifiedTimeline :events="data.timeline" />
    </template>
    <div v-else class="text-center text-muted small py-4">Selecciona una conversación.</div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useEnums } from '@/composables/useEnums';
import OrderContextCard from './OrderContextCard.vue';
import RentalContextCard from './RentalContextCard.vue';
import PaymentContextCard from './PaymentContextCard.vue';
import QuotationContextCard from './QuotationContextCard.vue';
import OperationContextCard from './OperationContextCard.vue';
import UnifiedTimeline from './UnifiedTimeline.vue';

const props = defineProps({
  userUuid: { type: String, default: '' },
  roomContexts: { type: Array, default: () => [] },
});

const api = useApi();
const enums = useEnums();
const loading = ref(false);
const data = ref(null);

const fullName = computed(() => {
  if (!data.value?.profile) return data.value?.user?.email || '';
  const p = data.value.profile;
  return `${p.first_name} ${p.last_name}`.trim() || data.value.user.email;
});
const initials = computed(() => fullName.value.slice(0, 2).toUpperCase());

const pinnedOrders = computed(() => {
  if (!data.value) return [];
  const uuids = new Set(props.roomContexts.filter(c => c.context_type === 'ORDER').map(c => c.uuid));
  return data.value.orders.filter(o => uuids.has(o.uuid));
});
const pinnedRentals = computed(() => {
  if (!data.value) return [];
  const uuids = new Set(props.roomContexts.filter(c => c.context_type === 'RENTAL').map(c => c.uuid));
  return data.value.rentals.filter(r => uuids.has(r.uuid));
});

async function load() {
  if (!props.userUuid) { data.value = null; return; }
  loading.value = true;
  try {
    const { data: res } = await api.get(`dashboard/support/chats/customer360/${props.userUuid}/`);
    data.value = res;
  } catch (_) {
    data.value = null;
  } finally {
    loading.value = false;
  }
}

watch(() => props.userUuid, load, { immediate: true });

enums.ensure('user-types');
enums.ensure('kyc-verification-statuses');
enums.ensure('order-statuses');
enums.ensure('order-payment-methods');
enums.ensure('rental-statuses');
enums.ensure('quote-statuses');
enums.ensure('operation-statuses');
enums.ensure('operation-types');
</script>

<style scoped>
.c360 { padding: 16px; overflow-y: auto; height: 100%; }
.c360-profile { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.c360-avatar {
  width: 40px; height: 40px; border-radius: 50%; background: #1e40af; color: #fff;
  display: grid; place-items: center; font-weight: 700; font-size: 13px; flex: none;
}
.c360-name { font-weight: 700; font-size: 14px; color: #111827; }
.c360-email { font-size: 12px; color: #6b7280; }
.c360-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.c360-section-title {
  font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #9ca3af;
  font-weight: 700; margin: 16px 0 8px;
}
.c360-cards { display: flex; flex-direction: column; gap: 8px; }
.min-w-0 { min-width: 0; }
</style>
