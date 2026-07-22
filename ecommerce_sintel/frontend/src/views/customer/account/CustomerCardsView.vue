<template>
  <CustomerAccountShell>
    <CustomerPageHeader title="Metodos de pago" subtitle="Tarjetas guardadas para pagos rapidos." />

    <CustomerSkeleton v-if="loading" layout="grid" :count="2" height="180px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchCards" />

    <template v-else>
      <CustomerEmptyState
        v-if="cards.length === 0"
        icon="bi-credit-card"
        title="No tienes tarjetas guardadas"
        description="Agrega una tarjeta para realizar pagos mas rapido."
        class="mb-4"
      />

      <div v-else class="cards-grid mb-4">
        <CustomerCard
          v-for="card in cards"
          :key="card.uuid"
          variant="brand"
          :brand-tone="card.is_default ? 'green' : 'blue'"
        >
          <div class="d-flex justify-content-between align-items-start">
            <div class="card-brand">
              <i class="bi bi-credit-card-2-front me-2"></i>
              <span class="fw-semibold">{{ card.brand }}</span>
            </div>
            <span v-if="card.is_default" class="badge bg-light text-success-emphasis small">Predeterminada</span>
          </div>
          <p class="card-number">**** **** **** {{ card.masked_number.slice(-4) }}</p>
          <div class="d-flex justify-content-between align-items-center">
            <p class="card-expiry text-muted small">Vence {{ card.exp_month }}/{{ card.exp_year }}</p>
            <p v-if="card.cardholder_name" class="card-holder text-muted small">{{ card.cardholder_name }}</p>
          </div>

          <CustomerConfirmInline
            v-if="pendingDelete?.uuid === card.uuid"
            message="Eliminar esta tarjeta?"
            :loading="deletingId === card.uuid"
            @confirm="deleteCard(card)"
            @cancel="pendingDelete = null"
          />
          <div v-else class="card-actions">
            <button v-if="!card.is_default" type="button" class="btn btn-sm btn-brand-outline" @click="setDefault(card)">
              Usar como predeterminada
            </button>
            <button type="button" class="btn btn-sm btn-brand-danger" @click="pendingDelete = card">
              <i class="bi bi-trash me-1"></i>Eliminar
            </button>
          </div>
        </CustomerCard>
      </div>

      <CustomerSection title="Agregar tarjeta" icon="bi-plus-circle">
        <div class="alert alert-info small d-flex align-items-start gap-2">
          <i class="bi bi-shield-lock-fill flex-shrink-0 mt-1"></i>
          <span>Tus datos de tarjeta se envian directo a Wompi, nunca pasan por nuestros servidores. Nunca mostramos el numero completo ni el CVC guardados.</span>
        </div>
        <form @submit.prevent="addCard">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label small fw-semibold">Numero de tarjeta</label>
              <input
                v-model="rawCard.number" type="text" inputmode="numeric" autocomplete="cc-number"
                class="form-control" placeholder="4242 4242 4242 4242" maxlength="19" required
              />
            </div>
            <div class="col-sm-4">
              <label class="form-label small fw-semibold">Mes exp.</label>
              <input
                v-model="rawCard.exp_month" type="text" inputmode="numeric" autocomplete="cc-exp-month"
                class="form-control" placeholder="MM" maxlength="2" required
              />
            </div>
            <div class="col-sm-4">
              <label class="form-label small fw-semibold">Ano exp.</label>
              <input
                v-model="rawCard.exp_year" type="text" inputmode="numeric" autocomplete="cc-exp-year"
                class="form-control" placeholder="AA" maxlength="2" required
              />
            </div>
            <div class="col-sm-4">
              <label class="form-label small fw-semibold">CVC</label>
              <input
                v-model="rawCard.cvc" type="password" inputmode="numeric" autocomplete="cc-csc"
                class="form-control" placeholder="123" maxlength="4" required
              />
            </div>
            <div class="col-12">
              <label class="form-label small fw-semibold">Nombre del titular</label>
              <input
                v-model="rawCard.card_holder" type="text" autocomplete="cc-name"
                class="form-control" placeholder="Como aparece en la tarjeta" required
              />
            </div>
          </div>
          <div class="d-flex justify-content-end mt-4">
            <CustomerButton variant="primary" size="md" :loading="saving">
              <i class="bi bi-plus-lg me-1"></i>Guardar tarjeta
            </CustomerButton>
          </div>
        </form>
      </CustomerSection>
    </template>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useCardTokenization } from '@/composables/useCardTokenization';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerSection from '@/components/customer/account/CustomerSection.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerConfirmInline from '@/components/customer/account/CustomerConfirmInline.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

const api = useApi();
const toast = useToast();
const { tokenizeCard } = useCardTokenization();

const loading = ref(true);
const loadError = ref(false);
const saving = ref(false);
const deletingId = ref(null);
const cards = ref([]);
const pendingDelete = ref(null);

const defaultRawCard = () => ({ number: '', exp_month: '', exp_year: '', cvc: '', card_holder: '' });
const rawCard = ref(defaultRawCard());

async function fetchCards() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await api.get('payment/cards/');
    cards.value = res.data.results ?? res.data ?? [];
  } catch {
    loadError.value = true;
    toast.error('Error al cargar las tarjetas');
  } finally {
    loading.value = false;
  }
}

async function addCard() {
  saving.value = true;
  try {
    // Tokenizacion: SIEMPRE directo al navegador->Wompi (useCardTokenization),
    // nunca via api (axios hacia nuestro backend) -- los datos crudos de la
    // tarjeta jamas deben llegar a nuestro servidor.
    const tokenData = await tokenizeCard(rawCard.value);

    const res = await api.post('payment/cards/', {
      token_id: tokenData.id,
      masked_number: `************${tokenData.last_four}`,
      brand: tokenData.brand,
      exp_month: tokenData.exp_month,
      exp_year: tokenData.exp_year,
      cardholder_name: tokenData.card_holder || rawCard.value.card_holder,
    });
    cards.value.unshift(res.data);
    toast.success('Tarjeta guardada correctamente');
  } catch (e) {
    toast.error(e.response?.data?.detail || e.message || 'Error al guardar la tarjeta');
  } finally {
    // Limpieza incondicional (exito o error) -- los datos crudos (numero, cvc)
    // nunca deben quedar en memoria mas tiempo del necesario.
    rawCard.value = defaultRawCard();
    saving.value = false;
  }
}

async function setDefault(card) {
  try {
    await api.post(`payment/cards/${card.uuid}/set-default/`);
    cards.value = cards.value.map(c => ({ ...c, is_default: c.uuid === card.uuid }));
    toast.success('Tarjeta predeterminada actualizada');
  } catch {
    toast.error('Error al actualizar');
  }
}

async function deleteCard(card) {
  deletingId.value = card.uuid;
  try {
    await api.delete(`payment/cards/${card.uuid}/`);
    cards.value = cards.value.filter(c => c.uuid !== card.uuid);
    toast.success('Tarjeta eliminada');
  } catch {
    toast.error('Error al eliminar');
  } finally {
    deletingId.value = null;
    pendingDelete.value = null;
  }
}

onMounted(fetchCards);
</script>

<style scoped>
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.card-brand { font-size: 0.9rem; }
.card-number { font-size: 1.1rem; font-weight: 600; letter-spacing: 2px; margin: 4px 0; }
.card-expiry, .card-holder { color: rgba(255, 255, 255, 0.8) !important; margin: 0; }

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.btn-brand-outline {
  border: 1px solid rgba(255, 255, 255, 0.5);
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}
.btn-brand-outline:hover { background: rgba(255, 255, 255, 0.2); color: #fff; }

.btn-brand-danger {
  border: 1px solid rgba(255, 100, 100, 0.6);
  color: #fca5a5;
  background: rgba(255, 0, 0, 0.1);
}
.btn-brand-danger:hover { background: rgba(255, 0, 0, 0.2); color: #fca5a5; }
</style>
