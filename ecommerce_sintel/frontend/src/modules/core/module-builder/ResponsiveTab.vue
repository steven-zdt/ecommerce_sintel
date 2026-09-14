<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-tablet me-2"></i>Responsive</div>
    <p class="mb-section-sub">Número de columnas por dispositivo.</p>
    <div class="mb-responsive-grid">
      <div v-for="dev in DEVICES" :key="dev.key" class="mb-responsive-device">
        <div class="mb-responsive-device__label">
          <i :class="['bi', dev.icon]"></i>
          {{ dev.label }}
        </div>
        <div class="mb-cols-picker mb-cols-picker--sm">
          <button v-for="n in [1,2,3,4,5,6]" :key="n"
            :class="['mb-col-btn mb-col-btn--sm', form[dev.key] === n && 'active']"
            @click="form[dev.key] = n">
            {{ n }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { DEVICES } from './constants';

defineProps({
  form: { type: Object, required: true },
});
</script>

<style scoped src="./_shared.css"></style>
