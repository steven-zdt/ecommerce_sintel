<template>
  <div class="content-blocks-tab">
    <!-- ═══════════════════════════════════════════════════════════════════
         Orden y visibilidad de los bloques de la PDP/SDP (Fase 4 Shop
         2026-08-05, generalizado para Technical Services 2026-08-05).
         Coexiste con las pestanas existentes -- NO las reemplaza: para los
         bloques que ya tienen pestana propia, el link "Editar" salta ahi.
         Esta pestana solo controla orden/visibilidad + edita inline los
         campos de texto nuevos (Alcance/Garantia/Cobertura) + relaciones.
         ═══════════════════════════════════════════════════════════════════ -->
    <p class="text-muted small mb-2">
      Arrastra para reordenar como aparecen en la pagina publica. El interruptor
      oculta/muestra el bloque sin borrar su contenido.
    </p>
    <div class="d-flex flex-column gap-2 mb-4">
      <div
        v-for="(block, idx) in blocks"
        :key="block.block_type"
        class="block-row d-flex align-items-center gap-2 p-2 rounded-3 border"
        :class="block.is_visible ? 'bg-white' : 'bg-light opacity-60'"
        draggable="true"
        @dragstart="handleDragStart(idx)"
        @dragover.prevent
        @drop="handleDrop(idx)"
      >
        <span class="drag-handle text-muted" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
        <i :class="['bi', BLOCK_META[block.block_type]?.icon || 'bi-square', 'text-primary']"></i>
        <span class="flex-grow-1 small fw-semibold">{{ BLOCK_META[block.block_type]?.label || block.block_type }}</span>
        <button
          v-if="config.ownTab[block.block_type]"
          type="button"
          class="btn btn-sm btn-light"
          @click="emit('jump-to-tab', config.ownTab[block.block_type])"
        >
          Editar <i class="bi bi-box-arrow-up-right ms-1"></i>
        </button>
        <button
          type="button"
          class="btn btn-link p-0"
          :title="block.is_visible ? 'Ocultar en la pagina publica' : 'Mostrar en la pagina publica'"
          @click="toggleVisible(block)"
        >
          <i :class="block.is_visible ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"></i>
        </button>
      </div>
      <div v-if="loadingBlocks" class="text-center text-muted small py-3">
        <span class="spinner-border spinner-border-sm me-1"></span>Cargando...
      </div>
    </div>

    <!-- ─── Campos de texto nuevos, sin pestana propia ─────────────────────── -->
    <div class="row g-3 mb-4">
      <div class="col-md-6">
        <label class="form-label small fw-semibold">Alcance</label>
        <textarea
          v-model="scopeText"
          class="form-control form-control-sm"
          rows="3"
          placeholder="Que abarca (instalacion, capacitacion, etc.)"
          @blur="saveTextField('scope', scopeText)"
        ></textarea>
      </div>
      <div class="col-md-6">
        <label class="form-label small fw-semibold">Garantia</label>
        <textarea
          v-model="warrantyText"
          class="form-control form-control-sm"
          rows="3"
          placeholder="Ej: 12 meses contra defectos de fabrica"
          @blur="saveTextField('warranty', warrantyText)"
        ></textarea>
      </div>
      <div v-if="entityType === 'service'" class="col-md-6">
        <label class="form-label small fw-semibold">Cobertura</label>
        <textarea
          v-model="coverageText"
          class="form-control form-control-sm"
          rows="3"
          placeholder="Ciudades/zonas donde se presta el servicio"
          @blur="saveTextField('coverage_notes', coverageText)"
        ></textarea>
      </div>
    </div>

    <!-- ─── Relaciones ───────────────────────────────────────────────────── -->
    <div v-for="rel in config.relationTypes" :key="rel.type" class="mb-4">
      <h6 class="fw-semibold small mb-2"><i :class="['bi', rel.icon, 'me-1']"></i>{{ rel.label }}</h6>

      <div class="position-relative mb-2">
        <input
          v-model="search[rel.type].query"
          type="text"
          class="form-control form-control-sm"
          :placeholder="`Buscar para agregar a ${rel.label.toLowerCase()}...`"
          @input="onSearchInput(rel)"
        >
        <div v-if="search[rel.type].results.length" class="search-results shadow-sm">
          <button
            v-for="p in search[rel.type].results"
            :key="p.uuid"
            type="button"
            class="search-result-item"
            @click="addRelation(rel, p)"
          >
            {{ p.name }}
          </button>
        </div>
      </div>

      <div v-if="relations[rel.type].length" class="d-flex flex-column gap-2">
        <div v-for="r in relations[rel.type]" :key="r.uuid" class="d-flex align-items-center gap-2 p-2 rounded-3 border bg-white">
          <span class="flex-grow-1 small">{{ relationLabel(r) }}</span>
          <button type="button" class="btn btn-sm btn-light" title="Quitar" @click="removeRelation(rel.type, r)">
            <i class="bi bi-trash text-danger"></i>
          </button>
        </div>
      </div>
      <p v-else class="text-muted small mb-0">Sin {{ rel.label.toLowerCase() }} agregados.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

// Espejo de shared.models.ContentBlockConfig.BLOCK_TYPE_CHOICES (backend) --
// ver DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md y
// technical_services/.AGENT/docs/UI_MODULO_SERVICES.md. Union de los 2
// catalogos (Shop 15 + Services 5 propios) -- cada entityType solo usa el
// subconjunto de su propio default_order (ver ENTITY_CONFIG abajo).
const BLOCK_META = {
  description:  { label: 'Descripcion general',      icon: 'bi-card-text' },
  scope:        { label: 'Alcance',                   icon: 'bi-signpost' },
  included:     { label: 'Que incluye',                icon: 'bi-check2-circle' },
  excluded:     { label: 'Que NO incluye',             icon: 'bi-x-circle' },
  installation: { label: 'Instalacion',                icon: 'bi-clipboard-check' },
  functioning:  { label: 'Como funciona',              icon: 'bi-gear-wide-connected' },
  support:      { label: 'Soporte',                    icon: 'bi-hand-thumbs-up' },
  benefits:     { label: 'Beneficios',                 icon: 'bi-stars' },
  warranty:     { label: 'Garantia',                   icon: 'bi-shield-check' },
  specs:        { label: 'Ficha tecnica',              icon: 'bi-card-list' },
  documents:    { label: 'Documentacion',              icon: 'bi-file-earmark-text' },
  videos:       { label: 'Videos',                     icon: 'bi-camera-reels' },
  faq:          { label: 'FAQ',                        icon: 'bi-question-circle' },
  compatible:   { label: 'Productos/servicios compatibles', icon: 'bi-plug' },
  accessories:  { label: 'Accesorios recomendados',    icon: 'bi-bag-plus' },
  related:      { label: 'Relacionados',               icon: 'bi-link-45deg' },
  coverage:            { label: 'Cobertura',                icon: 'bi-geo-alt' },
  process:             { label: 'Proceso del servicio',     icon: 'bi-list-ol' },
  materials:           { label: 'Materiales utilizados',    icon: 'bi-tools' },
  technicians:         { label: 'Tecnicos especializados',  icon: 'bi-person-badge' },
  recommended_products: { label: 'Productos recomendados',  icon: 'bi-bag-check' },
};

// Config por entityType -- endpoints, bloques con pestana propia (para el
// link "Editar"), y tipos de relacion administrables desde esta pestana.
const ENTITY_CONFIG = {
  product: {
    entityParam: 'product',
    blocksEndpoint: 'dashboard/product-content-blocks/',
    relationsEndpoint: 'dashboard/product-relations/',
    entityEndpoint: 'dashboard/products/',
    searchEndpoint: 'dashboard/products/',
    ownTab: {
      description: 'general', included: 'incluye', excluded: 'no-incluye',
      installation: 'requisitos', functioning: 'funcionamiento', support: 'servicios-incluidos', benefits: 'caracteristicas',
      specs: 'especificaciones', documents: 'documentacion', videos: 'videos', faq: 'faq',
    },
    relationTypes: [
      { type: 'compatible', label: 'Productos compatibles', icon: 'bi-plug', targetEntityType: 'product' },
      { type: 'accessory', label: 'Accesorios recomendados', icon: 'bi-bag-plus', targetEntityType: 'product' },
      { type: 'related', label: 'Productos relacionados', icon: 'bi-link-45deg', targetEntityType: 'product' },
    ],
  },
  service: {
    entityParam: 'service',
    blocksEndpoint: 'dashboard/service-content-blocks/',
    relationsEndpoint: 'dashboard/service-relations/',
    entityEndpoint: 'dashboard/services/',
    searchEndpoint: 'dashboard/services/',
    productSearchEndpoint: 'dashboard/products/',
    ownTab: {
      description: 'general', included: 'incluye', excluded: 'no-incluye',
      installation: 'requisitos', benefits: 'marketing', specs: 'ficha-tecnica',
      documents: 'documentacion', videos: 'videos', faq: 'faq', process: 'proceso',
      materials: 'variants',
    },
    relationTypes: [
      { type: 'compatible', label: 'Servicios compatibles', icon: 'bi-plug', targetEntityType: 'service' },
      { type: 'related', label: 'Servicios relacionados', icon: 'bi-link-45deg', targetEntityType: 'service' },
      { type: 'accessory', label: 'Productos recomendados', icon: 'bi-bag-check', targetEntityType: 'product' },
    ],
  },
};

const props = defineProps({
  entityType: { type: String, required: true, validator: (v) => ['product', 'service'].includes(v) },
  entityUuid: { type: String, required: true },
  scope: { type: String, default: '' },
  warranty: { type: String, default: '' },
  coverageNotes: { type: String, default: '' },
});
const emit = defineEmits(['jump-to-tab', 'field-saved']);

const config = computed(() => ENTITY_CONFIG[props.entityType]);

const api = useApi();
const toast = useToast();

const blocks = ref([]);
const loadingBlocks = ref(false);
const dragIndex = ref(null);

const scopeText = ref(props.scope || '');
const warrantyText = ref(props.warranty || '');
const coverageText = ref(props.coverageNotes || '');
watch(() => props.scope, (v) => { scopeText.value = v || ''; });
watch(() => props.warranty, (v) => { warrantyText.value = v || ''; });
watch(() => props.coverageNotes, (v) => { coverageText.value = v || ''; });

const relations = reactive({ compatible: [], accessory: [], related: [] });
const search = reactive({
  compatible: { query: '', results: [], timer: null },
  accessory: { query: '', results: [], timer: null },
  related: { query: '', results: [], timer: null },
});

function relationLabel(relation) {
  // Shop: shape plano {uuid, product:{name}}. Services: shape generico
  // {uuid, related_entity_type, entity:{name}} (ver AdminServiceRelationViewSet).
  return relation.entity?.name || relation.product?.name || '(eliminado)';
}

async function fetchBlocks() {
  if (!props.entityUuid) return;
  loadingBlocks.value = true;
  try {
    const res = await api.get(`${config.value.blocksEndpoint}?${config.value.entityParam}=${props.entityUuid}`);
    blocks.value = res.data;
  } catch {
    toast.error('No se pudieron cargar los bloques de contenido');
  } finally {
    loadingBlocks.value = false;
  }
}

async function fetchRelations() {
  if (!props.entityUuid) return;
  for (const rel of config.value.relationTypes) {
    try {
      const res = await api.get(`${config.value.relationsEndpoint}?${config.value.entityParam}=${props.entityUuid}&relation_type=${rel.type}`);
      relations[rel.type] = res.data;
    } catch {
      relations[rel.type] = [];
    }
  }
}

async function toggleVisible(block) {
  const nextVisible = !block.is_visible;
  try {
    const res = await api.post(`${config.value.blocksEndpoint}set-visibility/`, {
      [config.value.entityParam]: props.entityUuid,
      block_type: block.block_type,
      is_visible: nextVisible,
    });
    blocks.value = res.data;
  } catch {
    toast.error('No se pudo cambiar la visibilidad del bloque');
  }
}

function handleDragStart(index) {
  dragIndex.value = index;
}

async function handleDrop(targetIndex) {
  const fromIndex = dragIndex.value;
  dragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...blocks.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  blocks.value = reordered;
  try {
    const res = await api.post(`${config.value.blocksEndpoint}reorder/`, {
      [config.value.entityParam]: props.entityUuid,
      ordered_block_types: reordered.map((b) => b.block_type),
    });
    blocks.value = res.data;
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchBlocks();
  }
}

async function saveTextField(field, value) {
  try {
    await api.patch(`${config.value.entityEndpoint}${props.entityUuid}/`, { [field]: value });
    emit('field-saved', { field, value });
  } catch {
    toast.error('No se pudo guardar');
  }
}

function onSearchInput(rel) {
  const state = search[rel.type];
  clearTimeout(state.timer);
  const query = state.query.trim();
  if (query.length < 2) {
    state.results = [];
    return;
  }
  state.timer = setTimeout(async () => {
    try {
      const endpoint = rel.targetEntityType === 'product'
        ? (config.value.productSearchEndpoint || config.value.searchEndpoint)
        : config.value.searchEndpoint;
      const res = await api.get(`${endpoint}?search=${encodeURIComponent(query)}`);
      const items = res.data.results || res.data;
      const alreadyRelated = new Set(relations[rel.type].map((r) => r.entity?.uuid || r.product?.uuid));
      state.results = items
        .filter((p) => p.uuid !== props.entityUuid && !alreadyRelated.has(p.uuid))
        .slice(0, 8);
    } catch {
      state.results = [];
    }
  }, 400);
}

async function addRelation(rel, target) {
  try {
    const payload = props.entityType === 'service'
      ? {
          service: props.entityUuid,
          relation_type: rel.type,
          related_entity_type: rel.targetEntityType,
          related_uuid: target.uuid,
        }
      : {
          product: props.entityUuid,
          relation_type: rel.type,
          related_product: target.uuid,
        };
    await api.post(config.value.relationsEndpoint, payload);
    search[rel.type].query = '';
    search[rel.type].results = [];
    await fetchRelations();
    toast.success('Agregado');
  } catch {
    toast.error('No se pudo agregar la relacion');
  }
}

async function removeRelation(relationType, relation) {
  try {
    await api.delete(`${config.value.relationsEndpoint}${relation.uuid}/`);
    relations[relationType] = relations[relationType].filter((r) => r.uuid !== relation.uuid);
  } catch {
    toast.error('No se pudo quitar');
  }
}

watch(() => props.entityUuid, () => {
  fetchBlocks();
  fetchRelations();
}, { immediate: true });

defineExpose({ fetchBlocks, fetchRelations });
</script>

<style scoped>
.drag-handle { cursor: grab; }
.block-row { transition: background-color .15s ease; }
.search-results {
  position: absolute;
  z-index: 5;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-top: 2px;
  max-height: 220px;
  overflow-y: auto;
}
.search-result-item {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  padding: .5rem .75rem;
  font-size: .82rem;
  cursor: pointer;
}
.search-result-item:hover { background: #f8fafc; }
</style>
