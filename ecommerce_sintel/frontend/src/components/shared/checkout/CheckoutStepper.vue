<template>
  <nav class="cks-stepper" :aria-label="ariaLabel">
    <component
      :is="clickable && i + 1 <= current ? 'button' : 'div'"
      v-for="(s, i) in steps"
      :key="s"
      :type="clickable && i + 1 <= current ? 'button' : null"
      class="cks-step"
      :class="{ 'cks-step--active': current === i + 1, 'cks-step--done': current > i + 1, 'cks-step--clickable': clickable && i + 1 <= current }"
      @click="clickable && i + 1 <= current && emit('update:current', i + 1)"
    >
      <div class="cks-step-circle">
        <i v-if="current > i + 1" class="bi bi-check-lg"></i>
        <span v-else>{{ i + 1 }}</span>
      </div>
      <span class="cks-step-label d-none d-sm-inline">{{ s }}</span>
    </component>
    <div class="cks-track">
      <div class="cks-track-fill" :style="{ width: (Math.max(current - 1, 0) / Math.max(steps.length - 1, 1) * 100) + '%' }"></div>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  steps:     { type: Array, required: true },
  current:   { type: Number, required: true },
  clickable: { type: Boolean, default: false },
  ariaLabel: { type: String, default: 'Progreso del pago' },
});
const emit = defineEmits(['update:current']);
</script>

<style scoped>
.cks-stepper { position: relative; display: flex; justify-content: space-between; padding: 4px 4px 20px; }
.cks-track { position: absolute; top: 15px; left: 30px; right: 30px; height: 3px; background: #e5e7eb; border-radius: 2px; z-index: 0; }
.cks-track-fill { height: 100%; background: var(--checkout-accent, #7c3aed); border-radius: 2px; transition: width .3s ease; }
.cks-step { display: flex; flex-direction: column; align-items: center; gap: 4px; position: relative; z-index: 1; flex: 1; border: 0; background: none; padding: 0; }
.cks-step--clickable { cursor: pointer; }
.cks-step--clickable:hover .cks-step-circle { box-shadow: 0 0 0 4px var(--checkout-accent-ring, rgba(124,58,237,.15)); }
.cks-step-circle {
  width: 30px; height: 30px; border-radius: 50%; background: #fff;
  border: 2px solid #e5e7eb; color: #9ca3af;
  display: flex; align-items: center; justify-content: center;
  font-size: .8rem; font-weight: 700;
}
.cks-step--active .cks-step-circle { background: var(--checkout-accent, #7c3aed); color: #fff; border-color: var(--checkout-accent, #7c3aed); box-shadow: 0 0 0 4px var(--checkout-accent-ring, rgba(124,58,237,.2)); }
.cks-step--done .cks-step-circle { background: #16a34a; color: #fff; border-color: #16a34a; }
.cks-step-label { font-size: .68rem; color: #9ca3af; font-weight: 500; text-align: center; }
.cks-step--active .cks-step-label { color: var(--checkout-accent, #7c3aed); font-weight: 700; }
.cks-step--done .cks-step-label { color: #16a34a; }
</style>
