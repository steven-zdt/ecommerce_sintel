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

            <div v-if="step === 1" class="booking-card equipment-layout">
              <div class="equipment-visual">
                <img v-if="image" :src="image" :alt="equipment.name" /><i
                  v-else
                  class="bi bi-truck"
                ></i>
              </div>
              <div>
                <span class="soft-badge">{{
                  equipment.category_name || 'Equipo profesional'
                }}</span>
                <h2>{{ equipment.name }}</h2>
                <p class="text-secondary">{{ equipment.description }}</p>
                <label v-if="variants.length > 1" class="field"
                  ><span>Configuración del equipo</span
                  ><select v-model="draft.variantUuid">
                    <option v-for="v in variants" :key="v.uuid" :value="v.uuid">
                      {{ variantName(v) }}
                    </option>
                  </select></label
                >
                <div v-if="comodatoAvailable" class="priority-picker modality-picker">
                  <button
                    type="button"
                    :class="{ active: draft.commercialType === 'RENTAL' }"
                    @click="setCommercialType('RENTAL')"
                  >
                    <strong><i class="bi bi-calendar-check me-1"></i>Renting</strong
                    ><small>Alquiler pagado por días u horas</small>
                  </button>
                  <button
                    type="button"
                    :class="{ active: draft.commercialType === 'COMODATO' }"
                    @click="setCommercialType('COMODATO')"
                  >
                    <strong><i class="bi bi-hand-index-thumb me-1"></i>Comodato</strong
                    ><small>Préstamo de uso, sin costo, sujeto a aprobación</small>
                  </button>
                </div>
                <div class="included-grid">
                  <div v-for="item in inclusions" :key="item.label">
                    <i :class="item.icon"></i><span>{{ item.label }}</span
                    ><small>{{ item.value }}</small>
                  </div>
                </div>
                <div class="price-line">
                  <span>Precio desde</span
                  ><strong
                    >{{ money(selectedVariant?.rental_price_per_day) }} <small>/ día</small></strong
                  >
                </div>
              </div>
            </div>

            <div v-if="step === 2" class="cards-grid">
              <div class="booking-card">
                <h2><i class="bi bi-geo-alt"></i> ¿Dónde utilizarás el equipo?</h2>
                <p class="helper-text">
                  Selecciona la ubicación y construye la dirección con nomenclatura colombiana. Así
                  evitamos errores de digitación.
                </p>
                <div class="form-grid">
                  <label class="field"
                    ><span>Departamento *</span
                    ><select
                      v-model="draft.project.department"
                      autocomplete="address-level1"
                      @change="onDepartmentChange"
                    >
                      <option value="">Seleccionar departamento…</option>
                      <option
                        v-for="department in departments"
                        :key="department"
                        :value="department"
                      >
                        {{ department }}
                      </option>
                    </select></label
                  ><label class="field"
                    ><span>Ciudad / municipio *</span
                    ><select
                      v-model="draft.project.city"
                      autocomplete="address-level2"
                      :disabled="!draft.project.department"
                    >
                      <option value="">
                        {{
                          draft.project.department
                            ? 'Seleccionar ciudad…'
                            : 'Primero elige departamento'
                        }}
                      </option>
                      <option v-for="city in availableCities" :key="city" :value="city">
                        {{ city }}
                      </option>
                    </select></label
                  ><label class="field wide"
                    ><span>Barrio o localidad *</span
                    ><input
                      v-model.trim="draft.project.neighborhood"
                      maxlength="80"
                      autocomplete="address-level3"
                      placeholder="Ej. Kennedy, Chapinero, El Poblado"
                  /></label>
                </div>
                <div class="address-builder">
                  <span class="builder-title"><i class="bi bi-signpost-2"></i> Dirección *</span>
                  <div class="address-parts">
                    <label class="field"
                      ><span>Tipo de vía</span
                      ><select v-model="draft.project.roadType">
                        <option v-for="type in roadTypes" :key="type">{{ type }}</option>
                      </select></label
                    ><label class="field"
                      ><span>N.º vía</span
                      ><input
                        :value="draft.project.roadNumber"
                        maxlength="8"
                        placeholder="31 Bis"
                        @input="setAddressPart('roadNumber', $event)" /></label
                    ><label class="field compact"><span>&nbsp;</span><b>#</b></label
                    ><label class="field"
                      ><span>Generadora</span
                      ><input
                        :value="draft.project.generator"
                        maxlength="8"
                        placeholder="68 I"
                        @input="setAddressPart('generator', $event)" /></label
                    ><label class="field compact"><span>&nbsp;</span><b>−</b></label
                    ><label class="field"
                      ><span>Placa</span
                      ><input
                        :value="draft.project.plate"
                        maxlength="6"
                        placeholder="38"
                        @input="setAddressPart('plate', $event)"
                    /></label>
                  </div>
                  <label class="field mt-3"
                    ><span>Complemento (opcional)</span
                    ><input
                      v-model.trim="draft.project.complement"
                      maxlength="100"
                      placeholder="Torre, apartamento, piso, local o interior"
                  /></label>
                  <div v-if="structuredAddress" class="address-preview">
                    <i class="bi bi-check-circle-fill"></i>
                    <div>
                      <small>Así guardaremos la dirección</small
                      ><strong>{{ structuredAddress }}</strong>
                    </div>
                  </div>
                  <p v-else class="address-hint">
                    <i class="bi bi-info-circle"></i>Completa número de vía, generadora y placa.
                  </p>
                </div>
              </div>
              <div class="booking-card">
                <h2><i class="bi bi-buildings"></i> Información del proyecto</h2>
                <div class="form-grid">
                  <label class="field"
                    ><span>Tipo de proyecto</span
                    ><input
                      v-model.trim="draft.project.projectType"
                      placeholder="Construcción, evento..." /></label
                  ><label class="field"
                    ><span>Empresa</span><input v-model.trim="draft.project.company" /></label
                  ><label class="field wide"
                    ><span>Actividad</span
                    ><input
                      v-model.trim="draft.project.activity"
                      placeholder="¿Qué trabajo realizarás?" /></label
                  ><label class="field wide"
                    ><span>Observaciones</span
                    ><textarea v-model.trim="draft.project.notes" rows="3"></textarea>
                  </label>
                </div>
              </div>
              <div class="booking-card">
                <h2><i class="bi bi-signpost-split"></i> Condiciones del lugar</h2>
                <div class="choice-grid">
                  <label v-for="condition in conditions" :key="condition"
                    ><input
                      v-model="draft.project.conditions"
                      type="checkbox"
                      :value="condition"
                    /><span><i class="bi bi-check"></i>{{ condition }}</span></label
                  >
                </div>
              </div>
              <div class="booking-card">
                <h2><i class="bi bi-paperclip"></i> Fotos y documentos del proyecto</h2>
                <p class="helper-text">
                  Agrega fotografías de reconocimiento, planos o un PDF. Esto ayuda a preparar la
                  entrega y la instalación.
                </p>
                <label class="upload-zone"
                  ><input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    @change="addProjectFiles"
                  /><i class="bi bi-cloud-arrow-up"></i><strong>Seleccionar archivos</strong
                  ><small>JPG, PNG, WEBP o PDF · máximo 10 archivos · 15 MB cada uno</small></label
                >
                <div v-if="projectFiles.length" class="file-list">
                  <div v-for="(entry, index) in projectFiles" :key="entry.id">
                    <img v-if="entry.preview" :src="entry.preview" alt="Vista previa" /><i
                      v-else
                      class="bi bi-file-earmark-pdf"
                    ></i
                    ><span
                      ><strong>{{ entry.file.name }}</strong
                      ><small>{{ fileSize(entry.file.size) }}</small></span
                    ><button
                      type="button"
                      aria-label="Quitar archivo"
                      @click="removeProjectFile(index)"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <p v-if="fileError" class="field-error mt-2">{{ fileError }}</p>
              </div>
            </div>

            <div v-if="step === 3" class="schedule-layout">
              <div class="booking-card">
                <h2><i class="bi bi-calendar3"></i> Selecciona el período</h2>
                <div v-if="draft.commercialType !== 'COMODATO'" class="priority-picker">
                  <button
                    :class="{ active: draft.schedule.priority === 'LOW' }"
                    @click="setPriority('LOW')"
                  >
                    <strong>Planificada</strong
                    ><small>Inicia desde {{ earliestLabel(7) }}</small></button
                  ><button
                    :class="{ active: draft.schedule.priority === 'HIGH' }"
                    @click="setPriority('HIGH')"
                  >
                    <strong>Prioritaria</strong><small>Inicia desde {{ earliestLabel(3) }}</small>
                  </button>
                </div>
                <p class="schedule-rule">
                  <i class="bi bi-shield-check"></i> La primera fecha permitida es
                  {{ formattedEarliestDate }}. El calendario bloquea hoy, fechas pasadas y días que
                  no cumplen la anticipación.
                </p>

                <!-- Comodato: plazo fijo en vez de rango de fechas -->
                <template v-if="draft.commercialType === 'COMODATO'">
                  <label class="date-tile mb-3"
                    ><span>Fecha de inicio *</span
                    ><input
                      v-model="draft.schedule.startDate"
                      type="date"
                      :min="earliestStartDate"
                  /></label>
                  <span class="builder-title"><i class="bi bi-hourglass-split"></i> Plazo del comodato *</span>
                  <div class="choice-grid term-picker">
                    <button
                      v-for="term in comodatoTermOptions"
                      :key="term.term_months"
                      type="button"
                      class="term-chip"
                      :class="{ active: draft.termMonths === term.term_months }"
                      @click="setTermMonths(term.term_months)"
                    >
                      {{ term.term_months_display || `${term.term_months} meses` }}
                    </button>
                  </div>
                  <p v-if="!comodatoTermOptions.length" class="schedule-rule mt-2">
                    <i class="bi bi-exclamation-triangle"></i> Este equipo aún no tiene plazos de
                    comodato configurados.
                  </p>
                  <p v-else-if="draft.schedule.endDate" class="address-hint mt-2">
                    <i class="bi bi-info-circle"></i> Fecha estimada de devolución:
                    {{ dateLabel.split(' — ')[1] }}
                  </p>
                  <div class="form-grid mt-3">
                    <label class="field"
                      ><span>Cantidad *</span
                      ><input v-model.number="draft.schedule.quantity" min="1" type="number" /></label
                    >
                  </div>
                </template>

                <!-- Renting: rango de fechas continuo, sin cambios -->
                <template v-else>
                  <div class="date-grid">
                    <label class="date-tile"
                      ><span>Fecha de inicio *</span
                      ><input
                        v-model="draft.schedule.startDate"
                        type="date"
                        :min="earliestStartDate" /></label
                    ><label class="date-tile"
                      ><span>Fecha final *</span
                      ><input
                        v-model="draft.schedule.endDate"
                        type="date"
                        :min="minimumEndDate"
                        :disabled="!draft.schedule.startDate"
                    /></label>
                  </div>
                  <div class="form-grid mt-3">
                    <label class="field"
                      ><span>Cantidad *</span
                      ><input v-model.number="draft.schedule.quantity" min="1" type="number" /></label
                    ><label v-if="selectedVariant?.rental_price_per_hour" class="field"
                      ><span>Modalidad</span
                      ><select v-model="draft.schedule.mode">
                        <option value="days">Por días</option>
                        <option value="hours">Por horas</option>
                      </select></label
                    >
                  </div>
                  <RentalHourSelector
                    v-if="draft.schedule.mode === 'hours'"
                    class="mt-3"
                    v-model:delivery-time="draft.schedule.deliveryTime"
                    v-model:pickup-time="draft.schedule.pickupTime"
                  />
                </template>

                <div class="info-box">
                  <i class="bi bi-info-circle"></i
                  ><span
                    >Nuestro equipo verificará la disponibilidad definitiva y confirmará la reserva.
                    Si alguna fecha no está disponible, te ofreceremos alternativas.</span
                  >
                </div>
              </div>
              <div class="live-summary-stack">
                <div v-if="draft.schedule.startDate && draft.schedule.endDate" class="booking-card live-summary-head">
                  <span>Resumen en tiempo real</span><strong>{{ costs.days }} días</strong
                  ><AvailabilityPill
                    :checking="availability.checking"
                    :available="availability.result?.available ?? null"
                    :next-available-date="availability.result?.next_available_date"
                    :next-available-time="availability.result?.next_available_time"
                  />
                </div>
                <!-- Antes de tener fechas, delivery/pickup ya tienen costo fijo
                     pero el alquiler todavia no -- mostrar el desglose en ese
                     momento leia como "Alquiler $0 + Logistica $30.000" antes
                     de que el calculo estuviera completo. Se pide la fecha
                     primero en vez de mostrar un total parcial. -->
                <div v-if="draft.schedule.startDate && draft.schedule.endDate">
                  <RentalCostsCard :costs="costs" />
                </div>
                <div v-else class="booking-card live-summary-placeholder">
                  <i class="bi bi-calendar-range"></i>
                  <span>Selecciona las fechas de inicio y fin para ver el costo total.</span>
                </div>
              </div>
              <AvailabilityCard
                v-if="availability.result?.available === false"
                class="suggestion-card"
                :checking="availability.checking"
                :available="false"
                :next-available-date="availability.result?.next_available_date"
                :next-available-time="availability.result?.next_available_time"
                :rental-mode="draft.schedule.mode"
                :occupied-slots="availability.result?.occupied_slots"
                @select="applySuggestion"
              />
            </div>

            <div v-if="step === 4" class="confirm-grid">
              <div class="summary-stack">
                <div class="booking-card summary-card">
                  <button @click="step = 1">Editar</button><span>Equipo</span>
                  <h2>{{ equipment.name }}</h2>
                  <p>{{ variantName(selectedVariant) }}</p>
                </div>
                <div class="booking-card summary-card">
                  <button @click="step = 2">Editar</button><span>Proyecto</span>
                  <h2>{{ draft.project.city }}, {{ draft.project.department }}</h2>
                  <p>{{ draft.project.address }}</p>
                </div>
                <div class="booking-card summary-card">
                  <button @click="step = 3">Editar</button><span>Programación</span>
                  <h2>{{ dateLabel }}</h2>
                  <p v-if="draft.commercialType === 'COMODATO'">
                    {{ draft.schedule.quantity }} equipo(s) · Comodato {{ draft.termMonths }} meses
                  </p>
                  <p v-else>{{ draft.schedule.quantity }} equipo(s) · {{ costs.days }} días</p>
                </div>
                <RentalCostsCard :costs="costs" />
              </div>
              <div class="booking-card customer-card">
                <h2>Responsable de la reserva</h2>
                <p>
                  Correo y celular son obligatorios para confirmar disponibilidad y coordinar la
                  entrega.
                </p>
                <div class="form-grid">
                  <label class="field wide"
                    ><span>Nombre completo *</span
                    ><input v-model.trim="draft.customer.fullName" autocomplete="name" /></label
                  ><label class="field"
                    ><span>Tipo de documento</span
                    ><select v-model="draft.customer.docType">
                      <option>CC</option>
                      <option>CE</option>
                      <option>NIT</option>
                      <option>PP</option>
                    </select></label
                  ><label class="field"
                    ><span>Documento *</span
                    ><input v-model.trim="draft.customer.docNumber" /></label
                  ><label class="field"
                    ><span>Correo electrónico *</span
                    ><input
                      v-model.trim="draft.customer.email"
                      type="email"
                      autocomplete="email"
                      placeholder="nombre@empresa.com"
                    /><small v-if="draft.customer.email && !validEmail" class="field-error"
                      >Ingresa un correo válido.</small
                    ></label
                  ><label class="field"
                    ><span>Celular colombiano *</span>
                    <div class="phone-input">
                      <b>+57</b
                      ><input
                        :value="draft.customer.phone"
                        maxlength="10"
                        inputmode="numeric"
                        autocomplete="tel"
                        placeholder="3001234567"
                        @input="onPhoneInput"
                      />
                    </div>
                    <small v-if="draft.customer.phone && !validPhone" class="field-error"
                      >Debe tener 10 dígitos y comenzar por 3.</small
                    ></label
                  >
                </div>
                <label class="terms"
                  ><input v-model="draft.termsAccepted" type="checkbox" /><span
                    >Acepto los términos y condiciones de la reserva.</span
                  ></label
                >
              </div>
            </div>

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
import { formatCOP } from '@/utils/money';
import RentalCostsCard from '@/components/customer/renting/RentalCostsCard.vue';
import AvailabilityPill from '@/components/customer/renting/AvailabilityPill.vue';
import AvailabilityCard from '@/components/customer/renting/AvailabilityCard.vue';
import RentalHourSelector from '@/components/customer/renting/RentalHourSelector.vue';
import { COLOMBIA_LOCATIONS, COLOMBIAN_ROAD_TYPES } from '@/data/colombiaLocations';
import CheckoutStepper from '@/components/shared/checkout/CheckoutStepper.vue';

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
const conditions = [
  'Primer piso',
  'Ascensor',
  'Escaleras',
  'Zona restringida',
  'Carga pesada',
  'Necesita instalación',
  'Necesita capacitación',
];
const departments = Object.keys(COLOMBIA_LOCATIONS).sort((a, b) => a.localeCompare(b, 'es'));
const roadTypes = COLOMBIAN_ROAD_TYPES;
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
const localISO = (date) => {
  const y = date.getFullYear(),
    m = String(date.getMonth() + 1).padStart(2, '0'),
    d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};
const dateAfter = (days) => {
  const value = new Date();
  value.setHours(12, 0, 0, 0);
  value.setDate(value.getDate() + days);
  return value;
};
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
const cleanPart = (value) =>
  String(value || '')
    .toUpperCase()
    .replace(/[^0-9A-ZÁÉÍÓÚÑ\s]/g, '')
    .replace(/\s+/g, ' ')
    .trimStart();
const structuredAddress = computed(() => {
  const p = draft.project;
  if (!p.roadNumber.trim() || !p.generator.trim() || !p.plate.trim()) return '';
  const base = `${p.roadType} ${p.roadNumber.trim()} # ${p.generator.trim()} - ${p.plate.trim()}`;
  return p.complement.trim() ? `${base}, ${p.complement.trim()}` : base;
});
const validEmail = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.customer.email));
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
const money = (v) => formatCOP(v, { withSymbol: true });
const variantName = (v) =>
  v
    ? Object.values(v.attributes || {}).join(' · ') || 'Configuración estándar'
    : 'Configuración estándar';
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
function onDepartmentChange() {
  draft.project.city = '';
}
function setAddressPart(field, event) {
  draft.project[field] = cleanPart(event.target.value);
  event.target.value = draft.project[field];
}
function onPhoneInput(event) {
  // Bug real (hallado 2026-07-22): el campo ya muestra "+57" como prefijo
  // fijo al lado, pero muchos clientes de todos modos pegan/escriben su
  // numero completo con el indicativo (+57, 57 o 057) porque asi lo tienen
  // guardado en sus contactos. Sin esto, "+573041112233" quedaba en
  // "5730411122" tras quitar simbolos y recortar a 10 digitos -- ni
  // empezaba por 3 ni eran los digitos reales del numero, y el usuario veia
  // el error de validacion pese a haber escrito un numero valido.
  let digits = event.target.value.replace(/\D/g, '');
  if (digits.length > 10) {
    if (digits.startsWith('0057')) digits = digits.slice(4);
    else if (digits.startsWith('057')) digits = digits.slice(3);
    else if (digits.startsWith('57')) digits = digits.slice(2);
  }
  draft.customer.phone = digits.slice(0, 10);
  event.target.value = draft.customer.phone;
}
function earliestLabel(days) {
  return dateAfter(days).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
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
function fileSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.ceil(bytes / 1024)} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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
.booking-card {
  background: white;
  border: 1px solid #e8e7ee;
  border-radius: 24px;
  padding: clamp(1.2rem, 3vw, 2rem);
  box-shadow: 0 18px 50px rgba(31, 25, 55, 0.06);
}
.equipment-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) 1.1fr;
  gap: 2rem;
}
.equipment-visual {
  min-height: 360px;
  background: linear-gradient(145deg, #f5f3ff, #f8fafc);
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: 5rem;
  color: #c4b5fd;
  overflow: hidden;
}
.equipment-visual img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.soft-badge {
  display: inline-block;
  background: #f3e8ff;
  color: #6b21a8;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 750;
}
.equipment-layout h2 {
  font-size: 1.8rem;
  margin: 0.8rem 0;
}
.included-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.7rem;
  margin: 1.3rem 0;
}
.included-grid div {
  display: grid;
  grid-template-columns: 30px 1fr;
  align-items: center;
  background: #fafafa;
  border-radius: 12px;
  padding: 0.7rem;
}
.included-grid i {
  grid-row: 1/3;
  color: #7c3aed;
}
.included-grid small {
  color: #64748b;
}
.price-line {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid #eee;
  padding-top: 1.2rem;
}
.price-line strong {
  font-size: 1.35rem;
  color: #5b21b6;
}
.price-line small {
  font-size: 0.75rem;
  color: #64748b;
}
.cards-grid {
  display: grid;
  gap: 1rem;
}
.booking-card h2 {
  font-size: 1.08rem;
  font-weight: 780;
}
.booking-card h2 i {
  color: #7c3aed;
  margin-right: 0.4rem;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}
.wide {
  grid-column: 1/-1;
}
.field {
  display: grid;
  gap: 0.38rem;
}
.field > span,
.date-tile > span {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}
.field input,
.field select,
.field textarea,
.date-tile input {
  width: 100%;
  border: 1.5px solid #dddbe5;
  border-radius: 12px;
  padding: 0.78rem 0.85rem;
  background: #fff;
  outline: none;
}
.field input:focus,
.field select:focus,
.field textarea:focus,
.date-tile input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px #ede9fe;
}
.choice-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.choice-grid input {
  position: absolute;
  opacity: 0;
}
.choice-grid span {
  display: block;
  border: 1.5px solid #e2e0e8;
  border-radius: 999px;
  padding: 0.55rem 0.8rem;
  cursor: pointer;
}
.choice-grid i {
  display: none;
}
.choice-grid input:checked + span {
  border-color: #7c3aed;
  background: #f5f3ff;
  color: #5b21b6;
}
.choice-grid input:checked + span i {
  display: inline;
  margin-right: 0.3rem;
}
.schedule-layout {
  display: grid;
  grid-template-columns: 1.7fr 0.8fr;
  gap: 1rem;
  align-items: start;
}
.suggestion-card {
  grid-column: 1/-1;
}
.date-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.date-tile {
  display: grid;
  gap: 0.5rem;
  background: #fafafa;
  border-radius: 16px;
  padding: 1rem;
}
.info-box {
  display: flex;
  gap: 0.7rem;
  background: #eff6ff;
  color: #1e40af;
  border-radius: 14px;
  padding: 1rem;
  margin-top: 1rem;
  font-size: 0.84rem;
}
.live-summary-stack {
  display: grid;
  gap: 1rem;
  align-content: start;
}
.live-summary-head > span {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}
.live-summary-head > strong {
  display: block;
  font-size: 2rem;
  margin: 0.45rem 0 0.7rem;
}
.live-summary-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  text-align: center;
  color: #64748b;
  font-size: 0.9rem;
  padding: 2rem 1.5rem;
}
.live-summary-placeholder i {
  font-size: 1.6rem;
  color: #94a3b8;
}
.confirm-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  align-items: start;
}
.summary-stack {
  display: grid;
  gap: 1rem;
}
.summary-card {
  position: relative;
}
.summary-card button {
  position: absolute;
  right: 1rem;
  top: 1rem;
  border: 0;
  background: none;
  color: #7c3aed;
  font-weight: 700;
}
.summary-card > span {
  font-size: 0.72rem;
  text-transform: uppercase;
  color: #64748b;
}
.summary-card h2 {
  margin: 0.4rem 0;
}
.summary-card p {
  margin: 0;
  color: #64748b;
}
.terms {
  display: flex;
  gap: 0.7rem;
  margin-top: 1.2rem;
  font-size: 0.88rem;
}
.terms input {
  width: 18px;
  height: 18px;
  accent-color: #7c3aed;
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
.error-box {
  background: #fff1f2;
  color: #be123c;
  border-radius: 14px;
  padding: 0.9rem 1rem;
  margin: 1rem 0;
  display: flex;
  gap: 0.6rem;
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
@media (max-width: 800px) {
  .equipment-layout,
  .schedule-layout,
  .confirm-grid {
    grid-template-columns: 1fr;
  }
  .equipment-visual {
    min-height: 260px;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .wide {
    grid-column: auto;
  }
}
@media (max-width: 480px) {
  .date-grid {
    grid-template-columns: 1fr;
  }
  .included-grid {
    grid-template-columns: 1fr;
  }
  .booking-card {
    border-radius: 18px;
  }
}
.helper-text {
  color: #64748b;
  font-size: 0.88rem;
  margin-bottom: 1.25rem;
}
.field select:disabled {
  background: #f1f5f9;
  color: #94a3b8;
}
.address-builder {
  margin-top: 1.25rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 1rem;
}
.builder-title {
  display: block;
  font-size: 0.82rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 0.8rem;
}
.builder-title i {
  color: #7c3aed;
  margin-right: 0.35rem;
}
.address-parts {
  display: grid;
  grid-template-columns: 1.2fr 0.85fr 34px 0.85fr 34px 0.65fr;
  gap: 0.55rem;
  align-items: end;
}
.compact b {
  height: 47px;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  color: #64748b;
}
.address-preview {
  display: flex;
  gap: 0.7rem;
  align-items: center;
  background: #ecfdf5;
  border: 1px solid #bbf7d0;
  color: #166534;
  border-radius: 12px;
  padding: 0.75rem;
  margin-top: 1rem;
}
.address-preview small,
.address-preview strong {
  display: block;
}
.address-preview small {
  font-size: 0.68rem;
  text-transform: uppercase;
}
.address-hint {
  color: #64748b;
  font-size: 0.8rem;
  margin: 0.8rem 0 0;
}
.field-error {
  color: #be123c;
  font-size: 0.75rem;
}
.phone-input {
  display: flex;
  border: 1.5px solid #dddbe5;
  border-radius: 12px;
  overflow: hidden;
}
.phone-input:focus-within {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px #ede9fe;
}
.phone-input b {
  display: grid;
  place-items: center;
  background: #f1f5f9;
  padding: 0 0.8rem;
  color: #475569;
}
.phone-input input {
  border: 0;
  border-radius: 0;
  box-shadow: none !important;
}
.priority-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
  margin: 1rem 0;
}
.priority-picker button {
  display: grid;
  text-align: left;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  border-radius: 14px;
  padding: 0.8rem;
}
.priority-picker button.active {
  border-color: #7c3aed;
  background: #f5f3ff;
  color: #5b21b6;
}
.priority-picker small {
  color: #64748b;
  margin-top: 0.2rem;
}
.schedule-rule {
  background: #fff7ed;
  color: #9a3412;
  border-radius: 12px;
  padding: 0.75rem;
  font-size: 0.82rem;
}
.schedule-rule i {
  margin-right: 0.4rem;
}
.term-picker {
  margin-top: 0.6rem;
}
.term-chip {
  border: 1.5px solid #e2e0e8;
  background: #fff;
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  font-weight: 650;
  color: #475569;
}
.term-chip.active {
  border-color: #7c3aed;
  background: #f5f3ff;
  color: #5b21b6;
}
.modality-picker {
  margin-bottom: 1.3rem;
}
.upload-zone {
  border: 2px dashed #c4b5fd;
  background: #faf5ff;
  border-radius: 16px;
  padding: 1.3rem;
  display: grid;
  place-items: center;
  text-align: center;
  cursor: pointer;
  color: #5b21b6;
}
.upload-zone input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.upload-zone i {
  font-size: 1.8rem;
}
.upload-zone small {
  display: block;
  color: #64748b;
  margin-top: 0.2rem;
}
.file-list {
  display: grid;
  gap: 0.5rem;
  margin-top: 1rem;
}
.file-list > div {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  background: #f8fafc;
  border-radius: 12px;
  padding: 0.55rem;
}
.file-list img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 8px;
}
.file-list > div > i {
  width: 48px;
  text-align: center;
  font-size: 1.6rem;
  color: #dc2626;
}
.file-list span {
  display: grid;
  min-width: 0;
  flex: 1;
}
.file-list span strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
}
.file-list span small {
  color: #64748b;
}
.file-list button {
  border: 0;
  background: #e2e8f0;
  border-radius: 50%;
  width: 28px;
  height: 28px;
}
@media (max-width: 800px) {
  .address-parts {
    grid-template-columns: 1fr 1fr;
  }
  .compact {
    display: none;
  }
}
@media (max-width: 480px) {
  .priority-picker {
    grid-template-columns: 1fr;
  }
}
</style>
