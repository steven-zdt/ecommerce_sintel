<template>
  <div v-if="includedServices.length || optionalServices.length" class="eq-service-columns">
    <article v-if="includedServices.length" class="eq-service-card">
      <h3><i class="bi bi-hand-thumbs-up text-primary"></i>Servicios incluidos</h3>
      <ul>
        <li v-for="service in includedServices" :key="service.uuid">
          <IconRenderer v-if="service.icon" :icon="service.icon" extra-class="eq-service-icon" />
          <div>
            <strong>{{ service.title }}</strong>
            <p v-if="service.description">{{ service.description }}</p>
          </div>
        </li>
      </ul>
    </article>

    <article v-if="optionalServices.length" class="eq-service-card">
      <h3><i class="bi bi-plus-circle text-success"></i>Servicios opcionales</h3>
      <ul>
        <li v-for="service in optionalServices" :key="service.uuid">
          <IconRenderer v-if="service.icon" :icon="service.icon" extra-class="eq-service-icon" />
          <div class="flex-grow-1">
            <strong>{{ service.title }}</strong>
            <p v-if="service.description">{{ service.description }}</p>
          </div>
          <span v-if="service.price" class="eq-service-price">{{ formatCOP(service.price) }}</span>
        </li>
      </ul>
    </article>
  </div>
</template>

<script setup>
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { formatCOP as formatCOPBase } from '@/utils/money';

defineProps({
  includedServices: { type: Array, default: () => [] },
  optionalServices: { type: Array, default: () => [] },
});

function formatCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) return '';
  return formatCOPBase(number, { withSymbol: true });
}
</script>

<style scoped>
.eq-service-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
.eq-service-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1rem; }
.eq-service-card h3 {
  display: flex; align-items: center; gap: .5rem;
  color: #0f172a; font-size: .95rem; font-weight: 850; margin: 0 0 .6rem;
}
.eq-service-card ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .6rem; }
.eq-service-card li { display: flex; gap: .5rem; align-items: flex-start; }
.eq-service-icon { color: #2563eb; margin-top: .15rem; flex-shrink: 0; }
.eq-service-card strong { display: block; color: #0f172a; font-size: .84rem; }
.eq-service-card p { color: #64748b; font-size: .78rem; margin: .15rem 0 0; }
.eq-service-price { color: #16a34a; font-weight: 800; font-size: .8rem; white-space: nowrap; }
@media (max-width: 767px) {
  .eq-service-columns { grid-template-columns: 1fr; }
}
</style>
