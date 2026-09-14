<template>
  <div class="step-card">
    <h5 class="fw-bold mb-4">Experiencia y portafolio</h5>

    <!-- Experiencia laboral -->
    <div class="mb-5">
      <div class="section-header">
        <span class="fw-bold small">Experiencia laboral</span>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="showExpForm = !showExpForm">
          <i class="bi bi-plus me-1"></i>Agregar
        </button>
      </div>

      <div v-if="showExpForm" class="add-form mb-3">
        <div class="row g-2">
          <div class="col-sm-6">
            <input v-model="newExp.company" class="form-control form-control-sm" placeholder="Empresa *">
          </div>
          <div class="col-sm-6">
            <input v-model="newExp.position" class="form-control form-control-sm" placeholder="Cargo *">
          </div>
          <div class="col-12">
            <textarea v-model="newExp.description" class="form-control form-control-sm" rows="2" placeholder="Descripcion y logros"></textarea>
          </div>
          <div class="col-sm-4">
            <label class="form-label form-label-sm mb-0 text-muted">Inicio *</label>
            <input v-model="newExp.start_date" type="date" class="form-control form-control-sm">
          </div>
          <div class="col-sm-4">
            <label class="form-label form-label-sm mb-0 text-muted">Fin</label>
            <input v-model="newExp.end_date" type="date" class="form-control form-control-sm" :disabled="newExp.is_current">
          </div>
          <div class="col-sm-4 d-flex align-items-end pb-1">
            <div class="form-check form-check-sm">
              <input v-model="newExp.is_current" type="checkbox" class="form-check-input" id="exp-current">
              <label for="exp-current" class="form-check-label small">Trabajo actual</label>
            </div>
          </div>
          <div class="col-12 d-flex justify-content-end gap-2">
            <button type="button" class="btn btn-primary btn-sm" @click="onAddExperience">Guardar</button>
            <button type="button" class="btn btn-light btn-sm" @click="showExpForm = false">Cancelar</button>
          </div>
        </div>
      </div>

      <div v-for="exp in experiences" :key="exp.id">
        <!-- Edit mode -->
        <div v-if="editingExpId === exp.id" class="add-form mb-2">
          <div class="row g-2">
            <div class="col-sm-6">
              <input v-model="editExp.company" class="form-control form-control-sm" placeholder="Empresa">
            </div>
            <div class="col-sm-6">
              <input v-model="editExp.position" class="form-control form-control-sm" placeholder="Cargo">
            </div>
            <div class="col-12">
              <textarea v-model="editExp.description" class="form-control form-control-sm" rows="2" placeholder="Descripcion"></textarea>
            </div>
            <div class="col-sm-4">
              <input v-model="editExp.start_date" type="date" class="form-control form-control-sm">
            </div>
            <div class="col-sm-4">
              <input v-model="editExp.end_date" type="date" class="form-control form-control-sm" :disabled="editExp.is_current">
            </div>
            <div class="col-sm-4 d-flex align-items-center">
              <div class="form-check form-check-sm">
                <input v-model="editExp.is_current" type="checkbox" class="form-check-input" id="edit-exp-current">
                <label for="edit-exp-current" class="form-check-label small">Trabajo actual</label>
              </div>
            </div>
            <div class="col-12 d-flex justify-content-end gap-2">
              <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="onSaveExperience(exp.id)">
                <span v-if="editSaving" class="spinner-border spinner-border-sm me-1"></span>Guardar
              </button>
              <button type="button" class="btn btn-light btn-sm" @click="editingExpId = null">Cancelar</button>
            </div>
          </div>
        </div>
        <!-- Delete confirm -->
        <div v-else-if="deletingId === `ex-${exp.id}`" class="list-item bg-danger-subtle d-flex justify-content-between align-items-center">
          <span class="small text-danger fw-semibold">¿Eliminar "{{ exp.position }}" en {{ exp.company }}?</span>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-danger btn-sm" @click="onRemoveExperience(exp)">Eliminar</button>
            <button type="button" class="btn btn-light btn-sm" @click="deletingId = null">Cancelar</button>
          </div>
        </div>
        <!-- Display mode -->
        <div v-else class="list-item d-flex justify-content-between align-items-start">
          <div>
            <div class="fw-semibold small">{{ exp.position }}</div>
            <div class="text-muted small">{{ exp.company }}</div>
            <div class="text-muted small">{{ exp.start_date }}<span v-if="exp.is_current"> — Actual</span><span v-else-if="exp.end_date"> — {{ exp.end_date }}</span></div>
          </div>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-light" @click="startEditExperience(exp)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-sm text-danger" @click="deletingId = `ex-${exp.id}`"><i class="bi bi-trash3"></i></button>
          </div>
        </div>
      </div>
      <p v-if="!experiences.length" class="text-muted small fst-italic">Sin experiencia laboral registrada.</p>
    </div>

    <!-- Casos de exito -->
    <div>
      <div class="section-header">
        <span class="fw-bold small">Casos de exito / Portafolio</span>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="showCaseForm = !showCaseForm">
          <i class="bi bi-plus me-1"></i>Agregar
        </button>
      </div>

      <div v-if="showCaseForm" class="add-form mb-3">
        <div class="row g-2">
          <div class="col-sm-6">
            <input v-model="newCase.title" class="form-control form-control-sm" placeholder="Titulo del proyecto *">
          </div>
          <div class="col-sm-6">
            <label class="form-label form-label-sm mb-0 text-muted">Fecha de finalizacion</label>
            <input v-model="newCase.completion_date" type="date" class="form-control form-control-sm">
          </div>
          <div class="col-12">
            <textarea v-model="newCase.description" class="form-control form-control-sm" rows="3" placeholder="Describe el proyecto y los resultados *"></textarea>
          </div>
          <div class="col-12 d-flex justify-content-end gap-2">
            <button type="button" class="btn btn-primary btn-sm" @click="onAddCase">Guardar</button>
            <button type="button" class="btn btn-light btn-sm" @click="showCaseForm = false">Cancelar</button>
          </div>
        </div>
      </div>

      <div v-for="sc in successCases" :key="sc.id">
        <!-- Edit mode -->
        <div v-if="editingCaseId === sc.id" class="add-form mb-2">
          <div class="row g-2">
            <div class="col-sm-6">
              <input v-model="editCase.title" class="form-control form-control-sm" placeholder="Titulo">
            </div>
            <div class="col-sm-6">
              <input v-model="editCase.completion_date" type="date" class="form-control form-control-sm">
            </div>
            <div class="col-12">
              <textarea v-model="editCase.description" class="form-control form-control-sm" rows="3" placeholder="Descripcion"></textarea>
            </div>
            <div class="col-12 d-flex justify-content-end gap-2">
              <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="onSaveCase(sc.id)">
                <span v-if="editSaving" class="spinner-border spinner-border-sm me-1"></span>Guardar
              </button>
              <button type="button" class="btn btn-light btn-sm" @click="editingCaseId = null">Cancelar</button>
            </div>
          </div>
        </div>
        <!-- Delete confirm -->
        <div v-else-if="deletingId === `sc-${sc.id}`" class="list-item bg-danger-subtle d-flex justify-content-between align-items-center">
          <span class="small text-danger fw-semibold">¿Eliminar "{{ sc.title }}"?</span>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-danger btn-sm" @click="onRemoveCase(sc)">Eliminar</button>
            <button type="button" class="btn btn-light btn-sm" @click="deletingId = null">Cancelar</button>
          </div>
        </div>
        <!-- Display mode -->
        <div v-else class="list-item d-flex justify-content-between align-items-start">
          <div>
            <div class="fw-semibold small">{{ sc.title }}</div>
            <p class="text-muted small mb-0">{{ truncate(sc.description, 100) }}</p>
          </div>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-light" @click="startEditCase(sc)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-sm text-danger" @click="deletingId = `sc-${sc.id}`"><i class="bi bi-trash3"></i></button>
          </div>
        </div>
      </div>
      <p v-if="!successCases.length" class="text-muted small fst-italic">Sin casos de exito registrados.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  experiences: { type: Array, required: true },
  successCases: { type: Array, required: true },
  // Funciones de red del padre; ver Step2Skills.vue para la explicacion del patron.
  actions: { type: Object, required: true },
});

function truncate(s, n) { return (s || '').length > n ? s.slice(0, n) + '...' : (s || ''); }

// `deletingId`/`editSaving` compartidos entre las 2 subsecciones de este
// paso, replica el comportamiento original.
const deletingId = ref(null);
const editSaving = ref(false);

// ─── Experiencia laboral ───────────────────────────────────────────────────
const showExpForm = ref(false);
const newExp = ref({ company: '', position: '', description: '', start_date: '', end_date: '', is_current: false });
const editingExpId = ref(null);
const editExp = ref({});

async function onAddExperience() {
  const ok = await props.actions.addExperience({ ...newExp.value });
  if (ok) {
    newExp.value = { company: '', position: '', description: '', start_date: '', end_date: '', is_current: false };
    showExpForm.value = false;
  }
}

function startEditExperience(exp) {
  editingExpId.value = exp.id;
  editExp.value = { company: exp.company, position: exp.position, description: exp.description || '', start_date: exp.start_date || '', end_date: exp.end_date || '', is_current: exp.is_current };
}

async function onSaveExperience(id) {
  editSaving.value = true;
  const ok = await props.actions.saveExperience(id, { ...editExp.value });
  if (ok) editingExpId.value = null;
  editSaving.value = false;
}

async function onRemoveExperience(exp) {
  const ok = await props.actions.removeExperience(exp);
  if (ok) deletingId.value = null;
}

// ─── Casos de exito ─────────────────────────────────────────────────────────
const showCaseForm = ref(false);
const newCase = ref({ title: '', description: '', completion_date: '' });
const editingCaseId = ref(null);
const editCase = ref({});

async function onAddCase() {
  const ok = await props.actions.addCase({ ...newCase.value });
  if (ok) {
    newCase.value = { title: '', description: '', completion_date: '' };
    showCaseForm.value = false;
  }
}

function startEditCase(sc) {
  editingCaseId.value = sc.id;
  editCase.value = { title: sc.title, description: sc.description || '', completion_date: sc.completion_date || '' };
}

async function onSaveCase(id) {
  editSaving.value = true;
  const ok = await props.actions.saveCase(id, { ...editCase.value });
  if (ok) editingCaseId.value = null;
  editSaving.value = false;
}

async function onRemoveCase(sc) {
  const ok = await props.actions.removeCase(sc);
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
