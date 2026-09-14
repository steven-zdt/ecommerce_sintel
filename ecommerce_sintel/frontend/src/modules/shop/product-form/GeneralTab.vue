<template>
  <form @submit.prevent="$emit('submit')">
    <div class="mb-3">
      <label class="form-label small fw-semibold">Nombre <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required placeholder="Ej: Laptop XPS 15">
    </div>

    <div class="mb-3">
      <label class="form-label small fw-semibold">Resumen corto</label>
      <input v-model="form.short_description" type="text" class="form-control" maxlength="255"
             placeholder="Frase breve para tarjetas y resultados de busqueda">
      <div class="form-text d-flex justify-content-between">
        <span>Max 255 caracteres.</span>
        <span :class="(form.short_description || '').length > 220 ? 'text-warning' : 'text-muted'">
          {{ (form.short_description || '').length }}/255
        </span>
      </div>
    </div>

    <div class="row g-2 mb-3">
      <div class="col-8">
        <label class="form-label small fw-semibold">Categoria <span class="text-danger">*</span></label>
        <select v-model="form.category" class="form-select" required>
          <option value="" disabled>Seleccionar categoria...</option>
          <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
        </select>
      </div>
      <div class="col-4">
        <label class="form-label small fw-semibold">Condicion</label>
        <select v-model="form.condition" class="form-select">
          <option value="new">Nuevo</option>
          <option value="used">Usado</option>
          <option value="refurbished">Reacondicionado</option>
        </select>
      </div>
    </div>

    <div class="mb-3">
      <label class="form-label small fw-semibold">Marca</label>
      <select v-model="form.brand" class="form-select">
        <option :value="null">Sin marca</option>
        <option v-for="b in brands" :key="b.uuid" :value="b.uuid">{{ b.name }}</option>
      </select>
    </div>

    <div class="mb-3">
      <label class="form-label small fw-semibold">Descripcion</label>
      <textarea v-model="form.description" class="form-control" rows="3"
                placeholder="Descripcion completa del producto..."></textarea>
    </div>

    <div class="mb-3">
      <label class="form-label small fw-semibold">URL de video</label>
      <input v-model="form.video_url" type="url" class="form-control"
             placeholder="https://www.youtube.com/watch?v=...">
      <div class="form-text">YouTube o Vimeo.</div>
    </div>

    <!-- Inventario inicial: solo visible en CREATE -->
    <div v-if="localMode === 'create'" class="card border-0 p-3 mb-3 rounded-3" style="background:#f8fafc">
      <p class="small fw-semibold mb-2">
        <i class="bi bi-box-seam me-1 text-success"></i>
        Inventario de la variante principal
      </p>
      <div class="row g-2">
        <div class="col-4">
          <label class="form-label smaller mb-1 fw-semibold">Stock disponible</label>
          <input v-model.number="form.stock" type="number" min="0" class="form-control form-control-sm"
                 placeholder="0">
        </div>
        <div class="col-4">
          <label class="form-label smaller mb-1 fw-semibold">Precio base <span class="text-danger">*</span></label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="form.price" type="number" step="0.01" min="0.01" class="form-control"
                   required placeholder="0.00">
          </div>
        </div>
        <div class="col-4">
          <label class="form-label smaller mb-1 fw-semibold">Precio descuento</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="form.discounted_price" type="number" step="0.01" min="0"
                   class="form-control" placeholder="Opcional">
          </div>
        </div>
      </div>
      <div class="form-text mt-1">
        <i class="bi bi-info-circle me-1"></i>
        El SKU se genera automaticamente y se mostrara despues de guardar.
      </div>
    </div>

    <div class="row mb-3">
      <div class="col-6">
        <div class="form-check form-switch">
          <input v-model="form.is_active" class="form-check-input" type="checkbox" id="prodActive">
          <label class="form-check-label small" for="prodActive">Activo</label>
        </div>
      </div>
      <div class="col-6">
        <div class="form-check form-switch">
          <input v-model="form.is_featured" class="form-check-input" type="checkbox" id="prodFeatured">
          <label class="form-check-label small" for="prodFeatured">Destacado</label>
        </div>
      </div>
    </div>

    <!-- Footer CREATE: solo boton crear -->
    <div v-if="localMode === 'create'" class="d-flex gap-2 mt-3">
      <button type="submit" class="btn btn-primary flex-grow-1" :disabled="actionLoading">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-2"></span>
        <i v-else class="bi bi-plus-lg me-1"></i>
        Crear Producto
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="actionLoading">
        Cancelar
      </button>
    </div>

    <!-- Footer EDIT: guardar + cerrar -->
    <div v-else class="d-flex gap-2 mt-3">
      <button type="submit" class="btn btn-primary flex-grow-1" :disabled="actionLoading">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-2"></span>
        Guardar General
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </form>
</template>

<script setup>
defineProps({
  // Objeto del padre mutado in-place por los v-model de este tab -- el
  // padre lo repuebla por completo al cambiar de item/modo, y este tab
  // tambien lo comparte con SeoTab.vue (mismo `form`, un solo submit).
  form: { type: Object, required: true },
  localMode: { type: String, required: true },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] },
  actionLoading: { type: Boolean, default: false },
});
defineEmits(['submit', 'cancel', 'close']);
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
</style>
