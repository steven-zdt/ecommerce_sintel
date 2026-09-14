<template>
  <div>
    <p class="text-muted small mb-3">
      Configuracion comercial y visual exclusiva de este servicio -- se refleja
      automaticamente en el detalle publico. Nada de esto se comparte ni se hereda
      de otros servicios.
    </p>

    <!-- Precio comercial -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2">Precio comercial</h6>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label small">Precio de referencia (anterior)</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input v-model.number="marketingForm.reference_price" type="number" min="0" step="0.01" class="form-control" placeholder="250000">
        </div>
      </div>
      <div class="col-6">
        <label class="form-label small">Precio promocional</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input v-model.number="marketingForm.promo_price" type="number" min="0" step="0.01" class="form-control" placeholder="190000">
        </div>
      </div>
      <div class="col-12">
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" v-model="marketingForm.show_discount_percentage" id="svcMktShowDiscount">
          <label class="form-check-label small" for="svcMktShowDiscount">Mostrar porcentaje de descuento (calculado automaticamente)</label>
        </div>
        <span v-if="marketingDiscountPreview" class="badge bg-danger-subtle text-danger border border-danger-subtle mt-1">
          AHORRA {{ marketingDiscountPreview }}%
        </span>
      </div>
    </div>

    <!-- Etiquetas comerciales -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Etiquetas comerciales</h6>
    <div class="d-flex flex-wrap gap-2 mb-3">
      <button
        v-for="opt in marketingTagOptions" :key="opt.value"
        type="button"
        class="btn btn-sm"
        :class="marketingForm.tags.includes(opt.value) ? 'btn-primary' : 'btn-outline-secondary'"
        @click="toggleMarketingTag(opt.value)"
      >{{ opt.label }}</button>
    </div>

    <!-- Mensajes de conversion -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Mensajes de conversion</h6>
    <div class="row g-2 mb-3">
      <div class="col-12">
        <label class="form-label small">Mensaje principal</label>
        <textarea v-model="marketingForm.main_message" class="form-control form-control-sm" rows="2" placeholder="Ideal para hogares, oficinas y conjuntos residenciales..."></textarea>
      </div>
      <div class="col-6">
        <label class="form-label small">Beneficio destacado</label>
        <input v-model="marketingForm.featured_benefit" type="text" class="form-control form-control-sm" placeholder="Visita tecnica sin costo">
      </div>
      <div class="col-6">
        <label class="form-label small">Mensaje de confianza</label>
        <input v-model="marketingForm.trust_message" type="text" class="form-control form-control-sm" placeholder="Tecnicos certificados">
      </div>
      <div class="col-6">
        <label class="form-label small">Mensaje de urgencia</label>
        <input v-model="marketingForm.urgency_message" type="text" class="form-control form-control-sm" placeholder="Cupos limitados esta semana">
      </div>
      <div class="col-6">
        <label class="form-label small">Prueba social</label>
        <input v-model="marketingForm.social_proof_message" type="text" class="form-control form-control-sm" placeholder="Mas de 300 servicios realizados">
      </div>
    </div>

    <!-- Casos de uso -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Casos de uso</h6>
    <div class="d-flex flex-wrap gap-2 mb-2">
      <span v-for="(uc, idx) in marketingForm.use_cases" :key="idx" class="badge bg-light text-dark border d-flex align-items-center gap-1">
        {{ uc }}
        <i class="bi bi-x-lg" style="cursor:pointer;font-size:.65rem" @click="removeUseCase(idx)"></i>
      </span>
    </div>
    <div class="input-group input-group-sm mb-3" style="max-width:320px">
      <input v-model="newUseCase" type="text" class="form-control" placeholder="Ej: Oficinas" @keyup.enter="addUseCase">
      <button type="button" class="btn btn-outline-secondary" @click="addUseCase">Agregar</button>
    </div>

    <!-- CTA y Banner -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Llamado a la accion y banner</h6>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label small">Texto del boton (CTA)</label>
        <input v-model="marketingForm.cta_label" type="text" class="form-control form-control-sm" placeholder="Solicitar ahora">
      </div>
      <div class="col-6">
        <label class="form-label small">Banner promocional</label>
        <input v-model="marketingForm.promo_banner_message" type="text" class="form-control form-control-sm" placeholder="Diagnostico gratis por tiempo limitado">
      </div>
    </div>

    <!-- Beneficios rapidos -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Beneficios rapidos</h6>
    <div class="d-flex flex-column gap-1 mb-2">
      <div v-for="(b, idx) in marketingForm.quick_benefits" :key="idx" class="d-flex align-items-center gap-2 p-1 rounded border bg-white">
        <i :class="['bi', b.icon || 'bi-check-circle']"></i>
        <span class="small flex-grow-1">{{ b.label }}</span>
        <i class="bi bi-trash text-danger" style="cursor:pointer" @click="removeQuickBenefit(idx)"></i>
      </div>
    </div>
    <div class="row g-2 mb-3">
      <div class="col-4">
        <input v-model="newQuickBenefit.icon" type="text" class="form-control form-control-sm" placeholder="bi-shield-check (icono)">
      </div>
      <div class="col-6">
        <input v-model="newQuickBenefit.label" type="text" class="form-control form-control-sm" placeholder="Garantia de 6 meses" @keyup.enter="addQuickBenefit">
      </div>
      <div class="col-2">
        <button type="button" class="btn btn-sm btn-outline-secondary w-100" @click="addQuickBenefit">
          <i class="bi bi-plus-lg"></i>
        </button>
      </div>
    </div>

    <div class="d-flex gap-2 mt-4">
      <button type="button" class="btn btn-primary w-100" @click="saveMarketing" :disabled="marketingLoading">
        <span v-if="marketingLoading" class="spinner-border spinner-border-sm me-2"></span>
        <i v-else class="bi bi-floppy me-1"></i>
        {{ hasMarketing ? 'Actualizar Marketing' : 'Guardar Marketing' }}
      </button>
      <button
        v-if="hasMarketing"
        type="button"
        class="btn btn-outline-danger"
        @click="deleteMarketing"
        :disabled="marketingLoading"
        title="Eliminar configuracion"
      >
        <i class="bi bi-trash"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useToast } from '@/composables/useToast';
import useApi from '@/composables/useApi';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  serviceUuid: { type: String, default: '' },
});

const toast = useToast();
const api = useApi();
const { handleError } = useErrorHandler();

const marketingLoading = ref(false);
const hasMarketing = ref(false);
const marketingForm = reactive({
  reference_price: null, promo_price: null, show_discount_percentage: true,
  tags: [], main_message: '', featured_benefit: '', trust_message: '',
  urgency_message: '', social_proof_message: '', use_cases: [],
  cta_label: '', promo_banner_message: '', quick_benefits: [],
});
const marketingTagOptions = [
  { value: 'OFERTA', label: 'Oferta' },
  { value: 'NUEVO', label: 'Nuevo' },
  { value: 'MAS_SOLICITADO', label: 'Mas solicitado' },
  { value: 'PREMIUM', label: 'Premium' },
  { value: 'RECOMENDADO', label: 'Recomendado' },
  { value: 'HOT', label: 'Hot' },
  { value: 'TOP_CALIFICADO', label: 'Top calificado' },
  { value: 'IDEAL_EMPRESAS', label: 'Ideal para empresas' },
  { value: 'CUPOS_LIMITADOS', label: 'Cupos limitados' },
];
const newUseCase = ref('');
const newQuickBenefit = reactive({ icon: '', label: '' });

const marketingDiscountPreview = computed(() => {
  const { reference_price: ref_, promo_price: promo } = marketingForm;
  if (!ref_ || !promo || ref_ <= 0 || promo >= ref_) return null;
  return Math.round((1 - promo / ref_) * 100);
});

function toggleMarketingTag(value) {
  const idx = marketingForm.tags.indexOf(value);
  if (idx === -1) marketingForm.tags.push(value);
  else marketingForm.tags.splice(idx, 1);
}
function addUseCase() {
  const val = newUseCase.value.trim();
  if (val && !marketingForm.use_cases.includes(val)) marketingForm.use_cases.push(val);
  newUseCase.value = '';
}
function removeUseCase(idx) {
  marketingForm.use_cases.splice(idx, 1);
}
function addQuickBenefit() {
  if (!newQuickBenefit.label.trim()) return;
  marketingForm.quick_benefits.push({ icon: newQuickBenefit.icon.trim() || 'bi-check-circle', label: newQuickBenefit.label.trim() });
  newQuickBenefit.icon = '';
  newQuickBenefit.label = '';
}
function removeQuickBenefit(idx) {
  marketingForm.quick_benefits.splice(idx, 1);
}

function resetMarketingForm() {
  Object.assign(marketingForm, {
    reference_price: null, promo_price: null, show_discount_percentage: true,
    tags: [], main_message: '', featured_benefit: '', trust_message: '',
    urgency_message: '', social_proof_message: '', use_cases: [],
    cta_label: '', promo_banner_message: '', quick_benefits: [],
  });
}

async function fetchMarketing() {
  if (!props.serviceUuid) return;
  try {
    const res = await api.get(`dashboard/services/${props.serviceUuid}/marketing/`);
    if (res.data?.uuid) {
      hasMarketing.value = true;
      const d = res.data;
      Object.assign(marketingForm, {
        reference_price: d.reference_price != null ? parseFloat(d.reference_price) : null,
        promo_price: d.promo_price != null ? parseFloat(d.promo_price) : null,
        show_discount_percentage: d.show_discount_percentage ?? true,
        tags: d.tags || [],
        main_message: d.main_message || '',
        featured_benefit: d.featured_benefit || '',
        trust_message: d.trust_message || '',
        urgency_message: d.urgency_message || '',
        social_proof_message: d.social_proof_message || '',
        use_cases: d.use_cases || [],
        cta_label: d.cta_label || '',
        promo_banner_message: d.promo_banner_message || '',
        quick_benefits: d.quick_benefits || [],
      });
    } else {
      hasMarketing.value = false;
    }
  } catch {
    hasMarketing.value = false;
  }
}

async function saveMarketing() {
  marketingLoading.value = true;
  try {
    await api.put(`dashboard/services/${props.serviceUuid}/marketing/`, { ...marketingForm });
    hasMarketing.value = true;
    toast.success('Marketing guardado');
  } catch (e) {
    handleError(e, 'Error al guardar marketing');
  } finally {
    marketingLoading.value = false;
  }
}

async function deleteMarketing() {
  marketingLoading.value = true;
  try {
    await api.delete(`dashboard/services/${props.serviceUuid}/marketing/`);
    hasMarketing.value = false;
    resetMarketingForm();
    toast.success('Marketing eliminado');
  } catch {
    toast.error('Error al eliminar marketing');
  } finally {
    marketingLoading.value = false;
  }
}

onMounted(fetchMarketing);
</script>
