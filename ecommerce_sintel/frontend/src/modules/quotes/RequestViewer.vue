<template>
  <div class="request-viewer">
    <div v-if="loading" class="text-center py-5"><div class="spinner-border"></div></div>

    <template v-else-if="quotation">
      <div class="row g-4">
        <!-- Columna izquierda: contenido -->
        <div class="col-lg-7">
          <div class="card bg-light border-0 mb-3">
            <div class="card-body p-3">
              <h6 class="text-muted text-uppercase smaller fw-bold mb-1">Solicitante</h6>
              <h5 class="fw-bold mb-1">{{ quotation.client_name }}</h5>
              <div class="text-muted small"><i class="bi bi-envelope me-1"></i>{{ quotation.client_email }}</div>
              <div v-if="quotation.phone" class="text-muted small"><i class="bi bi-telephone me-1"></i>{{ quotation.phone }}</div>
              <div v-if="quotation.company" class="text-muted small"><i class="bi bi-building me-1"></i>{{ quotation.company }}</div>
              <div v-if="quotation.address || quotation.city" class="text-muted small">
                <i class="bi bi-geo-alt me-1"></i>{{ [quotation.address, quotation.city, quotation.department].filter(Boolean).join(', ') }}
              </div>
              <div v-if="quotation.project_name" class="text-muted small"><i class="bi bi-kanban me-1"></i>{{ quotation.project_name }}</div>
            </div>
          </div>

          <div v-if="quotation.template_name" class="mb-3">
            <span class="badge bg-light text-secondary border">
              <i class="bi bi-collection me-1"></i>{{ quotation.template_name }}
            </span>
          </div>

          <div v-if="!template && quotation.template_uuid" class="text-center py-4 text-muted small">
            <div class="spinner-border spinner-border-sm"></div> Cargando cuestionario...
          </div>

          <div v-for="group in answerGroups" :key="group.type" v-show="group.rows.length" class="card border-0 shadow-sm mb-3">
            <div class="card-header bg-white fw-semibold small text-uppercase">{{ group.label }}</div>
            <div class="card-body p-0">
              <table class="table table-sm mb-0">
                <tbody>
                  <tr v-for="row in group.rows" :key="row.key">
                    <td class="ps-3 text-muted small" style="width: 45%">{{ row.label }}</td>
                    <td class="small">
                      <a v-if="row.attachment" :href="row.attachment.file" target="_blank">
                        <i class="bi bi-paperclip me-1"></i>Ver adjunto
                      </a>
                      <span v-else>{{ row.value }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Items ya cotizados -->
          <div v-if="quotation.items?.length" class="card border-0 shadow-sm mb-3">
            <div class="card-header bg-white fw-semibold small text-uppercase">Productos cotizados</div>
            <div class="card-body p-0">
              <table class="table table-sm mb-0">
                <tbody>
                  <tr v-for="item in quotation.items" :key="item.uuid">
                    <td class="ps-3 small">{{ item.product_name }} × {{ item.quantity }}</td>
                    <td class="text-end pe-3 small fw-semibold">{{ money(item.subtotal) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="quotation.services?.length" class="card border-0 shadow-sm mb-3">
            <div class="card-header bg-white fw-semibold small text-uppercase">Servicios cotizados</div>
            <div class="card-body p-0">
              <table class="table table-sm mb-0">
                <tbody>
                  <tr v-for="svc in quotation.services" :key="svc.uuid">
                    <td class="ps-3 small">{{ svc.service_name }} ({{ svc.hours }}h)</td>
                    <td class="text-end pe-3 small fw-semibold">{{ money(svc.subtotal) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="card border-0 bg-primary-subtle">
            <div class="card-body p-3 d-flex justify-content-between align-items-center">
              <span class="fw-bold text-primary">TOTAL</span>
              <span class="fw-bold text-primary fs-5">{{ money(quotation.total_amount) }}</span>
            </div>
          </div>
        </div>

        <!-- Columna derecha: estado + acciones -->
        <div class="col-lg-5">
          <div class="card border-0 shadow-sm mb-3">
            <div class="card-body p-3">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <code class="small text-muted">#{{ quotation.uuid.slice(0, 8) }}</code>
                <span class="badge border rounded-pill" :class="enums.cssClass('quote-statuses', quotation.status, 'bg-light text-secondary')">
                  {{ enums.label('quote-statuses', quotation.status, quotation.status) }}
                </span>
              </div>
              <label class="form-label small fw-semibold mt-2">Cambiar estado</label>
              <select v-model="newStatus" class="form-select form-select-sm mb-2">
                <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
              <textarea v-model="statusNotes" class="form-control form-control-sm mb-2" rows="2" placeholder="Notas (opcional)"></textarea>
              <button class="btn btn-primary btn-sm w-100" :disabled="quotationsStore.actionLoading" @click="handleChangeStatus">
                <span v-if="quotationsStore.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                Actualizar estado
              </button>
            </div>
          </div>

          <div class="card border-0 shadow-sm mb-3">
            <div class="card-body p-3">
              <h6 class="small fw-semibold text-uppercase mb-2">Agregar producto</h6>
              <div class="row g-2">
                <div class="col-6">
                  <input v-model.number="newItem.variant_id" type="number" class="form-control form-control-sm" placeholder="ID variante" />
                </div>
                <div class="col-4">
                  <input v-model.number="newItem.quantity" type="number" min="1" class="form-control form-control-sm" placeholder="Cant." />
                </div>
                <div class="col-2">
                  <button class="btn btn-sm btn-success w-100" @click="handleAddItem"><i class="bi bi-plus-lg"></i></button>
                </div>
              </div>

              <h6 class="small fw-semibold text-uppercase mt-3 mb-2">Agregar servicio personalizado</h6>
              <input v-model="newService.service_name" class="form-control form-control-sm mb-2" placeholder="Nombre del servicio" />
              <div class="row g-2">
                <div class="col-6">
                  <input v-model.number="newService.hours" type="number" step="0.5" class="form-control form-control-sm" placeholder="Horas" />
                </div>
                <div class="col-6">
                  <input v-model.number="newService.labor_cost" type="number" step="1000" class="form-control form-control-sm" placeholder="Costo M.O." />
                </div>
              </div>
              <button class="btn btn-sm btn-success w-100 mt-2" @click="handleAddService"><i class="bi bi-plus-lg me-1"></i>Agregar</button>
            </div>
          </div>

          <div class="card border-0 shadow-sm mb-3">
            <div class="card-body p-3">
              <h6 class="small fw-semibold text-uppercase mb-2">Historial</h6>
              <div v-for="event in quotation.timeline" :key="event.uuid" class="d-flex justify-content-between small border-bottom py-2">
                <div>
                  <span class="badge border rounded-pill" :class="enums.cssClass('quote-statuses', event.status, 'bg-light text-secondary')">
                    {{ event.status_display }}
                  </span>
                  <div v-if="event.notes" class="text-muted mt-1">{{ event.notes }}</div>
                </div>
                <span class="text-muted">{{ formatDate(event.created_at) }}</span>
              </div>
            </div>
          </div>

          <button class="btn btn-outline-danger w-100" :disabled="pdfLoading" @click="downloadPdf">
            <span v-if="pdfLoading" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-file-pdf me-1"></i>Generar / Descargar PDF
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useQuotationsAdminStore } from '@/store/quotesAdmin/quotations';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';
import useApi from '@/composables/useApi';

const props = defineProps({
  uuid: { type: String, required: true },
});

const templateStore = useQuoteTemplateBuilderStore();
const quotationsStore = useQuotationsAdminStore();
const toast = useToast();
const enums = useEnums();
const api = useApi();

const loading = ref(true);
const pdfLoading = ref(false);
const newStatus = ref('');
const statusNotes = ref('');
const newItem = ref({ variant_id: null, quantity: 1 });
const newService = ref({ service_name: '', hours: null, labor_cost: null });

const quotation = computed(() => quotationsStore.currentQuotation);
const template = computed(() => templateStore.currentTemplate);

const statusOptions = [
  { value: 'BORRADOR', label: 'Borrador' },
  { value: 'RECIBIDA', label: 'Recibida' },
  { value: 'EN_REVISION', label: 'En revisión' },
  { value: 'PENDIENTE_INFORMACION', label: 'Pendiente información' },
  { value: 'COTIZADA', label: 'Cotizada' },
  { value: 'ENVIADA', label: 'Enviada' },
  { value: 'ACEPTADA', label: 'Aceptada' },
  { value: 'RECHAZADA', label: 'Rechazada' },
  { value: 'VENCIDA', label: 'Vencida' },
  { value: 'CANCELADA', label: 'Cancelada' },
];

const GROUP_LABELS = { EQUIPMENT: 'Equipos', MATERIALS: 'Materiales', LABOR: 'Mano de Obra' };

const answerGroups = computed(() => {
  if (!template.value || !quotation.value) return [];
  const answers = quotation.value.answers || {};
  return Object.entries(GROUP_LABELS).map(([type, label]) => {
    const modules = (template.value.modules || []).filter((m) => m.module_type === type);
    const rows = [];
    for (const module of modules) {
      const moduleAnswers = answers[module.uuid] || {};
      for (const q of module.questions) {
        if (!(q.key in moduleAnswers)) continue;
        const value = moduleAnswers[q.key];
        if (value === '<attachment>') {
          const attachment = (quotation.value.attachments || []).find((a) => a.note === `${module.uuid}__${q.key}`);
          rows.push({ key: `${module.uuid}-${q.key}`, label: q.label, attachment });
        } else {
          rows.push({ key: `${module.uuid}-${q.key}`, label: q.label, value: Array.isArray(value) ? value.join(', ') : String(value) });
        }
      }
    }
    return { type, label, rows };
  });
});

async function load() {
  loading.value = true;
  const q = await quotationsStore.fetchQuotationDetail(props.uuid);
  if (q?.template_uuid) {
    await templateStore.fetchTemplateDetail(q.template_uuid);
  }
  newStatus.value = q?.status || '';
  loading.value = false;
}

watch(() => props.uuid, load);
onMounted(load);

async function handleChangeStatus() {
  const { ok, error } = await quotationsStore.changeQuotationStatus(props.uuid, newStatus.value, statusNotes.value);
  if (ok) {
    toast.success('Estado actualizado.');
    statusNotes.value = '';
  } else {
    toast.error(error || 'Error al cambiar el estado.');
  }
}

async function handleAddItem() {
  if (!newItem.value.variant_id || !newItem.value.quantity) {
    toast.error('ID de variante y cantidad son obligatorios.');
    return;
  }
  const { ok, error } = await quotationsStore.addQuotationItem(props.uuid, newItem.value);
  if (ok) {
    toast.success('Producto agregado.');
    newItem.value = { variant_id: null, quantity: 1 };
  } else {
    toast.error(error || 'Error al agregar el producto.');
  }
}

async function handleAddService() {
  if (!newService.value.service_name) {
    toast.error('El nombre del servicio es obligatorio.');
    return;
  }
  const { ok, error } = await quotationsStore.addQuotationService(props.uuid, newService.value);
  if (ok) {
    toast.success('Servicio agregado.');
    newService.value = { service_name: '', hours: null, labor_cost: null };
  } else {
    toast.error(error || 'Error al agregar el servicio.');
  }
}

async function downloadPdf() {
  pdfLoading.value = true;
  try {
    const response = await api.get(`quotes/quotations/${props.uuid}/download_pdf/`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cotizacion-${props.uuid.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch {
    toast.error('No se pudo descargar el PDF.');
  } finally {
    pdfLoading.value = false;
  }
}

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0);
}

function formatDate(d) {
  if (!d) return '';
  return new Date(d).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}
</script>

<style scoped>
.smaller { font-size: 0.72rem; }
</style>
