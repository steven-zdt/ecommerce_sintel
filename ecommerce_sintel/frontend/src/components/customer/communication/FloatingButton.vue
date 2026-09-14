<template>
  <button
    type="button"
    class="comm-fab"
    :class="{ 'comm-fab--open': isOpen }"
    :aria-expanded="isOpen ? 'true' : 'false'"
    aria-haspopup="dialog"
    aria-controls="communication-panel"
    :aria-label="isOpen ? 'Cerrar centro de comunicación' : 'Abrir centro de comunicación'"
    @click="$emit('toggle')"
  >
    <span class="comm-fab-icon">
      <i class="bi bi-x-lg" v-if="isOpen"></i>
      <i class="bi bi-chat-dots-fill" v-else></i>
    </span>
  </button>
</template>

<script setup>
defineProps({
  isOpen: { type: Boolean, default: false },
});
defineEmits(['toggle']);
</script>

<style scoped>
/* Paleta corporativa Sintel (gradiente azul, el mismo de CustomerNavbar.vue
   y del sidebar admin) -- deliberadamente NO el verde de WhatsApp, ver
   requisito 2 del Centro de Comunicacion. */
.comm-fab {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: #fff;
  box-shadow: 0 8px 24px rgba(30, 58, 138, 0.35);
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.comm-fab:hover,
.comm-fab:focus-visible {
  transform: scale(1.06);
  box-shadow: 0 10px 28px rgba(30, 58, 138, 0.45);
}

.comm-fab:focus-visible {
  outline: 3px solid #93c5fd;
  outline-offset: 3px;
}

.comm-fab--open {
  background: linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%);
}

.comm-fab-icon {
  font-size: 1.5rem;
  line-height: 1;
  display: flex;
}

@media (prefers-reduced-motion: reduce) {
  .comm-fab {
    transition: none;
  }
  .comm-fab:hover,
  .comm-fab:focus-visible {
    transform: none;
  }
}
</style>
