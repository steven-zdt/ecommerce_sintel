---
description: Patron CRUD con offcanvas lateral — useOffcanvas + SintelOffcanvas + Form component. Receta completa lista para implementar en cualquier modulo.
metadata:
  domain: components
  supersedes: FRONTEND_OFFCANVAS_SKILL.md (movido integro)
---

# Offcanvas — Patron CRUD

Todo modulo admin del panel usa el mismo patron: tabla + panel lateral deslizable (offcanvas)
para crear y editar. Este documento es la receta canonica.

## 1. Piezas del patron

```
useOffcanvas()          composable de estado (show/mode/selected)
    │
    ▼
SintelOffcanvas.vue     componente UI: backdrop + panel + header + slot
    │
    └─ slot ──────────► {Nombre}Form.vue   formulario dentro del panel
```

## 2. `useOffcanvas()` — API completa

```js
import { useOffcanvas } from '@/composables/useOffcanvas';
const { show, mode, selected, openCreate, openEdit, openDetail, close } = useOffcanvas();
```

| Propiedad / Metodo | Tipo | Descripcion |
|---|---|---|
| `show` | `ref(Boolean)` | Controla visibilidad. Bindear a `v-model` de `SintelOffcanvas` |
| `mode` | `ref(String)` | `'create'` \| `'edit'` \| `'detail'` |
| `selected` | `ref(Object\|null)` | Item seleccionado. `null` en modo create |
| `openCreate()` | funcion | Limpia selected, `mode='create'`, `show=true` |
| `openEdit(item)` | funcion | Shallow copy del item, `mode='edit'`, `show=true` |
| `openDetail(item)` | funcion | item sin copiar, `mode='detail'`, `show=true` |
| `close()` | funcion | `show=false`; limpia selected con delay 300ms (espera transicion) |

## 3. `SintelOffcanvas.vue` — `@/components/ui/SintelOffcanvas.vue`

```vue
<SintelOffcanvas v-model="show" title="Nueva Marca" subtitle="Agrega una marca al catalogo" width="480px">
  <!-- contenido del form va aqui en el slot default -->
</SintelOffcanvas>
```

| Prop | Tipo | Default | Descripcion |
|---|---|---|---|
| `modelValue` | Boolean | requerido | `v-model` — controla visibilidad |
| `title` | String | `''` | Titulo en el header |
| `subtitle` | String | `''` | Subtitulo gris debajo del titulo |
| `width` | String | `'480px'` | Ancho del panel (CSS string) |
| `loading` | Boolean | `false` | Deshabilita el boton X del header |

Emits: `update:modelValue`. Slot `footer` opcional para botones fijos en el pie del panel.

## 4. Contrato del Form component

```vue
<script setup>
const props = defineProps({
  item: { type: Object, default: null },    // null = crear / objeto = editar
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
});
const emit = defineEmits(['success', 'cancel']);
</script>
```

Flujo interno:

```
1. watch(props.item, ..., { immediate: true })
   ├─ modo 'edit'   → poblar form.value con los datos del item
   └─ modo 'create' → form.value = emptyForm()

2. submit()
   ├─ 'create' → api.post('dashboard/{recurso}/', form.value)
   └─ 'edit'   → api.patch(`dashboard/{recurso}/${props.item.id}/`, form.value)

3. Exito → toast.success(...) → emit('success')
4. Error → toast.error(e.response?.data?.detail || e.response?.data?.{campo}?.[0] || 'Error generico')
```

## 5. Receta completa — List component

```vue
<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Marcas</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nueva Marca
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr><th>Nombre</th><th>Estado</th><th class="text-end">Acciones</th></tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="3" class="text-center py-5"><div class="spinner-border text-primary"></div></td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="3" class="text-center py-5 text-muted">Sin registros.</td>
            </tr>
            <template v-for="item in items" :key="item.uuid">
              <tr v-if="pendingDelete?.uuid === item.uuid" class="bg-danger-subtle">
                <td colspan="3" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ item.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(item)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="fw-bold">{{ item.name }}</td>
                <td>
                  <span :class="['badge rounded-pill', item.is_active ? 'bg-success' : 'bg-secondary']">
                    {{ item.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(item)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = item" title="Eliminar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted small">{{ items.length }} de {{ totalCount }}</span>
        <nav v-if="totalPages > 1">
          <ul class="pagination pagination-sm m-0">
            <li class="page-item" :class="{ disabled: !pagination.previous }">
              <button class="page-link" @click="changePage(currentPage - 1)">Ant.</button>
            </li>
            <li class="page-item" :class="{ disabled: !pagination.next }">
              <button class="page-link" @click="changePage(currentPage + 1)">Sig.</button>
            </li>
          </ul>
        </nav>
      </div>
    </div>

    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nueva Marca' : 'Editar Marca'"
      :subtitle="mode === 'create' ? 'Agrega una marca al catalogo' : `Modificando: ${selected?.name}`"
      width="400px"
    >
      <MarcaForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import MarcaForm from './MarcaForm.vue';

const api = useApi();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const loading = ref(true);
const actionLoading = ref(false);
const items = ref([]);
const totalCount = ref(0);
const totalPages = ref(0);
const currentPage = ref(1);
const pendingDelete = ref(null);
const pagination = reactive({ next: null, previous: null });

const fetchItems = async () => {
  loading.value = true;
  try {
    const res = await api.get('shop/brands/', { params: { page: currentPage.value } });
    items.value = res.data.results || res.data;
    totalCount.value = res.data.count || items.value.length;
    totalPages.value = Math.ceil(totalCount.value / 25);
    pagination.next = res.data.next;
    pagination.previous = res.data.previous;
  } catch { toast.error('Error al cargar'); }
  finally { loading.value = false; }
};

const executeDelete = async (item) => {
  actionLoading.value = true;
  try {
    await api.delete(`dashboard/brands/${item.id}/`);
    toast.success(`"${item.name}" eliminado`);
    await fetchItems();
  } catch { toast.error('No se pudo eliminar'); }
  finally { actionLoading.value = false; pendingDelete.value = null; }
};

const onFormSuccess = () => { close(); fetchItems(); };
const changePage = (p) => { if (p >= 1 && p <= totalPages.value) { currentPage.value = p; fetchItems(); } };

onMounted(fetchItems);
</script>
```

## 6. Receta completa — Form component

```vue
<template>
  <form @submit.prevent="submit">
    <div class="mb-3">
      <label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required>
    </div>
    <div class="mb-3 form-check form-switch">
      <input v-model="form.is_active" class="form-check-input" type="checkbox" id="switchActive">
      <label class="form-check-label small" for="switchActive">Activo</label>
    </div>
    <div class="d-flex gap-2 mt-4">
      <button type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? 'Crear' : 'Guardar Cambios' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const api = useApi();
const toast = useToast();
const loading = ref(false);

const emptyForm = () => ({ name: '', is_active: true });
const form = ref(emptyForm());

watch(() => props.item, (val) => {
  form.value = (val && props.mode === 'edit')
    ? { name: val.name, is_active: val.is_active ?? true }
    : emptyForm();
}, { immediate: true });

async function submit() {
  loading.value = true;
  try {
    if (props.mode === 'create') {
      await api.post('dashboard/brands/', form.value);
      toast.success('Marca creada');
    } else {
      await api.patch(`dashboard/brands/${props.item.id}/`, form.value);
      toast.success('Marca actualizada');
    }
    emit('success');
  } catch (e) {
    const msg = e.response?.data?.name?.[0] || e.response?.data?.detail || 'Error al guardar';
    toast.error(msg);
  } finally {
    loading.value = false;
  }
}
</script>
```

## 7. Patrones adicionales

### Select cargado desde API (ej. Categoria en Producto)

```js
const categories = ref([]);
const fetchCategories = async () => {
  const res = await api.get('dashboard/categories/');
  categories.value = res.data.results || res.data;
};
onMounted(fetchCategories);
```

```html
<select v-model="form.category" class="form-select" required>
  <option value="" disabled>Seleccionar categoria...</option>
  <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
</select>
```

### Tabs dentro del offcanvas

Ver [forms.md](forms.md#tabs-dentro-del-offcanvas).

## Ver tambien

- [dialogs.md](dialogs.md) — confirmacion inline de eliminacion (fuera del offcanvas, en la tabla)
- [forms.md](forms.md) — labels, inputs de precio, contador SEO, manejo de errores DRF
- [../architecture/vue_patterns.md](../architecture/vue_patterns.md) — estructura de modulo, `uuid` vs `id`
