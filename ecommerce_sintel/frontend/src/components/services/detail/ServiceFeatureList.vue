<template>
  <div class="sv-resource-grid">
    <article v-for="group in groups" :key="group.title">
      <h3><i :class="['bi', group.icon]"></i>{{ group.title }}</h3>
      <div class="sv-chip-list">
        <span v-for="item in group.items" :key="item">{{ item }}</span>
      </div>
    </article>
  </div>
</template>

<script setup>
defineProps({
  groups: { type: Array, default: () => [] }, // [{ title, icon, items: [] }]
});
</script>

<style scoped>
.sv-resource-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
}
.sv-resource-grid article {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: .9rem;
}
.sv-resource-grid h3 {
  display: flex; align-items: center; gap: .45rem;
  color: #0f172a; font-size: .95rem; font-weight: 850;
  margin: 0 0 .3rem;
}
.sv-resource-grid h3 i { color: #0e7490; font-size: 1.1rem; }
.sv-chip-list { display: flex; flex-wrap: wrap; gap: .4rem; }
.sv-chip-list span {
  background: #fff; border: 1px solid #e2e8f0; color: #475569;
  border-radius: 999px; padding: .28rem .6rem; font-size: .76rem; font-weight: 700;
}
@media (max-width: 991px) {
  .sv-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 575px) {
  .sv-resource-grid { grid-template-columns: 1fr; }
}
</style>
