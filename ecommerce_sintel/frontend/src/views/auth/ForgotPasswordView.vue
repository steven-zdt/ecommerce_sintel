<template>
  <CustomerAuthLayout variant="split">
    <div class="stepper mb-4">
      <span v-for="n in 4" :key="n" class="stepper-dot" :class="{ active: step >= n, done: step > n }"></span>
    </div>

    <Transition name="step-fade" mode="out-in">

      <!-- ── PASO 1: Email ──────────────────────────────────────────── -->
      <div v-if="step === 1" key="step-1">
        <div class="text-center mb-4">
          <h1 class="h4 fw-bold mb-1">Recupera tu contraseña</h1>
          <p class="text-muted small">Ingresa tu correo y te enviaremos un código de verificación</p>
        </div>

        <form @submit.prevent="submitStep1">
          <div class="form-floating mb-3">
            <input id="fp-email" v-model="email" type="email" class="form-control"
              placeholder="tu@email.com" autocomplete="email" required>
            <label for="fp-email">Correo electrónico</label>
          </div>

          <button type="submit" class="btn-fp w-100 py-3 fw-bold" :disabled="loadingStep1">
            <span v-if="loadingStep1" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-envelope me-2"></i>
            {{ loadingStep1 ? 'Enviando...' : 'Enviar código' }}
          </button>
        </form>
      </div>

      <!-- ── PASO 2: Codigo OTP ─────────────────────────────────────── -->
      <div v-else-if="step === 2" key="step-2">
        <div class="text-center mb-4">
          <div class="mail-icon mx-auto mb-3">
            <i class="bi bi-envelope-check fs-3 text-primary"></i>
          </div>
          <h1 class="h4 fw-bold mb-1">Verifica tu correo</h1>
          <p class="text-muted small">
            Ingresa el codigo de 6 digitos que enviamos a <strong>{{ email }}</strong>
          </p>
        </div>

        <form @submit.prevent="submitStep2">
          <div class="mb-4">
            <OtpInput ref="otpInputRef" v-model="otpCode" :error="codeError" />
          </div>

          <p v-if="codeError" class="text-danger small text-center mb-3" role="alert" aria-live="polite">{{ codeError }}</p>

          <button type="submit" class="btn-fp w-100 py-3 fw-bold" :disabled="loadingStep2 || otpCode.length < 6">
            <span v-if="loadingStep2" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-check-lg me-2"></i>
            {{ loadingStep2 ? 'Verificando...' : 'Verificar código' }}
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
      </div>

      <!-- ── PASO 3: Nueva contrasena ───────────────────────────────── -->
      <div v-else-if="step === 3" key="step-3">
        <div class="text-center mb-4">
          <h1 class="h4 fw-bold mb-1">Crea una nueva contraseña</h1>
          <p class="text-muted small">Tu nueva contraseña debe ser distinta a la anterior</p>
        </div>

        <form @submit.prevent="submitStep3">
          <div class="form-floating mb-1">
            <input id="fp-password" v-model="newPassword" :type="showPwd ? 'text' : 'password'"
              class="form-control" :class="{ 'is-invalid': step3Errors.new_password }"
              placeholder="Nueva contraseña" required>
            <label for="fp-password">Nueva contraseña</label>
            <button
              type="button" class="pwd-eye-btn" tabindex="-1"
              :aria-label="showPwd ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              @click="showPwd = !showPwd"
            >
              <i :class="['bi', showPwd ? 'bi-eye-slash' : 'bi-eye']" aria-hidden="true"></i>
            </button>
          </div>
          <div v-if="step3Errors.new_password" class="invalid-feedback d-block mb-1">{{ step3Errors.new_password }}</div>
          <PasswordStrengthMeter :password="newPassword" />

          <div class="form-floating mt-3 mb-3">
            <input id="fp-password-confirm" v-model="newPasswordConfirm" :type="showPwd ? 'text' : 'password'"
              class="form-control" :class="{ 'is-invalid': step3Errors.new_password_confirm }"
              placeholder="Confirmar contraseña" required>
            <label for="fp-password-confirm">Confirmar contraseña</label>
            <div class="invalid-feedback">{{ step3Errors.new_password_confirm }}</div>
          </div>

          <button type="submit" class="btn-fp w-100 py-3 fw-bold" :disabled="loadingStep3">
            <span v-if="loadingStep3" class="spinner-border spinner-border-sm me-2"></span>
            {{ loadingStep3 ? 'Guardando...' : 'Restablecer contraseña' }}
          </button>
        </form>
      </div>

      <!-- ── PASO 4: Exito ──────────────────────────────────────────── -->
      <div v-else key="step-4" class="text-center">
        <div class="success-icon mx-auto mb-3">
          <i class="bi bi-check-lg"></i>
        </div>
        <h1 class="h4 fw-bold mb-1">¡Contraseña actualizada!</h1>
        <p class="text-muted small">Iniciando sesión...</p>
      </div>

    </Transition>

    <p v-if="step < 4" class="text-center text-muted small mt-4 mb-0">
      <RouterLink :to="{ name: 'login' }" class="text-decoration-none">
        <i class="bi bi-arrow-left me-1"></i>Volver al login
      </RouterLink>
    </p>
  </CustomerAuthLayout>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRouter, RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useAuthStore } from '@/store/auth';
import CustomerAuthLayout from '@/components/auth/CustomerAuthLayout.vue';
import OtpInput from '@/components/auth/OtpInput.vue';
import PasswordStrengthMeter from '@/components/auth/kyc/PasswordStrengthMeter.vue';

const api = useApi();
const router = useRouter();
const authStore = useAuthStore();
const { handleError } = useErrorHandler();

const step = ref(1);
const email = ref('');
const otpCode = ref('');
const codeError = ref('');
const newPassword = ref('');
const newPasswordConfirm = ref('');
const showPwd = ref(false);
const otpInputRef = ref(null);

const loadingStep1 = ref(false);
const loadingStep2 = ref(false);
const loadingStep3 = ref(false);
const resending = ref(false);
const step3Errors = ref({});

let cooldownTimer = null;
const resendCooldown = ref(0);

// Mueve el foco al primer control util del paso nuevo -- accesibilidad para
// navegacion por teclado/lectores de pantalla. 260ms coincide con la duracion
// de la transicion de salida (mode="out-in", ver .step-fade-leave-active).
watch(step, (value) => {
  setTimeout(() => {
    if (value === 2) otpInputRef.value?.clear();
    else if (value === 3) document.getElementById('fp-password')?.focus();
  }, 260);
});

onMounted(() => document.getElementById('fp-email')?.focus());

function startCooldown() {
  resendCooldown.value = 60;
  cooldownTimer = setInterval(() => {
    resendCooldown.value -= 1;
    if (resendCooldown.value <= 0) clearInterval(cooldownTimer);
  }, 1000);
}
onBeforeUnmount(() => clearInterval(cooldownTimer));

async function submitStep1() {
  loadingStep1.value = true;
  try {
    // La respuesta del backend es siempre el mismo 200 generico (no revela si
    // el correo existe) -- el frontend simplemente avanza al paso 2.
    await api.post('auth/forgot-password-request/', { email: email.value.trim() });
    step.value = 2;
    startCooldown();
  } catch (e) {
    handleError(e, 'No se pudo enviar el codigo. Intenta de nuevo.');
  } finally {
    loadingStep1.value = false;
  }
}

async function submitStep2() {
  if (otpCode.value.length < 6) return;
  loadingStep2.value = true;
  codeError.value = '';
  try {
    await api.post('auth/forgot-password-verify/', { email: email.value.trim(), code: otpCode.value });
    step.value = 3;
  } catch (e) {
    codeError.value = e.response?.data?.code?.[0] || e.response?.data?.detail || 'Codigo incorrecto o caducado.';
    otpInputRef.value?.clear();
  } finally {
    loadingStep2.value = false;
  }
}

async function resendCode() {
  if (resendCooldown.value > 0 || resending.value) return;
  resending.value = true;
  try {
    await api.post('auth/forgot-password-request/', { email: email.value.trim() });
    startCooldown();
    otpInputRef.value?.clear();
  } finally {
    resending.value = false;
  }
}

async function submitStep3() {
  step3Errors.value = {};
  if (newPassword.value !== newPasswordConfirm.value) {
    step3Errors.value.new_password_confirm = 'Las contrasenas no coinciden';
    return;
  }
  loadingStep3.value = true;
  try {
    const { data } = await api.post('auth/forgot-password-reset/', {
      email: email.value.trim(),
      code: otpCode.value,
      new_password: newPassword.value,
      new_password_confirm: newPasswordConfirm.value,
    });
    authStore.setTokens({ access: data.tokens.access, refresh: data.tokens.refresh });
    authStore.setUser(data.user);
    step.value = 4;
    setTimeout(() => router.push({ name: 'shop-catalog' }), 1400);
  } catch (e) {
    const data = e.response?.data;
    if (data && typeof data === 'object') {
      for (const key of ['new_password', 'new_password_confirm']) {
        if (data[key]) step3Errors.value[key] = Array.isArray(data[key]) ? data[key][0] : data[key];
      }
    }
    if (!Object.keys(step3Errors.value).length) {
      handleError(e, 'No se pudo restablecer la contraseña. Solicita un nuevo código.');
    }
  } finally {
    loadingStep3.value = false;
  }
}
</script>

<style scoped>
.stepper { display: flex; justify-content: center; gap: .5rem; }
.stepper-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #e5e7eb; transition: background-color .2s, transform .2s;
}
.stepper-dot.active { background: #2563eb; transform: scale(1.2); }
.stepper-dot.done { background: #16a34a; transform: scale(1); }

.pwd-eye-btn {
  position: absolute; right: .9rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: #94a3b8; cursor: pointer; padding: 0; z-index: 5;
}

.btn-fp {
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: #fff; border: none; border-radius: .75rem;
  transition: all .3s;
}
.btn-fp:hover:not(:disabled) { opacity: .9; box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3); }
.btn-fp:disabled { opacity: .65; cursor: not-allowed; }

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

.step-fade-enter-active,
.step-fade-leave-active { transition: opacity .22s ease, transform .22s ease; }
.step-fade-enter-from { opacity: 0; transform: translateX(18px); }
.step-fade-leave-to { opacity: 0; transform: translateX(-18px); }

/* Ver RegisterView.vue: sin esto, prefers-reduced-motion puede dejar
   <Transition mode="out-in"> esperando "transitionend" para siempre. */
@media (prefers-reduced-motion: reduce) {
  .step-fade-enter-active,
  .step-fade-leave-active { transition: none; }
}
</style>
