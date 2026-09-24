<template>
  <div>
    <h6 class="fw-bold mb-1">{{ campaign.title }}</h6>
    <div class="text-muted small mb-3">Estado: {{ campaign.status || 'DRAFT' }}</div>

    <div v-if="loadingPreview" class="text-center py-4">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>
    <div v-else-if="!previews.length" class="alert alert-warning small">
      La campaña no tiene canales reales seleccionados. Edítela y elija al menos uno.
    </div>
    <div v-for="p in previews" :key="p.channel" class="card border shadow-sm mb-3">
      <div class="card-header bg-light small fw-semibold text-uppercase">{{ p.channel }}</div>
      <div class="card-body">
        <div class="fw-semibold mb-2">{{ p.subject }}</div>
        <pre class="small mb-2 preview-body">{{ p.body }}</pre>
        <img v-if="p.media_url" :src="p.media_url" alt="media" class="img-fluid rounded" style="max-height: 160px;" />
      </div>
    </div>

    <div v-if="needsRecipient" class="mb-3">
      <label class="form-label small fw-semibold">Destinatario (email o teléfono, para canales directos)</label>
      <input v-model="recipient" type="text" class="form-control" placeholder="correo@dominio.com" />
    </div>

    <div class="d-flex gap-2 justify-content-end">
      <button class="btn btn-primary rounded-pill px-4" :disabled="!previews.length || sending" @click="send">
        <span v-if="sending" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-send me-1"></i> Enviar ahora
      </button>
    </div>

    <div v-if="result" class="alert alert-success small mt-3 mb-0">
      Despachados: {{ result.dispatched_channels.join(', ') || 'ninguno' }}.
      <span v-if="result.skipped_channels.length">
        Omitidos (falta destinatario): {{ result.skipped_channels.join(', ') }}.
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useMarketingAdminStore } from '@/store/marketingAdmin';

const props = defineProps({ campaign: { type: Object, required: true } });
const emit = defineEmits(['sent']);

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useMarketingAdminStore();

const DIRECT_CHANNELS = ['email', 'whatsapp'];
const previews = ref([]);
const loadingPreview = ref(false);
const sending = ref(false);
const recipient = ref('');
const result = ref(null);

const needsRecipient = computed(() => previews.value.some((p) => DIRECT_CHANNELS.includes(p.channel)));

onMounted(async () => {
  loadingPreview.value = true;
  const res = await store.previewCampaign(props.campaign.uuid);
  loadingPreview.value = false;
  if (res.ok) previews.value = res.data.channels || [];
  else handleError(res.error, 'No se pudo cargar la previsualización.');
});

async function send() {
  if (!confirm('¿Enviar la campaña ahora por los canales seleccionados?')) return;
  sending.value = true;
  const res = await store.sendCampaign(props.campaign.uuid, recipient.value.trim());
  sending.value = false;
  if (res.ok) {
    result.value = res.data;
    toast.success('Campaña enviada a la cola de difusión.');
    emit('sent');
  } else {
    handleError(res.error, 'No se pudo enviar la campaña.');
  }
}
</script>

<style scoped>
.preview-body { white-space: pre-wrap; font-family: inherit; }
</style>
