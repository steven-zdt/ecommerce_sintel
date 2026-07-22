<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Notificaciones</h4>
    </div>

    <ul class="nav nav-tabs mb-3">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'templates' }" @click="tab = 'templates'">
          <i class="bi bi-file-earmark-text me-1"></i>Plantillas
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'logs' }" @click="tab = 'logs'">
          <i class="bi bi-list-check me-1"></i>Logs de envio
        </button>
      </li>
    </ul>

    <!-- ── Plantillas ─────────────────────────────────────────────── -->
    <div v-show="tab === 'templates'" class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Slug</th>
              <th>Nombre</th>
              <th>Canales configurados</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="templatesLoading">
              <td colspan="5" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
              </td>
            </tr>
            <tr v-else-if="templates.length === 0">
              <td colspan="5" class="text-center py-5 text-muted">No se encontraron plantillas.</td>
            </tr>
            <tr v-for="t in templates" :key="t.uuid">
              <td><code class="small text-muted">{{ t.slug }}</code></td>
              <td class="fw-bold">{{ t.name }}</td>
              <td>
                <span v-if="t.email_body" class="badge bg-primary-subtle text-primary me-1">Email</span>
                <span v-if="t.whatsapp_template_name" class="badge bg-success-subtle text-success me-1">WhatsApp</span>
                <span v-if="t.ws_event_type" class="badge bg-info-subtle text-info">WebSocket</span>
                <span v-if="!t.email_body && !t.whatsapp_template_name && !t.ws_event_type" class="text-muted small">Sin canales</span>
              </td>
              <td>
                <span :class="['badge rounded-pill', t.is_active ? 'bg-success' : 'bg-secondary']">
                  {{ t.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="text-end">
                <button class="btn btn-light btn-sm border" @click="openEdit(t)" title="Editar">
                  <i class="bi bi-pencil text-primary"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Logs ───────────────────────────────────────────────────── -->
    <div v-show="tab === 'logs'">
      <div class="d-flex gap-2 mb-3">
        <select v-model="logFilters.status" class="form-select form-select-sm" style="max-width:180px" @change="fetchLogs">
          <option value="">Todos los estados</option>
          <option value="PENDING">Pendiente</option>
          <option value="SENT">Enviado</option>
          <option value="FAILED">Fallido</option>
        </select>
        <select v-model="logFilters.channel" class="form-select form-select-sm" style="max-width:180px" @change="fetchLogs">
          <option value="">Todos los canales</option>
          <option value="EMAIL">Correo electronico</option>
          <option value="WHATSAPP">WhatsApp</option>
          <option value="WEB_SOCKET">WebSocket</option>
        </select>
        <input
          v-model="logFilters.template_slug"
          type="text"
          class="form-control form-control-sm"
          style="max-width:220px"
          placeholder="Buscar por slug..."
          @input="debouncedFetchLogs"
        >
      </div>

      <div class="card shadow-sm border-0 overflow-hidden">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Fecha</th>
                <th>Plantilla</th>
                <th>Canal</th>
                <th>Estado</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="logsLoading">
                <td colspan="5" class="text-center py-5">
                  <div class="spinner-border text-primary" role="status"></div>
                </td>
              </tr>
              <tr v-else-if="logs.length === 0">
                <td colspan="5" class="text-center py-5 text-muted">No se encontraron registros.</td>
              </tr>
              <tr v-for="log in logs" :key="log.uuid">
                <td class="small text-muted">{{ formatDate(log.created_at) }}</td>
                <td><code class="small">{{ log.template_slug }}</code></td>
                <td>{{ log.channel }}</td>
                <td>
                  <span :class="['badge', statusClass(log.status)]">{{ log.status }}</span>
                </td>
                <td class="small text-danger">{{ log.error_message || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="logsTotalCount > 0">
          <span class="text-muted small">{{ logs.length }} de {{ logsTotalCount }} registros</span>
          <nav v-if="logsTotalPages > 1">
            <ul class="pagination pagination-sm m-0">
              <li class="page-item" :class="{ disabled: !logsPagination.previous }">
                <button class="page-link" @click="changeLogsPage(logsCurrentPage - 1)">Ant.</button>
              </li>
              <li class="page-item" :class="{ disabled: !logsPagination.next }">
                <button class="page-link" @click="changeLogsPage(logsCurrentPage + 1)">Sig.</button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </div>

    <!-- ── Offcanvas edicion de plantilla ────────────────────────────── -->
    <SintelOffcanvas
      v-model="showEdit"
      :title="`Editar plantilla: ${selected?.name || ''}`"
      :subtitle="selected?.slug"
      width="480px"
    >
      <form v-if="selected" @submit.prevent="submitEdit">
        <div class="mb-3 form-check form-switch">
          <input v-model="form.is_active" class="form-check-input" type="checkbox" id="tplActive">
          <label class="form-check-label small" for="tplActive">Plantilla activa</label>
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Nombre</label>
          <input v-model="form.name" type="text" class="form-control" required>
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Asunto (email)</label>
          <input v-model="form.subject" type="text" class="form-control">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Cuerpo del email</label>
          <textarea v-model="form.email_body" class="form-control" rows="5"></textarea>
          <div class="form-text">Soporta variables Django Template: <code>&#123;&#123; order_uuid &#125;&#125;</code>, <code>&#123;&#123; total &#125;&#125;</code>, etc.</div>
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Plantilla WhatsApp (Meta Business Manager)</label>
          <input v-model="form.whatsapp_template_name" type="text" class="form-control">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Evento WebSocket (event_type)</label>
          <input v-model="form.ws_event_type" type="text" class="form-control">
        </div>

        <div class="d-flex gap-2 mt-4">
          <button type="submit" class="btn btn-primary w-100" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
            Guardar Cambios
          </button>
          <button type="button" class="btn btn-light border" @click="showEdit = false" :disabled="saving">Cancelar</button>
        </div>
      </form>
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';

const api = useApi();
const toast = useToast();

const tab = ref('templates');

// ── Plantillas ──────────────────────────────────────────────────────
const templates = ref([]);
const templatesLoading = ref(true);
const showEdit = ref(false);
const selected = ref(null);
const saving = ref(false);
const form = ref({});

async function fetchTemplates() {
  templatesLoading.value = true;
  try {
    const { data } = await api.get('dashboard/notification-templates/');
    templates.value = data.results || data;
  } catch {
    toast.error('Error al cargar las plantillas');
  } finally {
    templatesLoading.value = false;
  }
}

function openEdit(template) {
  selected.value = template;
  form.value = {
    name: template.name,
    subject: template.subject,
    email_body: template.email_body,
    whatsapp_template_name: template.whatsapp_template_name,
    ws_event_type: template.ws_event_type,
    is_active: template.is_active,
  };
  showEdit.value = true;
}

async function submitEdit() {
  saving.value = true;
  try {
    await api.patch(`dashboard/notification-templates/${selected.value.uuid}/`, form.value);
    toast.success('Plantilla actualizada');
    showEdit.value = false;
    await fetchTemplates();
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al guardar');
  } finally {
    saving.value = false;
  }
}

// ── Logs ────────────────────────────────────────────────────────────
const logs = ref([]);
const logsLoading = ref(true);
const logsTotalCount = ref(0);
const logsTotalPages = ref(0);
const logsCurrentPage = ref(1);
const logsPagination = reactive({ next: null, previous: null });
const logFilters = reactive({ status: '', channel: '', template_slug: '' });
let debounceTimer = null;

async function fetchLogs() {
  logsLoading.value = true;
  try {
    const params = { page: logsCurrentPage.value };
    if (logFilters.status) params.status = logFilters.status;
    if (logFilters.channel) params.channel = logFilters.channel;
    if (logFilters.template_slug) params.template_slug = logFilters.template_slug;
    const { data } = await api.get('dashboard/notification-logs/', { params });
    logs.value = data.results || data;
    logsTotalCount.value = data.count || logs.value.length;
    logsTotalPages.value = Math.ceil(logsTotalCount.value / 25);
    logsPagination.next = data.next;
    logsPagination.previous = data.previous;
  } catch {
    toast.error('Error al cargar los logs');
  } finally {
    logsLoading.value = false;
  }
}

function debouncedFetchLogs() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    logsCurrentPage.value = 1;
    fetchLogs();
  }, 400);
}

function changeLogsPage(p) {
  if (p >= 1 && p <= logsTotalPages.value) {
    logsCurrentPage.value = p;
    fetchLogs();
  }
}

function statusClass(status) {
  if (status === 'SENT') return 'bg-success';
  if (status === 'FAILED') return 'bg-danger';
  return 'bg-warning text-dark';
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('es-CO');
}

onMounted(() => {
  fetchTemplates();
  fetchLogs();
});
</script>
