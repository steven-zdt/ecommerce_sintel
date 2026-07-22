<template>
  <div class="pwd-meter mt-2 mb-1">
    <div class="pwd-meter-track">
      <div class="pwd-meter-fill" :class="bandClass" :style="{ width: `${(score / 5) * 100}%` }"></div>
    </div>
    <div class="d-flex justify-content-between align-items-center mt-1">
      <span class="small fw-semibold" :class="bandTextClass">{{ bandLabel }}</span>
    </div>
    <ul class="pwd-checklist list-unstyled small mb-0 mt-1">
      <li :class="checks.length ? 'text-success' : 'text-muted'">
        <i :class="['bi', checks.length ? 'bi-check-circle-fill' : 'bi-circle']"></i> Minimo 12 caracteres
      </li>
      <li :class="checks.upper ? 'text-success' : 'text-muted'">
        <i :class="['bi', checks.upper ? 'bi-check-circle-fill' : 'bi-circle']"></i> Una letra mayuscula
      </li>
      <li :class="checks.lower ? 'text-success' : 'text-muted'">
        <i :class="['bi', checks.lower ? 'bi-check-circle-fill' : 'bi-circle']"></i> Una letra minuscula
      </li>
      <li :class="checks.digit ? 'text-success' : 'text-muted'">
        <i :class="['bi', checks.digit ? 'bi-check-circle-fill' : 'bi-circle']"></i> Un numero
      </li>
      <li :class="checks.special ? 'text-success' : 'text-muted'">
        <i :class="['bi', checks.special ? 'bi-check-circle-fill' : 'bi-circle']"></i> Un caracter especial (ej. !@#$%*)
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  password: { type: String, default: '' },
});

// Mismos criterios que ecommerce/validators.py::ComplexPasswordValidator +
// MinimumLengthValidator(min_length=12) -- no reflejar aqui nada que el
// backend no exija, para que el feedback nunca contradiga al servidor.
const checks = computed(() => ({
  length: props.password.length >= 12,
  upper: /[A-Z]/.test(props.password),
  lower: /[a-z]/.test(props.password),
  digit: /[0-9]/.test(props.password),
  special: /[^A-Za-z0-9]/.test(props.password),
}));

const score = computed(() => Object.values(checks.value).filter(Boolean).length);

const bandLabel = computed(() => {
  if (score.value <= 2) return 'Debil';
  if (score.value <= 4) return 'Media';
  return 'Fuerte';
});

const bandClass = computed(() => {
  if (score.value <= 2) return 'bg-danger';
  if (score.value <= 4) return 'bg-warning';
  return 'bg-success';
});

const bandTextClass = computed(() => {
  if (score.value <= 2) return 'text-danger';
  if (score.value <= 4) return 'text-warning';
  return 'text-success';
});

defineExpose({ score });
</script>

<style scoped>
.pwd-meter-track {
  height: 6px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}
.pwd-meter-fill {
  height: 100%;
  border-radius: 999px;
  transition: width .2s ease, background-color .2s ease;
}
.pwd-checklist li i { font-size: .8rem; margin-right: 4px; }
</style>
