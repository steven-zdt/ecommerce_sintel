import { ref, reactive, computed, watch } from 'vue';
import { quotesService } from '@/services/quotes/quotesService';
import { isQuestionVisible as checkQuestionVisible } from '@/utils/quoteVisibility';

const STORAGE_KEY = 'sintel:quote-wizard:v2';
const FILE_TYPES = ['IMAGE', 'FILE', 'SIGNATURE'];

const blankApplicant = () => ({
  client_name: '', client_email: '', company: '',
  document_type: 'CC', document_number: '', phone: '',
  city: '', department: '', address: '', gps_location: '',
  project_name: '', notes: '',
});

/**
 * useQuoteWizard — centraliza el estado del Constructor de Cuestionarios
 * Tecnicos en /cotizar. El cliente solo responde preguntas; nunca ve
 * precios ni calculos. El backend crea una Solicitud de Cotizacion
 * (Quotation en estado RECIBIDA) que un asesor revisa y cotiza despues.
 */
export function useQuoteWizard() {
  const step = ref(0);
  const steps = ['Destinatario', 'Plantilla', 'Equipos', 'Materiales', 'Mano de Obra', 'Resumen'];

  const categories = ref([]);
  const subcategories = ref([]);
  const templates = ref([]);
  const selectedTemplate = ref(null); // arbol completo (modules -> questions -> options)

  const applicant = reactive(blankApplicant());
  const answers = reactive({}); // { [moduleUuid]: { [questionKey]: valor } }
  const files = reactive({}); // { "moduleUuid__questionKey": File }

  const loading = ref(false);
  const submitting = ref(false);
  const error = ref('');
  const createdQuotation = ref(null);

  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
      if (saved.applicant) Object.assign(applicant, saved.applicant);
      if (saved.answers) Object.assign(answers, saved.answers);
      if (saved.templateUuid) return saved.templateUuid;
    } catch { /* borrador es una mejora progresiva */ }
    return null;
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      applicant, answers,
      templateUuid: selectedTemplate.value?.uuid || null,
    }));
  }

  function clear() {
    step.value = 0;
    selectedTemplate.value = null;
    Object.assign(applicant, blankApplicant());
    Object.keys(answers).forEach((k) => delete answers[k]);
    Object.keys(files).forEach((k) => delete files[k]);
    createdQuotation.value = null;
    localStorage.removeItem(STORAGE_KEY);
  }

  const modulesByType = (type) => selectedTemplate.value?.modules?.filter((m) => m.module_type === type) || [];

  const allQuestions = computed(() => {
    const list = [];
    for (const module of selectedTemplate.value?.modules || []) {
      for (const q of module.questions) list.push({ ...q, moduleUuid: module.uuid });
    }
    return list;
  });

  function answerFor(moduleUuid, key) {
    return answers[moduleUuid]?.[key];
  }

  function setAnswer(moduleUuid, key, value) {
    if (!answers[moduleUuid]) answers[moduleUuid] = {};
    answers[moduleUuid][key] = value;
  }

  function fileKeyFor(moduleUuid, key) {
    return `${moduleUuid}__${key}`;
  }

  // Visibilidad condicional (Fase F) -- ver frontend/src/utils/quoteVisibility.js.
  function isQuestionVisible(moduleUuid, question) {
    return checkQuestionVisible(question, answers[moduleUuid]);
  }

  async function fetchCategories() {
    try {
      const data = await quotesService.templateCategories();
      categories.value = data.results ?? data;
    } catch {
      error.value = 'No pudimos cargar las categorias.';
    }
  }

  async function fetchSubcategories(categoryUuid) {
    try {
      const data = await quotesService.templateSubcategories(categoryUuid);
      subcategories.value = data.results ?? data;
    } catch {
      subcategories.value = [];
    }
  }

  async function fetchTemplates() {
    loading.value = true;
    try {
      const data = await quotesService.templates();
      templates.value = data.results ?? data;
    } catch {
      error.value = 'No pudimos cargar las plantillas disponibles.';
    } finally {
      loading.value = false;
    }
  }

  async function selectTemplate(uuid) {
    loading.value = true;
    error.value = '';
    try {
      const data = await quotesService.templateDetail(uuid);
      selectedTemplate.value = data;
      persist();
      return true;
    } catch {
      error.value = 'No pudimos cargar esa plantilla.';
      return false;
    } finally {
      loading.value = false;
    }
  }

  function validateApplicant() {
    // Destinatario obligatorio: nombre, correo y documento de identificacion
    // (propio o de un tercero) — el backend exige lo mismo.
    return !!(
      applicant.client_name && applicant.client_email &&
      applicant.document_type && applicant.document_number
    );
  }

  function validateModuleType(type) {
    return modulesByType(type).every((module) =>
      module.questions
        .filter((q) => q.is_required && isQuestionVisible(module.uuid, q))
        .every((q) => {
          if (FILE_TYPES.includes(q.question_type)) {
            return !!files[fileKeyFor(module.uuid, q.key)];
          }
          const v = answerFor(module.uuid, q.key);
          return v !== undefined && v !== null && v !== '';
        }),
    );
  }

  async function submitQuotation() {
    if (!selectedTemplate.value) return false;
    submitting.value = true;
    error.value = '';
    try {
      const hasFiles = Object.keys(files).length > 0;
      let payload;
      if (hasFiles) {
        const form = new FormData();
        form.append('template', selectedTemplate.value.uuid);
        form.append('answers', JSON.stringify(answers));
        for (const [key, value] of Object.entries(applicant)) form.append(key, value ?? '');
        for (const [key, file] of Object.entries(files)) form.append(`file__${key}`, file);
        payload = form;
      } else {
        payload = { template: selectedTemplate.value.uuid, answers, ...applicant };
      }
      const data = await quotesService.createFromTemplate(payload);
      createdQuotation.value = data;
      localStorage.removeItem(STORAGE_KEY);
      return true;
    } catch (e) {
      const fieldErrors = e.response?.data;
      const firstFieldError = fieldErrors && typeof fieldErrors === 'object'
        ? Object.values(fieldErrors).flat()[0]
        : null;
      error.value = fieldErrors?.detail || firstFieldError || 'No pudimos enviar tu solicitud. Intenta de nuevo.';
      return false;
    } finally {
      submitting.value = false;
    }
  }

  watch([applicant, answers], persist, { deep: true });

  return {
    step, steps,
    categories, subcategories, templates, selectedTemplate, allQuestions,
    applicant, answers, files,
    loading, submitting, error, createdQuotation,
    restore, persist, clear,
    modulesByType, answerFor, setAnswer, fileKeyFor, isQuestionVisible,
    fetchCategories, fetchSubcategories, fetchTemplates, selectTemplate,
    validateApplicant, validateModuleType,
    submitQuotation,
  };
}
