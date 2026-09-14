<template>
  <div>
    <p class="text-muted small mb-3">
      Configuracion comercial y visual exclusiva de este equipo -- se refleja automaticamente
      en el detalle publico. Nada de esto se comparte ni se hereda de otros equipos.
    </p>

    <!-- Precio Base de Referencia (desde variante) -->
    <div v-if="variants.length" class="alert alert-info border-0 p-3 mb-3 rounded-3" style="background-color:#dbeafe;border-left:3px solid #0284c7 !important">
      <div class="d-flex align-items-start gap-2">
        <i class="bi bi-info-circle-fill text-info mt-1" style="font-size:.9rem;flex-shrink:0"></i>
        <div class="flex-grow-1 small">
          <div class="fw-semibold text-dark mb-1">Precio base (desde variante principal)</div>
          <div class="text-muted mb-2">SKU: <code class="text-dark">{{ variants[0]?.sku }}</code></div>
          <div v-if="variants[0]?.rental_price_per_day" class="text-dark fw-semibold">
            <i class="bi bi-tag me-1"></i>{{ formatCOP(variants[0].rental_price_per_day) }} por día
            <span v-if="variants[0]?.rental_price_per_hour" class="ms-2">
              <i class="bi bi-clock me-1"></i>{{ formatCOP(variants[0].rental_price_per_hour) }} por hora
            </span>
          </div>
          <div v-else class="text-warning small">
            <i class="bi bi-exclamation-circle me-1"></i>No has configurado precios en la variante
          </div>
        </div>
      </div>
    </div>
    <div v-else class="alert alert-warning border-0 p-3 mb-3 rounded-3" style="background-color:#fef3c7;border-left:3px solid #f59e0b !important">
      <i class="bi bi-exclamation-triangle me-2 text-warning"></i>
      <span class="small">Crea una variante primero para establecer el precio base de marketing</span>
    </div>

    <!-- Precio comercial -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2">Precio comercial</h6>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label small">Precio de referencia (anterior)</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input v-model.number="marketingForm.reference_price" type="number" min="0" step="0.01" class="form-control" placeholder="850000">
        </div>
        <small class="text-muted mt-1 d-block">
          <i class="bi bi-lightbulb me-1"></i>
          <span v-if="variants[0]?.rental_price_per_day">
            Sugerencia: usa {{ formatCOP(variants[0].rental_price_per_day) }} como referencia
          </span>
          <span v-else>Completa el precio en la variante principal</span>
        </small>
      </div>
      <div class="col-6">
        <label class="form-label small">Precio promocional</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input v-model.number="marketingForm.promo_price" type="number" min="0" step="0.01" class="form-control" placeholder="520000">
        </div>
      </div>
      <div class="col-12">
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" v-model="marketingForm.show_discount_percentage" id="mktShowDiscount">
          <label class="form-check-label small" for="mktShowDiscount">Mostrar porcentaje de descuento (calculado automaticamente)</label>
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
        <textarea v-model="marketingForm.main_message" class="form-control form-control-sm" rows="2" placeholder="Ideal para conciertos, ferias, eventos empresariales..."></textarea>
      </div>
      <div class="col-6">
        <label class="form-label small">Beneficio destacado</label>
        <input v-model="marketingForm.featured_benefit" type="text" class="form-control form-control-sm" placeholder="Entrega inmediata">
      </div>
      <div class="col-6">
        <label class="form-label small">Mensaje de confianza</label>
        <input v-model="marketingForm.trust_message" type="text" class="form-control form-control-sm" placeholder="Equipo certificado">
      </div>
      <div class="col-6">
        <label class="form-label small">Mensaje de urgencia</label>
        <input v-model="marketingForm.urgency_message" type="text" class="form-control form-control-sm" placeholder="Ultimas unidades disponibles">
      </div>
      <div class="col-6">
        <label class="form-label small">Prueba social</label>
        <input v-model="marketingForm.social_proof_message" type="text" class="form-control form-control-sm" placeholder="Mas de 500 alquileres realizados">
      </div>
    </div>

    <!-- Comparativa economica -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Comparativa economica (comprar vs alquilar)</h6>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label small">Precio estimado de compra</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input v-model.number="marketingForm.purchase_price_reference" type="number" min="0" step="0.01" class="form-control" placeholder="12500000">
        </div>
      </div>
      <div class="col-6">
        <label class="form-label small">Mensaje financiero</label>
        <input v-model="marketingForm.financial_message" type="text" class="form-control form-control-sm" placeholder="Ahorra comprando vs alquilar">
      </div>
      <div v-if="marketingSavingsPreview" class="col-12">
        <span class="badge bg-success-subtle text-success border border-success-subtle">
          Ahorras {{ marketingSavingsPreview }}% alquilando
        </span>
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
      <input v-model="newUseCase" type="text" class="form-control" placeholder="Ej: Eventos" @keyup.enter="addUseCase">
      <button type="button" class="btn btn-outline-secondary" @click="addUseCase">Agregar</button>
    </div>

    <!-- CTA y Banner -->
    <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Llamado a la accion y banner</h6>
    <div class="row g-2 mb-3">
      <div class="col-6">
        <label class="form-label small">Texto del boton (CTA)</label>
        <input v-model="marketingForm.cta_label" type="text" class="form-control form-control-sm" placeholder="Reservar ahora">
      </div>
      <div class="col-6">
        <label class="form-label small">Banner promocional</label>
        <input v-model="marketingForm.promo_banner_message" type="text" class="form-control form-control-sm" placeholder="Transporte incluido por tiempo limitado">
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
        <input v-model="newQuickBenefit.icon" type="text" class="form-control form-control-sm" placeholder="bi-truck (icono)">
      </div>
      <div class="col-6">
        <input v-model="newQuickBenefit.label" type="text" class="form-control form-control-sm" placeholder="Transporte incluido" @keyup.enter="addQuickBenefit">
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
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { formatCOP as formatCOPBase } from '@/utils/money';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
  // Solo lectura -- viene del padre (compartido con la pestana Variantes),
  // usado para el precio de referencia sugerido.
  variants: { type: Array, required: true },
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

function formatCOP(value) {
  if (value == null || value === '') return null;
  return formatCOPBase(value, { withSymbol: true });
}

const marketingLoading = ref(false);
const hasMarketing = ref(false);
const marketingForm = reactive({
  reference_price: null, promo_price: null, show_discount_percentage: true,
  tags: [], main_message: '', featured_benefit: '', trust_message: '',
  urgency_message: '', social_proof_message: '', purchase_price_reference: null,
  financial_message: '', use_cases: [], cta_label: '', promo_banner_message: '',
  quick_benefits: [],
});
const marketingTagOptions = [
  { value: 'OFERTA', label: 'Oferta' },
  { value: 'NUEVO', label: 'Nuevo' },
  { value: 'MAS_ALQUILADO', label: 'Mas alquilado' },
  { value: 'PREMIUM', label: 'Premium' },
  { value: 'RECOMENDADO', label: 'Recomendado' },
  { value: 'HOT', label: 'Hot' },
  { value: 'TOP_VENTAS', label: 'Top ventas' },
  { value: 'IDEAL_EVENTOS', label: 'Ideal para eventos' },
  { value: 'ULTIMAS_UNIDADES', label: 'Ultimas unidades' },
];
const newUseCase = ref('');
const newQuickBenefit = reactive({ icon: '', label: '' });

const marketingDiscountPreview = computed(() => {
  const { reference_price: ref_, promo_price: promo } = marketingForm;
  if (!ref_ || !promo || ref_ <= 0 || promo >= ref_) return null;
  return Math.round((1 - promo / ref_) * 100);
});
const marketingSavingsPreview = computed(() => {
  const purchase = marketingForm.purchase_price_reference;
  if (!purchase || purchase <= 0) return null;
  const effective = marketingForm.promo_price || marketingForm.reference_price
    || props.variants[0]?.rental_price_per_day;
  if (!effective || effective >= purchase) return null;
  return Math.round((1 - effective / purchase) * 100);
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

async function fetchMarketing() {
  try {
    const res = await api.get(`dashboard/equipment/${props.equipmentUuid}/marketing/`);
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
        purchase_price_reference: d.purchase_price_reference != null ? parseFloat(d.purchase_price_reference) : null,
        financial_message: d.financial_message || '',
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
    await api.put(`dashboard/equipment/${props.equipmentUuid}/marketing/`, { ...marketingForm });
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
    await api.delete(`dashboard/equipment/${props.equipmentUuid}/marketing/`);
    hasMarketing.value = false;
    Object.assign(marketingForm, {
      reference_price: null, promo_price: null, show_discount_percentage: true,
      tags: [], main_message: '', featured_benefit: '', trust_message: '',
      urgency_message: '', social_proof_message: '', purchase_price_reference: null,
      financial_message: '', use_cases: [], cta_label: '', promo_banner_message: '',
      quick_benefits: [],
    });
    toast.success('Configuracion de marketing eliminada');
  } catch {
    toast.error('Error al eliminar marketing');
  } finally {
    marketingLoading.value = false;
  }
}

// Sincroniza automaticamente reference_price con el precio/dia de la
// variante principal (misma logica que tenia el padre antes de esta split).
watch(
  () => props.variants[0]?.rental_price_per_day,
  (newPrice) => {
    if (newPrice != null && newPrice > 0) {
      marketingForm.reference_price = parseFloat(newPrice);
    }
  },
);

onMounted(fetchMarketing);
</script>
