<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-film me-2"></i>Multimedia</div>

    <div class="mb-subsection">Fondo de Card (Imagen/Video)</div>
    <div class="mb-grid">
      <div class="mb-field mb-field--full">
        <label class="mb-label">Tipo de fondo</label>
        <select v-model="form.media.type" class="mb-select">
          <option value="color">Color sólido</option>
          <option value="image">Imagen</option>
          <option value="video">Video</option>
        </select>
      </div>
      <div v-if="form.media.type === 'video'" class="mb-field mb-field--full">
        <label class="mb-label">URL del video (MP4)</label>
        <input v-model="form.media.video_url" class="mb-input" placeholder="https://...">
      </div>
      <div v-if="form.media.type === 'video'" class="mb-field mb-field--full">
        <label class="mb-label">URL del video (WebM - opcional)</label>
        <input v-model="form.media.video_url_webm" class="mb-input" placeholder="https://...">
      </div>
      <div v-if="form.media.type === 'video'" class="mb-field mb-field--full">
        <label class="mb-label">Poster (imagen preview)</label>
        <input v-model="form.media.poster" class="mb-input" placeholder="https://...">
      </div>
      <div class="mb-field">
        <label class="mb-label">Desenfoque (blur px)</label>
        <input v-model.number="form.media.blur" type="number" class="mb-input" min="0" max="20" step="1">
      </div>
      <div class="mb-field mb-field--full">
        <div class="form-check form-switch">
          <input v-model="form.media.glass" class="form-check-input" type="checkbox" id="mb-media-glass">
          <label class="form-check-label" for="mb-media-glass">Glassmorphism (overlay)</label>
        </div>
      </div>
    </div>

    <div class="mb-subsection mt-3">Encabezado de Sección</div>
    <div class="mb-grid">
      <div class="mb-field mb-field--full">
        <label class="mb-label">Título</label>
        <input v-model="form.header.title" class="mb-input" placeholder="El ecosistema Sintel">
      </div>
      <div class="mb-field mb-field--full">
        <label class="mb-label">Subtítulo (eyebrow)</label>
        <input v-model="form.header.subtitle" class="mb-input" placeholder="Marketplace">
      </div>
      <div class="mb-field mb-field--full">
        <label class="mb-label">Descripción</label>
        <textarea v-model="form.header.description" class="mb-input" rows="2" placeholder="Detalle sobre esta sección..."></textarea>
      </div>
      <div class="mb-field">
        <label class="mb-label">CTA - Texto</label>
        <input v-model="form.header.cta_text" class="mb-input" placeholder="Explorar todo">
      </div>
      <div class="mb-field">
        <label class="mb-label">CTA - URL</label>
        <input v-model="form.header.cta_url" class="mb-input" placeholder="/tienda">
      </div>
      <div class="mb-field">
        <label class="mb-label">CTA - Target</label>
        <select v-model="form.header.cta_target" class="mb-select">
          <option value="_self">Misma pestaña</option>
          <option value="_blank">Nueva pestaña</option>
        </select>
      </div>
    </div>

    <div class="mb-subsection mt-3">Fondo de Sección Completa</div>
    <div class="mb-grid">
      <div class="mb-field mb-field--full">
        <label class="mb-label">Tipo</label>
        <select v-model="form.section_background.type" class="mb-select">
          <option value="none">Ninguno</option>
          <option value="image">Imagen</option>
          <option value="video">Video</option>
          <option value="color">Color sólido</option>
        </select>
      </div>
      <div v-if="form.section_background.type === 'image'" class="mb-field mb-field--full">
        <label class="mb-label">URL de imagen</label>
        <input v-model="form.section_background.image" class="mb-input" placeholder="https://...">
      </div>
      <div v-if="form.section_background.type === 'video'" class="mb-field mb-field--full">
        <label class="mb-label">URL de video</label>
        <input v-model="form.section_background.video_url" class="mb-input" placeholder="https://...">
      </div>
      <div v-if="form.section_background.type === 'video'" class="mb-field mb-field--full">
        <label class="mb-label">Poster</label>
        <input v-model="form.section_background.poster" class="mb-input" placeholder="https://...">
      </div>
      <div class="mb-field mb-field--full">
        <div class="form-check form-switch">
          <input v-model="form.section_background.parallax" class="form-check-input" type="checkbox" id="mb-section-parallax">
          <label class="form-check-label" for="mb-section-parallax">Efecto Parallax</label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
});
</script>

<style scoped src="./_shared.css"></style>
