<template>
  <div class="step-card">
    <h5 class="fw-bold mb-4">Habilidades y especialidades</h5>

    <!-- Especialidades -->
    <div class="mb-5">
      <div class="section-header">
        <span class="fw-bold small">Especialidades (categorias de servicio)</span>
      </div>
      <div class="d-flex gap-2 mb-3">
        <select v-model="newSpecialtyId" class="form-select">
          <option value="">Selecciona una categoria...</option>
          <option v-for="cat in availableCategories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
        </select>
        <button
          type="button"
          class="btn btn-primary px-3"
          :disabled="!newSpecialtyId || addingSpecialty"
          @click="onAddSpecialty"
        >
          <span v-if="addingSpecialty" class="spinner-border spinner-border-sm"></span>
          <i v-else class="bi bi-plus-lg"></i>
        </button>
      </div>
      <div v-if="specialties.length" class="d-flex flex-wrap gap-2">
        <div v-for="sp in specialties" :key="sp.id">
          <span v-if="deletingId !== `sp-${sp.id}`" class="badge-tag">
            {{ sp.category.name }}
            <button type="button" class="btn-remove" @click="deletingId = `sp-${sp.id}`">
              <i class="bi bi-x"></i>
            </button>
          </span>
          <span v-else class="badge-tag-danger">
            <span class="me-1">¿Eliminar?</span>
            <button type="button" class="btn btn-danger btn-xs" @click="onRemoveSpecialty(sp)">Si</button>
            <button type="button" class="btn btn-light btn-xs ms-1" @click="deletingId = null">No</button>
          </span>
        </div>
      </div>
      <p v-else class="text-muted small fst-italic">Sin especialidades agregadas.</p>
    </div>

    <!-- Habilidades -->
    <div>
      <div class="section-header">
        <span class="fw-bold small">Habilidades</span>
      </div>

      <!-- Formulario agregar habilidad -->
      <div class="add-form mb-3">
        <div class="row g-2 align-items-end">
          <div class="col">
            <input v-model="newSkill.name" type="text" class="form-control form-control-sm" placeholder="Nombre de la habilidad" @keyup.enter="onAddSkill">
          </div>
          <div class="col-auto">
            <select v-model="newSkill.level" class="form-select form-select-sm" style="min-width:130px">
              <option value="">Nivel</option>
              <option value="Basico">Basico</option>
              <option value="Intermedio">Intermedio</option>
              <option value="Avanzado">Avanzado</option>
              <option value="Experto">Experto</option>
            </select>
          </div>
          <div class="col-auto">
            <button type="button" class="btn btn-primary btn-sm" :disabled="!newSkill.name" @click="onAddSkill">
              <i class="bi bi-plus-lg me-1"></i>Agregar
            </button>
          </div>
        </div>
      </div>

      <!-- Lista de habilidades -->
      <div v-for="sk in skills" :key="sk.id">
        <!-- Edit mode -->
        <div v-if="editingSkillId === sk.id" class="add-form mb-2">
          <div class="row g-2 align-items-end">
            <div class="col">
              <input v-model="editSkill.name" type="text" class="form-control form-control-sm" placeholder="Habilidad">
            </div>
            <div class="col-auto">
              <select v-model="editSkill.level" class="form-select form-select-sm" style="min-width:130px">
                <option value="">Nivel</option>
                <option value="Basico">Basico</option>
                <option value="Intermedio">Intermedio</option>
                <option value="Avanzado">Avanzado</option>
                <option value="Experto">Experto</option>
              </select>
            </div>
            <div class="col-auto d-flex gap-1">
              <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="onSaveSkill(sk.id)">
                <span v-if="editSaving" class="spinner-border spinner-border-sm me-1"></span>Guardar
              </button>
              <button type="button" class="btn btn-light btn-sm" @click="editingSkillId = null">Cancelar</button>
            </div>
          </div>
        </div>

        <!-- Delete confirm -->
        <div v-else-if="deletingId === `sk-${sk.id}`" class="list-item bg-danger-subtle d-flex justify-content-between align-items-center">
          <span class="small text-danger fw-semibold">¿Eliminar "{{ sk.name }}"?</span>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-danger btn-sm" @click="onRemoveSkill(sk)">Eliminar</button>
            <button type="button" class="btn btn-light btn-sm" @click="deletingId = null">Cancelar</button>
          </div>
        </div>

        <!-- Display mode -->
        <div v-else class="list-item d-flex justify-content-between align-items-center">
          <div>
            <span class="fw-semibold small">{{ sk.name }}</span>
            <span v-if="sk.level" class="text-muted small ms-2">({{ sk.level }})</span>
          </div>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-light" @click="startEditSkill(sk)">
              <i class="bi bi-pencil"></i>
            </button>
            <button type="button" class="btn btn-sm text-danger" @click="deletingId = `sk-${sk.id}`">
              <i class="bi bi-trash3"></i>
            </button>
          </div>
        </div>
      </div>
      <p v-if="!skills.length" class="text-muted small fst-italic">Sin habilidades agregadas.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  categories: { type: Array, default: () => [] },
  specialties: { type: Array, required: true },
  skills: { type: Array, required: true },
  // Funciones de red del padre (fetch/push/etc. sobre los arrays de arriba
  // viven ahi) -- este paso solo posee su propio estado de UI efimero
  // (formularios/edicion/confirmacion de borrado) y llama a estas acciones
  // pasandoles el payload.
  actions: { type: Object, required: true },
});

const availableCategories = computed(() => {
  const usedIds = new Set(props.specialties.map(sp => sp.category?.id));
  return props.categories.filter(cat => !usedIds.has(cat.id));
});

const deletingId = ref(null);

// ─── Especialidades ───────────────────────────────────────────────────────
const newSpecialtyId = ref('');
const addingSpecialty = ref(false);

async function onAddSpecialty() {
  if (!newSpecialtyId.value) return;
  addingSpecialty.value = true;
  const ok = await props.actions.addSpecialty(newSpecialtyId.value);
  if (ok) newSpecialtyId.value = '';
  addingSpecialty.value = false;
}

async function onRemoveSpecialty(sp) {
  const ok = await props.actions.removeSpecialty(sp);
  if (ok) deletingId.value = null;
}

// ─── Habilidades ──────────────────────────────────────────────────────────
const newSkill = ref({ name: '', level: '' });
const editingSkillId = ref(null);
const editSkill = ref({ name: '', level: '' });
const editSaving = ref(false);

async function onAddSkill() {
  if (!newSkill.value.name.trim()) return;
  const ok = await props.actions.addSkill({ name: newSkill.value.name.trim(), level: newSkill.value.level });
  if (ok) newSkill.value = { name: '', level: '' };
}

function startEditSkill(sk) {
  editingSkillId.value = sk.id;
  editSkill.value = { name: sk.name, level: sk.level || '' };
}

async function onSaveSkill(id) {
  editSaving.value = true;
  const ok = await props.actions.saveSkill(id, { name: editSkill.value.name, level: editSkill.value.level });
  if (ok) editingSkillId.value = null;
  editSaving.value = false;
}

async function onRemoveSkill(sk) {
  const ok = await props.actions.removeSkill(sk);
  if (ok) deletingId.value = null;
}
</script>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f3f4f6;
}
.badge-tag {
  display: inline-flex; align-items: center; gap: 4px;
  background: #eff6ff; color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 8px; padding: 4px 10px; font-size: .8rem;
}
.badge-tag-danger {
  display: inline-flex; align-items: center; gap: 4px;
  background: #fef2f2; color: #dc2626;
  border: 1px solid #fca5a5;
  border-radius: 8px; padding: 4px 10px; font-size: .8rem;
}
.btn-remove {
  background: none; border: none; padding: 0; line-height: 1;
  color: #6b7280; font-size: .85rem; cursor: pointer;
}
.btn-remove:hover { color: #dc2626; }
.btn-xs {
  padding: 1px 6px; font-size: .72rem; border-radius: 4px;
}
.add-form {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
}
.list-item {
  border-left: 3px solid #e5e7eb;
  padding: 10px 10px 10px 14px;
  margin-bottom: 6px;
  border-radius: 0 6px 6px 0;
  transition: background .15s;
}
.list-item:last-child { margin-bottom: 0; }
.list-item.bg-danger-subtle { border-left-color: #dc2626; }
</style>
