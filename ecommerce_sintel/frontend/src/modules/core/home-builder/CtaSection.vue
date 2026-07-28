<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">CTA Final</h2>
        <p class="hcb-section-sub">Bloque de llamada a la accion que aparece antes del footer en la pagina principal.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" :disabled="savingCta" @click="saveCTA">
        <span v-if="savingCta" class="spinner-border spinner-border-sm me-1"></span>
        Guardar cambios
      </button>
    </div>

    <div v-if="loadingCta" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
    <div v-else class="hcb-form-grid">
      <div class="hcb-field hcb-field--full">
        <label class="hcb-label">Eyebrow (texto pequeno sobre el titulo)</label>
        <input v-model="ctaForm.eyebrow" class="hcb-input" placeholder="Empieza hoy">
      </div>
      <div class="hcb-field hcb-field--full">
        <label class="hcb-label">Linea 1 del titulo</label>
        <input v-model="ctaForm.title_prefix" class="hcb-input" placeholder="Impulsa tu empresa con">
      </div>
      <div class="hcb-field hcb-field--full">
        <label class="hcb-label">Nombre destacado (en color gradiente)</label>
        <input v-model="ctaForm.title_highlighted" class="hcb-input" placeholder="Sintel Technology">
      </div>
      <div class="hcb-field hcb-field--full">
        <label class="hcb-label">Subtitulo</label>
        <textarea v-model="ctaForm.subtitle" class="hcb-input" rows="2"
          placeholder="Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar."></textarea>
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Texto boton principal</label>
        <input v-model="ctaForm.btn_primary_label" class="hcb-input" placeholder="Solicitar cotizacion">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">URL boton principal</label>
        <input v-model="ctaForm.btn_primary_url" class="hcb-input" placeholder="/cotizar">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">Texto boton secundario</label>
        <input v-model="ctaForm.btn_ghost_label" class="hcb-input" placeholder="Explorar catalogo">
      </div>
      <div class="hcb-field">
        <label class="hcb-label">URL boton secundario</label>
        <input v-model="ctaForm.btn_ghost_url" class="hcb-input" placeholder="/tienda">
      </div>
      <div v-if="ctaError" class="hcb-field hcb-field--full">
        <div class="alert alert-danger small py-2 mb-0">{{ ctaError }}</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';

const toast = useToast();
const store = useCoreAdminStore();
const { footerCta, ctaLoading: loadingCta } = storeToRefs(store);

// ctaForm es v-model con el padre: el panel de preview compartido (HomeRenderer,
// pestaña 'cta') lo necesita -- mismo criterio que contactForm/brandForm.
// El default no puede referenciar una funcion local (defineModel se hoistea
// fuera de setup()) -- objeto inline.
const ctaForm = defineModel('ctaForm', {
  default: () => ({
    eyebrow:           'Empieza hoy',
    title_prefix:      'Impulsa tu empresa con',
    title_highlighted: 'Sintel Technology',
    subtitle:          'Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.',
    btn_primary_label: 'Solicitar cotizacion',
    btn_primary_url:   '/cotizar',
    btn_ghost_label:   'Explorar catalogo',
    btn_ghost_url:     '/tienda',
  }),
});

const savingCta = ref(false);
const ctaError  = ref('');

async function fetchFooterCTA() {
  await store.fetchFooterCta();
  const data = footerCta.value;
  if (data?.uuid) {
    ctaForm.value = {
      eyebrow:           data.eyebrow           || '',
      title_prefix:      data.title_prefix      || '',
      title_highlighted: data.title_highlighted || '',
      subtitle:          data.subtitle          || '',
      btn_primary_label: data.btn_primary_label || '',
      btn_primary_url:   data.btn_primary_url   || '',
      btn_ghost_label:   data.btn_ghost_label   || '',
      btn_ghost_url:     data.btn_ghost_url     || '',
    };
  }
}

async function saveCTA() {
  savingCta.value = true; ctaError.value = '';
  const res = await store.updateFooterCta(ctaForm.value);
  if (res.ok) {
    toast.success('CTA actualizado.');
    await fetchFooterCTA();
  } else {
    ctaError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingCta.value = false;
}
</script>
