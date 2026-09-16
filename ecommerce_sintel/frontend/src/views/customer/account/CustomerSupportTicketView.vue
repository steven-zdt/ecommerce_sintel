<template>
  <CustomerAccountShell max-width="720px">
    <CustomerPageHeader
      title="Soporte"
      subtitle="Abre un caso directo con nuestro equipo -- un agente humano lo revisara."
    />

    <CustomerCard v-if="!created">
      <form @submit.prevent="submit">
        <div class="mb-3">
          <label class="form-label small fw-semibold">Asunto</label>
          <input
            v-model.trim="form.subject"
            type="text"
            class="form-control"
            maxlength="200"
            placeholder="Ej. Producto llego danado"
            required
          />
        </div>

        <div class="mb-3">
          <label class="form-label small fw-semibold">Categoria (opcional)</label>
          <select v-model="form.category" class="form-select">
            <option value="">Sin categoria</option>
            <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>

        <div class="mb-3">
          <label class="form-label small fw-semibold">Cuentanos que paso</label>
          <textarea
            v-model.trim="form.description"
            class="form-control"
            rows="5"
            maxlength="4000"
            placeholder="Describe tu situacion con el mayor detalle posible."
            required
          ></textarea>
        </div>

        <CustomerButton type="submit" variant="primary" :loading="submitting">
          <i class="bi bi-send me-1"></i>Enviar ticket
        </CustomerButton>
      </form>
    </CustomerCard>

    <CustomerCard v-else>
      <div class="text-center py-4">
        <i class="bi bi-check-circle-fill text-success" style="font-size: 2.5rem"></i>
        <h5 class="mt-3 mb-1">Ticket {{ created.ticket_number }} creado</h5>
        <p class="text-muted mb-4">Un agente humano revisara tu caso pronto. Puedes seguir la conversacion en el chat de soporte.</p>
        <div class="d-flex gap-2 justify-content-center flex-wrap">
          <CustomerButton variant="secondary" @click="resetForm">
            <i class="bi bi-plus-circle me-1"></i>Abrir otro ticket
          </CustomerButton>
        </div>
      </div>
    </CustomerCard>
  </CustomerAccountShell>
</template>

<script setup>
import { reactive, ref } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

// Debe coincidir con support.models.SupportTicket.CATEGORY_CHOICES (backend)
// -- lista corta y estable, no justifica un endpoint de enums dedicado.
const categoryOptions = [
  { value: 'ACCOUNT', label: 'Cuenta' },
  { value: 'ORDER', label: 'Pedido' },
  { value: 'PAYMENT', label: 'Pago' },
  { value: 'PRODUCT', label: 'Producto' },
  { value: 'RENTING', label: 'Alquiler' },
  { value: 'TECHNICAL', label: 'Tecnico' },
  { value: 'DELIVERY', label: 'Entrega' },
  { value: 'OTHER', label: 'Otro' },
];

const form = reactive({ subject: '', description: '', category: '' });
const submitting = ref(false);
const created = ref(null);

async function submit() {
  submitting.value = true;
  try {
    const res = await api.post('support/tickets/create/', { ...form });
    created.value = res.data.ticket;
    toast.success('Ticket enviado -- un agente humano lo revisara pronto.');
  } catch (err) {
    handleError(err, 'No se pudo enviar el ticket. Intenta de nuevo.');
  } finally {
    submitting.value = false;
  }
}

function resetForm() {
  created.value = null;
  form.subject = '';
  form.description = '';
  form.category = '';
}
</script>
