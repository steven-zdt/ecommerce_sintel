<template>
  <div class="op-board">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div>
        <h4 class="fw-bold mb-1">{{ title }}</h4>
        <p v-if="subtitle" class="text-muted mb-0">{{ subtitle }}</p>
      </div>
      <button v-if="showRefresh" class="btn btn-outline-primary" :disabled="loading" @click="$emit('refresh')">
        <i class="bi bi-arrow-clockwise me-2"></i>Actualizar
      </button>
    </div>

    <div v-if="cards.length" class="row g-3 mb-4">
      <div v-for="card in cards" :key="card.label" class="col-6 col-md-3">
        <div class="card border-0 shadow-sm p-3" :class="{ 'border-start border-4 border-danger': card.danger }">
          <div class="small text-muted">{{ card.label }}</div>
          <div class="fs-3 fw-bold" :class="{ 'text-danger': card.danger }">{{ card.value }}</div>
        </div>
      </div>
    </div>

    <slot />
  </div>
</template>

<script setup>
// BaseOperationBoard -- cascaron compartido (encabezado + fila de metricas)
// de los 4 tableros de operaciones (Shop/Renting/Servicios/Admin general),
// que repetian este mismo marcado casi al caracter (ver AUDITORIA/07_FRONTEND.md
// FE-M4/FE-H1). La tabla, los filtros y el panel de detalle SI difieren
// genuinamente por dominio (columnas, acciones y logica de negocio propias
// de cada uno) -- eso se queda en cada board, expuesto via el slot por
// defecto, en vez de forzar una abstraccion falsa sobre lo que no es
// realmente identico entre los 4.
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  cards: { type: Array, default: () => [] }, // [{ label, value, danger }]
  loading: { type: Boolean, default: false },
  showRefresh: { type: Boolean, default: true },
});
defineEmits(['refresh']);
</script>

<style scoped>
.op-board { padding: 0; }
</style>
