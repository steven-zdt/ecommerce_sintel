<template>
  <article class="sv-scope-card">
    <h3><i :class="['bi', icon, iconColorClass]"></i>{{ title }}</h3>
    <ul>
      <li v-for="item in items" :key="item">{{ item }}</li>
    </ul>
  </article>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  icon:  { type: String, required: true },
  items: { type: Array, default: () => [] },
  iconColorClass: { type: String, default: 'text-success' },
});
</script>

<style scoped>
.sv-scope-card {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: .9rem;
}
.sv-scope-card h3 {
  color: #0f172a; font-size: .95rem; font-weight: 850;
  margin: 0;
}
.sv-scope-card ul { list-style: none; padding: 0; margin: .55rem 0 0; }
.sv-scope-card li { color: #475569; font-size: .84rem; margin-top: .42rem; }
.sv-scope-card li::before { content: "•"; color: #0f766e; font-weight: 900; margin-right: .4rem; }
</style>
