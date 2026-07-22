<template>
  <div class="os-card">
    <div class="os-row"><span class="text-muted small">Servicio</span><span class="fw-semibold">{{ operation.order?.service_name }}</span></div>
    <div class="os-row"><span class="text-muted small">Cliente</span><span>{{ operation.order?.user_name }}</span></div>
    <div class="os-row"><span class="text-muted small">Direccion</span><span class="text-end">{{ operation.order?.address }}</span></div>
    <div class="os-row"><span class="text-muted small">Orden</span><code class="small">{{ operation.order?.uuid }}</code></div>
    <div class="os-row">
      <span class="text-muted small">Pago</span>
      <span class="badge" :class="operation.order?.is_paid ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning'">
        {{ operation.order?.is_paid ? 'Confirmado' : 'Pendiente' }}
      </span>
    </div>
    <div class="os-row"><span class="text-muted small">Total</span><span class="fw-bold">${{ fmt(operation.order?.total_amount) }} COP</span></div>
    <div class="os-row"><span class="text-muted small">Prioridad</span><span class="badge bg-light text-dark border">{{ operation.priority }}</span></div>

    <div v-if="contact" class="os-row">
      <span class="text-muted small">Contacto de visita</span>
      <span class="text-end">
        {{ contact.full_name }}
        <template v-if="contact.cargo">— {{ contact.cargo }}</template>
        <br><span class="text-muted small">{{ contact.phone_alt || contact.phone }}<template v-if="contact.email"> · {{ contact.email }}</template></span>
      </span>
    </div>

    <div v-if="quotation" class="os-row">
      <span class="text-muted small">Cotizacion</span>
      <span class="text-end small">
        <template v-if="quotation.rate_type">{{ quotation.rate_type }} — ${{ fmt(quotation.rate_amount) }}<br></template>
        <template v-if="parseFloat(quotation.discount_amount) > 0">Descuento: ${{ fmt(quotation.discount_amount) }}<br></template>
      </span>
    </div>

    <div v-if="attachments.length" class="os-row" style="flex-direction:column; align-items:flex-start; gap:6px">
      <span class="text-muted small">Adjuntos ({{ attachments.length }})</span>
      <div class="d-flex flex-wrap gap-2">
        <a v-for="att in attachments" :key="att.uuid" :href="att.file" target="_blank" rel="noopener"
           class="badge bg-light text-dark border text-decoration-none">
          <i class="bi bi-paperclip me-1"></i>{{ att.file_name }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
const props = defineProps({ operation: { type: Object, required: true } });
function fmt(v) { return new Intl.NumberFormat('es-CO').format(Math.round(parseFloat(v) || 0)); }
const contact = computed(() => props.operation.order?.contact_person || null);
const quotation = computed(() => props.operation.order?.quotation || null);
const attachments = computed(() => props.operation.order?.attachments || []);
</script>

<style scoped>
.os-card { background: #f9fafb; border-radius: 10px; padding: 12px 16px; }
.os-row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid #eef0f2; }
.os-row:last-child { border-bottom: none; }
</style>
