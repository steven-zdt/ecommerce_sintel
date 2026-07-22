<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h6 class="mb-0">Historial</h6>
          <p class="small text-muted mb-0">Registro de acciones realizadas sobre la orden.</p>
        </div>
      </div>

      <div v-if="history.length" class="table-responsive">
        <table class="table table-sm mb-0">
          <thead class="table-light small text-uppercase">
            <tr>
              <th>Fecha</th>
              <th>Usuario</th>
              <th>Acción</th>
              <th>Comentario</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in history" :key="entry.id">
              <td class="small text-muted">{{ formatDate(entry.timestamp) }}</td>
              <td>{{ entry.user || 'Sistema' }}</td>
              <td>{{ entry.action }}</td>
              <td class="small text-muted">{{ entry.comment || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="text-center text-muted py-4">El historial aún no tiene registros.</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({ order: { type: Object, required: true } });
const history = ref([
  { id: 1, timestamp: props.order?.created_at, user: 'Sistema', action: 'Orden creada', comment: 'Estado inicial' },
]);

const formatDate = (value) => {
  if (!value) return 'N/D';
  return new Date(value).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};
</script>
