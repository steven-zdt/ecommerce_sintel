<template>
  <form @submit.prevent="$emit('submit')">

    <!-- Nombre + Descripcion -->
    <div class="mb-3">
      <label class="form-label small fw-semibold">Nombre <span class="text-danger">*</span></label>
      <input v-model="form.name" type="text" class="form-control" required
             placeholder="Ej: Instalacion de Camaras IP">
    </div>

    <div class="mb-3">
      <label class="form-label small fw-semibold">Descripcion <span class="text-danger">*</span></label>
      <textarea v-model="form.description" class="form-control" rows="3" required
                placeholder="Describe el alcance del servicio..."></textarea>
    </div>

    <!-- "Alcance"/"Garantia"/"Cobertura" (form.scope/warranty/coverage_notes,
         Fase reingenieria SDP 2026-08-05) se eliminaron de aqui por ser
         redundantes con el editor inline de ContentBlocksTab.vue (pestaña
         "Contenido del Servicio", solo EDIT) -- mismo campo, dos editores
         cada uno. Los 3 se conservan en el estado (emptyForm/submit/watch)
         sin cambios: siguen viajando al backend y siguen siendo la fuente
         que ContentBlocksTab lee/actualiza via sus props/evento
         `field-saved`. -->

    <!-- Categoria + Nivel -->
    <div class="row g-2 mb-3">
      <div class="col-7">
        <label class="form-label small fw-semibold">Categoria</label>
        <select v-model="form.category" class="form-select">
          <option :value="null">Sin categoria</option>
          <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
        </select>
      </div>
      <div class="col-5">
        <label class="form-label small fw-semibold">Nivel</label>
        <select v-model="form.level" class="form-select">
          <option :value="null">Sin nivel</option>
          <option v-for="lvl in levels" :key="lvl.uuid" :value="lvl.uuid">{{ lvl.name }}</option>
        </select>
      </div>
    </div>

    <!-- Toggles (Activo, Destacado, Comprable) -->
    <div class="row mb-4">
      <div class="col-4">
        <div class="form-check form-switch">
          <input v-model="form.is_active" class="form-check-input" type="checkbox" id="svcActive">
          <label class="form-check-label small" for="svcActive">Activo</label>
        </div>
      </div>
      <div class="col-4">
        <div class="form-check form-switch">
          <input v-model="form.is_featured" class="form-check-input" type="checkbox" id="svcFeatured">
          <label class="form-check-label small" for="svcFeatured">Destacado</label>
        </div>
      </div>
      <div class="col-4">
        <div class="form-check form-switch">
          <input v-model="form.is_purchasable" class="form-check-input" type="checkbox" id="svcPurchasable">
          <label class="form-check-label small" for="svcPurchasable">Comprable</label>
        </div>
      </div>
    </div>

    <!-- SEO (2026-07-18, unificacion con Renting -- solo en EDIT, replica Equipment.meta_*) -->
    <div v-if="localMode === 'edit'" class="card border-0 p-3 mb-4 rounded-3" style="background:#f8fafc">
      <div class="small fw-semibold mb-2" style="color:#334155">
        <i class="bi bi-search me-1"></i>SEO
      </div>
      <div class="mb-2">
        <label class="form-label smaller mb-1">Meta titulo</label>
        <input v-model="form.meta_title" type="text" class="form-control form-control-sm" maxlength="70" placeholder="Titulo para buscadores (max. 70 caracteres)">
      </div>
      <div class="mb-2">
        <label class="form-label smaller mb-1">Meta descripcion</label>
        <textarea v-model="form.meta_description" class="form-control form-control-sm" rows="2" placeholder="Descripcion para buscadores"></textarea>
      </div>
      <div>
        <label class="form-label smaller mb-1">Palabras clave</label>
        <input v-model="form.meta_keywords" type="text" class="form-control form-control-sm" maxlength="255" placeholder="separadas, por, coma">
      </div>
    </div>

    <!-- Variante inicial (solo en CREATE) -- el precio SIEMPRE se ingresa
         manualmente por el admin, en cualquiera de los formularios del
         panel (instruccion explicita del usuario, 2026-08-14): no existe
         via de omitirlo/dejarlo automatico en ninguna pestana. -->
    <div v-if="localMode === 'create'" class="card border-0 p-3 mb-4 rounded-3" style="background:#fffbeb">
      <div class="d-flex align-items-center justify-content-between mb-2">
        <span class="small fw-semibold" style="color:#92400e">
          <i class="bi bi-currency-dollar me-1"></i>Variante principal
        </span>
      </div>

      <div class="mt-3">
        <!-- Estrategia pricing -->
        <div class="d-flex gap-3 mb-3" style="font-size:.82rem">
          <div class="form-check">
            <input v-model="initVar.pricing_strategy" class="form-check-input" type="radio" value="FIXED" id="initFixed">
            <label class="form-check-label" for="initFixed">Precio fijo</label>
          </div>
          <div class="form-check">
            <input v-model="initVar.pricing_strategy" class="form-check-input" type="radio" value="HOURLY" id="initHourly">
            <label class="form-check-label" for="initHourly">Por horas (SMLV)</label>
          </div>
          <div class="form-check">
            <input v-model="initVar.pricing_strategy" class="form-check-input" type="radio" value="DAILY" id="initDaily">
            <label class="form-check-label" for="initDaily">Por dias (SMLV)</label>
          </div>
        </div>

        <!-- Campos dinamicos segun estrategia -->
        <div v-if="initVar.pricing_strategy === 'FIXED'" class="row g-2">
          <div class="col-12">
            <label class="form-label smaller mb-1 fw-semibold">Precio fijo (COP)</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="initVar.fixed_price" type="number" step="100" min="0"
                     class="form-control" placeholder="250000">
            </div>
          </div>
        </div>

        <div v-else class="row g-2">
          <div class="col-6">
            <label class="form-label smaller mb-1 fw-semibold">
              {{ initVar.pricing_strategy === 'DAILY' ? 'Dias estimados' : 'Horas estimadas' }}
            </label>
            <input v-model.number="initVar.estimated_hours" type="number" step="0.5" min="0.5"
                   class="form-control form-control-sm" placeholder="Ej: 4">
          </div>
          <div class="col-6">
            <label class="form-label smaller mb-1 fw-semibold">Factor complejidad</label>
            <input v-model.number="initVar.complexity_factor" type="number" step="0.1" min="0.1" max="5"
                   class="form-control form-control-sm" placeholder="1.0">
          </div>
        </div>

        <div class="form-text" style="font-size:.7rem">
          El SKU y la variante default se generan automáticamente al guardar.
        </div>
      </div>
    </div>

    <!-- Variante principal (EDIT) -- eliminada por redundancia: duplicaba el
         editor de VariantsTab.vue (pestaña "Variantes"), que es el mas
         completo (incluye is_default/is_active/historial de precios,
         ausentes aqui) y queda como unica fuente de edicion de variantes en
         EDIT, mismo criterio aplicado a Alcance/Garantia/Cobertura arriba.
         El bloque de CREATE (initVar, arriba) NO es redundante -- es la
         unica forma de fijar la variante inicial al crear el servicio,
         VariantsTab no existe todavia en ese momento (necesita un uuid). -->

    <!-- Botones footer -->
    <div v-if="localMode === 'create'" class="d-flex gap-2 mt-3">
      <button type="submit" class="btn btn-primary flex-grow-1" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        <i v-else class="bi bi-plus-lg me-1"></i>
        Crear Servicio
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">
        Cancelar
      </button>
    </div>

    <div v-else class="d-flex gap-2 mt-3">
      <button type="submit" class="btn btn-primary flex-grow-1" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        Guardar Cambios
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </form>
</template>

<script setup>
defineProps({
  // `form`/`initVar` son objetos del padre mutados in-place por los v-model
  // de este tab (misma referencia reactiva, no una copia) -- el padre los
  // repuebla por completo al cambiar de item/modo, este tab nunca los
  // reasigna, solo escribe campos individuales.
  form: { type: Object, required: true },
  initVar: { type: Object, required: true },
  localMode: { type: String, required: true },
  categories: { type: Array, default: () => [] },
  levels: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});
defineEmits(['submit', 'cancel', 'close']);
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
</style>
