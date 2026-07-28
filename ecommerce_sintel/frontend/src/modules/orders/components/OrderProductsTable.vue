<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h6 class="mb-0">Productos & Servicios</h6>
          <p class="small text-muted mb-0">Detalle del contenido de la orden.</p>
        </div>
      </div>

      <div v-if="!items?.length" class="text-center text-muted py-5">
        No se encontraron productos o servicios.
      </div>

      <div v-else class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase">
            <tr>
              <th>SKU</th>
              <th>Producto</th>
              <th>Tipo</th>
              <th class="text-center">Cantidad</th>
              <th class="text-end">Precio</th>
              <th class="text-end">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.uuid">
              <td class="text-muted small">{{ item.sku }}</td>
              <td>
                <div class="fw-semibold">{{ item.item_name }}</div>
              </td>
              <td>
                <span :class="['badge', badgeClass(item.type)]">{{ itemTypeLabel(item.type) }}</span>
              </td>
              <td class="text-center">{{ item.quantity }}</td>
              <td class="text-end">${{ formatCurrency(item.price) }}</td>
              <td class="text-end fw-semibold">${{ formatCurrency(item.quantity * item.price) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatCOP } from '@/utils/money';

const props = defineProps({ items: { type: Array, default: () => [] } });

const itemTypeLabel = (type) => {
  const normalized = String(type || 'PRODUCT').toUpperCase();
  if (normalized === 'SERVICE') return 'Servicio';
  if (normalized === 'RENTING') return 'Renta';
  return 'Producto';
};

const badgeClass = (type) => {
  const normalized = String(type || 'PRODUCT').toUpperCase();
  if (normalized === 'SERVICE') return 'badge bg-info text-dark';
  if (normalized === 'RENTING') return 'badge bg-warning text-dark';
  return 'badge bg-primary';
};

const formatCurrency = (value) => formatCOP(value);
</script>
