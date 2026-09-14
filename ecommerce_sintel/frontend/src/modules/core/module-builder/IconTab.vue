<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-star me-2"></i>Iconografía</div>
    <div class="mb-grid">
      <div class="mb-field mb-field--full">
        <label class="mb-label">Clase Bootstrap Icons</label>
        <div class="d-flex gap-2 align-items-center">
          <div class="mb-icon-preview" :style="{ background: form.color_primary + '22', color: form.color_primary }">
            <i :class="['bi', form.custom_icon || 'bi-grid']"></i>
          </div>
          <input v-model="form.custom_icon" class="mb-input" placeholder="bi-shop" style="flex:1">
        </div>
      </div>
    </div>
    <div class="mb-subsection mt-3">Íconos frecuentes</div>
    <div class="mb-icon-grid">
      <button
        v-for="ic in COMMON_ICONS" :key="ic"
        :class="['mb-icon-btn', form.custom_icon === ic && 'active']"
        @click="form.custom_icon = ic"
        :title="ic"
      >
        <i :class="['bi', ic]"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
});

const COMMON_ICONS = [
  'bi-shop','bi-grid','bi-tools','bi-truck','bi-star','bi-heart','bi-award','bi-trophy',
  'bi-lightning','bi-gem','bi-briefcase','bi-building','bi-people','bi-chat','bi-phone',
  'bi-envelope','bi-globe','bi-camera','bi-laptop','bi-cpu','bi-shield-check',
  'bi-graph-up','bi-cash-stack','bi-clock','bi-calendar3','bi-box-seam','bi-basket',
  'bi-tag','bi-layers','bi-bookmark-star',
];
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
/* ── Icon picker ─────────────────────────────────────────────────────────── */
.mb-icon-preview {
  width: 44px; height: 38px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.mb-icon-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.mb-icon-btn {
  width: 36px; height: 34px; border: 1px solid #e2e8f0; border-radius: 6px;
  background: #f8fafc; cursor: pointer; font-size: 1rem; color: #475569;
  transition: background .12s, border-color .12s, color .12s;
  display: flex; align-items: center; justify-content: center;
}
.mb-icon-btn:hover  { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
.mb-icon-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }
</style>
