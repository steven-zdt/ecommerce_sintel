<template>
  <div>
    <h1 class="step-title">¿Para quién es esta cotización?</h1>
    <p class="step-subtitle">Toda solicitud debe tener un destinatario identificado antes de continuar.</p>

    <div class="mode-toggle mb-4">
      <button
        type="button" class="mode-btn" :class="{ active: mode === 'self' }"
        @click="chooseSelf"
      >
        <i class="bi bi-person-check me-2"></i>Para mí
      </button>
      <button
        type="button" class="mode-btn" :class="{ active: mode === 'third' }"
        @click="chooseThird"
      >
        <i class="bi bi-building me-2"></i>Para un tercero
      </button>
    </div>

    <p v-if="mode === 'third'" class="text-muted small mb-3">
      Ingresa los datos de la persona natural (CC) o empresa (NIT) a nombre de quien se emitirá la cotización.
    </p>

    <div class="form-grid">
      <label class="field wide">
        <span>Nombre completo *</span>
        <input v-model.trim="wizard.applicant.client_name" type="text" autocomplete="name" />
      </label>
      <label class="field">
        <span>Correo electrónico *</span>
        <input
          v-model.trim="wizard.applicant.client_email" type="email" autocomplete="email"
          placeholder="nombre@empresa.com" :readonly="mode === 'self'"
          :class="{ 'field-readonly': mode === 'self' }"
        />
      </label>
      <label class="field">
        <span>Teléfono</span>
        <input v-model.trim="wizard.applicant.phone" type="tel" autocomplete="tel" placeholder="3001234567" />
      </label>
      <label class="field">
        <span>Empresa</span>
        <input v-model.trim="wizard.applicant.company" type="text" />
      </label>
      <label class="field">
        <span>Proyecto</span>
        <input v-model.trim="wizard.applicant.project_name" type="text" placeholder="Nombre del proyecto u obra" />
      </label>
      <label class="field">
        <span>Tipo de documento *</span>
        <select v-model="wizard.applicant.document_type">
          <option value="CC">Cédula (CC)</option>
          <option value="NIT">NIT</option>
        </select>
      </label>
      <label class="field">
        <span>Número de documento *</span>
        <input v-model.trim="wizard.applicant.document_number" type="text" />
      </label>
      <label class="field">
        <span>Departamento</span>
        <input v-model.trim="wizard.applicant.department" type="text" />
      </label>
      <label class="field">
        <span>Ciudad</span>
        <input v-model.trim="wizard.applicant.city" type="text" />
      </label>
      <label class="field wide">
        <span>Dirección</span>
        <input v-model.trim="wizard.applicant.address" type="text" />
      </label>
      <label class="field wide">
        <span>Observaciones</span>
        <textarea v-model.trim="wizard.applicant.notes" rows="3"></textarea>
      </label>
    </div>

    <p v-if="!isValid" class="text-danger small mt-3">Nombre, correo y documento (tipo y número) son obligatorios.</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuth } from '@/composables/useAuth';

const props = defineProps({ wizard: { type: Object, required: true } });

const { user, fetchProfile } = useAuth();

const mode = ref('self');

const isValid = computed(() => props.wizard.validateApplicant());

function applySelfData() {
  const profile = user.value?.profile || {};
  const name = `${profile.first_name || ''} ${profile.last_name || ''}`.trim();
  props.wizard.applicant.client_name = name || user.value?.full_name || '';
  props.wizard.applicant.client_email = user.value?.email || '';
  props.wizard.applicant.phone = profile.phone_number || '';
  props.wizard.applicant.document_type = profile.document_type === 'NIT' ? 'NIT' : 'CC';
  props.wizard.applicant.document_number = profile.document || '';
  props.wizard.applicant.company = profile.company || '';
  props.wizard.applicant.address = profile.address || '';
  props.wizard.applicant.city = profile.city || '';
}

function clearForThird() {
  props.wizard.applicant.client_name = '';
  props.wizard.applicant.client_email = '';
  props.wizard.applicant.phone = '';
  props.wizard.applicant.document_type = 'CC';
  props.wizard.applicant.document_number = '';
  props.wizard.applicant.company = '';
  props.wizard.applicant.address = '';
  props.wizard.applicant.city = '';
}

function chooseSelf() {
  mode.value = 'self';
  applySelfData();
}

function chooseThird() {
  mode.value = 'third';
  clearForThird();
}

onMounted(async () => {
  try {
    await fetchProfile();
  } catch {
    // el guard de ruta ya garantiza sesion activa; si el perfil falla, el
    // usuario simplemente completa los datos a mano.
  }
  if (mode.value === 'self') applySelfData();
});

defineExpose({ isValid });
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 1.4rem; }
.mode-toggle { display: flex; gap: 0.7rem; }
.mode-btn {
  flex: 1; border: 1.5px solid #e2e8f0; background: #fff; border-radius: 14px;
  padding: 0.9rem 1rem; font-weight: 700; color: #475569; cursor: pointer;
  transition: border-color .15s, background .15s;
}
.mode-btn.active { border-color: #7c3aed; background: #f5f3ff; color: #6d28d9; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
.wide { grid-column: 1 / -1; }
.field { display: grid; gap: 0.38rem; }
.field > span { font-size: 0.78rem; font-weight: 700; color: #475569; }
.field input, .field select, .field textarea {
  border: 1.5px solid #dddbe5; border-radius: 12px; padding: 0.78rem 0.85rem; outline: none;
}
.field input:focus, .field select:focus, .field textarea:focus { border-color: #7c3aed; box-shadow: 0 0 0 3px #ede9fe; }
.field-readonly { background: #f8fafc; color: #64748b; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; } .wide { grid-column: auto; } }
</style>
