<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h5 class="fw-bold mb-0">Plantillas de Cotización</h5>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nueva Plantilla
      </button>
    </div>

    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3">Plantilla</th>
              <th class="py-3">Categoría</th>
              <th class="py-3">Servicio / Sistema</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading && !store.templates.length">
              <td colspan="5" class="text-center py-5"><div class="spinner-border spinner-border-sm"></div></td>
            </tr>
            <tr v-else-if="!store.templates.length">
              <td colspan="5" class="text-center py-5 text-muted">
                <i class="bi bi-file-earmark-text fs-2 d-block mb-2"></i>
                Sin plantillas registradas.
              </td>
            </tr>

            <template v-for="tpl in store.templates" :key="tpl.uuid">
              <tr v-if="pendingDelete?.uuid === tpl.uuid" class="bg-danger-subtle">
                <td colspan="5" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar <strong>{{ tpl.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(tpl)" :disabled="store.actionLoading">Confirmar</button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="px-4">
                  <div class="d-flex align-items-center gap-2">
                    <span class="fw-semibold text-dark">{{ tpl.name }}</span>
                    <code v-if="tpl.code" class="text-muted smaller">{{ tpl.code }}</code>
                  </div>
                  <div class="text-muted smaller">{{ tpl.description || 'Sin descripción' }}</div>
                </td>
                <td>
                  <span class="badge bg-light text-secondary border rounded-pill">{{ tpl.category_name || 'N/A' }}</span>
                </td>
                <td>
                  <div class="small">{{ tpl.service_type_name || '—' }}</div>
                  <div class="text-muted smaller">{{ tpl.system_type_name || '' }}</div>
                </td>
                <td class="text-center">
                  <InlineSwitch
                    :model-value="tpl.is_active"
                    :on-save="(value) => handleToggleActive(tpl, value)"
                  />
                </td>
                <td class="text-end px-4">
                  <div class="d-flex gap-2 justify-content-end">
                    <button class="btn btn-sm btn-primary" @click="openBuilder(tpl)">
                      <i class="bi bi-sliders me-1"></i> Configurar
                    </button>
                    <TableRowActions :item="tpl" :actions="rowActions" @edit="handleEdit" @duplicate="handleDuplicate" @delete="pendingDelete = $event" />
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nueva Plantilla' : 'Editar Plantilla'"
      :subtitle="mode === 'create' ? 'Define una plantilla de cotización inteligente' : `Modificando: ${selected?.name}`"
      width="520px"
    >
      <QuoteTemplateForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import InlineSwitch from '@/modules/technical_services/InlineSwitch.vue';
import TableRowActions from '@/modules/technical_services/TableRowActions.vue';
import QuoteTemplateForm from './QuoteTemplateForm.vue';

const router = useRouter();
const store = useQuoteTemplateBuilderStore();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const pendingDelete = ref(null);

const rowActions = [
  { key: 'edit', label: 'Editar', icon: 'bi bi-pencil' },
  { key: 'duplicate', label: 'Duplicar', icon: 'bi bi-copy' },
  { key: 'delete', label: 'Eliminar', icon: 'bi bi-trash', class: 'text-danger' },
];

onMounted(() => {
  store.fetchTemplates();
});

function openBuilder(tpl) {
  router.push({ name: 'quote-template-builder', params: { uuid: tpl.uuid } });
}

async function handleEdit(tpl) {
  // El listado usa el serializer liviano (solo *_name); se trae el detalle
  // completo (con category/subcategory/service_type/etc. anidados) antes
  // de abrir el formulario para que los selects queden bien preseleccionados.
  const full = await store.fetchTemplateDetail(tpl.uuid);
  if (full) openEdit(full);
  else toast.error('No se pudo cargar la plantilla.');
}

async function handleToggleActive(tpl, value) {
  const { ok, error } = await store.updateTemplate(tpl.uuid, { is_active: value });
  if (ok) {
    toast.success(`Plantilla "${tpl.name}" ${value ? 'activada' : 'desactivada'}.`);
  } else {
    toast.error(error || 'Error al actualizar.');
    throw new Error(error);
  }
}

async function handleDuplicate(tpl) {
  const { ok, data, error } = await store.cloneTemplate(tpl.uuid);
  if (ok) {
    toast.success(`Plantilla duplicada como "${data.name}".`);
  } else {
    toast.error(error || 'No se pudo duplicar la plantilla.');
  }
}

async function executeDelete(tpl) {
  const { ok, error } = await store.deleteTemplate(tpl.uuid);
  if (ok) {
    toast.success(`Plantilla "${tpl.name}" eliminada.`);
  } else {
    toast.error(error || 'No se pudo eliminar la plantilla.');
  }
  pendingDelete.value = null;
}

const onFormSuccess = () => { close(); };
</script>

<style scoped>
.smaller { font-size: 0.75rem; }
</style>
