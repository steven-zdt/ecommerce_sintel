<template>
  <div class="seo-tags-module">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div>
        <h4 class="fw-bold m-0">Meta Tags SEO</h4>
        <p class="text-muted small mb-0">
          Metaetiquetas del <code>&lt;head&gt;</code> del sitio publico (verificacion de dominio,
          analytics, pixels...). Cambios aqui se reflejan en producto sin tocar codigo.
        </p>
      </div>
      <div v-if="activeTab === 'tags'" class="d-flex gap-2">
        <button type="button" class="btn btn-outline-secondary btn-sm" @click="exportTags">
          <i class="bi bi-download me-1"></i>Exportar
        </button>
        <label class="btn btn-outline-secondary btn-sm mb-0">
          <i class="bi bi-upload me-1"></i>Importar
          <input type="file" accept="application/json" class="d-none" @change="onImportFile">
        </label>
        <button type="button" class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg me-1"></i>Nueva metaetiqueta
        </button>
      </div>
    </div>

    <ul class="nav nav-tabs mb-3">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: activeTab === 'tags' }" @click="activeTab = 'tags'">
          <i class="bi bi-tags me-1"></i>Metaetiquetas
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: activeTab === 'files' }" @click="activeTab = 'files'">
          <i class="bi bi-file-earmark-code me-1"></i>Archivos de verificacion
        </button>
      </li>
    </ul>

    <SeoVerificationFilesPanel v-if="activeTab === 'files'" />

    <template v-if="activeTab === 'tags'">
    <!-- Filtros -->
    <div class="card shadow-sm border-0 mb-3">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-4">
            <div class="input-group input-group-sm">
              <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
              <input v-model="filters.search" type="text" class="form-control border-start-0 ps-0"
                     placeholder="Buscar por nombre, meta_name o descripcion...">
            </div>
          </div>
          <div class="col-md-2">
            <select v-model="filters.provider" class="form-select form-select-sm">
              <option value="">Proveedor: todos</option>
              <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="col-md-2">
            <select v-model="filters.tag_type" class="form-select form-select-sm">
              <option value="">Tipo: todos</option>
              <option v-for="opt in tagTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="col-md-2">
            <select v-model="filters.environment" class="form-select form-select-sm">
              <option value="">Entorno: todos</option>
              <option v-for="opt in environmentOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="col-md-2">
            <select v-model="filters.is_active" class="form-select form-select-sm">
              <option value="">Estado: todos</option>
              <option value="true">Activas</option>
              <option value="false">Inactivas</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Nombre</th>
              <th>Proveedor</th>
              <th>meta_name / content</th>
              <th style="width:90px">Prioridad</th>
              <th>Entorno</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
              </td>
            </tr>
            <tr v-else-if="tags.length === 0">
              <td colspan="7" class="text-center py-5 text-muted">Sin metaetiquetas con estos filtros.</td>
            </tr>
            <template v-for="tag in tags" :key="tag.uuid">
              <tr v-if="pendingDelete?.uuid === tag.uuid" class="bg-danger-subtle">
                <td colspan="7" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ tag.name }}</strong>? Esta accion es reversible.</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" :disabled="actionLoading" @click="executeDelete(tag)">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td>
                  <div class="fw-bold">{{ tag.name }}</div>
                  <div class="text-muted smaller">{{ tag.tag_type_label }}</div>
                </td>
                <td>{{ tag.provider_label }}</td>
                <td class="smaller">
                  <code v-if="tag.meta_name">{{ tag.meta_name }} = {{ tag.meta_content }}</code>
                  <span v-else class="text-muted">HTML avanzado</span>
                </td>
                <td>
                  <input v-model.number="tag._priority" type="number" min="0"
                         class="form-control form-control-sm" @change="reorderDirty = true">
                </td>
                <td>
                  <span class="badge bg-light text-dark border">{{ tag.environment_label }}</span>
                </td>
                <td>
                  <span class="badge" :class="tag.is_active ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
                    {{ tag.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button type="button" class="btn btn-light border-end" title="Vista previa" @click="openPreview(tag)">
                      <i class="bi bi-eye text-secondary"></i>
                    </button>
                    <button type="button" class="btn btn-light border-end" title="Historial" @click="openHistory(tag)">
                      <i class="bi bi-clock-history text-secondary"></i>
                    </button>
                    <button type="button" class="btn btn-light border-end" title="Editar" @click="openEdit(tag)">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button type="button" class="btn btn-light border-end" title="Duplicar" @click="duplicateTag(tag)">
                      <i class="bi bi-files text-primary"></i>
                    </button>
                    <button type="button" class="btn btn-light border-end" :title="tag.is_active ? 'Desactivar' : 'Activar'" @click="toggleTag(tag)">
                      <i class="bi" :class="tag.is_active ? 'bi-toggle-on text-success' : 'bi-toggle-off text-secondary'"></i>
                    </button>
                    <button type="button" class="btn btn-light" title="Eliminar" @click="pendingDelete = tag">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="tags.length">
        <span class="text-muted smaller">Mostrando {{ tags.length }} de {{ totalCount }} registros</span>
        <div class="d-flex align-items-center gap-2">
          <button v-if="reorderDirty" class="btn btn-sm btn-outline-primary" :disabled="actionLoading" @click="saveOrder">
            <i class="bi bi-sort-numeric-down me-1"></i>Guardar orden
          </button>
          <nav v-if="totalPages > 1">
            <ul class="pagination pagination-sm m-0">
              <li class="page-item" :class="{ disabled: currentPage <= 1 }">
                <button class="page-link" @click="changePage(currentPage - 1)">Ant.</button>
              </li>
              <li class="page-item" :class="{ disabled: currentPage >= totalPages }">
                <button class="page-link" @click="changePage(currentPage + 1)">Sig.</button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </div>

    <!-- Offcanvas crear/editar -->
    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nueva metaetiqueta' : 'Editar metaetiqueta'"
      :subtitle="mode === 'create' ? 'Se agrega al <head> del sitio si queda activa' : `Modificando: ${selected?.name}`"
      width="720px"
    >
      <SeoMetaTagForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>

    <!-- Vista previa -->
    <BaseModal v-model="showPreview" title="Vista previa del HTML real">
      <pre class="preview-box mb-0">{{ previewHtml }}</pre>
    </BaseModal>

    <!-- Historial -->
    <BaseModal v-model="showHistory" title="Historial de auditoria" wide>
      <div v-if="historyLoading" class="text-center py-4">
        <div class="spinner-border text-primary"></div>
      </div>
      <div v-else-if="!historyEntries.length" class="text-muted small">Sin movimientos registrados.</div>
      <table v-else class="table table-sm">
        <thead>
          <tr><th>Fecha</th><th>Accion</th><th>Usuario</th><th>IP</th></tr>
        </thead>
        <tbody>
          <tr v-for="entry in historyEntries" :key="entry.uuid">
            <td class="smaller">{{ new Date(entry.created_at).toLocaleString() }}</td>
            <td><span class="badge bg-light text-dark border">{{ entry.action_label }}</span></td>
            <td class="smaller">{{ entry.user_email || '—' }}</td>
            <td class="smaller">{{ entry.ip_address || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </BaseModal>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import BaseModal from '@/components/base/BaseModal.vue';
import SeoMetaTagForm from './SeoMetaTagForm.vue';
import SeoVerificationFilesPanel from './SeoVerificationFilesPanel.vue';

const activeTab = ref('tags');

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const BASE_URL = 'dashboard/seo/meta-tags/';

const providerOptions = [
  { value: 'meta', label: 'Meta Business Suite' }, { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' }, { value: 'google_search_console', label: 'Google Search Console' },
  { value: 'google_tag_manager', label: 'Google Tag Manager' }, { value: 'google_analytics', label: 'Google Analytics' },
  { value: 'bing', label: 'Microsoft Bing' }, { value: 'pinterest', label: 'Pinterest' },
  { value: 'tiktok', label: 'TikTok' }, { value: 'linkedin', label: 'LinkedIn' },
  { value: 'apple', label: 'Apple' }, { value: 'cloudflare', label: 'Cloudflare' },
  { value: 'custom', label: 'Personalizado' },
];
const tagTypeOptions = [
  { value: 'domain_verification', label: 'Verificacion de dominio' }, { value: 'analytics', label: 'Analytics' },
  { value: 'pixel', label: 'Pixel de conversion' }, { value: 'seo', label: 'SEO' },
  { value: 'social', label: 'Redes sociales' }, { value: 'custom', label: 'Personalizado' },
];
const environmentOptions = [
  { value: 'all', label: 'Todos' }, { value: 'development', label: 'Development' },
  { value: 'testing', label: 'Testing' }, { value: 'staging', label: 'Staging' },
  { value: 'production', label: 'Production' },
];

const tags = ref([]);
const loading = ref(false);
const actionLoading = ref(false);
const totalCount = ref(0);
const totalPages = ref(1);
const currentPage = ref(1);
const pendingDelete = ref(null);
const reorderDirty = ref(false);

const filters = reactive({ search: '', provider: '', tag_type: '', environment: '', is_active: '' });

const showPreview = ref(false);
const previewHtml = ref('');
const showHistory = ref(false);
const historyLoading = ref(false);
const historyEntries = ref([]);

async function fetchTags() {
  loading.value = true;
  try {
    const params = { page: currentPage.value };
    if (filters.search) params.search = filters.search;
    if (filters.provider) params.provider = filters.provider;
    if (filters.tag_type) params.tag_type = filters.tag_type;
    if (filters.environment) params.environment = filters.environment;
    if (filters.is_active) params.is_active = filters.is_active;

    const { data } = await api.get(BASE_URL, { params });
    tags.value = (data.results || data).map(t => ({ ...t, _priority: t.priority }));
    totalCount.value = data.count ?? tags.value.length;
    totalPages.value = data.count ? Math.ceil(data.count / 25) : 1;
    reorderDirty.value = false;
  } catch (err) {
    handleError(err, 'No se pudieron cargar las metaetiquetas.');
  } finally {
    loading.value = false;
  }
}

function changePage(page) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    fetchTags();
  }
}

let debounceTimer = null;
watch(filters, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => { currentPage.value = 1; fetchTags(); }, 400);
}, { deep: true });

function onFormSuccess() {
  close();
  fetchTags();
}

async function executeDelete(tag) {
  actionLoading.value = true;
  try {
    await api.delete(`${BASE_URL}${tag.uuid}/`);
    toast.success(`Metaetiqueta "${tag.name}" eliminada.`);
    await fetchTags();
  } catch (err) {
    handleError(err, 'No se pudo eliminar.');
  } finally {
    actionLoading.value = false;
    pendingDelete.value = null;
  }
}

async function duplicateTag(tag) {
  try {
    await api.post(`${BASE_URL}${tag.uuid}/duplicate/`);
    toast.success('Metaetiqueta duplicada (inactiva).');
    await fetchTags();
  } catch (err) {
    handleError(err, 'No se pudo duplicar.');
  }
}

async function toggleTag(tag) {
  try {
    const { data } = await api.post(`${BASE_URL}${tag.uuid}/toggle/`);
    toast.success(data.is_active ? 'Metaetiqueta activada.' : 'Metaetiqueta desactivada.');
    await fetchTags();
  } catch (err) {
    handleError(err, 'No se pudo cambiar el estado.');
  }
}

async function openPreview(tag) {
  try {
    const { data } = await api.get(`${BASE_URL}${tag.uuid}/preview/`);
    previewHtml.value = data.html;
    showPreview.value = true;
  } catch (err) {
    handleError(err, 'No se pudo cargar la vista previa.');
  }
}

async function openHistory(tag) {
  showHistory.value = true;
  historyLoading.value = true;
  try {
    const { data } = await api.get(`${BASE_URL}${tag.uuid}/history/`);
    historyEntries.value = data;
  } catch (err) {
    handleError(err, 'No se pudo cargar el historial.');
  } finally {
    historyLoading.value = false;
  }
}

async function saveOrder() {
  actionLoading.value = true;
  try {
    const ordered = [...tags.value].sort((a, b) => a._priority - b._priority).map(t => t.uuid);
    await api.post(`${BASE_URL}reorder/`, { items: ordered });
    toast.success('Orden guardado.');
    await fetchTags();
  } catch (err) {
    handleError(err, 'No se pudo guardar el orden.');
  } finally {
    actionLoading.value = false;
  }
}

async function exportTags() {
  try {
    const { data } = await api.get(`${BASE_URL}export/`);
    const blob = new Blob([JSON.stringify(data.items, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'sintel-seo-meta-tags.json';
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    handleError(err, 'No se pudo exportar.');
  }
}

function onImportFile(event) {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const items = JSON.parse(reader.result);
      await api.post(`${BASE_URL}import/`, { items: Array.isArray(items) ? items : items.items });
      toast.success('Metaetiquetas importadas.');
      await fetchTags();
    } catch (err) {
      handleError(err, 'No se pudo importar el archivo (verifica el formato JSON).');
    }
  };
  reader.readAsText(file);
}

onMounted(fetchTags);
</script>

<style scoped>
.smaller { font-size: 0.8rem; }
.preview-box {
  background: #0f172a; color: #e2e8f0; border-radius: 8px;
  padding: .75rem 1rem; font-size: .8rem; white-space: pre-wrap; word-break: break-all;
}
</style>
