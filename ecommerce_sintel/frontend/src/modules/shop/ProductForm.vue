<template>
  <div>

    <!-- Banner informativo post-creacion -->
    <div v-if="isNewlyCreated" class="alert border-0 py-2 px-3 mb-3 d-flex align-items-center gap-2"
         style="background:#f0fdf4;border-left:3px solid #22c55e !important;border-radius:8px;font-size:.82rem">
      <i class="bi bi-check-circle-fill text-success flex-shrink-0"></i>
      <div>
        <strong>Producto creado.</strong>
        Ahora configura la variante por defecto: precio, descuento, logistica y costos adicionales.
      </div>
    </div>

    <!-- ================================================================
         TABS: create→ General|SEO   |   edit → General|SEO|Variantes|Costos
    ================================================================ -->
    <ul class="nav nav-tabs nav-fill mb-4" style="font-size:.82rem">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'general' }" @click="tab = 'general'">
          <i class="bi bi-box me-1"></i>General
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'seo' }" @click="tab = 'seo'">
          <i class="bi bi-search me-1"></i>SEO
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
          <span v-if="activeCostRulesCount" class="badge bg-warning-subtle text-warning ms-1">{{ activeCostRulesCount }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'imagenes' }" @click="tab = 'imagenes'">
          <i class="bi bi-images me-1"></i>Imagenes
          <span v-if="productImages.length" class="badge bg-secondary-subtle text-secondary ms-1">{{ productImages.length }}</span>
        </button>
      </li>
      <!-- Catalogo enriquecido (2026-08-03, espejo de renting.Equipment) -->
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
        <button type="button" class="nav-link" :class="{ active: tab === 'caracteristicas' }" @click="tab = 'caracteristicas'">
          <i class="bi bi-stars me-1"></i>Caracteristicas
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'especificaciones' }" @click="tab = 'especificaciones'">
          <i class="bi bi-card-list me-1"></i>Especificaciones
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'requisitos' }" @click="tab = 'requisitos'">
          <i class="bi bi-clipboard-check me-1"></i>Requisitos
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'servicios-incluidos' }" @click="tab = 'servicios-incluidos'">
          <i class="bi bi-hand-thumbs-up me-1"></i>Servicios incluidos
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'servicios-opcionales' }" @click="tab = 'servicios-opcionales'">
          <i class="bi bi-plus-circle me-1"></i>Servicios opcionales
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
        <button type="button" class="nav-link" :class="{ active: tab === 'galeria' }" @click="tab = 'galeria'">
          <i class="bi bi-images me-1"></i>Galeria
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'funcionamiento' }" @click="tab = 'funcionamiento'">
          <i class="bi bi-gear-wide-connected me-1"></i>Funcionamiento
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'faq' }" @click="tab = 'faq'">
          <i class="bi bi-question-circle me-1"></i>FAQ
        </button>
      </li>
      <!-- Contenido del Producto (Fase 4, reingenieria PDP 2026-08-05) -- coexiste con las
           9 pestanas de arriba, no las reemplaza (ver DISENO_FASE2_SHOP_CONTENIDO_PDP.md). -->
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'contenido' }" @click="tab = 'contenido'">
          <i class="bi bi-layout-text-sidebar-reverse me-1"></i>Contenido del Producto
        </button>
      </li>
    </ul>

    <!-- ================================================================
         TAB: GENERAL
    ================================================================ -->
    <div v-show="tab === 'general'">
      <GeneralTab
        :form="form"
        :local-mode="localMode"
        :categories="categories"
        :brands="brands"
        :action-loading="actionLoading"
        @submit="submit"
        @cancel="emit('cancel')"
        @close="closeForm"
      />
    </div>

    <!-- ================================================================
         TAB: SEO
    ================================================================ -->
    <div v-show="tab === 'seo'">
      <SeoTab
        :form="form"
        :local-mode="localMode"
        :action-loading="actionLoading"
        @submit="submit"
        @close="closeForm"
      />
    </div>

    <!-- ================================================================
         TAB: VARIANTES (solo localMode === 'edit')
    ================================================================ -->
    <div v-show="tab === 'variants' && localMode === 'edit'" :key="`variants-${localItem?.uuid}`">
      <VariantsTab :product-uuid="localItem?.uuid" @close="closeForm" @saved="emit('itemSaved', localItem)" />
    </div>

    <!-- ================================================================
         TAB: COSTOS (solo localMode === 'edit') — ProductCostRule
    ================================================================ -->
    <div v-show="tab === 'costos' && localMode === 'edit'" :key="`costos-${localItem?.uuid}`">
      <CostosTab @close="closeForm" />
    </div>

    <!-- ================================================================
         TAB: IMAGENES (solo localMode === 'edit')
    ================================================================ -->
    <div v-show="tab === 'imagenes' && localMode === 'edit'" :key="`imagenes-${localItem?.uuid}`">
      <ImagenesTab :product-uuid="localItem?.uuid" @close="closeForm" />
    </div>

    <!-- ================================================================
         Catalogo enriquecido (2026-08-03) — espejo de renting.Equipment
    ================================================================ -->
    <div v-show="tab === 'incluye' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-included-items/"
        resource="included-items"
        resource-label="Item incluido"
        resource-label-plural="Items incluidos"
        hint="Que trae la caja (accesorios, cables, manual impreso, etc.)."
        empty-icon="bi-check2-circle"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-check-circle' },
        ]"
      />
    </div>

    <div v-show="tab === 'no-incluye' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-excluded-items/"
        resource="excluded-items"
        resource-label="Item no incluido"
        resource-label-plural="Items no incluidos"
        hint="Que NO trae el producto (pilas, instalacion, accesorios opcionales, etc.)."
        empty-icon="bi-x-circle"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-x-circle' },
        ]"
      />
    </div>

    <div v-show="tab === 'caracteristicas' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-features/"
        resource="features"
        resource-label="Caracteristica"
        resource-label-plural="Caracteristicas"
        hint="Atributos destacados del producto (ej. Resolucion: 4MP)."
        empty-icon="bi-stars"
        :fields="[
          { key: 'title', label: 'Titulo', required: true, col: 'col-6' },
          { key: 'value', label: 'Valor', col: 'col-6' },
          { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-lightning-charge' },
        ]"
      />
    </div>

    <div v-show="tab === 'especificaciones' && localMode === 'edit'">
      <SpecificationsManager entity-type="product" :entity-uuid="localItem?.uuid" />
    </div>

    <div v-show="tab === 'requisitos' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-requirements/"
        resource="requirements"
        resource-label="Requisito"
        resource-label-plural="Requisitos"
        hint="Condiciones necesarias para instalar/usar el producto (punto electrico, internet, etc.)."
        empty-icon="bi-clipboard-check"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
        ]"
      />
    </div>

    <div v-show="tab === 'servicios-incluidos' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-services-included/"
        resource="services-included"
        resource-label="Servicio incluido"
        resource-label-plural="Servicios incluidos"
        hint="Servicios que ya vienen en el precio del producto (ej. instalacion basica)."
        empty-icon="bi-hand-thumbs-up"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-truck' },
        ]"
      />
    </div>

    <div v-show="tab === 'servicios-opcionales' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-optional-services/"
        resource="optional-services"
        resource-label="Servicio opcional"
        resource-label-plural="Servicios opcionales"
        hint="Servicios adicionales que el cliente puede contratar por un costo extra (ej. instalacion profesional)."
        empty-icon="bi-plus-circle"
        :fields="[
          { key: 'title', label: 'Titulo', required: true },
          { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          { key: 'price', label: 'Precio', type: 'price', col: 'col-6' },
          { key: 'icon', label: 'Icono', type: 'icon', col: 'col-6' },
        ]"
      />
    </div>

    <div v-show="tab === 'documentacion' && localMode === 'edit'">
      <DocumentsManager entity-type="product" :entity-uuid="localItem?.uuid" />
    </div>

    <div v-show="tab === 'videos' && localMode === 'edit'">
      <VideosManager entity-type="product" :entity-uuid="localItem?.uuid" />
    </div>

    <div v-show="tab === 'galeria' && localMode === 'edit'">
      <GalleryImagesManager :product-uuid="localItem?.uuid" />
    </div>

    <div v-show="tab === 'funcionamiento' && localMode === 'edit'">
      <ProductFunctioningStepsManager :product-uuid="localItem?.uuid" />
    </div>

    <div v-show="tab === 'faq' && localMode === 'edit'">
      <CatalogListManager
        :equipment-uuid="localItem?.uuid"
        parent-key="product"
        endpoint="dashboard/product-faqs/"
        resource="faqs"
        resource-label="Pregunta"
        resource-label-plural="Preguntas frecuentes"
        hint="Preguntas frecuentes mostradas en el detalle publico del producto."
        empty-icon="bi-question-circle"
        primary-field="question"
        secondary-field="answer"
        :fields="[
          { key: 'question', label: 'Pregunta', required: true, col: 'col-12' },
          { key: 'answer', label: 'Respuesta', type: 'textarea', required: true, col: 'col-12' },
        ]"
      />
    </div>

    <!-- ================================================================
         TAB: CONTENIDO DEL PRODUCTO (Fase 4, solo localMode === 'edit')
    ================================================================ -->
    <div v-show="tab === 'contenido' && localMode === 'edit'" :key="`contenido-${localItem?.uuid}`">
      <ContentBlocksTab
        entity-type="product"
        :entity-uuid="localItem?.uuid"
        :scope="form.scope"
        :warranty="form.warranty"
        @jump-to-tab="tab = $event"
        @field-saved="({ field, value }) => { form[field] = value; }"
      />
    </div>

  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useShopAdminStore } from '@/store/shopAdmin';
import GeneralTab from './product-form/GeneralTab.vue';
import SeoTab from './product-form/SeoTab.vue';
import VariantsTab from './product-form/VariantsTab.vue';
import CostosTab from './product-form/CostosTab.vue';
import ImagenesTab from './product-form/ImagenesTab.vue';
// Catalogo enriquecido (2026-08-03): CatalogListManager es generico y ya lo usa renting (con
// parent-key="equipment" por defecto) -- se reusa aqui con parent-key="product" en vez de
// duplicarlo. SpecificationsManager/DocumentsManager/VideosManager [generalizados 2026-08-05,
// Sprint 5 auditoria transversal] tambien son genericos ahora via prop entity-type
// ('product'/'equipment'/'service') -- viven aqui por ser su dominio de origen, renting y
// technical_services los importan cruzado (mismo patron ya establecido por ContentBlocksTab.vue).
import CatalogListManager from '@/modules/renting/catalog/CatalogListManager.vue';
import SpecificationsManager from './catalog/SpecificationsManager.vue';
import DocumentsManager from './catalog/DocumentsManager.vue';
import VideosManager from './catalog/VideosManager.vue';
import GalleryImagesManager from './catalog/GalleryImagesManager.vue';
import ProductFunctioningStepsManager from './catalog/ProductFunctioningStepsManager.vue';
import ContentBlocksTab from './product-form/ContentBlocksTab.vue';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel', 'itemSaved']);

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useShopAdminStore();
const {
  productCategories: categories, productBrands: brands,
  variants, productImages, costRules,
  actionLoading,
} = storeToRefs(store);

// ─── Estado interno — permite transicion create→edit sin cerrar el offcanvas ──
const localMode      = ref(props.mode);
const localItem      = ref(props.item);
const isNewlyCreated = ref(false);
const tab            = ref('general');

const activeCostRulesCount = computed(() => costRules.value.filter(r => r.is_active).length);

// ─── Formulario general + SEO (un solo `form` compartido por ambos tabs) ──────
const emptyForm = () => ({
  name: '', short_description: '', description: '', video_url: '',
  scope: '', warranty: '',
  is_active: true, is_featured: false,
  category: '', brand: null, condition: 'new',
  stock: 0, price: null, discounted_price: null,
  meta_title: '', meta_description: '',
});
const form = ref(emptyForm());

// ─── Sync cuando el padre cambia item/mode (apertura desde la lista) ──────────
watch(
  [() => props.item, () => props.mode],
  ([item, mode]) => {
    localMode.value      = mode;
    localItem.value      = item;
    isNewlyCreated.value = false;
    tab.value            = 'general';

    if (item && mode === 'edit') {
      form.value = {
        name:              item.name,
        short_description: item.short_description || '',
        description:       item.description || '',
        video_url:         item.video_url || '',
        scope:             item.scope || '',
        warranty:          item.warranty || '',
        is_active:         item.is_active,
        is_featured:       item.is_featured,
        category:          item.category_uuid || '',
        brand:             item.brand_uuid || null,
        condition:         item.condition || 'new',
        stock:             item.stock ?? 0,
        price: null,
        discounted_price: null,
        meta_title:        item.meta_title || '',
        meta_description:  item.meta_description || '',
      };
    } else {
      form.value          = emptyForm();
      variants.value      = [];
      costRules.value     = [];
      productImages.value = [];
    }
  },
  { immediate: true },
);

// ─── Catalogo ─────────────────────────────────────────────────────────────────
async function fetchCategories() {
  await store.fetchProductCategories();
}
async function fetchBrands() {
  await store.fetchProductBrands();
}
async function fetchTaxes() {
  await store.fetchActiveTaxes();
}

// ─── Limpieza numerica — NaN / '' → null (solo usada aqui, en create) ────────
const cleanNum = (val) => {
  if (val === '' || val === null || val === undefined) return null;
  if (typeof val === 'number' && Number.isNaN(val)) return null;
  return val;
};

// ─── Submit General / SEO (un solo form, 2 tabs) ─────────────────────────────
async function submit() {
  const payload = {
    name:              form.value.name,
    short_description: form.value.short_description || null,
    description:       form.value.description,
    video_url:         form.value.video_url || null,
    is_active:         form.value.is_active,
    is_featured:       form.value.is_featured,
    category:          form.value.category,
    brand:             form.value.brand,
    condition:         form.value.condition,
    meta_title:        form.value.meta_title,
    meta_description:  form.value.meta_description,
  };

  if (localMode.value === 'create') {
    payload.stock = cleanNum(form.value.stock) ?? 0;
    payload.price = form.value.price;
    payload.discounted_price = cleanNum(form.value.discounted_price);

    const res = await store.createProduct(payload);
    if (!res.ok) {
      handleError(res.error, 'Error al guardar. Revisa los campos.');
      return;
    }

    // ── Transicion interna create→edit (offcanvas permanece abierto) ──
    localItem.value      = res.data;
    localMode.value      = 'edit';
    isNewlyCreated.value = true;
    tab.value            = 'variants';
    toast.success('Producto creado. Configura variantes, descuentos y logistica.');
  } else {
    const res = await store.updateProduct(localItem.value.uuid, payload);
    if (!res.ok) {
      handleError(res.error, 'Error al guardar. Revisa los campos.');
      return;
    }
    localItem.value = res.data;
    emit('itemSaved', res.data);
    toast.success('Datos generales actualizados.');
  }
}

// ─── Cerrar: notifica al padre que recargue la lista ─────────────────────────
function closeForm() {
  emit('success');
}

onMounted(() => {
  fetchCategories();
  fetchBrands();
  fetchTaxes();
});
</script>
