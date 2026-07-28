<template>
  <CustomerAccountShell max-width="900px">
    <!-- ═══ ONBOARDING HUB — pantalla de entrada (estado/requisitos/progreso) ═══ -->
    <template v-if="showHub">
      <CustomerPageHeader
        title="Solicitar cuenta como Asociado de Negocio"
        subtitle="Convierte tu cuenta en un Asociado de Negocio de Sintel y ofrece tus servicios profesionales en el marketplace."
      />

      <CustomerSkeleton v-if="loadingHub" :count="3" height="120px" />
      <template v-else>
        <CustomerSection title="Estado actual" icon="bi-flag">
          <CustomerDetailRow label="Estado de la solicitud" icon="bi-hourglass-split">
            <span class="badge" :class="hubStatusClass">{{ hubStatusLabel }}</span>
          </CustomerDetailRow>
          <CustomerDetailRow v-if="verification?.requested_user_type" label="Tipo solicitado" icon="bi-briefcase">
            {{ typeLabelOf(verification.requested_user_type) }}
          </CustomerDetailRow>
        </CustomerSection>

        <CustomerSection title="Progreso" icon="bi-bar-chart-steps">
          <StatusTimeline mode="steps" :steps="hubSteps" :active-index="hubActiveIndex" accent-color="#7c3aed" />
        </CustomerSection>

        <CustomerSection title="Requisitos y Documentacion" icon="bi-file-earmark-check">
          <p class="text-muted small mb-3">Estos son los 5 documentos que se solicitan para verificar tu identidad y experiencia.</p>
          <div class="doc-req-list">
            <div v-for="doc in requiredDocs" :key="doc.type" class="doc-req-row">
              <i class="bi" :class="isDocUploaded(doc.type) ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'"></i>
              <span>{{ doc.label }}</span>
              <span v-if="isDocUploaded(doc.type)" class="badge bg-success-subtle text-success ms-auto">Enviado</span>
              <span v-else class="badge bg-secondary-subtle text-secondary ms-auto">Pendiente</span>
            </div>
          </div>
        </CustomerSection>

        <CustomerSection v-if="verification?.admin_message" title="Observaciones del administrador" icon="bi-chat-square-text">
          <p class="small mb-0">{{ verification.admin_message }}</p>
        </CustomerSection>

        <CustomerSection title="Pasos pendientes" icon="bi-list-check">
          <ul class="pending-steps mb-0">
            <li v-for="(step, i) in pendingSteps" :key="i">{{ step }}</li>
          </ul>
          <p v-if="!pendingSteps.length" class="text-success small mb-0">
            <i class="bi bi-check-circle-fill me-1"></i>No tienes pasos pendientes por ahora.
          </p>
        </CustomerSection>

        <div class="d-flex justify-content-end mt-4">
          <CustomerButton v-if="hubPrimaryAction" variant="primary" size="md" @click="hubPrimaryAction.handler">
            {{ hubPrimaryAction.label }}
          </CustomerButton>
        </div>
      </template>
    </template>

    <!-- ═══ WIZARD DE 4 PASOS — sin cambios de logica, solo re-empaquetado ═══ -->
    <template v-else>
      <div class="mb-4">
        <h1 class="h3 fw-bold mb-1">Solicitar cuenta como Asociado de Negocio</h1>
        <p class="text-muted">Completa tu informacion para aparecer en el marketplace de asociados de negocio</p>
      </div>

      <!-- Progreso -->
      <div class="step-progress mb-4">
        <div
          v-for="(s, i) in steps"
          :key="i"
          class="step-item"
          :class="{ active: currentStep === i, done: currentStep > i }"
        >
          <div class="step-circle">
            <i v-if="currentStep > i" class="bi bi-check2"></i>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <span class="step-label d-none d-md-block">{{ s.label }}</span>
        </div>
      </div>
      <div class="progress mb-5" style="height:3px;border-radius:2px">
        <div class="progress-bar bg-primary" :style="{ width: (currentStep / (steps.length - 1) * 100) + '%' }"></div>
      </div>

      <!-- ═══ STEP 1: Info profesional ═══ -->
      <div v-if="currentStep === 0" class="step-card">
        <h5 class="fw-bold mb-4">Informacion profesional</h5>
        <div class="row g-3">

          <div class="col-sm-6" v-if="needsTypeSelection">
            <label class="form-label small fw-bold">Tipo de profesional <span class="text-danger">*</span></label>
            <select v-model="step1.user_type" class="form-select">
              <option value="">Selecciona...</option>
              <option value="TECHNICIAN">Tecnico</option>
              <option value="PROFESSIONAL">Profesional</option>
              <option value="SPECIALIST">Especialista</option>
              <option value="CONTRACTOR">Contratista</option>
            </select>
          </div>
          <div class="col-sm-6" v-else-if="upgradeAlreadyRequested">
            <label class="form-label small fw-bold">Tipo de profesional solicitado</label>
            <div class="form-control-plaintext">
              {{ verification?.requested_user_type }}
              <span class="badge bg-warning-subtle text-warning ms-1">{{ verification?.status }}</span>
            </div>
          </div>

          <div class="col-sm-6">
            <label class="form-label small fw-bold">Tipo de contratista</label>
            <input v-model="step1.contractor_type" type="text" class="form-control" placeholder="Ej: Electricista residencial">
          </div>

          <div class="col-12">
            <label class="form-label small fw-bold">Biografia / Presentacion</label>
            <textarea v-model="step1.bio" class="form-control" rows="4" placeholder="Describe tu experiencia y lo que ofreces..."></textarea>
          </div>

          <div class="col-sm-6">
            <label class="form-label small fw-bold">Tipo de documento</label>
            <select v-model="step1.document_type" class="form-select">
              <option value="">Selecciona...</option>
              <option value="CC">Cedula de Ciudadania</option>
              <option value="CE">Cedula de Extranjeria</option>
              <option value="NIT">NIT</option>
              <option value="PP">Pasaporte</option>
            </select>
          </div>

          <div class="col-sm-6">
            <label class="form-label small fw-bold">Numero de documento</label>
            <input v-model="step1.document" type="text" class="form-control">
          </div>

          <div class="col-sm-6">
            <label class="form-label small fw-bold">Fecha de nacimiento</label>
            <input v-model="step1.birth_date" type="date" class="form-control">
          </div>

          <div class="col-sm-6">
            <label class="form-label small fw-bold">Ciudad</label>
            <input v-model="step1.city" type="text" class="form-control">
          </div>

          <div class="col-sm-6">
            <label class="form-label small fw-bold">Pais</label>
            <input v-model="step1.country" type="text" class="form-control" placeholder="Colombia">
          </div>

          <div class="col-12"><hr class="my-1"></div>

          <div class="col-sm-4">
            <label class="form-label small fw-bold">Tarifa por hora (COP)</label>
            <input v-model="step1.hourly_rate" type="number" class="form-control" placeholder="0" min="0">
          </div>

          <div class="col-sm-4">
            <label class="form-label small fw-bold">Tarifa por dia (COP)</label>
            <input v-model="step1.daily_rate" type="number" class="form-control" placeholder="0" min="0">
          </div>

          <div class="col-sm-4">
            <label class="form-label small fw-bold">Tarifa por proyecto (COP)</label>
            <input v-model="step1.project_rate" type="number" class="form-control" placeholder="0" min="0">
          </div>

          <div class="col-sm-4">
            <label class="form-label small fw-bold">Moneda</label>
            <select v-model="step1.currency" class="form-select">
              <option value="COP">COP</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="MXN">MXN</option>
            </select>
          </div>

        </div>
      </div>

      <!-- ═══ STEP 2: Habilidades y especialidades ═══ -->
      <div v-if="currentStep === 1" class="step-card">
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
              @click="addSpecialty"
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
                <button type="button" class="btn btn-danger btn-xs" @click="removeSpecialty(sp)">Si</button>
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
                <input v-model="newSkill.name" type="text" class="form-control form-control-sm" placeholder="Nombre de la habilidad" @keyup.enter="addSkill">
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
                <button type="button" class="btn btn-primary btn-sm" :disabled="!newSkill.name" @click="addSkill">
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
                  <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveSkill(sk.id)">
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
                <button type="button" class="btn btn-danger btn-sm" @click="removeSkill(sk)">Eliminar</button>
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

      <!-- ═══ STEP 3: Formacion y certificaciones ═══ -->
      <div v-if="currentStep === 2" class="step-card">
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
                  <button type="button" class="btn btn-primary btn-sm" @click="addAcademic">Guardar</button>
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
                    <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveAcademic(a.id)">
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
                <button type="button" class="btn btn-danger btn-sm" @click="removeAcademic(a)">Eliminar</button>
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
                <button type="button" class="btn btn-primary btn-sm" @click="addCourse">Guardar</button>
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
                  <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveCourse(c.id)">
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
                <button type="button" class="btn btn-danger btn-sm" @click="removeCourse(c)">Eliminar</button>
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
                <button type="button" class="btn btn-primary btn-sm" @click="addCert">Guardar</button>
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
                  <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveCert(cert.id)">
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
                <button type="button" class="btn btn-danger btn-sm" @click="removeCert(cert)">Eliminar</button>
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

      <!-- ═══ STEP 4: Experiencia y portafolio ═══ -->
      <div v-if="currentStep === 3" class="step-card">
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
                <button type="button" class="btn btn-primary btn-sm" @click="addExperience">Guardar</button>
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
                  <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveExperience(exp.id)">
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
                <button type="button" class="btn btn-danger btn-sm" @click="removeExperience(exp)">Eliminar</button>
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
                <button type="button" class="btn btn-primary btn-sm" @click="addCase">Guardar</button>
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
                  <button type="button" class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveCase(sc.id)">
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
                <button type="button" class="btn btn-danger btn-sm" @click="removeCase(sc)">Eliminar</button>
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

      <!-- Navegacion -->
      <div class="d-flex justify-content-between align-items-center mt-4">
        <button v-if="currentStep > 0" type="button" class="btn btn-light px-4" @click="currentStep--">
          <i class="bi bi-chevron-left me-1"></i>Anterior
        </button>
        <span v-else></span>

        <button
          v-if="currentStep < steps.length - 1"
          type="button"
          class="btn btn-primary px-4"
          :disabled="saving"
          @click="nextStep"
        >
          <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
          Siguiente <i class="bi bi-chevron-right ms-1"></i>
        </button>
        <button
          v-else
          type="button"
          class="btn btn-success px-4"
          :disabled="saving"
          @click="nextStep"
        >
          <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-check2 me-1"></i>Finalizar perfil
        </button>
      </div>
    </template>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import StatusTimeline from '@/components/shared/StatusTimeline.vue';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerSection from '@/components/customer/account/CustomerSection.vue';
import CustomerDetailRow from '@/components/customer/account/CustomerDetailRow.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

const api    = useApi();
const toast  = useToast();
const { handleError } = useErrorHandler();
const router = useRouter();

// ─── Onboarding hub (pantalla de entrada) ──────────────────────────────────
const showHub = ref(true);
const loadingHub = ref(true);

const REQUIRED_DOCS = [
  { type: 'CEDULA_FRONTAL', label: 'Cedula - frente' },
  { type: 'CEDULA_REVERSO', label: 'Cedula - reverso' },
  { type: 'RUT', label: 'RUT' },
  { type: 'HOJA_VIDA', label: 'Hoja de vida' },
  { type: 'DIPLOMA', label: 'Diploma o certificado' },
];
const requiredDocs = REQUIRED_DOCS;

function isDocUploaded(docType) {
  return !!verification.value?.documents?.some(d => d.doc_type === docType && d.status !== 'REJECTED');
}

const TYPE_LABELS = { TECHNICIAN: 'Tecnico', PROFESSIONAL: 'Profesional', SPECIALIST: 'Especialista', CONTRACTOR: 'Contratista' };
function typeLabelOf(t) { return TYPE_LABELS[t] || t || ''; }

const hubSteps = [
  { key: 'request', label: 'Solicitud enviada', icon: 'bi-send' },
  { key: 'documents', label: 'Documentos', icon: 'bi-file-earmark-text' },
  { key: 'review', label: 'En revision', icon: 'bi-hourglass-split' },
  { key: 'approved', label: 'Aprobado', icon: 'bi-patch-check' },
];

const hubActiveIndex = computed(() => {
  if (isAlreadyProfessional.value) return 3;
  if (!upgradeAlreadyRequested.value) return 0;
  const status = verification.value?.status;
  if (status === 'APPROVED') return 3;
  if (status === 'UNDER_REVIEW') return 2;
  const allUploaded = REQUIRED_DOCS.every(d => isDocUploaded(d.type));
  return allUploaded ? 2 : 1;
});

const hubStatusLabel = computed(() => {
  if (isAlreadyProfessional.value) return 'Ya eres Asociado de Negocio';
  if (!upgradeAlreadyRequested.value) return 'Aun no has iniciado tu solicitud';
  const status = verification.value?.status;
  if (status === 'APPROVED') return 'Aprobado';
  if (status === 'UNDER_REVIEW') return 'En revision';
  if (status === 'REJECTED') return 'Rechazado - revisa las observaciones';
  if (status === 'BLOCKED') return 'Bloqueado';
  return 'Pendiente de documentacion';
});

const hubStatusClass = computed(() => {
  if (isAlreadyProfessional.value || verification.value?.status === 'APPROVED') return 'bg-success-subtle text-success';
  if (verification.value?.status === 'REJECTED' || verification.value?.status === 'BLOCKED') return 'bg-danger-subtle text-danger';
  if (upgradeAlreadyRequested.value) return 'bg-warning-subtle text-warning';
  return 'bg-secondary-subtle text-secondary';
});

const pendingSteps = computed(() => {
  if (isAlreadyProfessional.value) return [];
  if (!upgradeAlreadyRequested.value) return ['Inicia tu solicitud completando tu informacion profesional.'];
  const steps = [];
  const missing = REQUIRED_DOCS.filter(d => !isDocUploaded(d.type));
  if (missing.length) steps.push(`Sube ${missing.length} documento(s) pendiente(s): ${missing.map(d => d.label).join(', ')}.`);
  if (!missing.length && verification.value?.status !== 'UNDER_REVIEW' && verification.value?.status !== 'APPROVED') {
    steps.push('Envia tu documentacion a revision desde Verificacion de identidad.');
  }
  if (verification.value?.status === 'UNDER_REVIEW') steps.push('Espera la revision del equipo Sintel.');
  return steps;
});

const hubPrimaryAction = computed(() => {
  if (isAlreadyProfessional.value) {
    return { label: 'Editar mi perfil profesional', handler: () => { showHub.value = false; } };
  }
  if (!upgradeAlreadyRequested.value) {
    return { label: 'Iniciar solicitud', handler: () => { showHub.value = false; } };
  }
  const allUploaded = REQUIRED_DOCS.every(d => isDocUploaded(d.type));
  if (!allUploaded) {
    return { label: 'Continuar solicitud', handler: () => { showHub.value = false; } };
  }
  if (verification.value?.status !== 'APPROVED') {
    return { label: 'Ir a subir documentos', handler: () => router.push({ name: 'kyc-verification' }) };
  }
  return null;
});

const currentStep = ref(0);
const saving      = ref(false);
const editSaving  = ref(false);
const deletingId  = ref(null); // clave unica: 'sp-1', 'sk-2', 'ac-3', etc.

const steps = [
  { label: 'Info' },
  { label: 'Habilidades' },
  { label: 'Formacion' },
  { label: 'Portafolio' },
];

// ─── Step 1 ───────────────────────────────────────────────────────────────────
const step1 = ref({
  user_type: '', bio: '', contractor_type: '',
  document_type: '', document: '', birth_date: '',
  city: '', country: '',
  hourly_rate: '', daily_rate: '', project_rate: '', currency: 'COP',
});
// KYC de la cuenta -- si ya tiene requested_user_type, el upgrade ya se pidio
// (KycCommands.request_upgrade) y no se debe volver a solicitar; se muestra
// el estado en vez del selector de tipo. `originalUserType` distingue a un
// profesional YA aprobado (editando su perfil) de un CUSTOMER pidiendo un
// upgrade -- solo el segundo caso dispara request-upgrade.
const SERVICE_PROVIDER_VALUES = ['TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR'];
const verification = ref(null);
const originalUserType = ref('');
const upgradeAlreadyRequested = computed(() => !!verification.value?.requested_user_type);
const isAlreadyProfessional = computed(() => SERVICE_PROVIDER_VALUES.includes(originalUserType.value));
const needsTypeSelection = computed(() => !isAlreadyProfessional.value && !upgradeAlreadyRequested.value);

// ─── Step 2 ───────────────────────────────────────────────────────────────────
const categories       = ref([]);
const specialties      = ref([]);
const skills           = ref([]);
const newSpecialtyId   = ref('');
const addingSpecialty  = ref(false);
const newSkill         = ref({ name: '', level: '' });
const editingSkillId   = ref(null);
const editSkill        = ref({ name: '', level: '' });

// ─── Step 3 ───────────────────────────────────────────────────────────────────
const academics        = ref([]);
const courses          = ref([]);
const certifications   = ref([]);
const showAcademicForm = ref(false);
const showCourseForm   = ref(false);
const showCertForm     = ref(false);
const newAcademic      = ref({ institution: '', degree: '', field_of_study: '', start_date: '', end_date: '', is_current: false });
const newCourse        = ref({ title: '', institution: '', completion_date: '', hours: '' });
const newCert          = ref({ name: '', issuing_organization: '', issue_date: '', expiration_date: '', credential_id: '' });
const editingAcademicId = ref(null);
const editingCourseId   = ref(null);
const editingCertId     = ref(null);
const editAcademic     = ref({});
const editCourse       = ref({});
const editCert         = ref({});

// ─── Step 4 ───────────────────────────────────────────────────────────────────
const experiences    = ref([]);
const successCases   = ref([]);
const showExpForm    = ref(false);
const showCaseForm   = ref(false);
const newExp         = ref({ company: '', position: '', description: '', start_date: '', end_date: '', is_current: false });
const newCase        = ref({ title: '', description: '', completion_date: '' });
const editingExpId   = ref(null);
const editingCaseId  = ref(null);
const editExp        = ref({});
const editCase       = ref({});

// Categorias filtradas: excluir las ya agregadas como especialidad
const availableCategories = computed(() => {
  const usedIds = new Set(specialties.value.map(sp => sp.category?.id));
  return categories.value.filter(cat => !usedIds.has(cat.id));
});

function truncate(s, n) { return (s || '').length > n ? s.slice(0, n) + '...' : (s || ''); }

// ─── Carga inicial ─────────────────────────────────────────────────────────────
async function loadInitialData() {
  try {
    const [profileRes, verRes, catRes] = await Promise.all([
      api.get('auth/profile/'),
      api.get('auth/verification/'),
      api.get('services/categories/'),
    ]);

    const p = profileRes.data?.profile || {};
    originalUserType.value = p.user_type || '';
    verification.value = verRes.data;
    categories.value = catRes.data?.results ?? catRes.data ?? [];
    loadingHub.value = false;

    step1.value = {
      user_type:      p.user_type || '',
      bio:            p.bio || '',
      contractor_type: p.contractor_type || '',
      document_type:  p.document_type || '',
      document:       p.document || '',
      birth_date:     p.birth_date || '',
      city:           p.city || '',
      country:        p.country || '',
      hourly_rate:    p.hourly_rate || '',
      daily_rate:     p.daily_rate || '',
      project_rate:   p.project_rate || '',
      currency:       p.currency || 'COP',
    };

    // Las 7 secciones de CV (specialties/skills/academic-training/courses/
    // certifications/experiences/success-cases) estan gateadas por
    // IsServiceProviderOrUpgrading -- un CUSTOMER que aun no solicito su
    // upgrade (needsTypeSelection) no tiene acceso todavia, y tampoco tiene
    // nada que cargar (recien esta empezando el wizard).
    if (!needsTypeSelection.value) {
      const [spRes, skillsRes, acaRes, courseRes, certRes, expRes, caseRes] = await Promise.all([
        api.get('auth/specialties/'),
        api.get('auth/skills/'),
        api.get('auth/academic-training/'),
        api.get('auth/courses/'),
        api.get('auth/certifications/'),
        api.get('auth/experiences/'),
        api.get('auth/success-cases/'),
      ]);
      specialties.value    = spRes.data?.results   ?? spRes.data   ?? [];
      skills.value         = skillsRes.data?.results ?? skillsRes.data ?? [];
      academics.value      = acaRes.data?.results  ?? acaRes.data  ?? [];
      courses.value        = courseRes.data?.results ?? courseRes.data ?? [];
      certifications.value = certRes.data?.results ?? certRes.data ?? [];
      experiences.value    = expRes.data?.results  ?? expRes.data  ?? [];
      successCases.value   = caseRes.data?.results ?? caseRes.data ?? [];
    }
  } catch {
    toast.error('Error al cargar los datos del perfil');
  } finally {
    loadingHub.value = false;
  }
}

// ─── Step 1 save ──────────────────────────────────────────────────────────────
async function saveStep1() {
  if (needsTypeSelection.value) {
    if (!step1.value.user_type) {
      throw new Error('Selecciona el tipo de profesional.');
    }
    const { data } = await api.post('auth/request-upgrade/', {
      requested_user_type: step1.value.user_type,
    });
    verification.value = data;
  }

  const payload = {};
  Object.entries(step1.value).forEach(([k, v]) => {
    if (k === 'user_type') return; // ya no se envia via profile -- ver request-upgrade arriba
    if (v !== '' && v !== null && v !== undefined) payload[k] = v;
  });
  await api.patch('auth/profile/', payload);
}

// ─── Especialidades ───────────────────────────────────────────────────────────
async function addSpecialty() {
  if (!newSpecialtyId.value) return;
  addingSpecialty.value = true;
  try {
    const { data } = await api.post('auth/specialties/', { category_id: Number(newSpecialtyId.value) });
    specialties.value.push(data);
    newSpecialtyId.value = '';
  } catch (e) {
    handleError(e, 'Error al agregar especialidad');
  } finally {
    addingSpecialty.value = false;
  }
}

async function removeSpecialty(sp) {
  try {
    await api.delete(`auth/specialties/${sp.id}/`);
    specialties.value = specialties.value.filter(s => s.id !== sp.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar especialidad'); }
}

// ─── Habilidades ──────────────────────────────────────────────────────────────
async function addSkill() {
  if (!newSkill.value.name.trim()) return;
  try {
    const { data } = await api.post('auth/skills/', { name: newSkill.value.name.trim(), level: newSkill.value.level });
    skills.value.push(data);
    newSkill.value = { name: '', level: '' };
  } catch (e) { handleError(e, 'Error al agregar habilidad'); }
}

function startEditSkill(sk) {
  editingSkillId.value = sk.id;
  editSkill.value = { name: sk.name, level: sk.level || '' };
}

async function saveSkill(id) {
  editSaving.value = true;
  try {
    const { data } = await api.patch(`auth/skills/${id}/`, { name: editSkill.value.name, level: editSkill.value.level });
    const idx = skills.value.findIndex(x => x.id === id);
    if (idx >= 0) skills.value[idx] = data;
    editingSkillId.value = null;
    toast.success('Habilidad actualizada');
  } catch { toast.error('Error al actualizar'); }
  finally { editSaving.value = false; }
}

async function removeSkill(sk) {
  try {
    await api.delete(`auth/skills/${sk.id}/`);
    skills.value = skills.value.filter(s => s.id !== sk.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar'); }
}

// ─── Formacion academica ──────────────────────────────────────────────────────
async function addAcademic() {
  if (!newAcademic.value.institution || !newAcademic.value.degree || !newAcademic.value.start_date) {
    toast.error('Completa: institucion, titulo y fecha de inicio');
    return;
  }
  try {
    const { data } = await api.post('auth/academic-training/', newAcademic.value);
    academics.value.push(data);
    newAcademic.value = { institution: '', degree: '', field_of_study: '', start_date: '', end_date: '', is_current: false };
    showAcademicForm.value = false;
  } catch (e) { handleError(e, 'Error al guardar'); }
}

function startEditAcademic(a) {
  editingAcademicId.value = a.id;
  editAcademic.value = { institution: a.institution, degree: a.degree, field_of_study: a.field_of_study || '', start_date: a.start_date || '', end_date: a.end_date || '', is_current: a.is_current };
}

async function saveAcademic(id) {
  editSaving.value = true;
  try {
    const { data } = await api.patch(`auth/academic-training/${id}/`, editAcademic.value);
    const idx = academics.value.findIndex(x => x.id === id);
    if (idx >= 0) academics.value[idx] = data;
    editingAcademicId.value = null;
    toast.success('Actualizado');
  } catch { toast.error('Error al actualizar'); }
  finally { editSaving.value = false; }
}

async function removeAcademic(a) {
  try {
    await api.delete(`auth/academic-training/${a.id}/`);
    academics.value = academics.value.filter(x => x.id !== a.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar'); }
}

// ─── Cursos ───────────────────────────────────────────────────────────────────
async function addCourse() {
  if (!newCourse.value.title || !newCourse.value.completion_date) {
    toast.error('Completa nombre y fecha de finalizacion');
    return;
  }
  try {
    const { data } = await api.post('auth/courses/', newCourse.value);
    courses.value.push(data);
    newCourse.value = { title: '', institution: '', completion_date: '', hours: '' };
    showCourseForm.value = false;
  } catch (e) { handleError(e, 'Error al guardar'); }
}

function startEditCourse(c) {
  editingCourseId.value = c.id;
  editCourse.value = { title: c.title, institution: c.institution || '', completion_date: c.completion_date || '', hours: c.hours || '' };
}

async function saveCourse(id) {
  editSaving.value = true;
  try {
    const { data } = await api.patch(`auth/courses/${id}/`, editCourse.value);
    const idx = courses.value.findIndex(x => x.id === id);
    if (idx >= 0) courses.value[idx] = data;
    editingCourseId.value = null;
    toast.success('Actualizado');
  } catch { toast.error('Error al actualizar'); }
  finally { editSaving.value = false; }
}

async function removeCourse(c) {
  try {
    await api.delete(`auth/courses/${c.id}/`);
    courses.value = courses.value.filter(x => x.id !== c.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar'); }
}

// ─── Certificaciones ──────────────────────────────────────────────────────────
async function addCert() {
  if (!newCert.value.name || !newCert.value.issue_date) {
    toast.error('Completa nombre y fecha de emision');
    return;
  }
  try {
    const { data } = await api.post('auth/certifications/', newCert.value);
    certifications.value.push(data);
    newCert.value = { name: '', issuing_organization: '', issue_date: '', expiration_date: '', credential_id: '' };
    showCertForm.value = false;
  } catch (e) { handleError(e, 'Error al guardar'); }
}

function startEditCert(cert) {
  editingCertId.value = cert.id;
  editCert.value = { name: cert.name, issuing_organization: cert.issuing_organization || '', issue_date: cert.issue_date || '', expiration_date: cert.expiration_date || '', credential_id: cert.credential_id || '' };
}

async function saveCert(id) {
  editSaving.value = true;
  try {
    const { data } = await api.patch(`auth/certifications/${id}/`, editCert.value);
    const idx = certifications.value.findIndex(x => x.id === id);
    if (idx >= 0) certifications.value[idx] = data;
    editingCertId.value = null;
    toast.success('Actualizado');
  } catch { toast.error('Error al actualizar'); }
  finally { editSaving.value = false; }
}

async function removeCert(cert) {
  try {
    await api.delete(`auth/certifications/${cert.id}/`);
    certifications.value = certifications.value.filter(x => x.id !== cert.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar'); }
}

// ─── Experiencia ──────────────────────────────────────────────────────────────
async function addExperience() {
  if (!newExp.value.company || !newExp.value.position || !newExp.value.start_date) {
    toast.error('Completa empresa, cargo y fecha de inicio');
    return;
  }
  try {
    const { data } = await api.post('auth/experiences/', newExp.value);
    experiences.value.push(data);
    newExp.value = { company: '', position: '', description: '', start_date: '', end_date: '', is_current: false };
    showExpForm.value = false;
  } catch (e) { handleError(e, 'Error al guardar'); }
}

function startEditExperience(exp) {
  editingExpId.value = exp.id;
  editExp.value = { company: exp.company, position: exp.position, description: exp.description || '', start_date: exp.start_date || '', end_date: exp.end_date || '', is_current: exp.is_current };
}

async function saveExperience(id) {
  editSaving.value = true;
  try {
    const { data } = await api.patch(`auth/experiences/${id}/`, editExp.value);
    const idx = experiences.value.findIndex(x => x.id === id);
    if (idx >= 0) experiences.value[idx] = data;
    editingExpId.value = null;
    toast.success('Actualizado');
  } catch { toast.error('Error al actualizar'); }
  finally { editSaving.value = false; }
}

async function removeExperience(exp) {
  try {
    await api.delete(`auth/experiences/${exp.id}/`);
    experiences.value = experiences.value.filter(x => x.id !== exp.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar'); }
}

// ─── Casos de exito ───────────────────────────────────────────────────────────
async function addCase() {
  if (!newCase.value.title || !newCase.value.description) {
    toast.error('Completa titulo y descripcion');
    return;
  }
  try {
    const { data } = await api.post('auth/success-cases/', newCase.value);
    successCases.value.push(data);
    newCase.value = { title: '', description: '', completion_date: '' };
    showCaseForm.value = false;
  } catch (e) { handleError(e, 'Error al guardar'); }
}

function startEditCase(sc) {
  editingCaseId.value = sc.id;
  editCase.value = { title: sc.title, description: sc.description || '', completion_date: sc.completion_date || '' };
}

async function saveCase(id) {
  editSaving.value = true;
  try {
    const { data } = await api.patch(`auth/success-cases/${id}/`, editCase.value);
    const idx = successCases.value.findIndex(x => x.id === id);
    if (idx >= 0) successCases.value[idx] = data;
    editingCaseId.value = null;
    toast.success('Actualizado');
  } catch { toast.error('Error al actualizar'); }
  finally { editSaving.value = false; }
}

async function removeCase(sc) {
  try {
    await api.delete(`auth/success-cases/${sc.id}/`);
    successCases.value = successCases.value.filter(x => x.id !== sc.id);
    deletingId.value = null;
  } catch { toast.error('Error al eliminar'); }
}

// ─── Navegacion entre pasos ───────────────────────────────────────────────────
async function nextStep() {
  saving.value = true;
  try {
    if (currentStep.value === 0) {
      await saveStep1();
      toast.success('Informacion profesional guardada');
    }
    if (currentStep.value < steps.length - 1) {
      currentStep.value++;
      deletingId.value = null;
    } else if (isAlreadyProfessional.value) {
      toast.success('Perfil profesional actualizado');
      router.push({ name: 'contractor-marketplace' });
    } else {
      toast.success('Perfil guardado. Ahora sube tus documentos para completar la verificacion.');
      router.push({ name: 'kyc-verification' });
    }
  } catch {
    toast.error('Error al guardar. Revisa los datos e intenta de nuevo.');
  } finally {
    saving.value = false;
  }
}

onMounted(loadInitialData);
</script>

<style scoped>
/* Step bar */
.step-progress {
  display: flex;
  align-items: flex-start;
}
.step-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  gap: 6px;
  text-align: center;
}
.step-item:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 17px;
  left: calc(50% + 20px);
  right: calc(-50% + 20px);
  height: 2px;
  background: #e5e7eb;
  z-index: 0;
}
.step-item.done:not(:last-child)::after { background: #1e3a8a; }
.step-circle {
  width: 36px; height: 36px;
  border-radius: 50%;
  border: 2px solid #e5e7eb;
  background: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: .85rem;
  color: #9ca3af;
  position: relative; z-index: 1;
  transition: all .2s;
}
.step-item.active .step-circle { border-color: #1e3a8a; color: #1e3a8a; background: #eff6ff; box-shadow: 0 0 0 4px rgba(30,58,138,.1); }
.step-item.done .step-circle   { border-color: #1e3a8a; background: #1e3a8a; color: #fff; }
.step-label { font-size: .72rem; color: #6b7280; }
.step-item.active .step-label  { color: #1e3a8a; font-weight: 600; }
.step-item.done .step-label    { color: #1e3a8a; }

/* Card de cada paso */
.step-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 28px;
}

/* Encabezado de cada seccion */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f3f4f6;
}

/* Tags de especialidades */
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

/* Formulario inline de agregar/editar */
.add-form {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
}

/* Items de lista */
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
