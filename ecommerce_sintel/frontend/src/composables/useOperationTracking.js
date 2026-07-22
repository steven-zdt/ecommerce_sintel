import { ref, onMounted, onUnmounted } from 'vue';
import useApi from '@/composables/useApi';
import { useAuthStore } from '@/store/auth';

export function useOperationTracking(ticketUuid) {
  const api        = useApi();
  const authStore  = useAuthStore();

  const ticket     = ref(null);
  const timeline   = ref([]);
  const loading    = ref(false);
  const error      = ref(null);

  let ws = null;

  async function fetchTicket() {
    loading.value = true;
    error.value   = null;
    try {
      const { data } = await api.get(`operations/my/${ticketUuid}/`);
      ticket.value   = data;
    } catch (e) {
      error.value = e?.response?.data?.detail || 'Error al cargar la operacion.';
    } finally {
      loading.value = false;
    }
  }

  async function fetchTimeline() {
    try {
      const { data } = await api.get(`operations/my/${ticketUuid}/timeline/`);
      timeline.value = data;
    } catch (_) { /* silencioso */ }
  }

  async function uploadDocument(docType, file) {
    const form = new FormData();
    form.append('doc_type', docType);
    form.append('file', file);
    await api.post(`operations/my/${ticketUuid}/upload-document/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    await fetchTicket();
  }

  async function submitReview(payload) {
    await api.post(`operations/my/${ticketUuid}/review/`, payload);
    await fetchTicket();
  }

  function connectWebSocket() {
    const token = authStore.token;
    if (!token || !ticketUuid) return;

    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const host     = location.host;
    ws = new WebSocket(`${protocol}://${host}/ws/operations/${ticketUuid}/?token=${token}`);

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'tracking_update') {
        fetchTicket();
        fetchTimeline();
      }
    };

    ws.onerror = () => { ws = null; };
    ws.onclose = () => { ws = null; };
  }

  onMounted(async () => {
    await Promise.all([fetchTicket(), fetchTimeline()]);
    connectWebSocket();
  });

  onUnmounted(() => {
    ws?.close();
  });

  return { ticket, timeline, loading, error, uploadDocument, submitReview, fetchTicket };
}
