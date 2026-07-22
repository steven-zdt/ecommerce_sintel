<template>
  <div class="row g-3 mb-3">
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Primer nombre <span class="text-danger">*</span></label>
      <input v-model="form.primer_nombre" type="text" class="form-control"
        :class="{ 'is-invalid': errors.primer_nombre }" required>
      <div class="invalid-feedback">{{ errors.primer_nombre }}</div>
    </div>
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Segundo nombre</label>
      <input v-model="form.segundo_nombre" type="text" class="form-control">
    </div>
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Primer apellido <span class="text-danger">*</span></label>
      <input v-model="form.primer_apellido" type="text" class="form-control"
        :class="{ 'is-invalid': errors.primer_apellido }" required>
      <div class="invalid-feedback">{{ errors.primer_apellido }}</div>
    </div>
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Segundo apellido</label>
      <input v-model="form.segundo_apellido" type="text" class="form-control">
    </div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Fecha de nacimiento <span class="text-danger">*</span></label>
      <input v-model="form.fecha_nacimiento" type="date" class="form-control"
        :class="{ 'is-invalid': errors.fecha_nacimiento }" required>
      <div class="form-text">Debes ser mayor de 18 años para registrarte.</div>
      <div class="invalid-feedback">{{ errors.fecha_nacimiento }}</div>
    </div>
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Sexo <span class="text-muted fw-normal">(opcional)</span></label>
      <select v-model="form.sexo" class="form-select">
        <option value="">Prefiero no indicarlo</option>
        <option value="M">Masculino</option>
        <option value="F">Femenino</option>
        <option value="OTRO">Otro</option>
        <option value="PREFIERO_NO_DECIR">Prefiero no decir</option>
      </select>
    </div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Pais <span class="text-danger">*</span></label>
      <select v-model="form.pais" class="form-select" :class="{ 'is-invalid': errors.pais }" required @change="onPaisChange">
        <option v-for="country in LATAM_COUNTRIES" :key="country" :value="country">{{ country }}</option>
      </select>
      <div class="invalid-feedback">{{ errors.pais }}</div>
    </div>
    <div class="col-sm-6">
      <label class="form-label small fw-bold">Ciudad <span class="text-danger">*</span></label>
      <select v-model="form.ciudad" class="form-select" :class="{ 'is-invalid': errors.ciudad }" required>
        <option value="">Selecciona...</option>
        <option v-for="city in COLOMBIAN_CITIES" :key="city" :value="city">{{ city }}</option>
      </select>
      <div class="invalid-feedback">{{ errors.ciudad }}</div>
    </div>
  </div>

  <!-- Direccion estructurada -- mismo patron que RentalBookingWizard.vue
       (tipo de via + numero + generadora + placa se arman en un solo string) -->
  <div class="mb-3">
    <label class="form-label small fw-bold d-block">
      <i class="bi bi-signpost-2 me-1"></i>Direccion <span class="text-danger">*</span>
    </label>
    <div class="row g-2 align-items-end">
      <div class="col-4 col-sm-3">
        <label class="form-text small mb-1">Tipo de via</label>
        <select v-model="form.roadType" class="form-select" :class="{ 'is-invalid': errors.direccion }">
          <option v-for="type in COLOMBIAN_ROAD_TYPES" :key="type" :value="type">{{ type }}</option>
        </select>
      </div>
      <div class="col-4 col-sm-2">
        <label class="form-text small mb-1">N.º via</label>
        <input :value="form.roadNumber" maxlength="8" class="form-control"
          :class="{ 'is-invalid': errors.direccion }" placeholder="31 Bis"
          @input="setAddressPart('roadNumber', $event)">
      </div>
      <div class="col-1 text-center pb-2 d-none d-sm-block"><strong>#</strong></div>
      <div class="col-4 col-sm-2">
        <label class="form-text small mb-1">Generadora</label>
        <input :value="form.generator" maxlength="8" class="form-control"
          :class="{ 'is-invalid': errors.direccion }" placeholder="68 I"
          @input="setAddressPart('generator', $event)">
      </div>
      <div class="col-1 text-center pb-2 d-none d-sm-block"><strong>−</strong></div>
      <div class="col-4 col-sm-2">
        <label class="form-text small mb-1">Placa</label>
        <input :value="form.plate" maxlength="6" class="form-control"
          :class="{ 'is-invalid': errors.direccion }" placeholder="38"
          @input="setAddressPart('plate', $event)">
      </div>
    </div>
    <div v-if="errors.direccion" class="invalid-feedback d-block mt-1">{{ errors.direccion }}</div>

    <div class="mt-2">
      <label class="form-text small mb-1">Complemento (opcional)</label>
      <input v-model.trim="form.complement" maxlength="100" class="form-control"
        placeholder="Torre, apartamento, piso, local o interior">
    </div>

    <div v-if="structuredAddress" class="address-preview mt-2">
      <i class="bi bi-check-circle-fill text-success me-1"></i>
      <small class="text-muted">Asi guardaremos la direccion: </small>
      <strong>{{ structuredAddress }}</strong>
    </div>
    <p v-else class="text-muted small mt-2 mb-0">
      <i class="bi bi-info-circle me-1"></i>Completa numero de via, generadora y placa.
    </p>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-sm-4">
      <label class="form-label small fw-bold">Tipo de documento <span class="text-danger">*</span></label>
      <select v-model="form.tipo_documento" class="form-select" :class="{ 'is-invalid': errors.tipo_documento }" required>
        <option value="">Selecciona...</option>
        <option value="CC">Cedula de Ciudadania</option>
        <option value="CE">Cedula de Extranjeria</option>
        <option value="NIT">NIT</option>
        <option value="PP">Pasaporte</option>
      </select>
      <div class="invalid-feedback">{{ errors.tipo_documento }}</div>
    </div>
    <div class="col-sm-4">
      <label class="form-label small fw-bold">Numero de documento <span class="text-danger">*</span></label>
      <input v-model="form.numero_documento" type="text" inputmode="numeric" class="form-control"
        :class="{ 'is-invalid': errors.numero_documento }" placeholder="Solo digitos" required>
      <div class="invalid-feedback">{{ errors.numero_documento }}</div>
    </div>
    <div class="col-sm-4">
      <label class="form-label small fw-bold">Fecha de expedicion <span class="text-muted fw-normal">(opcional)</span></label>
      <input v-model="form.fecha_expedicion_documento" type="date" class="form-control"
        :class="{ 'is-invalid': errors.fecha_expedicion_documento }">
      <div class="invalid-feedback">{{ errors.fecha_expedicion_documento }}</div>
    </div>
  </div>

  <div class="mb-3">
    <label class="form-label small fw-bold">Lugar de expedicion <span class="text-danger">*</span></label>
    <input v-model="form.lugar_expedicion_documento" type="text" class="form-control"
      :class="{ 'is-invalid': errors.lugar_expedicion_documento }" placeholder="Bogota" required>
    <div class="invalid-feedback">{{ errors.lugar_expedicion_documento }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue';
import { LATAM_COUNTRIES, COLOMBIAN_CITIES, COUNTRY_TO_NATIONALITY } from './latamData';
import { COLOMBIAN_ROAD_TYPES } from '@/data/colombiaLocations';

const props = defineProps({
  form: { type: Object, required: true },
  errors: { type: Object, required: true },
});

// Nacionalidad ya no es un campo manual -- se deriva del pais elegido para
// minimizar el ingreso de datos (sigue viajando en el payload al backend).
function onPaisChange() {
  props.form.nacionalidad = COUNTRY_TO_NATIONALITY[props.form.pais] || '';
}

onMounted(() => {
  if (!props.form.nacionalidad) onPaisChange();
});

// Direccion estructurada -- mismo patron que RentalBookingWizard.vue: tipo de
// via + numero + generadora + placa (+ complemento opcional) se arman en un
// solo string, que es lo que en definitiva viaja al backend como `direccion`.
const cleanPart = (value) =>
  String(value || '')
    .toUpperCase()
    .replace(/[^0-9A-ZÁÉÍÓÚÑ\s]/g, '')
    .replace(/\s+/g, ' ')
    .trimStart();

function setAddressPart(field, event) {
  props.form[field] = cleanPart(event.target.value);
  event.target.value = props.form[field];
}

const structuredAddress = computed(() => {
  const f = props.form;
  if (!f.roadNumber.trim() || !f.generator.trim() || !f.plate.trim()) return '';
  const base = `${f.roadType} ${f.roadNumber.trim()} # ${f.generator.trim()} - ${f.plate.trim()}`;
  return f.complement.trim() ? `${base}, ${f.complement.trim()}` : base;
});

watch(structuredAddress, (value) => {
  props.form.direccion = value;
});
</script>
