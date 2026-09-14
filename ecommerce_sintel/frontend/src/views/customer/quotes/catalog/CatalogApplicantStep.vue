<template>
  <div>
    <h1 class="step-title">Tus datos</h1>
    <p class="step-subtitle">Te enviaremos la cotización con el precio calculado a este correo.</p>

    <div class="row g-3">
      <div class="col-12">
        <label class="form-label small fw-semibold" for="applicantName">Nombre completo *</label>
        <input id="applicantName" v-model="wizard.applicant.client_name" type="text" class="form-control" placeholder="Nombre y apellido" />
      </div>
      <div class="col-12">
        <label class="form-label small fw-semibold" for="applicantEmail">Correo electrónico *</label>
        <input id="applicantEmail" v-model="wizard.applicant.client_email" type="email" class="form-control" placeholder="correo@ejemplo.com" />
      </div>
      <div class="col-12">
        <label class="form-label small fw-semibold" for="applicantValidUntil">Válida hasta *</label>
        <input id="applicantValidUntil" v-model="wizard.applicant.valid_until" type="date" class="form-control" :min="today" />
      </div>
      <div class="col-12">
        <label class="form-label small fw-semibold" for="applicantNotes">Notas (opcional)</label>
        <textarea id="applicantNotes" v-model="wizard.applicant.notes" class="form-control" rows="3" placeholder="Detalles adicionales sobre tu solicitud..."></textarea>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ wizard: { type: Object, required: true } });
const today = new Date().toISOString().slice(0, 10);
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 2rem; }
</style>
