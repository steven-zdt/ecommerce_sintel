<template>
  <div class="step-card">
    <h5 class="fw-bold mb-4">Informacion profesional</h5>
    <div class="row g-3">

      <div class="col-sm-6" v-if="needsTypeSelection">
        <label class="form-label small fw-bold">Tipo de profesional <span class="text-danger">*</span></label>
        <select v-model="form.user_type" class="form-select">
          <option value="">Selecciona...</option>
          <option value="TECHNICIAN">Tecnico</option>
          <option value="PROFESSIONAL">Profesional</option>
          <option value="SPECIALIST">Especialista</option>
          <option value="CONTRACTOR">Contratista</option>
        </select>
      </div>
      <div class="col-sm-6" v-else-if="upgradeAlreadyRequested">
        <label class="form-label small fw-bold">Tipo de profesional solicitado</label>
        <div class="form-control-plaintext">
          {{ verification?.requested_user_type }}
          <span class="badge bg-warning-subtle text-warning ms-1">{{ verification?.status }}</span>
        </div>
      </div>

      <div class="col-sm-6">
        <label class="form-label small fw-bold">Tipo de contratista</label>
        <input v-model="form.contractor_type" type="text" class="form-control" placeholder="Ej: Electricista residencial">
      </div>

      <div class="col-12">
        <label class="form-label small fw-bold">Biografia / Presentacion</label>
        <textarea v-model="form.bio" class="form-control" rows="4" placeholder="Describe tu experiencia y lo que ofreces..."></textarea>
      </div>

      <div class="col-sm-6">
        <label class="form-label small fw-bold">Tipo de documento</label>
        <select v-model="form.document_type" class="form-select">
          <option value="">Selecciona...</option>
          <option value="CC">Cedula de Ciudadania</option>
          <option value="CE">Cedula de Extranjeria</option>
          <option value="NIT">NIT</option>
          <option value="PP">Pasaporte</option>
        </select>
      </div>

      <div class="col-sm-6">
        <label class="form-label small fw-bold">Numero de documento</label>
        <input v-model="form.document" type="text" class="form-control">
      </div>

      <div class="col-sm-6">
        <label class="form-label small fw-bold">Fecha de nacimiento</label>
        <input v-model="form.birth_date" type="date" class="form-control">
      </div>

      <div class="col-sm-6">
        <label class="form-label small fw-bold">Ciudad</label>
        <input v-model="form.city" type="text" class="form-control">
      </div>

      <div class="col-sm-6">
        <label class="form-label small fw-bold">Pais</label>
        <input v-model="form.country" type="text" class="form-control" placeholder="Colombia">
      </div>

      <div class="col-12"><hr class="my-1"></div>

      <div class="col-sm-4">
        <label class="form-label small fw-bold">Tarifa por hora (COP)</label>
        <input v-model="form.hourly_rate" type="number" class="form-control" placeholder="0" min="0">
      </div>

      <div class="col-sm-4">
        <label class="form-label small fw-bold">Tarifa por dia (COP)</label>
        <input v-model="form.daily_rate" type="number" class="form-control" placeholder="0" min="0">
      </div>

      <div class="col-sm-4">
        <label class="form-label small fw-bold">Tarifa por proyecto (COP)</label>
        <input v-model="form.project_rate" type="number" class="form-control" placeholder="0" min="0">
      </div>

      <div class="col-sm-4">
        <label class="form-label small fw-bold">Moneda</label>
        <select v-model="form.currency" class="form-select">
          <option value="COP">COP</option>
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
          <option value="MXN">MXN</option>
        </select>
      </div>

    </div>
  </div>
</template>

<script setup>
defineProps({
  // Objeto del padre (step1) mutado in-place por los v-model de este paso --
  // misma referencia reactiva, el padre lo repuebla por completo al cargar
  // el perfil, este componente nunca lo reasigna.
  form: { type: Object, required: true },
  needsTypeSelection: { type: Boolean, required: true },
  upgradeAlreadyRequested: { type: Boolean, required: true },
  verification: { type: Object, default: null },
});
</script>
