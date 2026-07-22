<template>
  <article v-if="items.length" class="eq-scope-card eq-scope-card--included">
    <h3><i class="bi bi-check2-circle text-success"></i>Incluye</h3>
    <ul>
      <li v-for="item in items" :key="item.uuid">
        <IconRenderer v-if="item.icon" :icon="item.icon" extra-class="eq-scope-icon" />
        <div>
          <strong>{{ item.title }}</strong>
          <p v-if="item.description">{{ item.description }}</p>
        </div>
      </li>
    </ul>
  </article>
</template>

<script setup>
import IconRenderer from '@/components/ui/IconRenderer.vue';

defineProps({
  items: { type: Array, default: () => [] },
});
</script>

<style scoped>
.eq-scope-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1rem;
}
.eq-scope-card h3 {
  display: flex; align-items: center; gap: .5rem;
  color: #0f172a; font-size: .95rem; font-weight: 850; margin: 0 0 .6rem;
}
.eq-scope-card ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .55rem; }
.eq-scope-card li { display: flex; gap: .5rem; align-items: flex-start; }
.eq-scope-card strong { display: block; color: #0f172a; font-size: .86rem; }
.eq-scope-card p { color: #64748b; font-size: .78rem; margin: .15rem 0 0; }
.eq-scope-icon { color: #16a34a; margin-top: .15rem; flex-shrink: 0; }
</style>
