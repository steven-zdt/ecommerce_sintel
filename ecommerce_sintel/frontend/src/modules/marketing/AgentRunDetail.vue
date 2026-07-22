<template>
  <div class="agent-run-detail">
    <!-- Status Header -->
    <div class="alert alert-success border-0 d-flex align-items-start mb-4 rounded-3 shadow-sm">
      <i class="bi bi-check-circle-fill fs-5 me-3 text-success mt-1 flex-shrink-0"></i>
      <div class="flex-grow-1">
        <div class="fw-bold mb-1">Ejecución Exitosa</div>
        <div class="smaller text-muted">Procesado por <span class="fw-semibold text-capitalize">{{ run.llm_provider }}</span> el {{ formatDate(run.created_at) }}</div>
      </div>
    </div>

    <!-- Metadata Grid -->
    <div class="row g-3 mb-4">
      <div class="col-6">
        <div class="p-3 bg-light rounded-3 border border-light h-100">
          <div class="text-muted smaller mb-2 text-uppercase fw-semibold" style="letter-spacing: 0.5px;">
            <i class="bi bi-lightning me-1 text-warning"></i>Disparador
          </div>
          <div class="fw-bold text-dark text-uppercase small">{{ run.triggered_by || 'N/A' }}</div>
        </div>
      </div>
      <div class="col-6">
        <div class="p-3 bg-light rounded-3 border border-light h-100">
          <div class="text-muted smaller mb-2 text-uppercase fw-semibold" style="letter-spacing: 0.5px;">
            <i class="bi bi-robot me-1 text-info"></i>Proveedor
          </div>
          <div class="fw-bold text-dark text-capitalize small">{{ run.llm_provider || 'N/A' }}</div>
        </div>
      </div>
    </div>

    <!-- Decision Section -->
    <div class="mb-4">
      <h6 class="fw-bold mb-3 d-flex align-items-center text-uppercase small" style="letter-spacing: 0.5px;">
        <i class="bi bi-cpu me-2 text-primary"></i>Decisión del Agente
      </h6>
      
      <div class="bg-dark rounded-3 p-4 overflow-auto border border-secondary-subtle" style="max-height: 350px;">
        <pre class="text-success mb-0 small font-monospace"><code>{{ formattedDecision }}</code></pre>
      </div>
    </div>

    <!-- Info Box -->
    <div class="p-3 bg-info-subtle rounded-3 border border-info-subtle shadow-sm">
      <p class="mb-0 smaller text-info-emphasis d-flex align-items-start">
        <i class="bi bi-info-circle me-2 mt-0.5 flex-shrink-0"></i>
        <span>Esta decisión fue generada autónomamente por el Agente de Marketing analizando tendencias de stock y comportamiento de usuarios.</span>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  run: { type: Object, required: true }
});

const formattedDecision = computed(() => {
  try {
    const content = props.run.llm_decision;
    if (typeof content === 'string' && (content.startsWith('{') || content.startsWith('['))) {
      return JSON.stringify(JSON.parse(content), null, 2);
    }
    if (typeof content === 'object') {
      return JSON.stringify(content, null, 2);
    }
    return content || '{}';
  } catch {
    return props.run.llm_decision || '{}';
  }
});

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}
</script>

<style scoped>
.smaller { font-size: 0.75rem; }

.font-monospace {
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
  line-height: 1.5;
}

.agent-run-detail {
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

pre {
  margin: 0;
}

code {
  word-wrap: break-word;
  white-space: pre-wrap;
}
</style>
