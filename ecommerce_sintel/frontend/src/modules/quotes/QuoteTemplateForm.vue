<template>
  <form @submit.prevent="handleSubmit" class="p-3 d-flex flex-column gap-3">
    <div>
      <label class="form-label small fw-semibold">Nombre *</label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Instalación CCTV" />
    </div>

    <div class="row g-2">
      <div class="col-8">
        <label class="form-label small fw-semibold d-flex align-items-center justify-content-between">
          Categoría
          <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" @click="isCreatingCategory = !isCreatingCategory">
            <i class="bi bi-plus-lg me-1"></i>Nueva
          </button>
        </label>
        <select v-if="!isCreatingCategory" v-model="form.category" class="form-select" @change="onCategoryChange">
          <option :value="null">-- Sin categoría --</option>
          <option v-for="cat in store.categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
        </select>
        <div v-else class="d-flex gap-2">
          <input v-model="newCategoryName" type="text" class="form-control" placeholder="Nombre de la categoría" @keyup.enter.prevent="handleCreateCategory" />
          <button type="button" class="btn btn-success" :disabled="store.actionLoading" @click="handleCreateCategory"><i class="bi bi-check-lg"></i></button>
          <button type="button" class="btn btn-light border" @click="isCreatingCategory = false"><i class="bi bi-x-lg"></i></button>
        </div>
      </div>
      <div class="col-4">
        <label class="form-label small fw-semibold">Código</label>
        <input :value="form.code || '(automático)'" type="text" class="form-control text-muted" readonly />
      </div>
    </div>

    <div v-if="selectedCategory" class="small bg-light border rounded-3 px-3 py-2">
      <i class="bi bi-diagram-3 me-1 text-primary"></i>
      Tipo de Servicio: <strong>{{ selectedCategory.service_type?.name || 'sin definir en la categoría' }}</strong>
      <span class="text-muted"> (heredado de la categoría — se edita en Catálogos → Tipos de Servicio → Categorías)</span>
    </div>

    <div v-if="filteredSubcategories.length">
      <label class="form-label small fw-semibold">Subcategoría</label>
      <select v-model="form.subcategory" class="form-select" @change="onSubcategoryChange">
        <option :value="null">-- Sin subcategoría --</option>
        <option v-for="sub in filteredSubcategories" :key="sub.uuid" :value="sub.uuid">{{ sub.name }}</option>
      </select>
    </div>

    <div>
      <label class="form-label small fw-semibold">Descripción</label>
      <textarea v-model="form.description" class="form-control" rows="2"></textarea>
    </div>

    <div class="row g-2">
      <div v-for="attr in attributeFields" :key="attr.kind" class="col-6">
        <label class="form-label small fw-semibold d-flex align-items-center justify-content-between">
          {{ attr.label }}
          <button
            type="button" class="btn btn-link btn-sm p-0 text-decoration-none"
            :disabled="attr.kind === 'INSTALLATION_TYPE' && !form.subcategory"
            @click="attr.creating.value = !attr.creating.value"
          >
            <i class="bi bi-plus-lg me-1"></i>Nuevo
          </button>
        </label>
        <select v-if="!attr.creating.value" v-model="form[attr.field]" class="form-select" :disabled="attr.kind === 'INSTALLATION_TYPE' && !form.subcategory">
          <option :value="null">-- Sin definir --</option>
          <option v-for="opt in attributesByKind(attr.kind)" :key="opt.uuid" :value="opt.uuid">{{ opt.name }}</option>
        </select>
        <div v-else class="d-flex gap-2">
          <input v-model="attr.newName.value" type="text" class="form-control form-control-sm" :placeholder="attr.placeholder" @keyup.enter.prevent="handleCreateAttribute(attr)" />
          <button type="button" class="btn btn-sm btn-success" :disabled="store.actionLoading" @click="handleCreateAttribute(attr)"><i class="bi bi-check-lg"></i></button>
          <button type="button" class="btn btn-sm btn-light border" @click="attr.creating.value = false"><i class="bi bi-x-lg"></i></button>
        </div>
        <div v-if="attr.kind === 'INSTALLATION_TYPE' && !form.subcategory" class="form-text small">Elige primero una subcategoría.</div>
      </div>
    </div>

    <div class="row g-2 align-items-end">
      <div class="col-4">
        <label class="form-label small fw-semibold">Versión</label>
        <input v-model.number="form.version" type="number" min="1" class="form-control" />
      </div>
      <div class="col-4">
        <label class="form-label small fw-semibold">Complejidad</label>
        <select v-model="form.complexity_hint" class="form-select">
          <option value="">-- Sin definir --</option>
          <option value="LOW">Baja</option>
          <option value="MEDIUM">Media</option>
          <option value="HIGH">Alta</option>
        </select>
      </div>
      <div class="col-4">
        <div class="form-check form-switch">
          <input v-model="form.is_active" class="form-check-input" type="checkbox" role="switch" id="tplActive" />
          <label class="form-check-label small" for="tplActive">Activa</label>
        </div>
      </div>
      <div class="col-12">
        <div class="form-check form-switch">
          <input v-model="form.is_published" class="form-check-input" type="checkbox" role="switch" id="tplPublished" />
          <label class="form-check-label small" for="tplPublished">Publicada (visible en /cotizar)</label>
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-end gap-2 mt-2">
      <button type="button" class="btn btn-light border" @click="$emit('cancel')">Cancelar</button>
      <button type="submit" class="btn btn-primary" :disabled="store.actionLoading">
        <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
        {{ mode === 'create' ? 'Crear plantilla' : 'Guardar cambios' }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const store = useQuoteTemplateBuilderStore();
const toast = useToast();

const blank = () => ({
  name: '', category: null, subcategory: null, code: '', description: '',
  installation_type: null, system_type: null,
  version: 1, is_published: false, is_active: true, complexity_hint: '',
});

const form = ref(blank());

const isCreatingCategory = ref(false);
const newCategoryName = ref('');

const selectedCategory = computed(() => store.categories.find((c) => c.uuid === form.value.category));

const filteredSubcategories = computed(() =>
  store.subcategories.filter((s) => s.category_uuid === form.value.category),
);

function onCategoryChange() {
  form.value.subcategory = null;
  form.value.installation_type = null;
}

function onSubcategoryChange() {
  form.value.installation_type = null;
}

async function handleCreateCategory() {
  if (!newCategoryName.value.trim()) {
    toast.error('El nombre de la categoría es obligatorio.');
    return;
  }
  const { ok, data, error } = await store.createCategory({ name: newCategoryName.value.trim() });
  if (ok) {
    toast.success(`Categoría "${data.name}" creada.`);
    form.value.category = data.uuid;
    form.value.subcategory = null;
    newCategoryName.value = '';
    isCreatingCategory.value = false;
  } else {
    toast.error(error || 'Error al crear la categoría.');
  }
}

// Tipo de Servicio ya no se elige aca — se hereda de la Categoria
// (Tipo de Servicio -> Categoria -> Subcategoria -> Tipo de Instalacion).
const attributeFields = [
  { kind: 'INSTALLATION_TYPE', field: 'installation_type', label: 'Tipo de instalación', placeholder: 'Altura doble, Confinamiento...', creating: ref(false), newName: ref('') },
  { kind: 'SYSTEM_TYPE', field: 'system_type', label: 'Tipo de sistema', placeholder: 'CCTV', creating: ref(false), newName: ref('') },
];

function attributesByKind(kind) {
  const items = store.attributes.filter((a) => a.kind === kind);
  if (kind === 'INSTALLATION_TYPE') {
    return items.filter((a) => a.subcategory_uuid === form.value.subcategory);
  }
  return items;
}

async function handleCreateAttribute(attr) {
  if (!attr.newName.value.trim()) {
    toast.error('El nombre es obligatorio.');
    return;
  }
  const payload = { kind: attr.kind, name: attr.newName.value.trim() };
  if (attr.kind === 'INSTALLATION_TYPE') payload.subcategory = form.value.subcategory;
  const { ok, data, error } = await store.createAttribute(payload);
  if (ok) {
    toast.success(`"${data.name}" creado.`);
    form.value[attr.field] = data.uuid;
    attr.newName.value = '';
    attr.creating.value = false;
  } else {
    toast.error(error || 'Error al crear.');
  }
}

onMounted(async () => {
  if (!store.categories.length) await store.fetchCategories();
  if (!store.subcategories.length) await store.fetchSubcategories();
  if (!store.attributes.length) await store.fetchAttributes();
  if (props.mode === 'edit' && props.item) {
    form.value = {
      name: props.item.name || '',
      category: props.item.category?.uuid || null,
      subcategory: props.item.subcategory?.uuid || null,
      code: props.item.code || '',
      description: props.item.description || '',
      installation_type: props.item.installation_type?.uuid || null,
      system_type: props.item.system_type?.uuid || null,
      version: props.item.version || 1,
      is_published: props.item.is_published || false,
      is_active: props.item.is_active ?? true,
      complexity_hint: props.item.complexity_hint || '',
    };
  }
});

async function handleSubmit() {
  if (!form.value.name) {
    toast.error('El nombre es obligatorio.');
    return;
  }
  const result = props.mode === 'create'
    ? await store.createTemplate(form.value)
    : await store.updateTemplate(props.item.uuid, form.value);

  if (result.ok) {
    toast.success(props.mode === 'create' ? 'Plantilla creada.' : 'Plantilla actualizada.');
    emit('success');
  } else {
    toast.error(result.error || 'Error al guardar la plantilla.');
  }
}
</script>
