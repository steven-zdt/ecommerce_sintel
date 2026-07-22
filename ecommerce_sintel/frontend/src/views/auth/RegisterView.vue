<template>
  <CustomerAuthLayout variant="wide">
    <!-- Indicador de progreso -->
    <div class="stepper mb-4">
      <div class="stepper-segment" :class="{ active: step >= 1, done: step > 1 }">
        <span class="stepper-dot">1</span><span class="stepper-label">Datos</span>
      </div>
      <div class="stepper-line" :class="{ done: step > 1 }"></div>
      <div class="stepper-segment" :class="{ active: step >= 2, done: step > 2 }">
        <span class="stepper-dot">2</span><span class="stepper-label">Verificación</span>
      </div>
      <div class="stepper-line" :class="{ done: step > 2 }"></div>
      <div class="stepper-segment" :class="{ active: step >= 3 }">
        <span class="stepper-dot">3</span><span class="stepper-label">Listo</span>
      </div>
    </div>

    <!-- Sin <Transition>: mode="out-in" espera a que termine la animacion de
         salida antes de montar el paso nuevo, y esa señal (transitionend o el
         propio requestAnimationFrame que Vue usa para orquestarla) puede no
         llegar nunca segun el navegador/pestaña -- dejando el flujo de
         registro completo congelado aunque el backend ya haya procesado todo.
         El costo visual de quitarla es minimo frente a ese riesgo. -->
    <div>

      <!-- ── PASO 1: Formulario de registro ─────────────────────────── -->
      <div v-if="step === 1" key="step-1">
        <div class="text-center mb-4">
          <h1 class="h4 fw-bold mb-1">Crea tu cuenta</h1>
          <p class="text-muted small">Registrate para comprar, alquilar y cotizar</p>
        </div>

        <form @submit.prevent="submitStep1" novalidate>
          <div class="row g-3">
            <div class="col-lg-7">
              <div class="card auth-card h-100">
                <div class="card-body">
                  <h2 class="card-title">Información personal e identidad</h2>
                  <PersonalInfoFields :form="form" :errors="errors" />
                </div>
              </div>
            </div>

            <div class="col-lg-5 d-flex flex-column gap-3">
              <div class="card auth-card">
                <div class="card-body">
                  <h2 class="card-title">Contacto</h2>
                  <div class="form-floating mb-3">
                    <input id="reg-email" v-model="form.email" type="email" class="form-control"
                      :class="{ 'is-invalid': errors.email }" placeholder="tu@email.com" required>
                    <label for="reg-email">Correo electrónico</label>
                    <div class="invalid-feedback">{{ errors.email }}</div>
                  </div>

                  <label for="reg-phone" class="form-label small fw-bold">Teléfono celular <span class="text-danger">*</span></label>
                  <div class="input-group">
                    <span class="input-group-text">+57</span>
                    <input id="reg-phone" v-model="form.phone_number" type="tel" inputmode="numeric" maxlength="10" class="form-control"
                      :class="{ 'is-invalid': errors.phone_number }" placeholder="3001234567" required
                      @input="form.phone_number = form.phone_number.replace(/\D/g, '').slice(0, 10)">
                  </div>
                  <div v-if="errors.phone_number" class="invalid-feedback d-block">{{ errors.phone_number }}</div>
                </div>
              </div>

              <div class="card auth-card">
                <div class="card-body">
                  <h2 class="card-title">Seguridad</h2>
                  <div class="form-floating mb-1">
                    <input id="reg-password" v-model="form.password" :type="showPwd ? 'text' : 'password'"
                      class="form-control" :class="{ 'is-invalid': errors.password }" placeholder="Contraseña" required>
                    <label for="reg-password">Contraseña</label>
                    <button
                      type="button" class="pwd-eye-btn" tabindex="-1"
                      :aria-label="showPwd ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                      @click="showPwd = !showPwd"
                    >
                      <i :class="['bi', showPwd ? 'bi-eye-slash' : 'bi-eye']" aria-hidden="true"></i>
                    </button>
                  </div>
                  <div v-if="errors.password" class="invalid-feedback d-block mb-1">{{ errors.password }}</div>
                  <PasswordStrengthMeter :password="form.password" />

                  <div class="form-floating mt-3">
                    <input id="reg-password-confirm" v-model="form.password_confirm" :type="showPwd ? 'text' : 'password'"
                      class="form-control" :class="{ 'is-invalid': errors.password_confirm }" placeholder="Confirmar contraseña" required>
                    <label for="reg-password-confirm">Confirmar contraseña</label>
                    <div class="invalid-feedback">{{ errors.password_confirm }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <HabeasDataConsent :form="form" :errors="errors" class="mt-3" />

          <button type="submit" class="btn-register w-100 py-3 fw-bold mt-2" :disabled="loadingStep1">
            <span v-if="loadingStep1" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-envelope me-2"></i>
            {{ loadingStep1 ? 'Enviando codigo...' : 'Continuar' }}
          </button>
        </form>

        <p class="text-center text-muted small mt-4 mb-0">
          Ya tienes cuenta?
          <RouterLink :to="{ name: 'login' }" class="fw-semibold text-decoration-none">Inicia sesion</RouterLink>
        </p>
      </div>

      <!-- ── PASO 2: Verificacion OTP ───────────────────────────────── -->
      <div v-else-if="step === 2" key="step-2" class="step-narrow mx-auto">
        <div class="text-center mb-4">
          <div class="mail-icon mx-auto mb-3">
            <i class="bi bi-envelope-check fs-3 text-primary"></i>
          </div>
          <h1 class="h4 fw-bold mb-1">Verifica tu correo</h1>
          <p class="text-muted small">
            Ingresa el codigo de 6 digitos que enviamos a
            <strong>{{ registeredEmail }}</strong>
          </p>
        </div>

        <form @submit.prevent="submitStep2">
          <div class="mb-4">
            <OtpInput ref="otpInputRef" v-model="otpCode" :error="codeError" />
          </div>

          <p v-if="codeError" class="text-danger small text-center mb-3" role="alert" aria-live="polite">{{ codeError }}</p>

          <button type="submit" class="btn-register w-100 py-3 fw-bold"
            :disabled="loadingStep2 || otpCode.length < 6">
            <span v-if="loadingStep2" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-check-lg me-2"></i>
            {{ loadingStep2 ? 'Verificando...' : 'Verificar y crear cuenta' }}
          </button>
        </form>

        <div class="text-center mt-4">
          <span class="text-muted small">No recibiste el codigo?</span>
          <button class="btn btn-link btn-sm p-0 ms-1"
            :disabled="resendCooldown > 0 || resending" @click="resendCode">
            <span v-if="resending" class="spinner-border spinner-border-sm me-1"></span>
            <span v-if="resendCooldown > 0">Reenviar en {{ resendCooldown }}s</span>
            <span v-else>Reenviar codigo</span>
          </button>
        </div>

        <div class="text-center mt-3">
          <button class="btn btn-link btn-sm text-muted p-0" @click="goBack">
            <i class="bi bi-arrow-left me-1"></i>Cambiar datos
          </button>
        </div>
      </div>

      <!-- ── PASO 3: Exito ──────────────────────────────────────────── -->
      <div v-else key="step-3" class="step-narrow mx-auto text-center">
        <div class="success-icon mx-auto mb-3">
          <i class="bi bi-check-lg"></i>
        </div>
        <h1 class="h4 fw-bold mb-1">¡Cuenta creada!</h1>
        <p class="text-muted small">Redirigiendo a tu panel...</p>
      </div>

    </div>
  </CustomerAuthLayout>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue';
import { useRouter, RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/store/auth';
import CustomerAuthLayout from '@/components/auth/CustomerAuthLayout.vue';
import OtpInput from '@/components/auth/OtpInput.vue';
import PersonalInfoFields from '@/components/auth/kyc/PersonalInfoFields.vue';
import PasswordStrengthMeter from '@/components/auth/kyc/PasswordStrengthMeter.vue';
import HabeasDataConsent from '@/components/auth/kyc/HabeasDataConsent.vue';
import {
  validatePersonalInfoFields, validateHabeasDataConsent,
  isValidEmail, validatePasswordComplexity,
  PERSONAL_INFO_FORM_DEFAULTS, PERSONAL_INFO_ERROR_DEFAULTS,
} from '@/components/auth/kyc/kycValidation';

const api       = useApi();
const toast     = useToast();
const router    = useRouter();
const authStore = useAuthStore();

const step            = ref(1);
const loadingStep1    = ref(false);
const loadingStep2    = ref(false);
const resending       = ref(false);
const showPwd         = ref(false);
const registeredEmail = ref('');
const codeError       = ref('');
const otpInputRef     = ref(null);

// Mueve el foco al primer control util del paso nuevo -- accesibilidad para
// navegacion por teclado/lectores de pantalla (el foco por defecto se queda en
// el boton que se acaba de ocultar tras la Transition). El nuevo paso recien se
// monta cuando termina la transicion de salida (mode="out-in", .22s) -- un
// setTimeout que coincide con esa duracion es mas confiable que un solo nextTick.
const FIELD_TO_INPUT_ID = { email: 'reg-email', phone_number: 'reg-phone' };
const focusFieldOnStep1 = ref(null);

watch(step, (value) => {
  if (value === 2) setTimeout(() => otpInputRef.value?.clear(), 260);
  else if (value === 1 && focusFieldOnStep1.value) {
    const fieldId = FIELD_TO_INPUT_ID[focusFieldOnStep1.value];
    focusFieldOnStep1.value = null;
    setTimeout(() => document.getElementById(fieldId)?.focus(), 260);
  }
});

let cooldownTimer = null;

// ── Reenvio OTP: cooldown 60s ─────────────────────────────────────────────────

const resendCooldown = ref(0);

function startCooldown() {
  resendCooldown.value = 60;
  cooldownTimer = setInterval(() => {
    resendCooldown.value -= 1;
    if (resendCooldown.value <= 0) clearInterval(cooldownTimer);
  }, 1000);
}

onBeforeUnmount(() => {
  clearInterval(cooldownTimer);
});

// ── Paso 1 ────────────────────────────────────────────────────────────────────

const form = reactive({
  ...PERSONAL_INFO_FORM_DEFAULTS,
  email: '',
  phone_number: '',
  password: '',
  password_confirm: '',
});

const errors = reactive({
  ...PERSONAL_INFO_ERROR_DEFAULTS,
  email: '',
  phone_number: '',
  password: '',
  password_confirm: '',
});

// Celular colombiano: siempre con indicativo +57 predefinido en la UI --
// el usuario solo ingresa los 10 digitos locales (empieza en 3).
function isValidColombianMobile(value) {
  return /^3\d{9}$/.test((value || '').trim());
}

// Valida el formulario COMPLETO localmente. Ninguna llamada al backend (ni el
// envio del OTP) puede ocurrir mientras exista un solo error -- ver submitStep1.
function validateStep1() {
  validatePersonalInfoFields(form, errors);
  validateHabeasDataConsent(form, errors);
  errors.email = !form.email.trim()
    ? 'El correo es requerido'
    : (isValidEmail(form.email) ? '' : 'Ingresa un correo electronico valido');
  errors.phone_number = !form.phone_number.trim()
    ? 'El numero celular es obligatorio'
    : (isValidColombianMobile(form.phone_number) ? '' : 'Ingresa un celular colombiano valido (10 digitos, ej. 3001234567)');
  errors.password = validatePasswordComplexity(form.password);
  errors.password_confirm = form.password !== form.password_confirm ? 'Las contrasenas no coinciden' : '';
  return !Object.values(errors).some(Boolean);
}

async function submitStep1() {
  // Guarda contra doble-invocacion: si el handler se dispara dos veces para
  // un mismo click, la segunda entrada debe ser un no-op.
  if (loadingStep1.value) return;
  // Gate obligatorio: nada de OTP/register-request/envio de correo hasta que
  // el formulario completo pase la validacion local. Si hay un solo error, el
  // flujo se detiene aqui mismo -- sin peticion al backend.
  if (!validateStep1()) {
    // Grid de 2 columnas: un error puede quedar fuera de la vista. Llevar al
    // usuario directo al primer campo invalido en vez de dejarlo adivinar.
    await nextTick();
    const firstInvalid = document.querySelector('.is-invalid');
    firstInvalid?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    firstInvalid?.focus();
    return;
  }
  // Normalizacion antes de enviar (trim + lowercase), igual que el backend.
  form.email = form.email.trim().toLowerCase();
  loadingStep1.value = true;
  try {
    await api.post('auth/register-request/', {
      email:            form.email.trim(),
      phone_number:     `+57${form.phone_number.trim()}`,
      password:         form.password,
      password_confirm: form.password_confirm,
      user_type:        'CUSTOMER',
      primer_nombre:    form.primer_nombre.trim(),
      segundo_nombre:   form.segundo_nombre.trim(),
      primer_apellido:  form.primer_apellido.trim(),
      segundo_apellido: form.segundo_apellido.trim(),
      fecha_nacimiento: form.fecha_nacimiento,
      sexo:             form.sexo,
      nacionalidad:     form.nacionalidad.trim(),
      pais:             form.pais.trim(),
      ciudad:           form.ciudad.trim(),
      direccion:        form.direccion.trim(),
      tipo_documento:   form.tipo_documento,
      numero_documento: form.numero_documento.trim(),
      fecha_expedicion_documento: form.fecha_expedicion_documento || null,
      lugar_expedicion_documento: form.lugar_expedicion_documento.trim(),
      acepta_politica_tratamiento_datos: form.acepta_politica_tratamiento_datos,
      acepta_autorizacion_tratamiento_datos: form.acepta_autorizacion_tratamiento_datos,
      acepta_terminos_condiciones: form.acepta_terminos_condiciones,
    });
    registeredEmail.value = form.email.trim();
    step.value = 2;
    startCooldown();
    toast.success('Codigo enviado. Revisa tu bandeja de entrada.');
  } catch (e) {
    const data = e.response?.data;
    if (data && typeof data === 'object') {
      for (const key of Object.keys(data)) {
        if (key in errors) errors[key] = Array.isArray(data[key]) ? data[key][0] : data[key];
      }
    }
    if (data?.non_field_errors) toast.error(data.non_field_errors[0]);
    else if (!data || !Object.keys(data).some(k => k in errors)) toast.error(data?.detail || 'Error al enviar el codigo.');
  } finally {
    loadingStep1.value = false;
  }
}

// ── Paso 2: OTP ───────────────────────────────────────────────────────────────

const otpCode = ref('');

async function submitStep2() {
  if (loadingStep2.value) return;
  if (otpCode.value.length < 6) return;
  loadingStep2.value = true;
  codeError.value = '';
  try {
    const res = await api.post('auth/register-verify/', {
      email: registeredEmail.value,
      code:  otpCode.value,
    });
    // Guardar sesion en Pinia + localStorage
    authStore.setTokens({ access: res.data.tokens.access, refresh: res.data.tokens.refresh });
    authStore.setUser(res.data.user);
    // Paso 3: micro-pantalla de exito antes de entrar al dashboard -- SSoT de
    // identidad (ver accounts/CLAUDE.md): todo registro publico crea siempre
    // un CUSTOMER con acceso instantaneo, no hace falta pasar por KYC.
    step.value = 3;
    setTimeout(() => {
      router.push({ name: 'customer-profile' });
    }, 1400);
  } catch (e) {
    const data = e.response?.data;
    // El codigo puede ser correcto y aun asi fallar la creacion de la cuenta
    // (ej. telefono/correo ya registrado por otra cuenta) -- eso NO es un
    // error del codigo OTP, es un dato del paso 1 que hay que corregir.
    // El backend revierte la transaccion completa en ese caso (el codigo
    // sigue siendo valido), pero no sirve reintentarlo: el payload guardado
    // ya tiene el dato incorrecto -- hay que volver al paso 1 y reenviar.
    const conflictKey = data?.phone_number ? 'phone_number' : (data?.email ? 'email' : null);
    if (conflictKey && !data?.code) {
      const raw = data[conflictKey];
      const msg = Array.isArray(raw) ? raw[0] : raw;
      // Error persistente en el campo exacto (mismo patron que el resto del
      // formulario: borde rojo + texto debajo, no solo un toast pasajero que
      // el usuario puede perderse) -- el toast se mantiene como aviso inmediato.
      errors[conflictKey] = msg;
      toast.error(msg);
      focusFieldOnStep1.value = conflictKey;
      goBack();
      return;
    }
    codeError.value = data?.code?.[0] || data?.detail || 'Codigo incorrecto o caducado.';
    otpInputRef.value?.clear();
  } finally {
    loadingStep2.value = false;
  }
}

async function resendCode() {
  if (resendCooldown.value > 0 || resending.value) return;
  resending.value = true;
  try {
    await api.post('auth/register-resend/', { email: registeredEmail.value });
    startCooldown();
    toast.success('Nuevo codigo enviado.');
    otpInputRef.value?.clear();
  } catch (e) {
    const data = e.response?.data;
    toast.error(data?.email?.[0] || data?.detail || 'No se pudo reenviar el codigo.');
  } finally {
    resending.value = false;
  }
}

function goBack() {
  otpInputRef.value?.clear();
  codeError.value = '';
  step.value = 1;
}
</script>

<style scoped>
.stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
}
.stepper-segment { display: flex; flex-direction: column; align-items: center; gap: .35rem; }
.stepper-dot {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .8rem; font-weight: 700;
  background: #e5e7eb; color: #6b7280;
  transition: background-color .2s, color .2s;
}
.stepper-segment.active .stepper-dot { background: #2563eb; color: #fff; }
.stepper-segment.done .stepper-dot { background: #16a34a; color: #fff; }
.stepper-label { font-size: .7rem; color: #6b7280; white-space: nowrap; }
.stepper-segment.active .stepper-label { color: #1e293b; font-weight: 600; }
.stepper-line { flex: 1; height: 2px; background: #e5e7eb; margin: 0 .5rem; margin-bottom: 1.1rem; }
.stepper-line.done { background: #16a34a; }

.auth-card { border: 1px solid rgba(0,0,0,.06); border-radius: 1rem; box-shadow: 0 2px 10px rgba(0,0,0,.03); }
.auth-card .card-title { font-size: .95rem; font-weight: 700; margin-bottom: 1rem; }

.pwd-eye-btn {
  position: absolute; right: .9rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: #94a3b8; cursor: pointer; padding: 0; z-index: 5;
}

.btn-register {
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: #fff; border: none; border-radius: .75rem;
  transition: all .3s;
}
.btn-register:hover:not(:disabled) {
  opacity: .9; box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
}
.btn-register:disabled { opacity: .65; cursor: not-allowed; }

.step-narrow { max-width: 420px; }

/* ── Mail / success icons paso 2-3 ── */
.mail-icon {
  width: 72px; height: 72px; border-radius: 50%;
  background: #eff6ff; border: 2px solid #bfdbfe;
  display: flex; align-items: center; justify-content: center;
}
.success-icon {
  width: 72px; height: 72px; border-radius: 50%;
  background: #f0fdf4; border: 2px solid #86efac;
  color: #16a34a; font-size: 1.75rem;
  display: flex; align-items: center; justify-content: center;
}

/* La transicion animada entre pasos (fade + slide via Vue <Transition>) se
   quito deliberadamente: dependia de "transitionend"/requestAnimationFrame
   para saber cuando montar el paso siguiente, y esa señal podia no llegar
   nunca (prefers-reduced-motion, pestaña en segundo plano, etc.), dejando
   el registro completo congelado pese a que el backend ya habia procesado
   todo. Ver commit que quito el <Transition> en el template. */
</style>
