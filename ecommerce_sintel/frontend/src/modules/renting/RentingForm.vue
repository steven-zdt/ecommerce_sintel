<template>
  <div>

    <!-- =========================================================
         CREATE MODE — formulario basico
    ========================================================= -->
    <template v-if="localMode === 'create'">
      <DatosTab
        :form="form"
        :local-mode="localMode"
        :categories="categories"
        :brands="brands"
        :loading="loading"
        @submit-create="submitCreate"
        @cancel="emit('cancel')"
      />
    </template>

    <!-- =========================================================
         EDIT MODE — tabs completos
    ========================================================= -->
    <template v-else-if="localItem">

      <!-- Header equipo -->
      <div class="d-flex align-items-center gap-3 mb-4 p-3 bg-light rounded-3">
        <div class="rounded-2 d-flex align-items-center justify-content-center bg-primary-subtle flex-shrink-0" style="width:38px;height:38px">
          <i class="bi bi-gear-wide-connected text-primary"></i>
        </div>
        <div class="flex-grow-1 min-w-0">
          <div class="fw-bold text-dark small text-truncate">{{ localItem.name }}</div>
          <div class="text-muted" style="font-size:.72rem">{{ localItem.category?.name || 'Sin categoria' }}</div>
        </div>
        <span
          v-if="isNewlyCreated"
          class="badge bg-success-subtle text-success border border-success-subtle flex-shrink-0"
          style="font-size:.68rem"
        >
          <i class="bi bi-check-circle me-1"></i>Creado
        </span>
        <span
          v-if="!localItem.is_active"
          class="badge bg-warning-subtle text-warning border border-warning-subtle flex-shrink-0"
          style="font-size:.68rem"
        >Inactivo</span>
      </div>

      <!-- Tabs -->
      <ul class="nav nav-tabs mb-4" style="flex-wrap:nowrap;overflow-x:auto">
        <li class="nav-item" v-for="tab in tabs" :key="tab.key">
          <button
            class="nav-link d-flex align-items-center gap-1 text-nowrap"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
            type="button"
          >
            <i :class="['bi', tab.icon]" style="font-size:.8rem"></i>
            <span class="small fw-medium">{{ tab.label }}</span>
            <span v-if="tab.badge" class="ms-1 badge rounded-pill" :class="tab.badgeClass" style="font-size:.6rem">{{ tab.badge }}</span>
          </button>
        </li>
      </ul>

      <!-- ======= TAB: DATOS ======= -->
      <div v-show="activeTab === 'datos'">
        <DatosTab
          :form="form"
          :local-mode="localMode"
          :categories="categories"
          :brands="brands"
          :loading="loading"
          @submit-update="submitUpdate"
        />
      </div>

      <!-- ======= TAB: VARIANTES ======= -->
      <div v-show="activeTab === 'variantes'" :key="`variantes-${localItem.uuid}`">
        <VariantesTab :variants="variants" :actions="variantsActions" />
      </div>

      <!-- ======= TAB: LOGISTICA ======= -->
      <div v-show="activeTab === 'logistica'" :key="`logistica-${localItem.uuid}`">
        <LogisticaTab :equipment-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: GALERIA ======= -->
      <div v-show="activeTab === 'galeria'">
        <GalleryManager :equipment-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: INCLUYE ======= -->
      <div v-show="activeTab === 'incluye'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-included-items/"
          resource="included-items"
          resource-label="Item incluido"
          resource-label-plural="Items incluidos"
          hint="Que trae el alquiler (equipo principal, cables, maletin, soporte, etc.)."
          empty-icon="bi-check2-circle"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-check-circle' },
          ]"
        />
      </div>

      <!-- ======= TAB: NO INCLUYE ======= -->
      <div v-show="activeTab === 'no-incluye'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-excluded-items/"
          resource="excluded-items"
          resource-label="Item no incluido"
          resource-label-plural="Items no incluidos"
          hint="Que NO cubre el alquiler (consumibles, obra civil, licencias, etc.)."
          empty-icon="bi-x-circle"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-x-circle' },
          ]"
        />
      </div>

      <!-- ======= TAB: CARACTERISTICAS ======= -->
      <div v-show="activeTab === 'caracteristicas'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-features/"
          resource="features"
          resource-label="Caracteristica"
          resource-label-plural="Caracteristicas"
          hint="Atributos destacados del equipo (ej. Potencia: 20T)."
          empty-icon="bi-stars"
          :fields="[
            { key: 'title', label: 'Titulo', required: true, col: 'col-6' },
            { key: 'value', label: 'Valor', col: 'col-6' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-lightning-charge' },
          ]"
        />
      </div>

      <!-- ======= TAB: ESPECIFICACIONES ======= -->
      <div v-show="activeTab === 'especificaciones'">
        <SpecificationsManager entity-type="equipment" :entity-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: SERVICIOS INCLUIDOS ======= -->
      <div v-show="activeTab === 'servicios-incluidos'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-services-included/"
          resource="services-included"
          resource-label="Servicio incluido"
          resource-label-plural="Servicios incluidos"
          hint="Servicios que ya vienen en el precio del alquiler (ej. entrega basica)."
          empty-icon="bi-hand-thumbs-up"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-truck' },
          ]"
        />
      </div>

      <!-- ======= TAB: SERVICIOS OPCIONALES ======= -->
      <div v-show="activeTab === 'servicios-opcionales'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-optional-services/"
          resource="optional-services"
          resource-label="Servicio opcional"
          resource-label-plural="Servicios opcionales"
          hint="Servicios adicionales que el cliente puede contratar por un costo extra."
          empty-icon="bi-plus-circle"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'price', label: 'Precio', type: 'price', col: 'col-6' },
            { key: 'icon', label: 'Icono', type: 'icon', col: 'col-6' },
          ]"
        />
      </div>

      <!-- ======= TAB: REQUISITOS ======= -->
      <div v-show="activeTab === 'requisitos'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-requirements/"
          resource="requirements"
          resource-label="Requisito"
          resource-label-plural="Requisitos"
          hint="Condiciones necesarias para rentar el equipo (acceso vehicular, punto electrico, etc.)."
          empty-icon="bi-clipboard-check"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          ]"
        />
      </div>

      <!-- ======= TAB: DOCUMENTACION ======= -->
      <div v-show="activeTab === 'documentacion'">
        <DocumentsManager entity-type="equipment" :entity-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: VIDEOS ======= -->
      <div v-show="activeTab === 'videos'">
        <VideosManager entity-type="equipment" :entity-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: FAQ ======= -->
      <div v-show="activeTab === 'faq'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-faqs/"
          resource="faqs"
          resource-label="Pregunta"
          resource-label-plural="Preguntas frecuentes"
          hint="Preguntas frecuentes mostradas en el detalle publico del equipo."
          empty-icon="bi-question-circle"
          primary-field="question"
          secondary-field="answer"
          :fields="[
            { key: 'question', label: 'Pregunta', required: true, col: 'col-12' },
            { key: 'answer', label: 'Respuesta', type: 'textarea', required: true, col: 'col-12' },
          ]"
        />
      </div>

      <!-- ======= TAB: SEO ======= -->
      <div v-show="activeTab === 'seo'">
        <SeoManager :equipment="localItem" @updated="(data) => Object.assign(localItem, data)" />
      </div>

      <!-- ======= TAB: MARKETING ======= -->
      <div v-show="activeTab === 'marketing'" :key="`marketing-${localItem.uuid}`">
        <MarketingTab :equipment-uuid="localItem.uuid" :variants="variants" />
      </div>

      <!-- ======= TAB: COSTOS ======= -->
      <div v-show="activeTab === 'costos'" :key="`costos-${localItem.uuid}`">
        <CostosTab :cost-rules="costRules" :variants="variants" :actions="costosActions" />
      </div>

      <!-- Footer acciones globales -->
      <div class="d-flex justify-content-between align-items-center mt-5 pt-3 border-top">
        <span class="text-muted" style="font-size:.73rem">
          <i class="bi bi-floppy me-1"></i>Los cambios se guardan por seccion
        </span>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="emit('success')">
          <i class="bi bi-x-lg me-1"></i> Cerrar
        </button>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import CatalogListManager from '@/modules/renting/catalog/CatalogListManager.vue';
// SpecificationsManager/DocumentsManager/VideosManager [generalizados 2026-08-05, Sprint 5
// auditoria transversal] viven en shop/catalog/, importados cruzado con entity-type="equipment"
// (mismo patron ya establecido por ContentBlocksTab.vue) -- antes eran copias propias de renting.
import SpecificationsManager from '@/modules/shop/catalog/SpecificationsManager.vue';
import GalleryManager from '@/modules/renting/catalog/GalleryManager.vue';
import DocumentsManager from '@/modules/shop/catalog/DocumentsManager.vue';
import VideosManager from '@/modules/shop/catalog/VideosManager.vue';
import SeoManager from '@/modules/renting/catalog/SeoManager.vue';
import DatosTab from './equipment-form/DatosTab.vue';
import VariantesTab from './equipment-form/VariantesTab.vue';
import LogisticaTab from './equipment-form/LogisticaTab.vue';
import MarketingTab from './equipment-form/MarketingTab.vue';
import CostosTab from './equipment-form/CostosTab.vue';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const api   = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

// Estado interno — permite transicion create→edit sin involucrar al padre
const localMode       = ref(props.mode);
const localItem       = ref(props.item);
const isNewlyCreated  = ref(false);
const activeTab       = ref('datos');
const loading         = ref(false);

const tabs = computed(() => [
  { key: 'datos',     label: 'Datos',     icon: 'bi-file-text' },
  { key: 'galeria',   label: 'Galeria',   icon: 'bi-images' },
  { key: 'incluye',   label: 'Incluye',   icon: 'bi-check2-circle' },
  { key: 'no-incluye', label: 'No incluye', icon: 'bi-x-circle' },
  { key: 'caracteristicas', label: 'Caracteristicas', icon: 'bi-stars' },
  { key: 'especificaciones', label: 'Especificaciones', icon: 'bi-card-list' },
  { key: 'requisitos', label: 'Requisitos', icon: 'bi-clipboard-check' },
  { key: 'servicios-incluidos', label: 'Serv. incluidos', icon: 'bi-hand-thumbs-up' },
  { key: 'servicios-opcionales', label: 'Serv. opcionales', icon: 'bi-plus-circle' },
  { key: 'documentacion', label: 'Documentacion', icon: 'bi-file-earmark-arrow-up' },
  { key: 'videos',    label: 'Videos',    icon: 'bi-camera-reels' },
  { key: 'faq',       label: 'FAQ',       icon: 'bi-question-circle' },
  { key: 'seo',       label: 'SEO',       icon: 'bi-search' },
  { key: 'marketing', label: 'Marketing', icon: 'bi-megaphone', badge: null, badgeClass: '' },
  { key: 'variantes', label: 'Variantes', icon: 'bi-layers',
    badge: variants.value.length || null, badgeClass: 'bg-primary-subtle text-primary' },
  { key: 'logistica', label: 'Logistica', icon: 'bi-truck', badge: null, badgeClass: '' },
  { key: 'costos',    label: 'Costos',    icon: 'bi-tags',
    badge: costRules.value.filter(r => r.is_active).length || null, badgeClass: 'bg-warning-subtle text-warning' },
]);

// ─── Catalogo ─────────────────────────────────────────────────────────────────
const categories = ref([]);
const brands     = ref([]);

// ─── Formulario basico ────────────────────────────────────────────────────────
const form = ref({ name: '', description: '', category: '', brand: '', is_active: true, is_featured: false });

// ─── Variantes (compartido con Marketing/Costos/badge de tabs) ────────────────
const variants = ref([]);

// ─── Reglas de costo (compartido con el badge de tabs) ────────────────────────
const costRules = ref([]);

// ─── Sincronizar desde props del padre ────────────────────────────────────────
watch(
  () => [props.mode, props.item],
  ([m, i]) => {
    localMode.value      = m;
    localItem.value      = i;
    isNewlyCreated.value = false;
    activeTab.value      = 'datos';
    if (i && m === 'edit') {
      syncBasicForm(i);
      resetEditState();
    } else {
      form.value = { name: '', description: '', category: '', brand: '', is_active: true, is_featured: false };
      resetEditState();
    }
  },
  { immediate: true },
);

function syncBasicForm(item) {
  form.value = {
    name:        item.name,
    description: item.description || '',
    category:    item.category_uuid || item.category?.uuid || '',
    brand:       item.brand_uuid    || item.brand?.uuid    || '',
    is_active:   item.is_active,
    is_featured: item.is_featured,
  };
}

function resetEditState() {
  variants.value  = [];
  costRules.value = [];
}

async function loadCatalog() {
  try {
    const [catRes, brdRes] = await Promise.all([
      api.get('dashboard/renting-categories/'),
      api.get('dashboard/renting-brands/'),
    ]);
    categories.value = catRes.data.results || catRes.data;
    brands.value     = brdRes.data.results || brdRes.data;
  } catch {}
}

// ─── Crear equipo (create mode) ───────────────────────────────────────────────
async function submitCreate() {
  loading.value = true;
  try {
    const { data } = await api.post('dashboard/equipment/', {
      name:        form.value.name,
      description: form.value.description,
      category:    form.value.category,
      brand:       form.value.brand || null,
      is_active:   form.value.is_active,
      is_featured: form.value.is_featured,
    });
    // Transicion interna a edit sin cerrar el offcanvas
    localItem.value      = data;
    localMode.value      = 'edit';
    isNewlyCreated.value = true;
    syncBasicForm(data);
    resetEditState();
    activeTab.value = 'variantes';
    toast.success('Equipo creado. Ahora agrega variantes y configura precios.');
  } catch (e) {
    handleError(e, 'Error al crear el equipo');
  } finally {
    loading.value = false;
  }
}

// ─── Actualizar equipo (edit mode → tab datos) ────────────────────────────────
async function submitUpdate() {
  loading.value = true;
  try {
    const { data } = await api.patch(`dashboard/equipment/${localItem.value.uuid}/`, {
      name:        form.value.name,
      description: form.value.description,
      category:    form.value.category,
      brand:       form.value.brand || null,
      is_active:   form.value.is_active,
      is_featured: form.value.is_featured,
    });
    localItem.value = { ...localItem.value, ...data };
    toast.success('Datos del equipo actualizados');
  } catch (e) {
    handleError(e, 'Error al actualizar');
  } finally {
    loading.value = false;
  }
}

// ─── Variantes ────────────────────────────────────────────────────────────────
async function fetchVariants() {
  try {
    const res = await api.get(`dashboard/equipment/${localItem.value.uuid}/variants/`);
    variants.value = res.data.results || res.data;
  } catch {}
}

async function createVariant(payload) {
  await api.post(`dashboard/equipment/${localItem.value.uuid}/variants/create/`, {
    ...payload, equipment: localItem.value.uuid,
  });
  await fetchVariants();
}

async function updateVariant(uuid, payload) {
  await api.patch(`dashboard/equipment/${localItem.value.uuid}/variants/${uuid}/`, {
    ...payload, equipment: localItem.value.uuid,
  });
  await fetchVariants();
}

async function deleteVariant(uuid) {
  await api.delete(`dashboard/equipment/${localItem.value.uuid}/variants/${uuid}/delete/`);
  await fetchVariants();
}

const variantsActions = { fetchVariants, createVariant, updateVariant, deleteVariant };

// ─── Reglas de Costo ──────────────────────────────────────────────────────────
// Regla arquitectonica: NO existen reglas globales/heredadas en Renting. Cada
// regla pertenece exclusivamente al Equipment donde se creo -- el listado
// SIEMPRE se filtra por equipment, nunca se pide el catalogo completo.
async function fetchCostRules() {
  try {
    const res = await api.get('dashboard/rental-cost-rules/', { params: { equipment: localItem.value.uuid } });
    costRules.value = res.data.results || res.data;
  } catch {}
}

async function saveCostRule(payload) {
  await api.post('dashboard/rental-cost-rules/', { ...payload, equipment: localItem.value.uuid });
  await fetchCostRules();
}

async function toggleCostRule(rule) {
  if (rule.is_active) {
    await api.post(`dashboard/rental-cost-rules/${rule.uuid}/deactivate/`);
  } else {
    await api.patch(`dashboard/rental-cost-rules/${rule.uuid}/update/`, { is_active: true });
  }
  await fetchCostRules();
}

async function deleteCostRule(rule) {
  await api.delete(`dashboard/rental-cost-rules/${rule.uuid}/`);
  await fetchCostRules();
}

async function assignCostRule(ruleUuid, variantUuid) {
  await api.post(`dashboard/rental-cost-rules/${ruleUuid}/assign/`, { variant_uuid: variantUuid });
}

const costosActions = { fetchCostRules, saveCostRule, toggleCostRule, deleteCostRule, assignCostRule };

onMounted(loadCatalog);
</script>
