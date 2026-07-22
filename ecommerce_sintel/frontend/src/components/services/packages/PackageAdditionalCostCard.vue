<template>
  <div class="cost-card" :class="{ selected, required: cost.is_required }">
    <label class="cost-card-check">
      <input
        type="checkbox"
        :checked="selected"
        :disabled="cost.is_required"
        @change="$emit('toggle', !selected)"
      >
      <span class="cost-card-checkmark"><i class="bi bi-check-lg"></i></span>
    </label>

    <div class="cost-card-body">
      <div class="cost-card-head">
        <strong>{{ cost.name }}</strong>
        <span class="cost-card-type">{{ cost.cost_type_display }}</span>
      </div>
      <p v-if="cost.description" class="cost-card-desc">{{ cost.description }}</p>
      <span v-if="cost.is_required" class="cost-card-required-tag">Obligatorio</span>
    </div>

    <div class="cost-card-price-col">
      <strong>{{ formatCOP(cost.price) }}</strong>
      <span class="cost-card-unit">{{ cost.unit_display }}</span>
      <div v-if="selected" class="cost-card-qty">
        <button type="button" @click="$emit('quantity-change', Math.max(1, quantity - 1))">-</button>
        <span>{{ quantity }}</span>
        <button type="button" @click="$emit('quantity-change', quantity + 1)">+</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  cost: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  quantity: { type: Number, default: 1 },
});
defineEmits(['toggle', 'quantity-change']);

function formatCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) return '';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(number);
}
</script>

<style scoped>
.cost-card {
  display: flex; align-items: center; gap: .75rem;
  border: 1px solid #e2e8f0; border-radius: 12px; padding: .75rem;
  background: #fff;
}
.cost-card.selected { border-color: #d97706; background: #fffbeb; }
.cost-card-check { position: relative; flex-shrink: 0; cursor: pointer; }
.cost-card-check input { position: absolute; opacity: 0; width: 22px; height: 22px; margin: 0; cursor: pointer; }
.cost-card-checkmark {
  width: 22px; height: 22px; border-radius: 6px; border: 1.5px solid #cbd5e1;
  display: flex; align-items: center; justify-content: center; color: transparent;
  background: #fff; transition: all .15s ease;
}
.cost-card-check input:checked + .cost-card-checkmark { background: #d97706; border-color: #d97706; color: #fff; }
.cost-card-check input:disabled + .cost-card-checkmark { opacity: .6; }
.cost-card-body { flex: 1; min-width: 0; }
.cost-card-head { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.cost-card-head strong { color: #0f172a; font-size: .86rem; }
.cost-card-type {
  background: #f1f5f9; color: #64748b; border-radius: 999px;
  padding: .12rem .5rem; font-size: .66rem; font-weight: 700;
}
.cost-card-desc { color: #64748b; font-size: .76rem; margin: .2rem 0 0; }
.cost-card-required-tag { color: #b45309; font-size: .7rem; font-weight: 700; }
.cost-card-price-col { text-align: right; flex-shrink: 0; }
.cost-card-price-col strong { display: block; color: #0f172a; font-size: .86rem; }
.cost-card-unit { display: block; color: #94a3b8; font-size: .7rem; }
.cost-card-qty { display: flex; align-items: center; gap: .4rem; margin-top: .35rem; justify-content: flex-end; }
.cost-card-qty button {
  width: 22px; height: 22px; border-radius: 6px; border: 1px solid #e2e8f0; background: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 800; color: #475569;
}
.cost-card-qty span { min-width: 18px; text-align: center; font-weight: 700; color: #0f172a; font-size: .8rem; }
</style>
