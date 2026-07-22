<template>
  <div class="sv-spec-table">
    <div v-for="spec in specs" :key="spec.label">
      <span>{{ spec.label }}</span>
      <strong>{{ spec.value }}</strong>
    </div>
  </div>
</template>

<script setup>
defineProps({
  specs: { type: Array, default: () => [] }, // [{ label, value }]
});
</script>

<style scoped>
.sv-spec-table {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
}
.sv-spec-table div {
  padding: .85rem;
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
}
.sv-spec-table span { display: block; color: #64748b; font-size: .72rem; font-weight: 700; }
.sv-spec-table strong { display: block; color: #0f172a; font-size: .86rem; margin-top: .18rem; }
@media (max-width: 991px) {
  .sv-spec-table { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 575px) {
  .sv-spec-table { grid-template-columns: 1fr; }
}
</style>
