<template>
  <div class="colombian-address-form">

    <!-- ── DATOS DE CONTACTO ─────────────────────────────────────────── -->
    <p class="subsection-label">
      <i class="bi bi-person-circle me-1"></i>Datos de contacto
    </p>
    <div class="row g-3 mb-4">
      <div class="col-12">
        <label class="form-label fw-semibold small">
          Nombre completo <span class="text-danger">*</span>
        </label>
        <input
          v-model="contact.fullName"
          type="text"
          class="form-control"
          :class="{ 'is-invalid': touched.fullName && errors.fullName }"
          placeholder="Nombres y apellidos completos"
          @blur="touch('fullName')"
        >
        <div class="invalid-feedback">Ingresa tu nombre completo</div>
      </div>
      <div class="col-sm-6">
        <label class="form-label fw-semibold small">
          Correo electrónico <span class="text-danger">*</span>
        </label>
        <input
          v-model="contact.email"
          type="email"
          class="form-control"
          :class="{ 'is-invalid': touched.email && errors.email }"
          placeholder="correo@ejemplo.com"
          @blur="touch('email')"
        >
        <div class="invalid-feedback">Ingresa un correo electrónico válido</div>
      </div>
      <div class="col-sm-6">
        <label class="form-label fw-semibold small">
          Celular <span class="text-danger">*</span>
        </label>
        <div class="input-group" :class="{ 'is-invalid-group': touched.phone && errors.phone }">
          <span class="input-group-text bg-light fw-semibold small text-muted">+57</span>
          <input
            v-model="contact.phone"
            type="tel"
            class="form-control"
            :class="{ 'is-invalid': touched.phone && errors.phone }"
            placeholder="3001234567"
            maxlength="10"
            @input="onPhoneInput"
            @blur="touch('phone')"
          >
          <div class="invalid-feedback">10 dígitos, comenzando con 3 (ej. 3001234567)</div>
        </div>
      </div>
    </div>

    <!-- ── UBICACIÓN ─────────────────────────────────────────────────── -->
    <p class="subsection-label">
      <i class="bi bi-geo-alt me-1"></i>Ubicación
    </p>
    <div class="row g-3 mb-4">
      <div class="col-sm-5">
        <label class="form-label fw-semibold small">
          Departamento <span class="text-danger">*</span>
        </label>
        <select
          v-model="location.department"
          class="form-select"
          :class="{ 'is-invalid': touched.department && errors.department }"
          @change="onDepartmentChange"
        >
          <option value="">Seleccionar departamento...</option>
          <option v-for="dep in departments" :key="dep" :value="dep">{{ dep }}</option>
        </select>
        <div class="invalid-feedback">Selecciona el departamento</div>
      </div>
      <div class="col-sm-4">
        <label class="form-label fw-semibold small">
          Ciudad / Municipio <span class="text-danger">*</span>
        </label>
        <select
          v-model="location.city"
          class="form-select"
          :class="{ 'is-invalid': touched.city && errors.city }"
          :disabled="!location.department"
          @change="touch('city')"
        >
          <option value="">Seleccionar ciudad...</option>
          <option v-for="c in availableCities" :key="c" :value="c">{{ c }}</option>
        </select>
        <div class="invalid-feedback">Selecciona la ciudad</div>
      </div>
      <div class="col-sm-3">
        <label class="form-label fw-semibold small">
          Barrio / Localidad <span class="text-danger">*</span>
        </label>
        <input
          v-model="location.neighborhood"
          type="text"
          class="form-control"
          :class="{ 'is-invalid': touched.neighborhood && errors.neighborhood }"
          placeholder="Ej. Chapinero, Poblado"
          @blur="touch('neighborhood')"
        >
        <div class="invalid-feedback">Indica el barrio o localidad</div>
      </div>
    </div>

    <!-- ── NOMENCLATURA COLOMBIANA ────────────────────────────────────── -->
    <p class="subsection-label">
      <i class="bi bi-signpost-2 me-1"></i>Dirección (nomenclatura colombiana)
    </p>
    <div class="nomenclatura-card">
      <div class="row g-2 align-items-end">

        <!-- Tipo de vía -->
        <div class="col-12 col-sm-3">
          <label class="form-label form-label-sm fw-semibold small">
            Tipo de vía <span class="text-danger">*</span>
          </label>
          <select v-model="addr.tipoVia" class="form-select form-select-sm">
            <option v-for="t in tiposVia" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>

        <!-- Número de vía -->
        <div class="col-5 col-sm-2">
          <label class="form-label form-label-sm fw-semibold small">
            N.° vía <span class="text-danger">*</span>
          </label>
          <input
            v-model="addr.numeroVia"
            type="text"
            class="form-control form-control-sm"
            :class="{ 'is-invalid': touched.numeroVia && errors.numeroVia }"
            placeholder="85, 45A"
            maxlength="8"
            @blur="touch('numeroVia')"
          >
        </div>

        <!-- Prefijo opcional -->
        <div class="col-5 col-sm-2">
          <label class="form-label form-label-sm small text-muted">Prefijo</label>
          <input
            v-model="addr.prefijoVia"
            type="text"
            class="form-control form-control-sm"
            placeholder="Sur, Este"
            maxlength="6"
          >
        </div>

        <!-- Separador # -->
        <div class="col-auto d-flex align-items-end" style="padding-bottom:2px">
          <span class="sep-badge">#</span>
        </div>

        <!-- Vía generadora -->
        <div class="col-5 col-sm-2">
          <label class="form-label form-label-sm fw-semibold small">
            Generadora <span class="text-danger">*</span>
          </label>
          <input
            v-model="addr.viaGeneradora"
            type="text"
            class="form-control form-control-sm"
            :class="{ 'is-invalid': touched.viaGeneradora && errors.viaGeneradora }"
            placeholder="15, 82"
            maxlength="8"
            @blur="touch('viaGeneradora')"
          >
        </div>

        <!-- Separador - -->
        <div class="col-auto d-flex align-items-end" style="padding-bottom:2px">
          <span class="sep-badge">-</span>
        </div>

        <!-- Número de placa -->
        <div class="col-5 col-sm-2">
          <label class="form-label form-label-sm fw-semibold small">
            Placa <span class="text-danger">*</span>
          </label>
          <input
            v-model="addr.numeroPlaca"
            type="text"
            class="form-control form-control-sm"
            :class="{ 'is-invalid': touched.numeroPlaca && errors.numeroPlaca }"
            placeholder="25, 40"
            maxlength="6"
            @blur="touch('numeroPlaca')"
          >
        </div>
      </div>

      <!-- Complemento -->
      <div class="row g-2 mt-2">
        <div class="col-12">
          <label class="form-label form-label-sm small text-muted">Complemento (opcional)</label>
          <input
            v-model="addr.complemento"
            type="text"
            class="form-control form-control-sm"
            placeholder="Apto 301, Torre 2, Interior 5, Casa 3..."
          >
        </div>
      </div>
    </div>

    <!-- ── VISTA PREVIA ────────────────────────────────────────────────── -->
    <div v-if="addressPreview" class="address-preview mt-3">
      <i class="bi bi-pin-map-fill me-2 text-primary"></i>
      <strong>{{ addressPreview }}</strong>
      <span v-if="location.neighborhood" class="text-muted ms-2 small">
        — {{ location.neighborhood }}, {{ location.city }}, {{ location.department }}
      </span>
    </div>

  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { COLOMBIA_LOCATIONS as colombiaLocations, COLOMBIAN_ROAD_TYPES as tiposVia } from '@/data/colombiaLocations.js';
import { isValidEmail } from '@/utils/validators';

// ── Estado reactivo ─────────────────────────────────────────────────────────────
const contact  = reactive({ fullName: '', email: '', phone: '' });
const location = reactive({ department: '', city: '', neighborhood: '' });
const addr     = reactive({
  tipoVia: 'Calle', numeroVia: '', prefijoVia: '',
  viaGeneradora: '', numeroPlaca: '', complemento: '',
});
const touched = reactive({
  fullName: false, email: false, phone: false,
  department: false, city: false, neighborhood: false,
  numeroVia: false, viaGeneradora: false, numeroPlaca: false,
});

// ── Computed ────────────────────────────────────────────────────────────────────
const departments     = computed(() => Object.keys(colombiaLocations).sort());
const availableCities = computed(() =>
  location.department ? (colombiaLocations[location.department] ?? []) : []
);

const errors = computed(() => ({
  fullName:      !contact.fullName.trim(),
  email:         !isValidEmail(contact.email),
  phone:         !/^[3][0-9]{9}$/.test(contact.phone.trim()),
  department:    !location.department,
  city:          !location.city,
  neighborhood:  !location.neighborhood.trim(),
  numeroVia:     !addr.numeroVia.trim(),
  viaGeneradora: !addr.viaGeneradora.trim(),
  numeroPlaca:   !addr.numeroPlaca.trim(),
}));

const addressPreview = computed(() => {
  if (!addr.numeroVia || !addr.viaGeneradora || !addr.numeroPlaca) return '';
  return [
    addr.tipoVia, addr.numeroVia, addr.prefijoVia || '',
    '#', addr.viaGeneradora, '-', addr.numeroPlaca,
  ].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
});

// ── Handlers ────────────────────────────────────────────────────────────────────
function touch(field) { touched[field] = true; }

function onDepartmentChange() {
  location.city = '';
  touch('department');
}

function onPhoneInput(e) {
  contact.phone = e.target.value.replace(/\D/g, '').slice(0, 10);
}

// ── API pública del componente (defineExpose) ───────────────────────────────────
function validate() {
  Object.keys(touched).forEach(k => { touched[k] = true; });
  return !Object.values(errors.value).some(Boolean);
}

function getFormData() {
  const line1 = [
    addr.tipoVia, addr.numeroVia, addr.prefijoVia,
    '#', addr.viaGeneradora, '-', addr.numeroPlaca,
  ].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();

  return {
    // Campos para ShippingAddress (backend DRF)
    full_name:      contact.fullName.trim(),
    phone_number:   contact.phone.trim(),
    address_line_1: line1,
    address_line_2: addr.complemento.trim(),
    city:           location.city,
    state:          location.department,
    country:        'CO',
    // Solo frontend (no se envían al endpoint de direcciones)
    email:          contact.email.trim(),
    neighborhood:   location.neighborhood.trim(),
  };
}

function prefill({ fullName = '', email = '', phone = '' } = {}) {
  if (fullName) contact.fullName = fullName;
  if (email)    contact.email    = email;
  if (phone)    contact.phone    = phone;
}

defineExpose({ validate, getFormData, prefill });
</script>

<style scoped>
.subsection-label {
  font-size: .72rem;
  font-weight: 700;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: .55px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.nomenclatura-card {
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
}

.sep-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 31px;
  background: #e5e7eb;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-weight: 800;
  font-size: .9rem;
  color: #374151;
  flex-shrink: 0;
  user-select: none;
}

.address-preview {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: .85rem;
  line-height: 1.5;
}
</style>
