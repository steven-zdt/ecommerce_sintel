<template>
  <div class="costos-panel">
    <!-- Loading state -->
    <div v-if="loading" class="skeleton-loading">
      <div class="skeleton" style="height: 200px"></div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="alert alert-danger alert-sm mb-0">
      <i class="bi bi-exclamation-circle me-2"></i>
      {{ error }}
    </div>

    <!-- Sin datos aun (variante no resuelta / primer render antes del fetch) -->
    <div v-else-if="!quotation" class="text-muted small py-3 text-center">
      Selecciona una variante para ver el calculo de costos.
    </div>

    <!-- Quotation Display -->
    <div v-else class="card border-0 bg-light rounded-3 p-0 overflow-hidden">
      <!-- Header -->
      <div class="card-header bg-white border-0 px-4 py-3">
        <div class="d-flex align-items-center justify-content-between">
          <span class="fw-semibold">Cálculo de Costos (Ejemplo)</span>
          <button 
            v-if="showRulesButton"
            type="button" 
            class="btn btn-sm btn-outline-secondary"
            @click="showRules = !showRules"
          >
            <i :class="`bi bi-chevron-${showRules ? 'up' : 'down'} me-1`"></i>
            Reglas de Costo
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="card-body px-4 py-3">
        <!-- Labor Cost -->
        <div class="mb-3">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="text-muted small">
              <i class="bi bi-person-check me-1"></i>Mano de Obra ({{ quotation.pricing_strategy }})
            </span>
          </div>
          <div class="ps-3 border-start border-secondary">
            <div class="row g-3 mb-2">
              <div class="col-6">
                <small class="text-muted d-block">Tarifa base por hora</small>
                <strong>${{ formatNumber(quotation.breakdown?.base_hourly_rate) }}</strong>
              </div>
              <div class="col-6">
                <small class="text-muted d-block">Duración</small>
                <strong>{{ quotation.breakdown?.duration }} {{ quotation.pricing_strategy === 'DAILY' ? 'días' : 'horas' }}</strong>
              </div>
              <div class="col-6">
                <small class="text-muted d-block">Complejidad</small>
                <strong>{{ quotation.breakdown?.complexity }}x</strong>
              </div>
              <div class="col-6">
                <small class="text-muted d-block">Cálculo</small>
                <code style="font-size: 11px">{{ quotation.breakdown?.labor_calculation }}</code>
              </div>
            </div>
            <div class="d-flex justify-content-between pt-2 border-top">
              <strong>Subtotal Mano de Obra:</strong>
              <strong style="color: #2563eb">${{ formatNumber(quotation.labor_cost) }}</strong>
            </div>
          </div>
        </div>

        <!-- Materials -->
        <div v-if="quotation.breakdown?.materials?.length" class="mb-3">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="text-muted small">
              <i class="bi bi-box me-1"></i>Materiales
            </span>
          </div>
          <div class="ps-3 border-start border-secondary">
            <div v-for="mat in quotation.breakdown.materials" :key="mat.name" class="d-flex justify-content-between mb-2 small">
              <span>{{ mat.name }} × {{ mat.qty }}</span>
              <strong>${{ formatNumber(mat.subtotal) }}</strong>
            </div>
            <div class="d-flex justify-content-between pt-2 border-top">
              <strong>Subtotal Materiales:</strong>
              <strong style="color: #f59e0b">${{ formatNumber(quotation.material_cost) }}</strong>
            </div>
          </div>
        </div>

        <!-- Base Amount -->
        <div class="mb-3 p-2 rounded" style="background: #fffbeb">
          <div class="d-flex justify-content-between">
            <span class="small">Base (Mano de obra + Materiales)</span>
            <strong>${{ formatNumber(quotation.base_amount) }}</strong>
          </div>
        </div>

        <!-- Discount -->
        <div v-if="quotation.discount_amount > 0" class="mb-3">
          <div class="d-flex justify-content-between mb-1 small">
            <span>Descuento ({{ quotation.discount_pct }}%)</span>
            <strong style="color: #16a34a">-${{ formatNumber(quotation.discount_amount) }}</strong>
          </div>
        </div>

        <!-- Cost Rules Additions/Subtractions -->
        <div v-if="showRules && quotation.breakdown?.cost_rules?.length" class="mb-3 p-2 rounded" style="background: #f3f4f6">
          <small class="fw-semibold mb-2 d-block">Reglas de Costo Aplicadas:</small>
          <div v-for="rule in quotation.breakdown.cost_rules" :key="rule.name" class="d-flex justify-content-between small mb-1">
            <span>{{ rule.name }} ({{ rule.context }})</span>
            <strong :style="{ color: rule.impact > 0 ? '#dc2626' : '#16a34a' }">
              {{ rule.impact > 0 ? '+' : '' }}${{ formatNumber(Math.abs(rule.impact)) }}
            </strong>
          </div>
          <div class="d-flex justify-content-between pt-2 border-top small mt-2">
            <strong>Total Reglas:</strong>
            <strong :style="{ color: quotation.breakdown?.total_additions > quotation.breakdown?.total_discounts_rules ? '#dc2626' : '#16a34a' }">
              ${{ formatNumber((quotation.breakdown?.total_additions || 0) - (quotation.breakdown?.total_discounts_rules || 0)) }}
            </strong>
          </div>
        </div>

        <!-- Subtotal After Rules -->
        <div class="mb-3 p-2 rounded" style="background: #f0fdf4">
          <div class="d-flex justify-content-between">
            <span class="small">Subtotal (después de reglas)</span>
            <strong>${{ formatNumber(quotation.breakdown?.subtotal_after_rules || quotation.base_amount - quotation.discount_amount) }}</strong>
          </div>
        </div>

        <!-- IVA -->
        <div class="mb-3">
          <div class="d-flex justify-content-between align-items-center mb-1 small">
            <span>IVA ({{ quotation.iva_rate }}%)</span>
            <strong style="color: #9ca3af">${{ formatNumber(quotation.iva_amount) }}</strong>
          </div>
        </div>

        <!-- Total Price (Final) -->
        <div class="p-3 rounded-3" style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white">
          <div class="d-flex justify-content-between align-items-center">
            <span class="fw-semibold">TOTAL ESTIMADO</span>
            <strong style="font-size: 1.5rem">${{ formatNumber(quotation.total_price) }}</strong>
          </div>
          <small class="d-block mt-2 opacity-75">Incluye IVA. Precio final puede variar según ubicación.</small>
        </div>
      </div>

      <!-- Footer Note -->
      <div class="card-footer bg-white border-0 px-4 py-2">
        <small class="text-muted">
          <i class="bi bi-info-circle me-1"></i>
          Calculado automáticamente basado en configuración SMLV y reglas de costo activas.
        </small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import useApi from '@/composables/useApi'
import { formatCOP } from '@/utils/money'

interface Quotation {
  variant_id: string
  sku: string
  service_name: string
  pricing_strategy: string
  labor_cost: number
  material_cost: number
  base_amount: number
  discount_pct: number
  discount_amount: number
  iva_rate: number
  iva_amount: number
  total_price: number
  breakdown: any
}

const props = defineProps<{
  variantUuid?: string
  duration?: number | null
  discount?: number | null
}>()

const emit = defineEmits<{
  loaded: [quotation: Quotation]
  error: [error: string]
}>()

const api = useApi()

const quotation = ref<Quotation | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const showRules = ref(false)
const showRulesButton = computed(() => quotation.value?.breakdown?.cost_rules?.length > 0)

const formatNumber = (num: number): string => {
  if (!num) return '0'
  return formatCOP(num)
}

const fetchQuotation = async () => {
  if (!props.variantUuid) return

  loading.value = true
  error.value = null

  try {
    const params = new URLSearchParams({
      variant_uuid: props.variantUuid,
      ...(props.duration && { duration: props.duration.toString() }),
      ...(props.discount && { discount_pct: props.discount.toString() }),
    })

    const { data } = await api.get(`services/services/quotation/?${params.toString()}`)
    quotation.value = data
    emit('loaded', data)
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : 'Error al calcular cotización'
    error.value = errorMsg
    emit('error', errorMsg)
  } finally {
    loading.value = false
  }
}

// Watch for changes in props
watch(
  () => [props.variantUuid, props.duration, props.discount],
  () => fetchQuotation(),
  { immediate: true }
)

onMounted(() => {
  fetchQuotation()
})
</script>

<style scoped>
.costos-panel .skeleton-loading .skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 8px;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.costos-panel .alert-sm {
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 8px;
}

.costos-panel code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}
</style>
