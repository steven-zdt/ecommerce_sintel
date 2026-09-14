<template>
  <main class="booking-shell">
    <div class="container-xl py-4 py-lg-5">
      <RouterLink :to="`/alquiler/equipo/${route.params.uuid}`" class="back-link"
        ><i class="bi bi-arrow-left"></i> Volver al equipo</RouterLink
      >
      <div class="wizard-stepper-wrap">
        <CheckoutStepper
          :steps="labels"
          :current="step"
          clickable
          aria-label="Progreso de la reserva"
          @update:current="step = $event"
        />
      </div>

      <div v-if="loading" class="booking-card skeleton-card">
        <div></div>
        <div></div>
        <div></div>
      </div>
      <template v-else-if="equipment">
        <!-- Sin <Transition mode="out-in">: esa animacion espera a que el
             navegador dispare "transitionend" (o el requestAnimationFrame que
             Vue usa para orquestarla) antes de montar el paso siguiente, y esa
             señal puede no llegar nunca segun el navegador/pestaña -- dejando
             la reserva completa congelada aunque el borrador ya haya avanzado
             de paso. El costo visual de quitarla es minimo frente a ese riesgo. -->
        <section :key="step" class="step-page">
          <header>
            <p class="eyebrow">Paso {{ step }} de 4</p>
            <h1>{{ headings[step - 1] }}</h1>
            <p>{{ descriptions[step - 1] }}</p>
          </header>

          <EquipmentStep
            v-if="step === 1"
            :equipment="equipment"
            :variants="variants"
            :image="image"
            :selected-variant="selectedVariant"
            :comodato-available="comodatoAvailable"
            :inclusions="inclusions"
            @set-commercial-type="setCommercialType"
          />

          <ProjectStep
            v-if="step === 2"
            :structured-address="structuredAddress"
            :available-cities="availableCities"
            :project-files="projectFiles"
            :file-error="fileError"
            @add-files="addProjectFiles"
            @remove-file="removeProjectFile"
          />

          <ScheduleStep
            v-if="step === 3"
            :costs="costs"
            :selected-variant="selectedVariant"
            :comodato-term-options="comodatoTermOptions"
            :earliest-start-date="earliestStartDate"
            :minimum-end-date="minimumEndDate"
            :formatted-earliest-date="formattedEarliestDate"
            :date-label="dateLabel"
            @set-priority="setPriority"
            @set-term-months="setTermMonths"
            @apply-suggestion="applySuggestion"
          />

          <ConfirmStep
            v-if="step === 4"
            :equipment="equipment"
            :selected-variant="selectedVariant"
            :costs="costs"
            :date-label="dateLabel"
            :valid-email="validEmail"
            :valid-phone="validPhone"
            @edit-step="step = $event"
          />

          <p v-if="error" class="error-box">
            <i class="bi bi-exclamation-circle"></i>{{ error }}
          </p>
          <footer class="step-actions">
            <button v-if="step > 1" class="secondary" @click="step--">Atrás</button
            ><button class="primary" :disabled="submitting" @click="continueFlow">
              <span v-if="submitting" class="spinner-border spinner-border-sm"></span
              >{{ step === 4 ? 'Confirmar reserva' : 'Continuar'
              }}<i v-if="!submitting" class="bi bi-arrow-right"></i>
            </button>
          </footer>
        </section>
      </template>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useBookingStore } from '@/store/renting/bookingStore';
import { useAvailabilityStore } from '@/store/renting/availabilityStore';
import { pricingService } from '@/services/renting/pricingService';
import { bookingService } from '@/services/renting/bookingService';
import { useAuthStore } from '@/store/auth';
import { COLOMBIA_LOCATIONS } from '@/data/colombiaLocations';
import CheckoutStepper from '@/components/shared/checkout/CheckoutStepper.vue';
import EquipmentStep from './booking-wizard/EquipmentStep.vue';
import ProjectStep from './booking-wizard/ProjectStep.vue';
import ScheduleStep from './booking-wizard/ScheduleStep.vue';
import ConfirmStep from './booking-wizard/ConfirmStep.vue';
import { localISO, dateAfter } from './booking-wizard/helpers';
import { isValidEmail } from '@/utils/validators';

const route = useRoute(),
  router = useRouter(),
  booking = useBookingStore(),
  availability = useAvailabilityStore(),
  auth = useAuthStore();
const loading = ref(true),
  submitting = ref(false),
  error = ref(''),
  equipment = ref(null),
  variants = ref([]),
  projectFiles = ref([]),
  fileError = ref('');
const labels = ['Equipo', 'Lugar del proyecto', 'Programación', 'Confirmar'];
const headings = [
  'El equipo para tu proyecto',
  'Cuéntanos sobre tu proyecto',
  'Programa tu alquiler',
  'Confirma tu reserva',
];
const descriptions = [
  'Revisa lo que estás reservando y lo que incluye.',
  'Así coordinaremos una entrega segura y sin contratiempos.',
  'Elige las fechas y conoce el valor estimado al instante.',
  'Revisa los detalles. Solo falta identificar al responsable.',
];
const step = computed({ get: () => booking.step, set: (v) => (booking.step = v) });
const draft = booking.draft;
const selectedVariant = computed(
  () => variants.value.find((v) => v.uuid === draft.variantUuid) || variants.value[0],
);
const image = computed(() => {
  const imgs = equipment.value?.images || [];
  return (imgs.find((i) => i.is_primary) || imgs[0])?.image || equipment.value?.image;
});
// Comodato no tiene tarifa continua (no hay $/dia ni $/hora) -- pasar
// variant: null hace que pricingService.calculate() ponga rental=0 mientras
// sigue calculando logistica/impuestos/dias reales, sin tocar ese servicio.
const costs = computed(() =>
  pricingService.calculate({
    variant: draft.commercialType === 'COMODATO' ? null : selectedVariant.value,
    logistics: equipment.value?.logistics_config || {},
    startDate: draft.schedule.startDate,
    endDate: draft.schedule.endDate,
    quantity: draft.schedule.quantity,
    mode: draft.schedule.mode,
    deliveryTime: draft.schedule.deliveryTime,
    pickupTime: draft.schedule.pickupTime,
  }),
);
const comodatoAvailable = computed(() => !!equipment.value?.commercial_config?.comodato_enabled);
const comodatoTermOptions = computed(() =>
  (equipment.value?.commercial_options || []).filter(
    (o) => o.modality === 'COMODATO' && o.is_enabled,
  ),
);
const earliestStartDate = computed(() =>
  localISO(dateAfter(draft.schedule.priority === 'HIGH' ? 3 : 7)),
);
const minimumEndDate = computed(() => {
  if (!draft.schedule.startDate) return earliestStartDate.value;
  const value = new Date(`${draft.schedule.startDate}T12:00:00`);
  value.setDate(value.getDate() + 1);
  return localISO(value);
});
const formattedEarliestDate = computed(() =>
  new Date(`${earliestStartDate.value}T12:00:00`).toLocaleDateString('es-CO', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }),
);
const dateLabel = computed(() =>
  draft.schedule.startDate && draft.schedule.endDate
    ? `${new Date(`${draft.schedule.startDate}T12:00`).toLocaleDateString('es-CO')} — ${new Date(`${draft.schedule.endDate}T12:00`).toLocaleDateString('es-CO')}`
    : 'Fechas pendientes',
);
const availableCities = computed(() =>
  (COLOMBIA_LOCATIONS[draft.project.department] || [])
    .slice()
    .sort((a, b) => a.localeCompare(b, 'es')),
);
const structuredAddress = computed(() => {
  const p = draft.project;
  if (!p.roadNumber.trim() || !p.generator.trim() || !p.plate.trim()) return '';
  const base = `${p.roadType} ${p.roadNumber.trim()} # ${p.generator.trim()} - ${p.plate.trim()}`;
  return p.complement.trim() ? `${base}, ${p.complement.trim()}` : base;
});
const validEmail = computed(() => isValidEmail(draft.customer.email));
const validPhone = computed(() => /^3\d{9}$/.test(draft.customer.phone));
const inclusions = computed(() => {
  const l = equipment.value?.logistics_config || {};
  return [
    {
      label: 'Entrega',
      value: l.delivery_cost ? 'Disponible' : 'Por coordinar',
      icon: 'bi bi-truck',
    },
    {
      label: 'Retiro',
      value: l.pickup_cost ? 'Disponible' : 'Por coordinar',
      icon: 'bi bi-box-arrow-in-down',
    },
    {
      label: 'Instalación',
      value: l.installation_cost ? 'Disponible' : 'Opcional',
      icon: 'bi bi-tools',
    },
    {
      label: 'Capacitación',
      value: l.training_cost ? 'Disponible' : 'Opcional',
      icon: 'bi bi-mortarboard',
    },
  ];
});
watch(
  () => booking.$state,
  () => booking.persist(),
  { deep: true },
);
watch(
  () => [draft.schedule.startDate, draft.schedule.endDate, draft.schedule.quantity],
  () => {
    availability.result = null;
  },
);
watch(earliestStartDate, (min) => {
  if (draft.schedule.startDate && draft.schedule.startDate < min) {
    draft.schedule.startDate = '';
    draft.schedule.endDate = '';
  }
});
watch(structuredAddress, (value) => {
  draft.project.address = value;
});
function addProjectFiles(event) {
  fileError.value = '';
  const incoming = Array.from(event.target.files || []);
  event.target.value = '';
  for (const file of incoming) {
    if (projectFiles.value.length >= 10) {
      fileError.value = 'Puedes adjuntar máximo 10 archivos.';
      break;
    }
    if (!['image/jpeg', 'image/png', 'image/webp', 'application/pdf'].includes(file.type)) {
      fileError.value = `${file.name}: formato no permitido.`;
      continue;
    }
    if (file.size > 15 * 1024 * 1024) {
      fileError.value = `${file.name}: supera 15 MB.`;
      continue;
    }
    projectFiles.value.push({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : '',
    });
  }
}
function removeProjectFile(index) {
  const [entry] = projectFiles.value.splice(index, 1);
  if (entry?.preview) URL.revokeObjectURL(entry.preview);
}
function validate() {
  error.value = '';
  if (step.value === 1 && !selectedVariant.value)
    error.value = 'Selecciona una configuración del equipo.';
  if (
    step.value === 2 &&
    (!structuredAddress.value ||
      !draft.project.city ||
      !draft.project.department ||
      !draft.project.neighborhood)
  )
    error.value = 'Selecciona departamento y ciudad, e indica barrio y nomenclatura completa.';
  if (
    step.value === 3 &&
    (!draft.schedule.startDate ||
      !draft.schedule.endDate ||
      draft.schedule.startDate < earliestStartDate.value ||
      costs.value.days < 1)
  )
    error.value = `La fecha inicial debe ser igual o posterior al ${formattedEarliestDate.value}.`;
  if (step.value === 3 && draft.commercialType === 'COMODATO' && !draft.termMonths)
    error.value = 'Selecciona un plazo de comodato.';
  if (
    step.value === 3 &&
    draft.commercialType !== 'COMODATO' &&
    draft.schedule.mode === 'hours' &&
    (!draft.schedule.deliveryTime ||
      !draft.schedule.pickupTime ||
      draft.schedule.pickupTime <= draft.schedule.deliveryTime)
  )
    error.value =
      'Indica hora de entrega y de recogida válidas (la recogida debe ser posterior a la entrega).';
  if (step.value === 4) {
    const c = draft.customer;
    if (
      !c.fullName ||
      !c.docNumber ||
      !validEmail.value ||
      !validPhone.value ||
      !draft.termsAccepted
    )
      error.value =
        'Completa los datos obligatorios. El correo debe ser válido y el celular colombiano debe comenzar por 3.';
  }
  return !error.value;
}
function applySuggestion({ date, time }) {
  if (!date) return;
  const prevDays = Math.max(1, costs.value.days || 1);
  draft.schedule.startDate = date;
  const end = new Date(`${date}T12:00:00`);
  end.setDate(end.getDate() + prevDays);
  draft.schedule.endDate = localISO(end);
  if (draft.schedule.mode === 'hours' && time) draft.schedule.deliveryTime = time.slice(0, 5);
  availability.result = null;
  error.value = '';
}
function setPriority(value) {
  draft.schedule.priority = value;
  if (draft.schedule.startDate && draft.schedule.startDate < earliestStartDate.value) {
    draft.schedule.startDate = '';
    draft.schedule.endDate = '';
  }
}
function addMonths(dateStr, months) {
  const d = new Date(`${dateStr}T12:00:00`);
  d.setMonth(d.getMonth() + months);
  return localISO(d);
}
function recomputeComodatoEndDate() {
  if (draft.commercialType === 'COMODATO' && draft.schedule.startDate && draft.termMonths) {
    draft.schedule.endDate = addMonths(draft.schedule.startDate, draft.termMonths);
  }
}
function setCommercialType(value) {
  draft.commercialType = value;
  if (value === 'COMODATO') {
    // Comodato es siempre por dias (nunca por horas) y no usa el concepto de
    // "prioridad" de renting -- se normaliza al elegir la modalidad.
    draft.schedule.mode = 'days';
    draft.schedule.priority = 'LOW';
    draft.schedule.deliveryTime = '';
    draft.schedule.pickupTime = '';
    if (!draft.termMonths && comodatoTermOptions.value.length) {
      draft.termMonths = comodatoTermOptions.value[0].term_months;
    }
    recomputeComodatoEndDate();
  } else {
    draft.termMonths = null;
  }
}
function setTermMonths(months) {
  draft.termMonths = months;
  recomputeComodatoEndDate();
}
watch(() => draft.schedule.startDate, recomputeComodatoEndDate);
async function continueFlow() {
  if (!validate()) return;
  if (step.value < 3) {
    step.value++;
    return;
  }
  if (step.value === 3) {
    try {
      const result = await availability.fetchAvailability(route.params.uuid, {
        variant: selectedVariant.value.uuid,
        start_date: draft.schedule.startDate,
        end_date: draft.schedule.endDate,
        quantity: draft.schedule.quantity,
        rental_mode: draft.schedule.mode,
      });
      if (!result.available) {
        error.value =
          'El equipo no está disponible en estas fechas. Revisa la sugerencia de abajo.';
        return;
      }
      step.value = 4;
    } catch {
      error.value = availability.error;
    }
    return;
  }
  await submit();
}
async function submit() {
  submitting.value = true;
  error.value = '';
  const p = draft.project,
    s = draft.schedule,
    c = draft.customer;
  const isHours = s.mode === 'hours';
  try {
    const created = await bookingService.create({
      equipment_variant: selectedVariant.value.uuid,
      commercial_type: draft.commercialType,
      location_address: p.address,
      location_city: p.city,
      location_department: p.department,
      project_type: p.projectType,
      access_conditions: p.conditions.join(', '),
      location_notes: [p.activity, p.notes].filter(Boolean).join(' — '),
      contact_full_name: c.fullName,
      contact_doc_type: c.docType,
      contact_doc_number: c.docNumber,
      contact_email: c.email,
      contact_phone: c.phone,
      contact_company: p.company,
      start_date: s.startDate,
      end_date: s.endDate,
      quantity: s.quantity,
      estimated_hours: isHours
        ? pricingService.hoursBetween(s.startDate, s.endDate, s.deliveryTime, s.pickupTime)
        : null,
      delivery_time: isHours ? s.deliveryTime : undefined,
      pickup_time: isHours ? s.pickupTime : undefined,
      rental_mode: s.mode,
      priority: s.priority,
      terms_accepted: draft.termsAccepted,
    });
    if (projectFiles.value.length)
      await bookingService.uploadAttachments(
        created.uuid,
        projectFiles.value.map((entry) => entry.file),
      );
    booking.created = { ...created, equipment: equipment.value, costs: costs.value };
    projectFiles.value.forEach((entry) => entry.preview && URL.revokeObjectURL(entry.preview));
    projectFiles.value = [];
    if (draft.commercialType === 'COMODATO') {
      // Comodato no tiene paso de pago (create_request() ya la deja en
      // pending_validation) -- salta directo a la pantalla de resultado,
      // reusando la misma rama que ya maneja COD-Renting (mismo estado:
      // "solicitud registrada, pendiente de aprobacion", sin pago).
      router.push({ path: '/payment/result', query: { status: 'RENTAL_COD_APPROVED', rental_uuid: created.uuid } });
    } else {
      router.push({ name: 'rental-confirmation', params: { uuid: created.uuid } });
    }
  } catch (e) {
    error.value =
      Object.values(e.response?.data || {})
        .flat()
        .join(' ') || 'No pudimos crear la reserva o subir sus adjuntos. Intenta nuevamente.';
  } finally {
    submitting.value = false;
  }
}
onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.push({ path: '/login', query: { next: route.fullPath } });
    return;
  }
  booking.restore();
  try {
    equipment.value = await bookingService.equipment(route.params.uuid);
    variants.value = equipment.value.variants || [];
    // Bug real (hallado en smoke test 2026-07-22): la variante se elegia por
    // uuid (query param, borrador persistido, o variants[0]) sin mirar el
    // stock. Si esa variante tenia stock=0 (ej. "taladro": drrrd stock=0,
    // SKU-SMOKE-UPDATED stock=7), CUALQUIER fecha -- incluida la recomendada
    // -- mostraba "no disponible" en el paso 3, sin ninguna pista de que el
    // problema era la variante, no la fecha. Ademas, como el draft persiste
    // en localStorage (bookingStore.js), un cliente que ya habia caido en la
    // variante sin stock quedaba atascado ahi en visitas futuras. Se
    // resuelve validando que la variante solicitada/persistida tenga stock
    // real antes de aceptarla; si no, cae a la primera con stock, y solo si
    // ninguna tiene se usa variants[0] (para que el usuario vea al menos una
    // opcion en el selector, en vez de un uuid vacio).
    const requestedUuid = route.query.variant || draft.variantUuid;
    const requestedVariant = variants.value.find((v) => v.uuid === requestedUuid);
    const fallbackVariant = variants.value.find((v) => v.stock > 0) || variants.value[0];
    draft.variantUuid =
      (requestedVariant?.stock > 0 ? requestedVariant.uuid : fallbackVariant?.uuid) || '';
    draft.schedule.startDate = route.query.start || draft.schedule.startDate;
    draft.schedule.endDate = route.query.end || draft.schedule.endDate;
    if (draft.schedule.startDate && draft.schedule.startDate < earliestStartDate.value) {
      draft.schedule.startDate = '';
      draft.schedule.endDate = '';
    }
    const u = auth.user || {};
    draft.customer.email ||= u.email || '';
    draft.customer.fullName ||= u.full_name || '';
  } catch {
    error.value = 'No pudimos cargar el equipo.';
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.booking-shell {
  min-height: 100vh;
  background: #f7f7fa;
  color: #17142a;
}
.back-link {
  display: inline-flex;
  gap: 0.45rem;
  color: #64748b;
  text-decoration: none;
  font-weight: 650;
  margin-bottom: 1.4rem;
}
.wizard-stepper-wrap {
  max-width: 760px;
  margin: 0 auto 3rem;
}
.step-page {
  max-width: 1100px;
  margin: auto;
}
.step-page > header {
  text-align: center;
  max-width: 680px;
  margin: 0 auto 2rem;
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #7c3aed;
  font-size: 0.72rem;
  font-weight: 800;
}
.step-page h1 {
  font-size: clamp(2rem, 4vw, 3.2rem);
  font-weight: 850;
  letter-spacing: -0.04em;
}
.step-page > header > p:last-child {
  color: #64748b;
}
.error-box {
  background: #fff1f2;
  color: #be123c;
  border-radius: 14px;
  padding: 0.9rem 1rem;
  margin: 1rem 0;
  display: flex;
  gap: 0.6rem;
}
.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
  margin: 1.5rem 0 3rem;
}
.step-actions button {
  border: 0;
  border-radius: 999px;
  padding: 0.8rem 1.4rem;
  font-weight: 750;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.secondary {
  background: white;
  color: #475569;
  border: 1px solid #ddd !important;
}
.primary {
  background: #6d28d9;
  color: white;
  min-width: 150px;
  justify-content: center;
}
.primary:hover {
  background: #5b21b6;
}
.primary:disabled {
  opacity: 0.6;
}
.skeleton-card div {
  height: 28px;
  background: #eee;
  border-radius: 8px;
  margin: 1rem;
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.45;
  }
}
</style>
