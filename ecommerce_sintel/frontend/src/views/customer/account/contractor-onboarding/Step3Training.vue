<template>
  <div class="step-card">
    <h5 class="fw-bold mb-4">Formacion y certificaciones</h5>

    <!-- Formacion academica -->
    <div class="mb-5">
      <div class="section-header">
        <span class="fw-bold small">Formacion academica</span>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="showAcademicForm = !showAcademicForm">
          <i class="bi bi-plus me-1"></i>Agregar
        </button>
      </div>

      <div v-if="showAcademicForm" class="add-form mb-3">
        <div class="row g-2">
          <div class="col-sm-6">
            <input v-model="newAcademic.institution" class="form-control form-control-sm" placeholder="Institucion *">
          </div>
          <div class="col-sm-6">
            <input v-model="newAcademic.degree" class="form-control form-control-sm" placeholder="Titulo obtenido *">
          </div>
          <div class="col-sm-6">
            <input v-model="newAcademic.field_of_study" class="form-control form-control-sm" placeholder="Area de estudio">
          </div>
          <div class="col-sm-3">
            <label class="form-label form-label-sm mb-0 text-muted">Inicio *</label>
            <input v-model="newAcademic.start_date" type="date" class="form-control form-control-sm">
          </div>
          <div class="col-sm-3">
            <label class="form-label form-label-sm mb-0 text-muted">Fin</label>
            <input v-model="newAcademic.end_date" type="date" class="form-control form-control-sm" :disabled="newAcademic.is_current">
          </div>
          <div class="col-12 d-flex align-items-center gap-3">
            <div class="form-check form-check-sm">
              <input v-model="newAcademic.is_current" type="checkbox" class="form-check-input" id="ac-current">
              <label for="ac-current" class="form-check-label small">En curso</label>
            </div>
            <div class="ms-auto d-flex gap-2">
              <button type="button" class="btn btn-primary btn-sm" @click="onAddAcademic">Guardar</button>
              <button type="button" class="btn btn-light btn-sm" @click="showAcademicForm = false">Cancelar</button>
            </div>
          </div>
        </div>
      </div>

      <div v-for="a in academics" :key="a.id">
        <!-- Edit mode -->
        <div v-if="editingAcademicId === a.id" class="add-form mb-2">
          <div class="row g-2">
            <div class="col-sm-6">
              <input v-model="editAcademic.institution" class="form-control form-control-sm" placeholder="Institucion">
            </div>
            <div class="col-sm-6">
              <input v-model="editAcademic.degree" class="form-control form-control-sm" placeholder="Titulo obtenido">
            </div>
            <div class="col-sm-6">
              <input v-model="editAcademic.field_of_study" class="form-control form-control-sm" placeholder="Area de estudio">
            </div>
            <div class="col-sm-3">
              <input v-model="editAcademic.start_date" type="date" class="form-control form-control-sm">
            </div>
            <div class="col-sm-3">
              <input v-model="editAcademic.end_date" type="date" class="form-control form-control-sm" :disabled="editAcademic.is_current">
            </div>
            <div class="col-12 d-flex align-items-center gap-3">
              <div class="form-check form-check-sm">
                <input v-model="editAcademic.is_current" type="checkbox" class="form-check-input" id="edit-ac-current">
                <label for="edit-ac-current" class="form-check-label small">En curso</label>
              </div>
              <div class="ms-auto d-flex gap-2">
                <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="onSaveAcademic(a.id)">
                  <span v-if="editSaving" class="spinner-border spinner-border-sm me-1"></span>Guardar
                </button>
                <button type="button" class="btn btn-light btn-sm" @click="editingAcademicId = null">Cancelar</button>
              </div>
            </div>
          </div>
        </div>
        <!-- Delete confirm -->
        <div v-else-if="deletingId === `ac-${a.id}`" class="list-item bg-danger-subtle d-flex justify-content-between align-items-center">
          <span class="small text-danger fw-semibold">¿Eliminar "{{ a.degree }}"?</span>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-danger btn-sm" @click="onRemoveAcademic(a)">Eliminar</button>
            <button type="button" class="btn btn-light btn-sm" @click="deletingId = null">Cancelar</button>
          </div>
        </div>
        <!-- Display mode -->
        <div v-else class="list-item d-flex justify-content-between align-items-start">
          <div>
            <div class="fw-semibold small">{{ a.degree }}</div>
            <div class="text-muted small">{{ a.institution }}<span v-if="a.field_of_study"> · {{ a.field_of_study }}</span></div>
            <div class="text-muted small">{{ a.start_date }}<span v-if="a.end_date"> — {{ a.end_date }}</span><span v-if="a.is_current"> — Actual</span></div>
          </div>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-light" @click="startEditAcademic(a)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-sm text-danger" @click="deletingId = `ac-${a.id}`"><i class="bi bi-trash3"></i></button>
          </div>
        </div>
      </div>
      <p v-if="!academics.length" class="text-muted small fst-italic">Sin formacion academica registrada.</p>
    </div>

    <!-- Cursos -->
    <div class="mb-5">
      <div class="section-header">
        <span class="fw-bold small">Cursos</span>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="showCourseForm = !showCourseForm">
          <i class="bi bi-plus me-1"></i>Agregar
        </button>
      </div>

      <div v-if="showCourseForm" class="add-form mb-3">
        <div class="row g-2">
          <div class="col-sm-6">
            <input v-model="newCourse.title" class="form-control form-control-sm" placeholder="Nombre del curso *">
          </div>
          <div class="col-sm-6">
            <input v-model="newCourse.institution" class="form-control form-control-sm" placeholder="Entidad certificadora">
          </div>
          <div class="col-sm-4">
            <label class="form-label form-label-sm mb-0 text-muted">Fecha de finalizacion *</label>
            <input v-model="newCourse.completion_date" type="date" class="form-control form-control-sm">
          </div>
          <div class="col-sm-3">
            <label class="form-label form-label-sm mb-0 text-muted">Horas</label>
            <input v-model="newCourse.hours" type="number" class="form-control form-control-sm" placeholder="Horas" min="0">
          </div>
          <div class="col-12 d-flex justify-content-end gap-2">
            <button type="button" class="btn btn-primary btn-sm" @click="onAddCourse">Guardar</button>
            <button type="button" class="btn btn-light btn-sm" @click="showCourseForm = false">Cancelar</button>
          </div>
        </div>
      </div>

      <div v-for="c in courses" :key="c.id">
        <!-- Edit mode -->
        <div v-if="editingCourseId === c.id" class="add-form mb-2">
          <div class="row g-2">
            <div class="col-sm-6">
              <input v-model="editCourse.title" class="form-control form-control-sm" placeholder="Nombre del curso">
            </div>
            <div class="col-sm-6">
              <input v-model="editCourse.institution" class="form-control form-control-sm" placeholder="Entidad">
            </div>
            <div class="col-sm-4">
              <input v-model="editCourse.completion_date" type="date" class="form-control form-control-sm">
            </div>
            <div class="col-sm-3">
              <input v-model="editCourse.hours" type="number" class="form-control form-control-sm" placeholder="Horas" min="0">
            </div>
            <div class="col-12 d-flex justify-content-end gap-2">
              <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="onSaveCourse(c.id)">
                <span v-if="editSaving" class="spinner-border spinner-border-sm me-1"></span>Guardar
              </button>
              <button type="button" class="btn btn-light btn-sm" @click="editingCourseId = null">Cancelar</button>
            </div>
          </div>
        </div>
        <!-- Delete confirm -->
        <div v-else-if="deletingId === `co-${c.id}`" class="list-item bg-danger-subtle d-flex justify-content-between align-items-center">
          <span class="small text-danger fw-semibold">¿Eliminar "{{ c.title }}"?</span>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-danger btn-sm" @click="onRemoveCourse(c)">Eliminar</button>
            <button type="button" class="btn btn-light btn-sm" @click="deletingId = null">Cancelar</button>
          </div>
        </div>
        <!-- Display mode -->
        <div v-else class="list-item d-flex justify-content-between align-items-start">
          <div>
            <div class="fw-semibold small">{{ c.title }}</div>
            <div class="text-muted small">{{ c.institution }}<span v-if="c.hours"> · {{ c.hours }}h</span></div>
          </div>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-light" @click="startEditCourse(c)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-sm text-danger" @click="deletingId = `co-${c.id}`"><i class="bi bi-trash3"></i></button>
          </div>
        </div>
      </div>
      <p v-if="!courses.length" class="text-muted small fst-italic">Sin cursos registrados.</p>
    </div>

    <!-- Certificaciones -->
    <div>
      <div class="section-header">
        <span class="fw-bold small">Certificaciones</span>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="showCertForm = !showCertForm">
          <i class="bi bi-plus me-1"></i>Agregar
        </button>
      </div>

      <div v-if="showCertForm" class="add-form mb-3">
        <div class="row g-2">
          <div class="col-sm-6">
            <input v-model="newCert.name" class="form-control form-control-sm" placeholder="Nombre del certificado *">
          </div>
          <div class="col-sm-6">
            <input v-model="newCert.issuing_organization" class="form-control form-control-sm" placeholder="Entidad emisora">
          </div>
          <div class="col-sm-4">
            <label class="form-label form-label-sm mb-0 text-muted">Fecha de emision *</label>
            <input v-model="newCert.issue_date" type="date" class="form-control form-control-sm">
          </div>
          <div class="col-sm-4">
            <label class="form-label form-label-sm mb-0 text-muted">Vencimiento</label>
            <input v-model="newCert.expiration_date" type="date" class="form-control form-control-sm">
          </div>
          <div class="col-sm-4">
            <label class="form-label form-label-sm mb-0 text-muted">ID credencial</label>
            <input v-model="newCert.credential_id" class="form-control form-control-sm" placeholder="ID (opcional)">
          </div>
          <div class="col-12 d-flex justify-content-end gap-2">
            <button type="button" class="btn btn-primary btn-sm" @click="onAddCert">Guardar</button>
            <button type="button" class="btn btn-light btn-sm" @click="showCertForm = false">Cancelar</button>
          </div>
        </div>
      </div>

      <div v-for="cert in certifications" :key="cert.id">
        <!-- Edit mode -->
        <div v-if="editingCertId === cert.id" class="add-form mb-2">
          <div class="row g-2">
            <div class="col-sm-6">
              <input v-model="editCert.name" class="form-control form-control-sm" placeholder="Nombre">
            </div>
            <div class="col-sm-6">
              <input v-model="editCert.issuing_organization" class="form-control form-control-sm" placeholder="Entidad">
            </div>
            <div class="col-sm-4">
              <input v-model="editCert.issue_date" type="date" class="form-control form-control-sm">
            </div>
            <div class="col-sm-4">
              <input v-model="editCert.expiration_date" type="date" class="form-control form-control-sm">
            </div>
            <div class="col-sm-4">
              <input v-model="editCert.credential_id" class="form-control form-control-sm" placeholder="ID credencial">
            </div>
            <div class="col-12 d-flex justify-content-end gap-2">
              <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="onSaveCert(cert.id)">
                <span v-if="editSaving" class="spinner-border spinner-border-sm me-1"></span>Guardar
              </button>
              <button type="button" class="btn btn-light btn-sm" @click="editingCertId = null">Cancelar</button>
            </div>
          </div>
        </div>
        <!-- Delete confirm -->
        <div v-else-if="deletingId === `ce-${cert.id}`" class="list-item bg-danger-subtle d-flex justify-content-between align-items-center">
          <span class="small text-danger fw-semibold">¿Eliminar "{{ cert.name }}"?</span>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-danger btn-sm" @click="onRemoveCert(cert)">Eliminar</button>
            <button type="button" class="btn btn-light btn-sm" @click="deletingId = null">Cancelar</button>
          </div>
        </div>
        <!-- Display mode -->
        <div v-else class="list-item d-flex justify-content-between align-items-start">
          <div>
            <div class="fw-semibold small">{{ cert.name }}</div>
            <div class="text-muted small">{{ cert.issuing_organization }}</div>
            <div v-if="cert.expiration_date" class="text-muted small">Vence: {{ cert.expiration_date }}</div>
          </div>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-light" @click="startEditCert(cert)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-sm text-danger" @click="deletingId = `ce-${cert.id}`"><i class="bi bi-trash3"></i></button>
          </div>
        </div>
      </div>
      <p v-if="!certifications.length" class="text-muted small fst-italic">Sin certificaciones registradas.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  academics: { type: Array, required: true },
  courses: { type: Array, required: true },
  certifications: { type: Array, required: true },
  // Funciones de red del padre; ver Step2Skills.vue para la explicacion del patron.
  actions: { type: Object, required: true },
});

// `deletingId`/`editSaving` se comparten entre las 3 subsecciones de este
// paso (replica el comportamiento original: guardar una edicion deshabilita
// el boton Guardar de las otras 2 subsecciones tambien, no es un bug).
const deletingId = ref(null);
const editSaving = ref(false);

// ─── Formacion academica ──────────────────────────────────────────────────
const showAcademicForm = ref(false);
const newAcademic = ref({ institution: '', degree: '', field_of_study: '', start_date: '', end_date: '', is_current: false });
const editingAcademicId = ref(null);
const editAcademic = ref({});

async function onAddAcademic() {
  const ok = await props.actions.addAcademic({ ...newAcademic.value });
  if (ok) {
    newAcademic.value = { institution: '', degree: '', field_of_study: '', start_date: '', end_date: '', is_current: false };
    showAcademicForm.value = false;
  }
}

function startEditAcademic(a) {
  editingAcademicId.value = a.id;
  editAcademic.value = { institution: a.institution, degree: a.degree, field_of_study: a.field_of_study || '', start_date: a.start_date || '', end_date: a.end_date || '', is_current: a.is_current };
}

async function onSaveAcademic(id) {
  editSaving.value = true;
  const ok = await props.actions.saveAcademic(id, { ...editAcademic.value });
  if (ok) editingAcademicId.value = null;
  editSaving.value = false;
}

async function onRemoveAcademic(a) {
  const ok = await props.actions.removeAcademic(a);
  if (ok) deletingId.value = null;
}

// ─── Cursos ────────────────────────────────────────────────────────────────
const showCourseForm = ref(false);
const newCourse = ref({ title: '', institution: '', completion_date: '', hours: '' });
const editingCourseId = ref(null);
const editCourse = ref({});

async function onAddCourse() {
  const ok = await props.actions.addCourse({ ...newCourse.value });
  if (ok) {
    newCourse.value = { title: '', institution: '', completion_date: '', hours: '' };
    showCourseForm.value = false;
  }
}

function startEditCourse(c) {
  editingCourseId.value = c.id;
  editCourse.value = { title: c.title, institution: c.institution || '', completion_date: c.completion_date || '', hours: c.hours || '' };
}

async function onSaveCourse(id) {
  editSaving.value = true;
  const ok = await props.actions.saveCourse(id, { ...editCourse.value });
  if (ok) editingCourseId.value = null;
  editSaving.value = false;
}

async function onRemoveCourse(c) {
  const ok = await props.actions.removeCourse(c);
  if (ok) deletingId.value = null;
}

// ─── Certificaciones ───────────────────────────────────────────────────────
const showCertForm = ref(false);
const newCert = ref({ name: '', issuing_organization: '', issue_date: '', expiration_date: '', credential_id: '' });
const editingCertId = ref(null);
const editCert = ref({});

async function onAddCert() {
  const ok = await props.actions.addCert({ ...newCert.value });
  if (ok) {
    newCert.value = { name: '', issuing_organization: '', issue_date: '', expiration_date: '', credential_id: '' };
    showCertForm.value = false;
  }
}

function startEditCert(cert) {
  editingCertId.value = cert.id;
  editCert.value = { name: cert.name, issuing_organization: cert.issuing_organization || '', issue_date: cert.issue_date || '', expiration_date: cert.expiration_date || '', credential_id: cert.credential_id || '' };
}

async function onSaveCert(id) {
  editSaving.value = true;
  const ok = await props.actions.saveCert(id, { ...editCert.value });
  if (ok) editingCertId.value = null;
  editSaving.value = false;
}

async function onRemoveCert(cert) {
  const ok = await props.actions.removeCert(cert);
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
