<template>
  <div class="au-view">
    <div class="au-header">
      <h1 class="au-title">Nosotros</h1>
      <p class="au-subtitle">
        Filosofia institucional de la empresa (historia, mision, vision y valores) — visible
        en la pagina publica <code>/nosotros</code>.
      </p>
    </div>

    <div class="au-panel">
      <h2 class="au-section-title">Contenido general</h2>
      <div class="row g-3">
        <div class="col-md-6">
          <BaseInput v-model="configForm.title" label="Titulo" placeholder="Sobre Nosotros" maxlength="255" />
        </div>
        <div class="col-md-6">
          <BaseInput v-model="configForm.subtitle" label="Subtitulo" maxlength="500" />
        </div>
        <div class="col-md-4">
          <BaseUpload label="Imagen principal" :preview-url="heroPreview" @file-selected="onHeroSelected" />
          <button v-if="heroPreview" type="button" class="btn btn-link btn-sm text-danger p-0 mt-1" @click="removeHero">
            Quitar imagen
          </button>
        </div>
        <div class="col-md-8">
          <BaseTextarea v-model="configForm.history" label="Nuestra historia" :rows="4" />
        </div>
        <div class="col-md-6">
          <BaseTextarea v-model="configForm.mission" label="Mision" :rows="3" />
        </div>
        <div class="col-md-6">
          <BaseTextarea v-model="configForm.vision" label="Vision" :rows="3" />
        </div>
        <div class="col-12">
          <div class="form-check form-switch">
            <input v-model="configForm.is_visible" class="form-check-input" type="checkbox" id="auVisible">
            <label class="form-check-label small" for="auVisible">Pagina visible para el publico</label>
          </div>
        </div>
      </div>
      <button class="au-btn-primary mt-3" :disabled="actionLoading" @click="saveConfig">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
        Guardar
      </button>
    </div>

    <div class="au-panel mt-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h2 class="au-section-title mb-0">Valores institucionales</h2>
        <button class="au-btn-primary" @click="openCreateValue">
          <i class="bi bi-plus-lg me-1"></i>Nuevo valor
        </button>
      </div>

      <div v-if="loadingValues" class="text-center py-5">
        <div class="spinner-border text-primary"></div>
      </div>
      <div v-else-if="!values.length" class="au-empty">Sin valores institucionales configurados.</div>
      <div v-else class="au-value-list">
        <div v-for="value in values" :key="value.uuid" class="au-value-row"
          :class="{ 'bg-danger-subtle': confirmingUuid === value.uuid }">
          <template v-if="confirmingUuid === value.uuid">
            <span class="text-danger small flex-grow-1">¿Eliminar "{{ value.title }}"?</span>
            <button class="btn btn-sm btn-danger me-1" :disabled="actionLoading" @click="deleteValue(value)">Confirmar</button>
            <button class="btn btn-sm btn-outline-secondary" @click="confirmingUuid = null">Cancelar</button>
          </template>
          <template v-else>
            <IconRenderer :icon="normalizeIconInput(value.icon_class)" size="1.4rem" class="au-value-icon" />
            <div class="au-value-text">
              <strong>{{ value.title }}</strong>
              <p class="mb-0 text-muted small">{{ value.description }}</p>
            </div>
            <span v-if="!value.is_active" class="badge bg-secondary-subtle text-secondary me-2">Inactivo</span>
            <button class="au-icon-btn" @click="openEditValue(value)"><i class="bi bi-pencil"></i></button>
            <button class="au-icon-btn text-danger" @click="confirmingUuid = value.uuid"><i class="bi bi-trash"></i></button>
          </template>
        </div>
      </div>
    </div>

    <BaseModal v-model="showValueModal" :title="editingValue ? 'Editar valor' : 'Nuevo valor'">
      <div class="mb-2">
        <BaseInput v-model="valueForm.title" label="Titulo" required maxlength="150" />
      </div>
      <div class="mb-2">
        <BaseTextarea v-model="valueForm.description" label="Descripcion" :rows="3" />
      </div>
      <div class="row g-2">
        <div class="col-7">
          <label class="bi-label">Icono (Bootstrap o atajo: gem, shield, people...)</label>
          <div class="d-flex align-items-center gap-2">
            <IconRenderer :icon="normalizeIconInput(valueForm.icon_class)" size="1.3rem" />
            <input v-model="valueForm.icon_class" class="form-control form-control-sm" placeholder="bi-gem">
          </div>
        </div>
        <div class="col-5">
          <BaseInput v-model="valueForm.display_order" type="number" label="Orden" />
        </div>
      </div>
      <div class="mt-2">
        <div class="form-check form-switch">
          <input v-model="valueForm.is_active" class="form-check-input" type="checkbox" id="auValueActive">
          <label class="form-check-label small" for="auValueActive">Activo</label>
        </div>
      </div>
      <p v-if="valueError" class="text-danger small mt-2">{{ valueError }}</p>
      <template #footer>
        <button class="btn btn-outline-secondary btn-sm" @click="showValueModal = false">Cancelar</button>
        <button class="btn btn-primary btn-sm" :disabled="actionLoading" @click="saveValue">
          <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Guardar
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import BaseInput from '@/components/base/BaseInput.vue';
import BaseTextarea from '@/components/base/BaseTextarea.vue';
import BaseUpload from '@/components/base/BaseUpload.vue';
import BaseModal from '@/components/base/BaseModal.vue';
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { normalizeIconInput } from '@/utils/iconShorthand';

const toast = useToast();
const store = useCoreAdminStore();
const {
  values, valuesLoading: loadingValues,
  actionLoading,
} = storeToRefs(store);

const heroFile = ref(null);
const heroPreview = ref(null);
const heroRemoved = ref(false);

const configForm = ref({
  title: '', subtitle: '', history: '', mission: '', vision: '', is_visible: true,
});

const confirmingUuid = ref(null);

const showValueModal = ref(false);
const editingValue = ref(null);
const valueError = ref('');
const valueForm = reactive({ title: '', description: '', icon_class: 'bi-gem', display_order: 0, is_active: true });

function onHeroSelected(file) {
  heroFile.value = file;
  heroPreview.value = URL.createObjectURL(file);
  heroRemoved.value = false;
}

function removeHero() {
  heroFile.value = null;
  heroPreview.value = null;
  heroRemoved.value = true;
}

async function fetchConfig() {
  await store.fetchConfig();
  if (store.error) { toast.error(store.error); return; }
  const data = store.config;
  if (!data) return;
  configForm.value = {
    title: data.title || '', subtitle: data.subtitle || '', history: data.history || '',
    mission: data.mission || '', vision: data.vision || '', is_visible: data.is_visible,
  };
  heroPreview.value = data.hero_image;
}

async function fetchValues() {
  await store.fetchValues();
  if (store.error) toast.error(store.error);
}

async function saveConfig() {
  const fd = new FormData();
  fd.append('title', configForm.value.title);
  fd.append('subtitle', configForm.value.subtitle);
  fd.append('history', configForm.value.history);
  fd.append('mission', configForm.value.mission);
  fd.append('vision', configForm.value.vision);
  fd.append('is_visible', configForm.value.is_visible);
  if (heroFile.value) fd.append('hero_image', heroFile.value);
  if (heroRemoved.value) fd.append('remove_hero_image', 'true');

  const res = await store.saveConfig(fd);
  if (res.ok) {
    toast.success('Contenido guardado.');
    heroFile.value = null;
    heroRemoved.value = false;
    await fetchConfig();
  } else {
    toast.error('Error guardando el contenido.');
  }
}

function openCreateValue() {
  editingValue.value = null;
  valueError.value = '';
  Object.assign(valueForm, { title: '', description: '', icon_class: 'bi-gem', display_order: values.value.length, is_active: true });
  showValueModal.value = true;
}

function openEditValue(value) {
  editingValue.value = value;
  valueError.value = '';
  Object.assign(valueForm, {
    title: value.title, description: value.description, icon_class: value.icon_class,
    display_order: value.display_order, is_active: value.is_active,
  });
  showValueModal.value = true;
}

async function saveValue() {
  if (!valueForm.title) {
    valueError.value = 'El titulo es obligatorio.';
    return;
  }
  valueError.value = '';
  const res = editingValue.value
    ? await store.updateValue(editingValue.value.uuid, valueForm)
    : await store.createValue(valueForm);

  if (res.ok) {
    toast.success(editingValue.value ? 'Valor actualizado.' : 'Valor creado.');
    showValueModal.value = false;
    await fetchValues();
  } else {
    valueError.value = res.error?.response?.data?.title?.[0] || res.error?.response?.data?.detail || 'Error al guardar.';
  }
}

async function deleteValue(value) {
  const res = await store.deleteValue(value.uuid);
  if (res.ok) {
    toast.success('Valor eliminado.');
    await fetchValues();
  } else {
    toast.error('Error al eliminar.');
  }
  confirmingUuid.value = null;
}

onMounted(() => {
  fetchConfig();
  fetchValues();
});
</script>

<style scoped>
.au-view { padding: 2rem; max-width: 900px; }
.au-title { font-size: 1.5rem; font-weight: 700; margin-bottom: .25rem; }
.au-subtitle { color: #6b7280; font-size: .9rem; margin-bottom: 1.5rem; }
.au-subtitle code { background: #f3f4f6; padding: .1rem .4rem; border-radius: 4px; }
.au-panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 1.5rem; }
.au-section-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; }
.au-btn-primary {
  background: #1d4ed8; color: #fff; border: none; border-radius: 8px;
  padding: .55rem 1.2rem; font-size: .88rem; font-weight: 600; cursor: pointer;
}
.au-btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.au-empty { color: #9ca3af; font-size: .85rem; }
.au-value-list { display: flex; flex-direction: column; gap: .5rem; }
.au-value-row {
  display: flex; align-items: center; gap: .75rem; padding: .6rem .75rem;
  border: 1px solid #f3f4f6; border-radius: 10px; font-size: .85rem;
}
.au-value-icon { color: #1d4ed8; flex-shrink: 0; }
.au-value-text { flex-grow: 1; }
.au-icon-btn {
  background: none; border: none; color: #6b7280; padding: .25rem .4rem;
  border-radius: 6px; cursor: pointer;
}
.au-icon-btn:hover { background: #f3f4f6; }
.bi-label { display: block; font-size: .8rem; font-weight: 600; color: #374151; margin-bottom: .3rem; }
</style>
