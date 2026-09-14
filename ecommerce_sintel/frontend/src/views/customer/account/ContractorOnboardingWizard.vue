<template>
  <CustomerAccountShell max-width="900px">
    <!-- ═══ ONBOARDING HUB — pantalla de entrada (estado/requisitos/progreso) ═══ -->
    <OnboardingHub
      v-if="showHub"
      :loading="loadingHub"
      :verification="verification"
      :is-already-professional="isAlreadyProfessional"
      :upgrade-already-requested="upgradeAlreadyRequested"
      @start="showHub = false"
    />

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

      <Step1Info
        v-if="currentStep === 0"
        :form="step1"
        :needs-type-selection="needsTypeSelection"
        :upgrade-already-requested="upgradeAlreadyRequested"
        :verification="verification"
      />
      <Step2Skills
        v-if="currentStep === 1"
        :categories="categories"
        :specialties="specialties"
        :skills="skills"
        :actions="step2Actions"
      />
      <Step3Training
        v-if="currentStep === 2"
        :academics="academics"
        :courses="courses"
        :certifications="certifications"
        :actions="step3Actions"
      />
      <Step4Portfolio
        v-if="currentStep === 3"
        :experiences="experiences"
        :success-cases="successCases"
        :actions="step4Actions"
      />

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
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import OnboardingHub from './contractor-onboarding/OnboardingHub.vue';
import Step1Info from './contractor-onboarding/Step1Info.vue';
import Step2Skills from './contractor-onboarding/Step2Skills.vue';
import Step3Training from './contractor-onboarding/Step3Training.vue';
import Step4Portfolio from './contractor-onboarding/Step4Portfolio.vue';

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

function isDocUploaded(docType) {
  return !!verification.value?.documents?.some(d => d.doc_type === docType && d.status !== 'REJECTED');
}

const currentStep = ref(0);
const saving      = ref(false);

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

// ─── Datos de las 7 secciones de CV (arrays fetched una sola vez, viven aqui
// para sobrevivir la navegacion entre pasos ya que cada Step usa v-if) ──────
const categories       = ref([]);
const specialties      = ref([]);
const skills           = ref([]);
const academics        = ref([]);
const courses          = ref([]);
const certifications   = ref([]);
const experiences      = ref([]);
const successCases     = ref([]);

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
async function addSpecialty(categoryId) {
  try {
    const { data } = await api.post('auth/specialties/', { category_id: Number(categoryId) });
    specialties.value.push(data);
    return true;
  } catch (e) {
    handleError(e, 'Error al agregar especialidad');
    return false;
  }
}

async function removeSpecialty(sp) {
  try {
    await api.delete(`auth/specialties/${sp.id}/`);
    specialties.value = specialties.value.filter(s => s.id !== sp.id);
    return true;
  } catch { toast.error('Error al eliminar especialidad'); return false; }
}

// ─── Habilidades ──────────────────────────────────────────────────────────────
async function addSkill(payload) {
  try {
    const { data } = await api.post('auth/skills/', payload);
    skills.value.push(data);
    return true;
  } catch (e) { handleError(e, 'Error al agregar habilidad'); return false; }
}

async function saveSkill(id, payload) {
  try {
    const { data } = await api.patch(`auth/skills/${id}/`, payload);
    const idx = skills.value.findIndex(x => x.id === id);
    if (idx >= 0) skills.value[idx] = data;
    toast.success('Habilidad actualizada');
    return true;
  } catch { toast.error('Error al actualizar'); return false; }
}

async function removeSkill(sk) {
  try {
    await api.delete(`auth/skills/${sk.id}/`);
    skills.value = skills.value.filter(s => s.id !== sk.id);
    return true;
  } catch { toast.error('Error al eliminar'); return false; }
}

const step2Actions = { addSpecialty, removeSpecialty, addSkill, saveSkill, removeSkill };

// ─── Formacion academica ──────────────────────────────────────────────────────
async function addAcademic(payload) {
  if (!payload.institution || !payload.degree || !payload.start_date) {
    toast.error('Completa: institucion, titulo y fecha de inicio');
    return false;
  }
  try {
    const { data } = await api.post('auth/academic-training/', payload);
    academics.value.push(data);
    return true;
  } catch (e) { handleError(e, 'Error al guardar'); return false; }
}

async function saveAcademic(id, payload) {
  try {
    const { data } = await api.patch(`auth/academic-training/${id}/`, payload);
    const idx = academics.value.findIndex(x => x.id === id);
    if (idx >= 0) academics.value[idx] = data;
    toast.success('Actualizado');
    return true;
  } catch { toast.error('Error al actualizar'); return false; }
}

async function removeAcademic(a) {
  try {
    await api.delete(`auth/academic-training/${a.id}/`);
    academics.value = academics.value.filter(x => x.id !== a.id);
    return true;
  } catch { toast.error('Error al eliminar'); return false; }
}

// ─── Cursos ───────────────────────────────────────────────────────────────────
async function addCourse(payload) {
  if (!payload.title || !payload.completion_date) {
    toast.error('Completa nombre y fecha de finalizacion');
    return false;
  }
  try {
    const { data } = await api.post('auth/courses/', payload);
    courses.value.push(data);
    return true;
  } catch (e) { handleError(e, 'Error al guardar'); return false; }
}

async function saveCourse(id, payload) {
  try {
    const { data } = await api.patch(`auth/courses/${id}/`, payload);
    const idx = courses.value.findIndex(x => x.id === id);
    if (idx >= 0) courses.value[idx] = data;
    toast.success('Actualizado');
    return true;
  } catch { toast.error('Error al actualizar'); return false; }
}

async function removeCourse(c) {
  try {
    await api.delete(`auth/courses/${c.id}/`);
    courses.value = courses.value.filter(x => x.id !== c.id);
    return true;
  } catch { toast.error('Error al eliminar'); return false; }
}

// ─── Certificaciones ──────────────────────────────────────────────────────────
async function addCert(payload) {
  if (!payload.name || !payload.issue_date) {
    toast.error('Completa nombre y fecha de emision');
    return false;
  }
  try {
    const { data } = await api.post('auth/certifications/', payload);
    certifications.value.push(data);
    return true;
  } catch (e) { handleError(e, 'Error al guardar'); return false; }
}

async function saveCert(id, payload) {
  try {
    const { data } = await api.patch(`auth/certifications/${id}/`, payload);
    const idx = certifications.value.findIndex(x => x.id === id);
    if (idx >= 0) certifications.value[idx] = data;
    toast.success('Actualizado');
    return true;
  } catch { toast.error('Error al actualizar'); return false; }
}

async function removeCert(cert) {
  try {
    await api.delete(`auth/certifications/${cert.id}/`);
    certifications.value = certifications.value.filter(x => x.id !== cert.id);
    return true;
  } catch { toast.error('Error al eliminar'); return false; }
}

const step3Actions = { addAcademic, saveAcademic, removeAcademic, addCourse, saveCourse, removeCourse, addCert, saveCert, removeCert };

// ─── Experiencia ──────────────────────────────────────────────────────────────
async function addExperience(payload) {
  if (!payload.company || !payload.position || !payload.start_date) {
    toast.error('Completa empresa, cargo y fecha de inicio');
    return false;
  }
  try {
    const { data } = await api.post('auth/experiences/', payload);
    experiences.value.push(data);
    return true;
  } catch (e) { handleError(e, 'Error al guardar'); return false; }
}

async function saveExperience(id, payload) {
  try {
    const { data } = await api.patch(`auth/experiences/${id}/`, payload);
    const idx = experiences.value.findIndex(x => x.id === id);
    if (idx >= 0) experiences.value[idx] = data;
    toast.success('Actualizado');
    return true;
  } catch { toast.error('Error al actualizar'); return false; }
}

async function removeExperience(exp) {
  try {
    await api.delete(`auth/experiences/${exp.id}/`);
    experiences.value = experiences.value.filter(x => x.id !== exp.id);
    return true;
  } catch { toast.error('Error al eliminar'); return false; }
}

// ─── Casos de exito ───────────────────────────────────────────────────────────
async function addCase(payload) {
  if (!payload.title || !payload.description) {
    toast.error('Completa titulo y descripcion');
    return false;
  }
  try {
    const { data } = await api.post('auth/success-cases/', payload);
    successCases.value.push(data);
    return true;
  } catch (e) { handleError(e, 'Error al guardar'); return false; }
}

async function saveCase(id, payload) {
  try {
    const { data } = await api.patch(`auth/success-cases/${id}/`, payload);
    const idx = successCases.value.findIndex(x => x.id === id);
    if (idx >= 0) successCases.value[idx] = data;
    toast.success('Actualizado');
    return true;
  } catch { toast.error('Error al actualizar'); return false; }
}

async function removeCase(sc) {
  try {
    await api.delete(`auth/success-cases/${sc.id}/`);
    successCases.value = successCases.value.filter(x => x.id !== sc.id);
    return true;
  } catch { toast.error('Error al eliminar'); return false; }
}

const step4Actions = { addExperience, saveExperience, removeExperience, addCase, saveCase, removeCase };

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
