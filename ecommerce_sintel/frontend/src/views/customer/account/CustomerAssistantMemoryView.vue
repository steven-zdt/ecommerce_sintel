<template>
  <CustomerAccountShell>
    <CustomerPageHeader
      title="Lo que el asistente recuerda"
      subtitle="Preferencias que el asistente virtual guardo de tus conversaciones para atenderte mejor. Tu decides que conservar."
    />

    <CustomerCard tag="div" class="memory-info">
      <i class="bi bi-shield-check" aria-hidden="true"></i>
      <p class="mb-0 small">
        Solo se guardan preferencias breves (por ejemplo, tu canal de contacto preferido). <strong>Nunca</strong> se guardan contrasenas,
        codigos de verificacion, numeros de tarjeta, correos, telefonos ni documentos, y cada recuerdo caduca automaticamente.
        Puedes borrar uno o todos cuando quieras.
      </p>
    </CustomerCard>

    <CustomerSkeleton v-if="loading" layout="list" :count="3" height="72px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchMemories" />

    <CustomerEmptyState
      v-else-if="memories.length === 0"
      icon="bi-chat-heart"
      title="El asistente aun no recuerda nada de ti"
      description="Cuando converses con el asistente y compartas una preferencia, aparecera aqui."
    />

    <template v-else>
      <div class="memory-toolbar">
        <span class="text-muted small">{{ memories.length }} {{ memories.length === 1 ? 'recuerdo' : 'recuerdos' }}</span>
        <CustomerConfirmInline
          v-if="confirmAll"
          message="Olvidar TODO lo que el asistente recuerda de ti? Esta accion no se puede deshacer."
          :loading="forgettingAll"
          @confirm="forgetAll"
          @cancel="confirmAll = false"
        />
        <CustomerButton v-else variant="secondary" @click="confirmAll = true">
          <i class="bi bi-eraser me-1"></i>Olvidar todo
        </CustomerButton>
      </div>

      <div class="memory-list">
        <CustomerCard v-for="m in memories" :key="m.uuid" tag="div" class="memory-item">
          <div class="memory-body">
            <span class="memory-category">{{ categoryLabel(m.category) }}</span>
            <p class="memory-content">{{ m.content }}</p>
            <p class="memory-meta text-muted small">
              Aprendido el {{ fmtDate(m.created_at) }}<template v-if="m.channel && m.channel !== 'unknown'"> por {{ channelLabel(m.channel) }}</template>
              <template v-if="m.expires_at"> · caduca el {{ fmtDate(m.expires_at) }}</template>
            </p>
          </div>
          <CustomerConfirmInline
            v-if="pendingRemove === m.uuid"
            message="Olvidar este recuerdo?"
            :loading="removingId === m.uuid"
            @confirm="removeOne(m)"
            @cancel="pendingRemove = null"
          />
          <CustomerButton v-else variant="icon" aria-label="Olvidar este recuerdo" @click="pendingRemove = m.uuid">
            <i class="bi bi-trash"></i>
          </CustomerButton>
        </CustomerCard>
      </div>
    </template>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerConfirmInline from '@/components/customer/account/CustomerConfirmInline.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

// HARDENING F7 (2026-09-24, Habeas Data): el propio cliente ve y borra la memoria del asistente.
// API: GET/DELETE /api/v1/customer-memory/ y DELETE /api/v1/customer-memory/<uuid>/ (customer_memory/api/owner_urls.py).
const toast = useToast();
const api = useApi();

const memories = ref([]);
const loading = ref(true);
const loadError = ref(false);
const pendingRemove = ref(null);
const removingId = ref(null);
const confirmAll = ref(false);
const forgettingAll = ref(false);

const CATEGORY_LABELS = {
  contact_preference: 'Preferencia de contacto',
  product_interest: 'Interes en productos',
  communication_style: 'Estilo de comunicacion',
  general_preference: 'Preferencia general',
};
const CHANNEL_LABELS = { web: 'la web', whatsapp: 'WhatsApp' };
const categoryLabel = (c) => CATEGORY_LABELS[c] || 'Preferencia';
const channelLabel = (c) => CHANNEL_LABELS[c] || c;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '');

async function fetchMemories() {
  loading.value = true;
  loadError.value = false;
  try {
    const { data } = await api.get('customer-memory/');
    memories.value = data.memories || [];
  } catch {
    loadError.value = true;
    toast.error('No se pudo cargar lo que el asistente recuerda');
  } finally {
    loading.value = false;
  }
}

async function removeOne(m) {
  removingId.value = m.uuid;
  try {
    await api.delete(`customer-memory/${m.uuid}/`);
    memories.value = memories.value.filter((x) => x.uuid !== m.uuid);
    toast.success('Recuerdo eliminado');
  } catch {
    toast.error('No se pudo eliminar el recuerdo');
  } finally {
    removingId.value = null;
    pendingRemove.value = null;
  }
}

async function forgetAll() {
  forgettingAll.value = true;
  try {
    await api.delete('customer-memory/');
    memories.value = [];
    toast.success('El asistente olvido todo lo que recordaba de ti');
  } catch {
    toast.error('No se pudo borrar la memoria del asistente');
  } finally {
    forgettingAll.value = false;
    confirmAll.value = false;
  }
}

onMounted(fetchMemories);
</script>

<style scoped>
/* CustomerCard trae `height: 100%` y `flex-direction: column` (pensado para celdas de grid): en flujo normal ocupaba todo el alto del
   contenedor y empujaba la lista debajo del footer. Doble clase = mas especificidad que `.acc-card`. */
.memory-info.memory-info { height: auto; flex-direction: row; align-items: flex-start; gap: 12px; margin-bottom: 20px; }
.memory-info .bi { font-size: 1.4rem; color: var(--acc-accent, #2563eb); flex-shrink: 0; }
.memory-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.memory-list { display: flex; flex-direction: column; gap: 12px; }
.memory-item.memory-item { height: auto; flex-direction: row; align-items: center; justify-content: space-between; gap: 12px; }
.memory-body { min-width: 0; }
.memory-category { display: inline-block; font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--acc-accent, #2563eb); }
.memory-content { margin: 2px 0; font-weight: 500; word-break: break-word; }
.memory-meta { margin: 0; }
</style>
