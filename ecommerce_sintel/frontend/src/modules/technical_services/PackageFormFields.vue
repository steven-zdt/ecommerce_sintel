<template>
  <div>
    <div class="row g-2 mb-2">
      <div class="col-12">
        <label class="form-label smaller mb-1 fw-semibold">Nombre <span class="text-danger">*</span></label>
        <input v-model="model.name" type="text" class="form-control form-control-sm" placeholder="Ej: Paquete Completo 8 camaras">
      </div>
      <div class="col-12">
        <label class="form-label smaller mb-1 fw-semibold">Descripcion</label>
        <textarea v-model="model.description" class="form-control form-control-sm" rows="2" placeholder="Que incluye este paquete..."></textarea>
      </div>
      <div class="col-6">
        <label class="form-label smaller mb-1 fw-semibold">Tipo de paquete</label>
        <input v-model="model.package_type" type="text" class="form-control form-control-sm" placeholder="Ej: basico, completo, premium">
      </div>
      <div class="col-6">
        <label class="form-label smaller mb-1 fw-semibold">Icono</label>
        <input v-model="model.icon" type="text" class="form-control form-control-sm" placeholder="bi-box-seam">
      </div>
      <div class="col-6">
        <label class="form-label smaller mb-1 fw-semibold">Precio base (COP)</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text">$</span>
          <input v-model.number="model.base_price" type="number" step="100" min="0" class="form-control">
        </div>
      </div>
      <div class="col-6">
        <label class="form-label smaller mb-1 fw-semibold">Duracion estimada (h)</label>
        <input v-model.number="model.estimated_duration" type="number" step="0.5" min="0" class="form-control form-control-sm" placeholder="Opcional">
      </div>
      <div class="col-12">
        <label class="form-label smaller mb-1 fw-semibold">Notas internas</label>
        <input v-model="model.notes" type="text" class="form-control form-control-sm" placeholder="Notas para el equipo admin (opcional)">
      </div>
    </div>

    <div class="d-flex gap-3 pt-1">
      <div class="form-check mb-0">
        <input v-model="model.is_default" class="form-check-input" type="checkbox" id="pkgDefault">
        <label class="form-check-label smaller" for="pkgDefault">Por defecto</label>
      </div>
      <div class="form-check mb-0">
        <input v-model="model.is_featured" class="form-check-input" type="checkbox" id="pkgFeatured">
        <label class="form-check-label smaller" for="pkgFeatured">Destacado</label>
      </div>
      <div class="form-check form-switch mb-0">
        <input v-model="model.is_active" class="form-check-input" type="checkbox" id="pkgActive" role="switch">
        <label class="form-check-label smaller" for="pkgActive">
          <span :class="model.is_active ? 'text-success fw-semibold' : 'text-danger fw-semibold'">
            {{ model.is_active ? 'Activo' : 'Inactivo' }}
          </span>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
const model = defineModel({ required: true });
</script>

<style scoped>
.smaller { font-size: 0.7rem; }
</style>
