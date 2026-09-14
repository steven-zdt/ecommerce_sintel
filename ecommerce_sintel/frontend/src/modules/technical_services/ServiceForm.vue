<template>
  <div>

    <!-- Banner post-creacion -->
    <div v-if="isNewlyCreated"
         class="alert border-0 py-2 px-3 mb-3 d-flex align-items-center gap-2"
         style="background:#fffbeb;border-left:3px solid #d97706 !important;border-radius:8px;font-size:.82rem">
      <i class="bi bi-check-circle-fill flex-shrink-0" style="color:#d97706"></i>
      <div>
        <strong>Servicio creado.</strong>
        Ahora configura las variantes de precio y los costos asociados.
      </div>
    </div>

    <!-- Vista previa (cliente) -- P6 del plan "Rediseno ServiceForm + Content/Media"
         (2026-08-14). Mismo patron que HomeConfigView.vue ("Ver sitio"): link plano
         target=_blank, sin componente/modal nuevo -- reusa la pagina publica real
         (ServiceDetailContent.vue, ya auditada en FASE 7) en vez de simularla. -->
    <div v-if="localMode === 'edit' && localItem?.uuid" class="d-flex justify-content-end mb-2">
      <a :href="`/servicios/${localItem.uuid}`" target="_blank" rel="noopener"
         class="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1">
        <i class="bi bi-eye"></i> Vista previa (cliente)
      </a>
    </div>

    <!-- ===================================================================
         TABS (4 consolidados: General, Imagen, Variantes, Costos)
    =================================================================== -->
    <ul class="nav nav-tabs nav-fill mb-4" style="font-size:.82rem">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'general' }" @click="tab = 'general'">
          <i class="bi bi-tools me-1"></i>General
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'images' }" @click="tab = 'images'">
          <i class="bi bi-image me-1"></i>Imagen
          <span v-if="localImages.length" class="badge bg-secondary-subtle text-secondary ms-1">{{ localImages.length }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'variants' }" @click="tab = 'variants'">
          <i class="bi bi-layers me-1"></i>Variantes
          <span v-if="variants.length" class="badge bg-primary-subtle text-primary ms-1">{{ variants.length }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'costos' }" @click="tab = 'costos'">
          <i class="bi bi-tags me-1"></i>Costos
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'packages' }" @click="tab = 'packages'">
          <i class="bi bi-box-seam me-1"></i>Paquetes
          <span v-if="packagesStore.packages.length" class="badge bg-primary-subtle text-primary ms-1">{{ packagesStore.packages.length }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'faq' }" @click="tab = 'faq'">
          <i class="bi bi-question-circle me-1"></i>FAQ
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'marketing' }" @click="tab = 'marketing'">
          <i class="bi bi-megaphone me-1"></i>Marketing
        </button>
      </li>
      <!-- Catalogo enriquecido (reingenieria SDP, 2026-08-05) -->
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'incluye' }" @click="tab = 'incluye'">
          <i class="bi bi-check2-circle me-1"></i>Incluye
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'no-incluye' }" @click="tab = 'no-incluye'">
          <i class="bi bi-x-circle me-1"></i>No incluye
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'requisitos' }" @click="tab = 'requisitos'">
          <i class="bi bi-clipboard-check me-1"></i>Requisitos
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'ficha-tecnica' }" @click="tab = 'ficha-tecnica'">
          <i class="bi bi-card-list me-1"></i>Ficha tecnica
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'documentacion' }" @click="tab = 'documentacion'">
          <i class="bi bi-file-earmark-text me-1"></i>Documentacion
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'videos' }" @click="tab = 'videos'">
          <i class="bi bi-camera-reels me-1"></i>Videos
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'proceso' }" @click="tab = 'proceso'">
          <i class="bi bi-list-ol me-1"></i>Proceso
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'contenido' }" @click="tab = 'contenido'">
          <i class="bi bi-layout-text-sidebar-reverse me-1"></i>Contenido del Servicio
        </button>
      </li>
    </ul>

    <!-- ===================================================================
         TAB 1: GENERAL
    =================================================================== -->
    <div v-show="tab === 'general'">
      <GeneralTab
        :form="form"
        :init-var="initVar"
        :local-mode="localMode"
        :categories="categories"
        :levels="levels"
        :loading="loading"
        @submit="submit"
        @cancel="emit('cancel')"
        @close="closeForm"
      />
    </div>

    <!-- ===================================================================
         TAB 2: IMAGEN
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('images')" v-show="tab === 'images'" :key="`images-${localItem?.uuid}`">
      <ServiceGalleryManager :images="localImages" :service-uuid="localItem?.uuid" @close="closeForm" />
    </div>

    <!-- ===================================================================
         TAB 3: VARIANTES
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('variants')" v-show="tab === 'variants'" :key="`variants-${localItem?.uuid}`">
      <VariantsTab :service-uuid="localItem?.uuid" @close="closeForm" />
    </div>

    <!-- ===================================================================
         TAB 4: COSTOS (Smart calculation panel)
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('costos')" v-show="tab === 'costos'">
      <CostosTab :service-uuid="localItem?.uuid" @close="closeForm" />
    </div>

    <!-- ===================================================================
         TAB 5: PAQUETES DE SERVICIO
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('packages')" v-show="tab === 'packages'">
      <ServicePackagesPanel :service="localItem" @close="closeForm" />
    </div>

    <!-- ===================================================================
         TAB 6: FAQ (unificacion con Renting, 2026-07-18)
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('faq')" v-show="tab === 'faq'">
      <ServiceFAQManager v-if="localItem?.uuid" :service-uuid="localItem.uuid" />
    </div>

    <!-- ===================================================================
         TAB 7: MARKETING (unificacion con Renting, 2026-07-18 -- replica
         RentingForm.vue, sin comparativa comprar-vs-alquilar: no aplica al
         dominio de servicios, ver ServiceMarketing en el modelo)
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('marketing')" v-show="tab === 'marketing'" :key="`marketing-${localItem?.uuid}`">
      <MarketingTab :service-uuid="localItem?.uuid" />
    </div>

    <!-- ===================================================================
         Catalogo enriquecido (reingenieria SDP, 2026-08-05) -- espejo del
         de Shop (ver frontend/src/modules/shop/ProductForm.vue)
    =================================================================== -->
    <div v-if="localMode === 'edit' && visitedTabs.has('incluye')" v-show="tab === 'incluye'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="service"
        endpoint="dashboard/service-included-items/"
        resource="included-items"
        resource-label="Item incluido"
        resource-label-plural="Items incluidos"
        hint="Que incluye este servicio."
        empty-icon="bi-check2-circle"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-check-circle' },
        ]"
      />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('no-incluye')" v-show="tab === 'no-incluye'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="service"
        endpoint="dashboard/service-excluded-items/"
        resource="excluded-items"
        resource-label="Item no incluido"
        resource-label-plural="Items no incluidos"
        hint="Que NO incluye este servicio."
        empty-icon="bi-x-circle"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-x-circle' },
        ]"
      />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('requisitos')" v-show="tab === 'requisitos'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="service"
        endpoint="dashboard/service-requirements/"
        resource="requirements"
        resource-label="Requisito"
        resource-label-plural="Requisitos"
        hint="Condiciones necesarias del cliente antes de prestar el servicio."
        empty-icon="bi-clipboard-check"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
        ]"
      />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('ficha-tecnica')" v-show="tab === 'ficha-tecnica'">
      <SpecificationsManager entity-type="service" :entity-uuid="localItem?.uuid" />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('documentacion')" v-show="tab === 'documentacion'">
      <DocumentsManager entity-type="service" :entity-uuid="localItem?.uuid" />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('videos')" v-show="tab === 'videos'">
      <VideosManager entity-type="service" :entity-uuid="localItem?.uuid" />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('proceso')" v-show="tab === 'proceso'">
      <ServiceProcessStepsManager :service-uuid="localItem?.uuid" />
    </div>

    <div v-if="localMode === 'edit' && visitedTabs.has('contenido')" v-show="tab === 'contenido'" :key="`contenido-${localItem?.uuid}`">
      <ContentBlocksTab
        entity-type="service"
        :entity-uuid="localItem?.uuid"
        :scope="form.scope"
        :warranty="form.warranty"
        :coverage-notes="form.coverage_notes"
        @jump-to-tab="tab = $event"
        @field-saved="({ field, value }) => { form[field] = value; }"
      />
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useTechnicalServicesCatalogStore } from '@/store/technicalServicesAdmin/catalog';
import { useTechnicalServicePackagesStore } from '@/store/technicalServicesAdmin/packages';
import { useToast } from '@/composables/useToast';
import GeneralTab from './service-form/GeneralTab.vue';
import ServiceGalleryManager from './service-form/ServiceGalleryManager.vue';
import VariantsTab from './service-form/VariantsTab.vue';
import CostosTab from './service-form/CostosTab.vue';
import MarketingTab from './service-form/MarketingTab.vue';
import ServicePackagesPanel from './ServicePackagesPanel.vue';
import ServiceFAQManager from './ServiceFAQManager.vue';
// Catalogo enriquecido (reingenieria SDP, 2026-08-05): CatalogListManager es
// generico y ya lo usan Renting/Shop (parent-key="service" aqui, mismo patron
// que Shop con parent-key="product") -- se reusa en vez de duplicarlo.
// ContentBlocksTab/SpecificationsManager/DocumentsManager/VideosManager [estas 3 ultimas
// generalizadas 2026-08-05, Sprint 5] tambien se reusan de Shop, con entity-type="service".
// ServiceProcessStepsManager NO tiene equivalente en Shop/Renting (paso a paso del servicio
// es un concepto exclusivo de Technical Services) -- se queda propio, sin generalizar.
import CatalogListManager from '@/modules/renting/catalog/CatalogListManager.vue';
import ContentBlocksTab from '@/modules/shop/product-form/ContentBlocksTab.vue';
import SpecificationsManager from '@/modules/shop/catalog/SpecificationsManager.vue';
import DocumentsManager from '@/modules/shop/catalog/DocumentsManager.vue';
import VideosManager from '@/modules/shop/catalog/VideosManager.vue';
import ServiceProcessStepsManager from './catalog/ServiceProcessStepsManager.vue';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const toast = useToast();
const store = useTechnicalServicesStore();
const catalogStore = useTechnicalServicesCatalogStore();
const packagesStore = useTechnicalServicePackagesStore();
const { categories, levels } = storeToRefs(catalogStore);
const { variants } = storeToRefs(store);

// ─── Estado general ───────────────────────────────────────────────────────────
const localMode      = ref(props.mode);
const localItem      = ref(props.item);
const isNewlyCreated = ref(false);
const tab            = ref('general');
const loading        = ref(false);

// ─── Lazy-mount de pestanas (P5, auditoria FASE 0-15 2026-08-14) ──────────────
// Antes las 14 pestanas de EDIT usaban solo v-show: todas se montaban al abrir
// el formulario, disparando de una vez los fetch onMounted/immediate de cada
// subcomponente (VariantsTab, CostosTab, ServicePackagesPanel, ContentBlocksTab,
// etc. -- 14 llamadas simultaneas por cada apertura, la pestana activa fuera la
// unica que el usuario ve). `visitedTabs` retrasa el `v-if` de cada pestana a su
// primera visita; una vez montada, `v-show` la conserva (no se desmonta al
// volver a "General") para no perder borradores en curso (ej. `pendingFiles` de
// ServiceGalleryManager). Se reinicia junto con `tab.value = 'general'` cada vez
// que cambia el item/modo -- cambiar de servicio no debe arrastrar pestanas
// "visitadas" del servicio anterior.
const visitedTabs = reactive(new Set(['general']));
watch(tab, (t) => visitedTabs.add(t));

// ─── Formulario General ───────────────────────────────────────────────────────
const emptyForm = () => ({
  name: '', description: '',
  scope: '', warranty: '', coverage_notes: '',
  category: null, level: null,
  is_active: true, is_featured: false, is_purchasable: true,
  meta_title: '', meta_description: '', meta_keywords: '',
});
const form = ref(emptyForm());

// ─── Variante inicial (CREATE) ────────────────────────────────────────────────
const emptyInitVar = () => ({
  pricing_strategy: 'FIXED', fixed_price: '',
  estimated_hours: 1, complexity_factor: 1,
});
const initVar = ref(emptyInitVar());

// ─── Imagenes (poblado desde item.images, mutado in-place por ServiceGalleryManager) ──
const localImages = ref([]);

// ─── Sync desde el padre ──────────────────────────────────────────────────────
watch(
  [() => props.item, () => props.mode],
  ([item, mode]) => {
    localMode.value      = mode;
    localItem.value      = item;
    isNewlyCreated.value = false;
    tab.value            = 'general';
    visitedTabs.clear();
    visitedTabs.add('general');

    if (item && mode === 'edit') {
      form.value = {
        name:           item.name,
        description:    item.description || '',
        scope:          item.scope || '',
        warranty:       item.warranty || '',
        coverage_notes: item.coverage_notes || '',
        category:       item.category_uuid || null,
        level:          item.level_uuid   || null,
        is_active:      item.is_active,
        is_featured:    item.is_featured,
        is_purchasable: item.is_purchasable,
        meta_title:       item.meta_title || '',
        meta_description: item.meta_description || '',
        meta_keywords:    item.meta_keywords || '',
      };
      localImages.value = item.images ? [...item.images] : [];
      packagesStore.fetchPackages(item.uuid);
    } else {
      form.value    = emptyForm();
      initVar.value = emptyInitVar();
      localImages.value = [];
      store.$patch({ variants: [] });
      packagesStore.$patch({ packages: [] });
    }
  },
  { immediate: true },
);

// ─── Submit General ───────────────────────────────────────────────────────────
async function submit() {
  loading.value = true;
  try {
    const payload = { ...form.value };

    if (localMode.value === 'create') {
      // El precio SIEMPRE se ingresa manualmente por el admin (instruccion
      // explicita del usuario, 2026-08-14) -- ninguna via para omitirlo al
      // crear el servicio.
      const iv = initVar.value;
      const isFixed = iv.pricing_strategy === 'FIXED';
      payload.initial_variant = {
        pricing_strategy: iv.pricing_strategy,
        fixed_price: isFixed ? (iv.fixed_price || null) : null,
        estimated_hours: isFixed ? 1 : (iv.estimated_hours || 1),
        complexity_factor: isFixed ? 1 : (iv.complexity_factor || 1),
      };
      const res = await store.createService(payload);
      if (!res.ok) throw new Error(res.error);
      const svc = res.data;

      localItem.value      = svc;
      localMode.value      = 'edit';
      isNewlyCreated.value = true;
      localImages.value    = svc.images ? [...svc.images] : [];
      tab.value            = 'variants';
      toast.success('Servicio creado con variante principal automática.');
    } else {
      const res = await store.updateService(localItem.value.uuid, payload);
      if (!res.ok) throw new Error(res.error);
      toast.success('Datos generales actualizados.');
    }
  } catch (e) {
    toast.error(e.message || 'Error al guardar el servicio.');
  } finally {
    loading.value = false;
  }
}

function closeForm() {
  emit('success');
}

onMounted(async () => {
  await Promise.all([catalogStore.fetchCategories(), catalogStore.fetchLevels()]);
});
</script>
