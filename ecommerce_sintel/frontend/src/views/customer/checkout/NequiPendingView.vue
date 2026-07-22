<template>
  <div class="nequi-pending-view">
    <div class="container py-5" style="max-width: 520px">

      <!-- Estado: Pendiente (polling activo) -->
      <div v-if="status === 'PENDING'">
        <PaymentHeader
          variant="warning"
          icon="bi-hourglass-split"
          :title="`Esperando ${pendingLabel.toLowerCase()}`"
          subtitle="Abre tu app Nequi y acepta el pago"
        />
        <PaymentCard class="mt-4">
          <PaymentRow label="Celular Nequi"><strong>{{ phone }}</strong></PaymentRow>
          <PaymentRow label="Total a pagar" bold-label>
            <span class="fw-bold fs-5 text-payment-accent">${{ fmt(amount) }}</span>
          </PaymentRow>
        </PaymentCard>
        <p class="text-muted text-center mt-3" style="font-size:.8rem">
          Revisando cada 5 segundos... ({{ elapsedSeconds }}s / {{ timeoutSeconds }}s)
        </p>
        <div class="text-center">
          <PaymentCTA variant="secondary" size="md" @click="cancelAndReturn">
            Cancelar y volver al checkout
          </PaymentCTA>
        </div>
      </div>

      <!-- Estado: Aprobado -->
      <div v-else-if="status === 'APPROVED'">
        <PaymentHeader
          variant="success"
          icon="bi-check-lg"
          :title="`Pago ${approvedLabel.toLowerCase()}`"
          subtitle="Tu pago con Nequi fue procesado exitosamente"
        />
        <div class="text-center mt-4">
          <PaymentCTA to="/mi-cuenta/pedidos">Ver mis pedidos</PaymentCTA>
        </div>
      </div>

      <!-- Estado: Rechazado -->
      <div v-else-if="status === 'REJECTED'">
        <PaymentHeader
          variant="danger"
          icon="bi-x-lg"
          :title="`Pago ${rejectedLabel.toLowerCase()}`"
          subtitle="El pago fue rechazado o no fue aprobado a tiempo"
        />
        <div class="text-center mt-4">
          <PaymentCTA to="/checkout">Intentar de nuevo</PaymentCTA>
        </div>
      </div>

      <!-- Estado: Error -->
      <div v-else-if="status === 'ERROR'">
        <PaymentHeader
          variant="warning"
          icon="bi-exclamation-triangle-fill"
          title="Error de comunicacion"
          subtitle="No pudimos verificar el estado de tu pago. Revisa tu app Nequi o contacta soporte."
        />
        <div class="text-center mt-4">
          <PaymentCTA variant="secondary" to="/mi-cuenta/pedidos">Ver mis pedidos</PaymentCTA>
        </div>
      </div>

      <!-- Timeout -->
      <div v-else-if="status === 'TIMEOUT'">
        <PaymentHeader
          variant="secondary"
          icon="bi-clock-history"
          title="Tiempo de espera agotado"
          subtitle="No recibimos confirmacion a tiempo. Puedes revisar el estado de tu pedido en Mi cuenta."
        />
        <div class="text-center mt-4">
          <PaymentCTA to="/mi-cuenta/pedidos">Ver mis pedidos</PaymentCTA>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useEnums } from '@/composables/useEnums';
import { usePaymentPolling } from '@/composables/usePaymentPolling';
import PaymentHeader from '@/components/shared/checkout/PaymentHeader.vue';
import PaymentCard from '@/components/shared/checkout/PaymentCard.vue';
import PaymentRow from '@/components/shared/checkout/PaymentRow.vue';
import PaymentCTA from '@/components/shared/checkout/PaymentCTA.vue';

const route  = useRoute();
const router = useRouter();
const api    = useApi();
const enums  = useEnums();

const status         = ref('PENDING');
const phone          = ref('');
const amount         = ref(0);
const elapsedSeconds = ref(0);
const timeoutSeconds = 180;

// Mecanica del timer de polling delegada a usePaymentPolling (ver
// PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 2, hallazgo 1). El segundo
// contador (tickInterval, para el texto "Xs / 180s" que sube cada segundo)
// se mantiene independiente tal cual estaba -- fusionarlo con el intervalo
// de 5s del polling cambiaria la cadencia visual del contador, que es
// comportamiento observable, no solo mecanica interna.
const polling = usePaymentPolling({
  intervalMs: 5000,
  timeoutMs: timeoutSeconds * 1000,
  onTimeout: () => { status.value = 'TIMEOUT'; },
});
let tickInterval = null;

const fmt = (val) => new Intl.NumberFormat('es-CO').format(parseFloat(val) || 0);

const pendingLabel = computed(() => enums.label('payment-statuses', 'PENDING', 'Pendiente'));
const approvedLabel = computed(() => enums.label('payment-statuses', 'APPROVED', 'Aprobado'));
const rejectedLabel = computed(() => enums.label('payment-statuses', 'REJECTED', 'Rechazado'));

async function checkStatus() {
  const txUuid = route.query.tx;
  if (!txUuid) { status.value = 'ERROR'; return; }

  try {
    const res = await api.get(`payment/nequi/status/?tx=${txUuid}`);
    const tx  = res.data;

    phone.value  = tx.phone_number || phone.value;
    amount.value = tx.amount       || amount.value;

    if (tx.status !== 'PENDING') {
      status.value = tx.status;
      stopPolling();

      if (tx.status === 'APPROVED') {
        setTimeout(() => router.push('/mi-cuenta/pedidos'), 2500);
      }
    }
  } catch {
    status.value = 'ERROR';
    stopPolling();
  }
}

function stopPolling() {
  polling.stop();
  if (tickInterval) { clearInterval(tickInterval); tickInterval = null; }
}

function cancelAndReturn() {
  stopPolling();
  if (route.query.rental_uuid) {
    router.push('/alquiler');
  } else {
    router.push({ name: 'checkout' });
  }
}

onMounted(() => {
  enums.ensure('payment-statuses');
  checkStatus();

  polling.start(checkStatus);

  tickInterval = setInterval(() => {
    elapsedSeconds.value++;
  }, 1000);
});

onUnmounted(() => stopPolling());
</script>

<style scoped>
.nequi-pending-view { min-height: 100vh; padding-top: 40px; background: #f8fafc; }
.text-payment-accent { color: var(--payment-accent, #7c3aed) !important; }
</style>
