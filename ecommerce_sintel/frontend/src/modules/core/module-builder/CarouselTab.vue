<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-arrows-move me-2"></i>Carrusel (Marketplace Showcase)</div>
    <p class="mb-section-sub">Configuración del scroll horizontal, autoplay y controles.</p>

    <div class="mb-subsection">Número de items visibles</div>
    <div class="mb-responsive-grid">
      <div v-for="dev in CAROUSEL_DEVICES" :key="dev.key" class="mb-responsive-device">
        <div class="mb-responsive-device__label">
          <i :class="['bi', dev.icon]"></i> {{ dev.label }}
        </div>
        <div class="mb-cols-picker mb-cols-picker--sm">
          <button v-for="n in [1,2,3,4,5,6]" :key="n"
            :class="['mb-col-btn mb-col-btn--sm', getCarouselItems(dev.key) === n && 'active']"
            @click="setCarouselItems(dev.key, n)">
            {{ n }}
          </button>
        </div>
      </div>
    </div>

    <div class="mb-grid mt-3">
      <div class="mb-field">
        <label class="mb-label">Velocidad autoplay (px/s)</label>
        <input v-model.number="form.carousel.speed" type="number" class="mb-input" min="10" max="200" step="10">
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.autoplay" class="form-check-input" type="checkbox" id="mb-autoplay">
          <label class="form-check-label" for="mb-autoplay">Autoplay</label>
        </div>
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.loop" class="form-check-input" type="checkbox" id="mb-loop">
          <label class="form-check-label" for="mb-loop">Loop infinito</label>
        </div>
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.pause_on_hover" class="form-check-input" type="checkbox" id="mb-pause-hover">
          <label class="form-check-label" for="mb-pause-hover">Pausar en hover</label>
        </div>
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.pause_on_touch" class="form-check-input" type="checkbox" id="mb-pause-touch">
          <label class="form-check-label" for="mb-pause-touch">Pausar en touch</label>
        </div>
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.pause_on_focus" class="form-check-input" type="checkbox" id="mb-pause-focus">
          <label class="form-check-label" for="mb-pause-focus">Pausar en foco</label>
        </div>
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.show_arrows" class="form-check-input" type="checkbox" id="mb-arrows">
          <label class="form-check-label" for="mb-arrows">Mostrar flechas</label>
        </div>
      </div>
      <div class="mb-field">
        <div class="form-check form-switch">
          <input v-model="form.carousel.show_indicators" class="form-check-input" type="checkbox" id="mb-indicators">
          <label class="form-check-label" for="mb-indicators">Mostrar indicadores (dots)</label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  form: { type: Object, required: true },
});

// Lista propia (no reusar DEVICES de constants.js: sus `key` son nombres de
// campo de ResponsiveTab -  'columns'/'columns_tablet'/'columns_mobile' -
// mientras que aqui getCarouselItems/setCarouselItems necesitan 'desktop'/'tablet'/'mobile').
const CAROUSEL_DEVICES = [
  { key: 'desktop', icon: 'bi-display', label: 'Desktop' },
  { key: 'tablet',  icon: 'bi-tablet',  label: 'Tablet' },
  { key: 'mobile',  icon: 'bi-phone',   label: 'Mobile' },
];

function getCarouselItems(device) {
  if (device === 'desktop') return props.form.carousel.items_desktop;
  if (device === 'tablet') return props.form.carousel.items_tablet;
  return props.form.carousel.items_mobile;
}

function setCarouselItems(device, value) {
  if (device === 'desktop') props.form.carousel.items_desktop = value;
  else if (device === 'tablet') props.form.carousel.items_tablet = value;
  else props.form.carousel.items_mobile = value;
}
</script>

<style scoped src="./_shared.css"></style>
