<template>
  <section v-if="availability" class="availability-section">
    <div class="container-xl">
      <h2>Disponibilidad</h2>
      <div class="alert" :class="availability.status === 'available' ? 'alert-success' : 'alert-warning'">
        <strong>{{ availability.status_label }}</strong>
        <p class="mb-0">{{ availability.status_detail }}</p>
      </div>
      <div class="row g-3 mt-3">
        <div class="col-md-4">
          <div class="card">
            <div class="card-body">
              <p class="text-muted mb-2">Total en stock</p>
              <h3>{{ availability.total_stock }}</h3>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card">
            <div class="card-body">
              <p class="text-muted mb-2">Disponibles ahora</p>
              <h3>{{ availability.available_now }}</h3>
            </div>
          </div>
        </div>
        <div v-if="availability.next_available_date" class="col-md-4">
          <div class="card">
            <div class="card-body">
              <p class="text-muted mb-2">Próximo disponible</p>
              <h3>{{ availability.next_available_date }}</h3>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  availability: Object
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
