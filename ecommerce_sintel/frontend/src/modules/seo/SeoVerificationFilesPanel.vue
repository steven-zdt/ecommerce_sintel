<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <p class="text-muted small mb-0">
        Archivos servidos en la raiz del dominio (<code>https://sintel.net.co/&lt;archivo&gt;.html</code>) —
        metodo alternativo de verificacion ("Subir archivo HTML") que algunos proveedores ofrecen
        ademas de la metaetiqueta.
      </p>
      <button type="button" class="btn btn-primary btn-sm flex-shrink-0" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i>Nuevo archivo
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Nombre</th>
              <th>Proveedor</th>
              <th>Ruta publica</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
              </td>
            </tr>
            <tr v-else-if="files.length === 0">
              <td colspan="5" class="text-center py-4 text-muted">Sin archivos de verificacion registrados.</td>
            </tr>
            <template v-for="file in files" :key="file.uuid">
              <tr v-if="pendingDelete?.uuid === file.uuid" class="bg-danger-subtle">
                <td colspan="5" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ file.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(file)">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="fw-bold">{{ file.name }}</td>
                <td>{{ file.provider_label }}</td>
                <td>
                  <a :href="file.url_path" target="_blank" rel="noopener" class="smaller">{{ file.url_path }}</a>
                </td>
                <td>
                  <span class="badge" :class="file.is_active ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
                    {{ file.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button type="button" class="btn btn-light border-end" title="Editar" @click="openEdit(file)">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button type="button" class="btn btn-light border-end" :title="file.is_active ? 'Desactivar' : 'Activar'" @click="toggleFile(file)">
                      <i class="bi" :class="file.is_active ? 'bi-toggle-on text-success' : 'bi-toggle-off text-secondary'"></i>
                    </button>
                    <button type="button" class="btn btn-light" title="Eliminar" @click="pendingDelete = file">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <BaseModal v-model="showForm" :title="editing ? 'Editar archivo de verificacion' : 'Nuevo archivo de verificacion'" wide>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Nombre administrativo</label>
          <input v-model="form.name" type="text" class="form-control" maxlength="255">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Proveedor</label>
          <select v-model="form.provider" class="form-select">
            <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="col-12">
          <label class="form-label small fw-semibold">Nombre de archivo</label>
          <div class="input-group">
            <span class="input-group-text">/</span>
            <input v-model="form.filename" type="text" class="form-control" placeholder="codigo-de-verificacion.html"
                   :disabled="editing">
          </div>
          <div class="form-text">Solo letras, numeros, puntos, guiones y guion bajo, terminado en <code>.html</code>.</div>
        </div>
        <div class="col-12">
          <label class="form-label small fw-semibold">Contenido exacto del archivo</label>
          <textarea v-model="form.content" class="form-control font-monospace" rows="4"
                    placeholder="Pega aqui el contenido exacto que exige el proveedor"></textarea>
        </div>
        <div class="col-12">
          <div class="form-check form-switch">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" id="vfActive">
            <label class="form-check-label small" for="vfActive">Activo (se sirve en la raiz del dominio)</label>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-outline-secondary btn-sm" @click="showForm = false">Cancelar</button>
        <button class="btn btn-primary btn-sm" :disabled="saving" @click="submit">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          Guardar
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import BaseModal from '@/components/base/BaseModal.vue';

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

const BASE_URL = 'dashboard/seo/verification-files/';

const providerOptions = [
  { value: 'meta', label: 'Meta Business Suite' }, { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' }, { value: 'google_search_console', label: 'Google Search Console' },
  { value: 'google_tag_manager', label: 'Google Tag Manager' }, { value: 'google_analytics', label: 'Google Analytics' },
  { value: 'bing', label: 'Microsoft Bing' }, { value: 'pinterest', label: 'Pinterest' },
  { value: 'tiktok', label: 'TikTok' }, { value: 'linkedin', label: 'LinkedIn' },
  { value: 'apple', label: 'Apple' }, { value: 'cloudflare', label: 'Cloudflare' },
  { value: 'custom', label: 'Personalizado' },
];

const files = ref([]);
const loading = ref(false);
const saving = ref(false);
const pendingDelete = ref(null);
const showForm = ref(false);
const editing = ref(null);

const emptyForm = () => ({ name: '', provider: 'custom', filename: '', content: '', is_active: true });
const form = reactive(emptyForm());

async function fetchFiles() {
  loading.value = true;
  try {
    const { data } = await api.get(BASE_URL);
    files.value = data;
  } catch (err) {
    handleError(err, 'No se pudieron cargar los archivos de verificacion.');
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  Object.assign(form, emptyForm());
  showForm.value = true;
}

function openEdit(file) {
  editing.value = file;
  Object.assign(form, {
    name: file.name, provider: file.provider, filename: file.filename,
    content: file.content, is_active: file.is_active,
  });
  showForm.value = true;
}

async function submit() {
  saving.value = true;
  try {
    if (editing.value) {
      await api.patch(`${BASE_URL}${editing.value.uuid}/`, form);
      toast.success('Archivo actualizado.');
    } else {
      await api.post(BASE_URL, form);
      toast.success('Archivo creado.');
    }
    showForm.value = false;
    await fetchFiles();
  } catch (err) {
    handleError(err, 'No se pudo guardar el archivo.');
  } finally {
    saving.value = false;
  }
}

async function toggleFile(file) {
  try {
    await api.post(`${BASE_URL}${file.uuid}/toggle/`);
    toast.success(file.is_active ? 'Archivo desactivado.' : 'Archivo activado.');
    await fetchFiles();
  } catch (err) {
    handleError(err, 'No se pudo cambiar el estado.');
  }
}

async function executeDelete(file) {
  try {
    await api.delete(`${BASE_URL}${file.uuid}/`);
    toast.success('Archivo eliminado.');
    await fetchFiles();
  } catch (err) {
    handleError(err, 'No se pudo eliminar.');
  } finally {
    pendingDelete.value = null;
  }
}

onMounted(fetchFiles);
</script>

<style scoped>
.smaller { font-size: 0.8rem; }
</style>
