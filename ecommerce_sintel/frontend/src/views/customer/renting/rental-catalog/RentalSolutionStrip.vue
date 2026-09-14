<template>
  <section class="renting-home">
    <div class="container-xl">
      <div class="rh-grid">
        <article v-for="solution in solutions" :key="solution.title" class="rh-card">
          <div class="rh-icon"><i :class="['bi', solution.icon]"></i></div>
          <div><h2>{{ solution.title }}</h2><p>{{ solution.copy }}</p></div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({ solutions: { type: Array, default: () => [] } });
</script>

<style scoped>
.renting-home { background: linear-gradient(180deg, #f8fafc 0%, #fff 100%); border-bottom: 1px solid #e2e8f0; padding: 1.35rem 0 1.85rem; }
.rh-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .9rem; margin-top: -2.35rem; position: relative; z-index: 2; }
.rh-card { min-height: 150px; background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1rem; display: flex; gap: .85rem; box-shadow: 0 16px 34px rgba(15,23,42,.08); }
.rh-icon { width: 42px; height: 42px; border-radius: 12px; background: #f0f9ff; color: #0369a1; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.12rem; }
.rh-card h2 { color: #0f172a; font-size: .98rem; line-height: 1.2; font-weight: 850; letter-spacing: 0; margin: 0; }
.rh-card p { color: #64748b; font-size: .82rem; line-height: 1.55; margin: .35rem 0 0; }
@media (max-width: 991px) { .rh-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 1rem; } }
@media (max-width: 575px) { .rh-grid { grid-template-columns: 1fr; } .rh-card { min-height: auto; } }
</style>
