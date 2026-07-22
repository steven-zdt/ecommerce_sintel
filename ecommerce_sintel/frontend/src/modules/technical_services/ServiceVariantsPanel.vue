<template>
  <div class="p-1">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">
        El SKU lo genera el backend automaticamente y no es editable.
      </p>
      <button class="btn btn-primary btn-sm" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nueva variante
      </button>
    </div>

    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="bg-light small text-uppercase fw-semibold">
          <tr>
            <th class="py-2">SKU</th>
            <th class="py-2">Estrategia</th>
            <th class="py-2">Precio fijo</th>
            <th class="py-2">Horas</th>
            <th class="py-2">Complejidad</th>
            <th class="py-2 text-center">Principal</th>
            <th class="py-2 text-center">Activa</th>
            <th class="py-2 text-end">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <!-- Fila de creacion rapida -->
          <tr v-if="isCreating" class="bg-light-subtle">
            <td class="text-muted small">Auto</td>
            <td>
              <select v-model="newVariant.pricing_strategy" class="form-select form-select-sm">
                <option value="HOURLY">Por hora</option>
                <option value="DAILY">Por dia</option>
                <option value="FIXED">Fijo</option>
              </select>
            </td>
            <td>
              <input
                v-model.number="newVariant.fixed_price"
                type="number"
                step="0.01"
                class="form-control form-control-sm"
                :disabled="newVariant.pricing_strategy !== 'FIXED'"
              />
            </td>
            <td>
              <input v-model.number="newVariant.estimated_hours" type="number" step="0.01" class="form-control form-control-sm" />
            </td>
            <td>
              <input v-model.number="newVariant.complexity_factor" type="number" step="0.01" class="form-control form-control-sm" />
            </td>
            <td class="text-center">
              <input v-model="newVariant.is_default" class="form-check-input" type="checkbox" />
            </td>
            <td class="text-center">
              <input v-model="newVariant.is_active" class="form-check-input" type="checkbox" />
            </td>
            <td class="text-end">
              <div class="d-flex gap-2 justify-content-end">
                <button class="btn btn-sm btn-success" @click="handleCreate" :disabled="store.actionLoading">
                  <span v-if="store.actionLoading" class="spinner-border spinner-border-sm"></span>
                  <i v-else class="bi bi-check-lg"></i>
                </button>
                <button class="btn btn-sm btn-secondary" @click="cancelCreate"><i class="bi bi-x-lg"></i></button>
              </div>
            </td>
          </tr>

          <tr v-if="store.loading && !store.variants.length">
            <td colspan="8" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div></td>
          </tr>
          <tr v-else-if="!store.variants.length && !isCreating">
            <td colspan="8" class="text-center py-4 text-muted">Sin variantes registradas.</td>
          </tr>

          <template v-for="variant in store.variants" :key="variant.uuid">
            <tr v-if="pendingDelete?.uuid === variant.uuid" class="bg-danger-subtle">
              <td colspan="8" class="p-0">
                <div class="d-flex align-items-center gap-3 px-3 py-2">
                  <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                  <span class="small">¿Eliminar la variante <strong>{{ variant.sku }}</strong>?</span>
                  <div class="ms-auto d-flex gap-2">
                    <button class="btn btn-sm btn-danger" @click="handleDelete(variant)" :disabled="store.actionLoading">Confirmar</button>
                    <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-else>
              <td><code class="small text-muted">{{ variant.sku }}</code></td>
              <td>
                <InlineSelectEditor
                  :model-value="variant.pricing_strategy"
                  :options="strategyOptions"
                  :on-save="(value) => handleSave(variant, { pricing_strategy: value })"
                />
              </td>
              <td>
                <InlineTextEditor
                  v-if="variant.pricing_strategy === 'FIXED'"
                  type="number"
                  :model-value="variant.fixed_price"
                  :on-save="(value) => handleSave(variant, { fixed_price: value })"
                />
                <span v-else class="badge bg-light text-secondary border">Calculado</span>
              </td>
              <td>
                <InlineTextEditor
                  type="number"
                  :model-value="variant.estimated_hours"
                  :on-save="(value) => handleSave(variant, { estimated_hours: value })"
                />
              </td>
              <td>
                <InlineTextEditor
                  type="number"
                  :model-value="variant.complexity_factor"
                  :on-save="(value) => handleSave(variant, { complexity_factor: value })"
                />
              </td>
              <td class="text-center">
                <InlineSwitch
                  :model-value="variant.is_default"
                  :on-save="(value) => handleSave(variant, { is_default: value })"
                />
              </td>
              <td class="text-center">
                <InlineSwitch
                  :model-value="variant.is_active"
                  :on-save="(value) => handleSave(variant, { is_active: value })"
                />
              </td>
              <td class="text-end">
                <button class="btn btn-sm btn-light border" @click="pendingDelete = variant" title="Eliminar">
                  <i class="bi bi-trash text-danger"></i>
                </button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useToast } from '@/composables/useToast';

import InlineTextEditor from './InlineTextEditor.vue';
import InlineSelectEditor from './InlineSelectEditor.vue';
import InlineSwitch from './InlineSwitch.vue';

const props = defineProps({
  service: { type: Object, required: true },
});

const store = useTechnicalServicesStore();
const toast = useToast();

const isCreating = ref(false);
const newVariant = ref({});
const pendingDelete = ref(null);

const strategyOptions = [
  { value: 'HOURLY', text: 'Por hora' },
  { value: 'DAILY', text: 'Por dia' },
  { value: 'FIXED', text: 'Fijo' },
];

const load = () => {
  if (props.service?.uuid) {
    store.fetchVariants(props.service.uuid);
  }
};

watch(() => props.service?.uuid, load, { immediate: true });

const beginCreate = () => {
  newVariant.value = {
    pricing_strategy: 'HOURLY',
    fixed_price: null,
    estimated_hours: 1,
    complexity_factor: 1,
    is_default: false,
    is_active: true,
  };
  isCreating.value = true;
};

const cancelCreate = () => {
  isCreating.value = false;
};

const handleCreate = async () => {
  const { ok, error } = await store.createVariant({ service: props.service.uuid, ...newVariant.value });
  if (ok) {
    toast.success('Variante creada.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear la variante.');
  }
};

const handleSave = async (variant, payload) => {
  const { ok, error } = await store.updateVariant(variant.uuid, props.service.uuid, payload);
  if (ok) {
    toast.success(`Variante "${variant.sku}" actualizada.`);
  } else {
    toast.error(error || 'Error al actualizar la variante.');
    load();
    throw new Error(error);
  }
};

const handleDelete = async (variant) => {
  const { ok, error } = await store.deleteVariant(variant.uuid, props.service.uuid);
  if (ok) {
    toast.success(`Variante "${variant.sku}" eliminada.`);
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar la variante.');
  }
};
</script>
