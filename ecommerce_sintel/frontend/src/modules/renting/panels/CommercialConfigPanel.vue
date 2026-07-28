<template>
  <div>
    <h6 class="fw-semibold mb-3">Modalidades comerciales</h6>

    <div class="card border-0 shadow-sm p-4">
      <p class="text-muted small mb-3">
        Elige que modalidades comerciales admite este equipo. Renting (alquiler
        pagado) esta habilitado por defecto; Comodato (prestamo de uso, sin
        cobro inmediato, requiere aprobacion manual) es opcional.
      </p>

      <div v-if="!editing">
        <div class="d-flex flex-wrap gap-2 mb-3">
          <span
            class="badge rounded-pill px-3 py-2"
            :class="config?.renting_enabled ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'"
          >
            <i class="bi bi-calendar-check me-1"></i> Renting
            {{ config?.renting_enabled ? 'habilitado' : 'deshabilitado' }}
          </span>
          <span
            class="badge rounded-pill px-3 py-2"
            :class="config?.comodato_enabled ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'"
          >
            <i class="bi bi-hand-index-thumb me-1"></i> Comodato
            {{ config?.comodato_enabled ? 'habilitado' : 'deshabilitado' }}
          </span>
        </div>
        <div v-if="config?.comodato_notes" class="border rounded-3 p-3 bg-light mb-3">
          <div class="text-muted small mb-1">Notas de comodato</div>
          <div>{{ config.comodato_notes }}</div>
        </div>
        <button class="btn btn-sm btn-outline-primary" @click="startEdit">
          <i class="bi bi-pencil me-1"></i> Editar
        </button>
      </div>

      <form v-else @submit.prevent="save">
        <div class="form-check form-switch mb-2">
          <input
            id="renting-enabled-switch"
            v-model="form.renting_enabled"
            class="form-check-input"
            type="checkbox"
            role="switch"
          />
          <label class="form-check-label" for="renting-enabled-switch">Renting habilitado</label>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            id="comodato-enabled-switch"
            v-model="form.comodato_enabled"
            class="form-check-input"
            type="checkbox"
            role="switch"
          />
          <label class="form-check-label" for="comodato-enabled-switch">Comodato habilitado</label>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold">Notas de comodato</label>
          <textarea
            v-model="form.comodato_notes"
            class="form-control form-control-sm"
            rows="2"
            placeholder="Condiciones particulares del comodato para este equipo..."
          ></textarea>
        </div>
        <div class="d-flex gap-2">
          <button type="submit" class="btn btn-sm btn-primary" :disabled="store.actionLoading">
            <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
            Guardar
          </button>
          <button type="button" class="btn btn-sm btn-light border" @click="editing = false">Cancelar</button>
        </div>
        <div v-if="error" class="alert alert-danger mt-3 py-2 small">{{ error }}</div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const store = useRentingCatalogAdminStore();
const toast = useToast();

const editing = ref(false);
const error = ref(null);
const config = computed(() => store.commercialConfig);

const form = reactive({
  renting_enabled: true,
  comodato_enabled: false,
  comodato_notes: '',
});

function startEdit() {
  if (config.value) {
    Object.assign(form, { ...config.value });
  }
  editing.value = true;
  error.value = null;
}

async function save() {
  error.value = null;
  const result = await store.upsertCommercialConfig(props.equipmentUuid, { ...form });
  if (result.ok) {
    toast.success('Configuración comercial guardada.');
    editing.value = false;
  } else {
    error.value = result.error;
  }
}

onMounted(() => store.fetchCommercialConfig(props.equipmentUuid));
</script>
