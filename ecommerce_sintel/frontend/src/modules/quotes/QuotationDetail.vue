<template>
  <div class="quotation-detail">
    <!-- Resumen -->
    <div class="card bg-light border-0 mb-4">
      <div class="card-body p-4">
        <div class="row align-items-center">
          <div class="col-md-7">
            <h6 class="text-muted text-uppercase smaller fw-bold mb-1">Información del Cliente</h6>
            <h5 class="fw-bold text-dark mb-1">{{ quotation.client_name }}</h5>
            <div class="text-muted small">
              <i class="bi bi-envelope me-1"></i> {{ quotation.client_email }}
            </div>
            <div class="mt-3">
              <span class="text-muted small d-block">Notas:</span>
              <p class="mb-0 small italic" v-if="quotation.notes">{{ quotation.notes }}</p>
              <p class="mb-0 small text-muted italic" v-else>Sin observaciones adicionales.</p>
            </div>
          </div>
          <div class="col-md-5 text-md-end mt-3 mt-md-0">
            <div class="mb-2">
              <span class="text-muted small me-2">Estado:</span>
              <span 
                class="badge border rounded-pill fw-medium"
                :class="enums.cssClass('quote-statuses', quotation.status, 'bg-light text-secondary')"
              >
                {{ enums.label('quote-statuses', quotation.status, quotation.status) }}
              </span>
            </div>
            <div>
              <span class="text-muted small me-2">Vence:</span>
              <span class="fw-bold text-dark">{{ formatDate(quotation.valid_until) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Items (Productos) -->
    <div v-if="quotation.items && quotation.items.length" class="mb-4">
      <h6 class="fw-bold mb-3 d-flex align-items-center">
        <i class="bi bi-box me-2 text-primary"></i>
        Productos ({{ quotation.items.length }})
      </h6>
      <div class="table-responsive rounded-3 border">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small">
            <tr>
              <th class="ps-3 py-2">Producto</th>
              <th class="py-2 text-center">Cant.</th>
              <th class="py-2 text-end">Unitario</th>
              <th class="py-2 text-end pe-3">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in quotation.items" :key="item.uuid">
              <td class="ps-3">
                <div class="fw-medium text-dark">{{ item.product_name }}</div>
                <div class="text-muted smaller">{{ item.sku }}</div>
              </td>
              <td class="text-center">{{ item.quantity }}</td>
              <td class="text-end">{{ formatCurrency(item.unit_price) }}</td>
              <td class="text-end pe-3 fw-bold">{{ formatCurrency(item.subtotal) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Servicios -->
    <div v-if="quotation.services && quotation.services.length" class="mb-4">
      <h6 class="fw-bold mb-3 d-flex align-items-center">
        <i class="bi bi-tools me-2 text-primary"></i>
        Servicios Técnicos ({{ quotation.services.length }})
      </h6>
      <div class="list-group rounded-3 border">
        <div 
          v-for="svc in quotation.services" 
          :key="svc.uuid"
          class="list-group-item p-3"
        >
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <div class="fw-bold text-dark">{{ svc.service_name }}</div>
              <div class="text-muted smaller">Mano de obra ({{ svc.hours }}h)</div>
            </div>
            <div class="text-end">
              <div class="fw-bold text-dark">{{ formatCurrency(svc.subtotal) }}</div>
            </div>
          </div>
          
          <!-- Materiales del servicio -->
          <div v-if="svc.materials && svc.materials.length" class="mt-2 pt-2 border-top">
            <div class="text-muted smaller fw-bold mb-2">MATERIALES REQUERIDOS:</div>
            <div class="row g-2">
              <div v-for="mat in svc.materials" :key="mat.uuid" class="col-12">
                <div class="d-flex justify-content-between smaller">
                  <span class="text-muted">
                    <i class="bi bi-dot"></i> {{ mat.quantity }}x {{ mat.material_name }}
                  </span>
                  <span class="text-muted">{{ formatCurrency(mat.subtotal) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Totales -->
    <div class="card border-0 bg-primary-subtle mb-4">
      <div class="card-body p-4">
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted">Subtotal Productos</span>
          <span class="text-dark">{{ formatCurrency(quotation.subtotal_products) }}</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted">Subtotal Servicios</span>
          <span class="text-dark">{{ formatCurrency(quotation.subtotal_services) }}</span>
        </div>
        <div class="d-flex justify-content-between border-top border-primary pt-2 mt-2">
          <span class="fw-bold text-primary">TOTAL COTIZACIÓN</span>
          <span class="fw-bold text-primary fs-4">{{ formatCurrency(quotation.total_amount) }}</span>
        </div>
      </div>
    </div>

    <!-- Botones -->
    <div class="d-grid gap-2">
      <button class="btn btn-primary py-2" @click="$emit('download', quotation)">
        <i class="bi bi-file-pdf me-2"></i> Descargar PDF de Cotización
      </button>
    </div>
  </div>
</template>

<script setup>
import { useEnums } from '@/composables/useEnums';
import { formatCOP } from '@/utils/money';
const props = defineProps({
  quotation: { type: Object, required: true }
});

defineEmits(['download']);

const enums = useEnums();

function formatCurrency(value) {
  return formatCOP(value, { withSymbol: true });
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  });
}
</script>

<style scoped>
.smaller {
  font-size: 0.7rem;
}
.italic {
  font-style: italic;
}
</style>
