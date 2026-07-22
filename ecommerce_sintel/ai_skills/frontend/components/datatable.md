---
description: Patron canonico de tabla — card+table Bootstrap, estados loading/vacio, paginacion. No existe un componente <DataTable> separado en el proyecto.
metadata:
  domain: components
  supersedes: FRONTEND_UI_RULES.md (seccion 5.2, 5.3, 5.7)
---

# DataTable — patron de tabla

**No inventar** `import { Table } from '@/components/ui/Table.vue'` ni ningun componente
`DataTable` — no existen. Toda tabla del proyecto es HTML nativo + clases Bootstrap con el mismo
patron. Ver [tables.md](tables.md).

## 1. Card de tabla

```html
<div class="card shadow-sm border-0 overflow-hidden">
  <div class="table-responsive">
    <table class="table table-hover align-middle mb-0">
      <thead class="table-light">
        <tr><th>Campo</th><th class="text-end">Acciones</th></tr>
      </thead>
      <tbody><!-- filas --></tbody>
    </table>
  </div>
</div>
```

Siempre dentro de `table-responsive` para scroll horizontal en mobile.

## 2. Estados de tabla (loading / vacio)

```html
<!-- Loading -->
<tr v-if="loading">
  <td colspan="N" class="text-center py-5">
    <div class="spinner-border text-primary" role="status"></div>
    <div class="mt-2 text-muted small">Cargando...</div>
  </td>
</tr>

<!-- Vacio -->
<tr v-else-if="items.length === 0">
  <td colspan="N" class="text-center py-5 text-muted">No se encontraron registros.</td>
</tr>
```

Ver detalle general de loading/empty/error en [../ux/loading_states.md](../ux/loading_states.md).

## 3. Badge de estado activo/inactivo

```html
<span :class="['badge rounded-pill', item.is_active ? 'bg-success' : 'bg-secondary']">
  {{ item.is_active ? 'Activo' : 'Inactivo' }}
</span>
```

## 4. Paginacion simple

```html
<div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
  <span class="text-muted small">{{ items.length }} de {{ totalCount }} registros</span>
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
```

## 5. Botones de accion por fila

```html
<div class="btn-group btn-group-sm shadow-sm bg-white rounded">
  <button class="btn btn-light border-end" @click="openEdit(item)" title="Editar">
    <i class="bi bi-pencil text-primary"></i>
  </button>
  <button class="btn btn-light" @click="pendingDelete = item" title="Eliminar">
    <i class="bi bi-trash text-danger"></i>
  </button>
</div>
```

## 6. Lookup field en filas

`v-for :key="item.uuid"` para las filas (el GET publico/dashboard siempre trae `uuid`). Las
acciones de escritura (edit/delete) usan `item.id` en la URL — ver
[../architecture/vue_patterns.md](../architecture/vue_patterns.md#5-lookup-field-uuid-vs-id).

## 7. Seleccion + acciones masivas + exportacion CSV

Implementado por primera vez en `modules/shop/BrandList.vue` (2026-07-11) — usarlo como
referencia copy-paste para otros módulos. No existe un componente reutilizable para esto todavia
(un solo caso real no justifica extraer un composable — ver
[[project_users_accounts_refactor]] sobre no crear abstracciones prematuras). Si se repite en un
tercer modulo, extraer a un composable `useBulkSelection(items, idField)`.

### Seleccion (checkbox por fila + "seleccionar todas las visibles")

```html
<th style="width:36px">
  <input type="checkbox" class="form-check-input" :checked="allVisibleSelected" @change="toggleSelectAll">
</th>
<!-- por fila -->
<td>
  <input type="checkbox" class="form-check-input" :checked="selectedIds.has(item.uuid)" @change="toggleSelect(item.uuid)">
</td>
```

```js
const selectedIds = ref(new Set());
const allVisibleSelected = computed(() =>
  items.value.length > 0 && items.value.every((i) => selectedIds.value.has(i.uuid)));

function toggleSelect(uuid) {
  if (selectedIds.value.has(uuid)) selectedIds.value.delete(uuid);
  else selectedIds.value.add(uuid);
  selectedIds.value = new Set(selectedIds.value); // Set no dispara reactividad por mutacion directa
}
function toggleSelectAll() {
  selectedIds.value = allVisibleSelected.value ? new Set() : new Set(items.value.map((i) => i.uuid));
}
```

**La seleccion persiste entre paginas** (es un `Set` de `uuid`, no un array de indices) — "todas
las visibles" solo afecta la pagina actual, pero un bulk-delete despues de cambiar de pagina
sigue incluyendo lo seleccionado antes.

### Barra de accion masiva (solo visible con seleccion activa)

```html
<div v-if="selectedIds.size > 0" class="alert alert-primary d-flex align-items-center justify-content-between py-2 px-3 mb-3">
  <span class="small fw-bold">{{ selectedIds.size }} seleccionado(s)</span>
  <div class="d-flex gap-2">
    <button class="btn btn-sm btn-danger" @click="pendingBulkDelete = true">Eliminar seleccionados</button>
    <button class="btn btn-sm btn-light border" @click="selectedIds.clear()">Cancelar seleccion</button>
  </div>
</div>
```

### Bulk delete — reusa el endpoint de borrado individual, no requiere backend nuevo

```js
async function executeBulkDelete() {
  bulkLoading.value = true;
  const ids = items.value.filter((i) => selectedIds.value.has(i.uuid)).map((i) => i.id);
  try {
    const results = await Promise.allSettled(ids.map((id) => api.delete(`dashboard/recurso/${id}/`)));
    const failed = results.filter((r) => r.status === 'rejected').length;
    failed > 0 ? toast.error(`${failed} de ${ids.length} no se pudieron eliminar`) : toast.success(`${ids.length} eliminado(s)`);
    selectedIds.value = new Set();
    await fetchItems();
  } finally {
    bulkLoading.value = false;
    pendingBulkDelete.value = false;
  }
}
```

`Promise.allSettled` (no `Promise.all`) — si una fila falla, las demas igual se eliminan; el
usuario ve cuantas fallaron sin perder el resto del batch.

### Exportacion CSV — client-side, sin endpoint de backend

```js
function exportCSV() {
  const rows = selectedIds.value.size > 0 ? items.value.filter((i) => selectedIds.value.has(i.uuid)) : items.value;
  if (rows.length === 0) return;
  const header = ['Nombre', 'Slug', 'Activo'];
  const lines = rows.map((r) => [r.name, r.slug, r.is_active ? 'Si' : 'No']
    .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','));
  const csv = [header.join(','), ...lines].join('\n');
  const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8;' }); // BOM para Excel/es-CO
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `recurso_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
```

**Limitacion conocida, no resuelta:** exporta solo lo seleccionado o lo cargado en la pagina
actual (25 filas tipico) — no hay endpoint de backend para exportar el dataset filtrado
completo. Si un modulo necesita exportar miles de filas, esto no alcanza; requeriria un endpoint
`dashboard/{recurso}/export/` dedicado (no implementado en ningun modulo todavia).

## Ver tambien

- [dialogs.md](dialogs.md) — confirmacion inline de eliminacion (reemplaza la fila, no modal)
- [offcanvas.md](offcanvas.md) — receta List component completa con esta tabla integrada
