<template>
  <div v-if="items.length" class="eq-requirement-list">
    <article v-for="item in items" :key="item.uuid" class="eq-requirement-card">
      <i class="bi bi-clipboard-check"></i>
      <div>
        <strong>{{ item.title }}</strong>
        <p v-if="item.description">{{ item.description }}</p>
      </div>
    </article>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, default: () => [] },
});
</script>

<style scoped>
.eq-requirement-list { display: flex; flex-direction: column; gap: .6rem; }
.eq-requirement-card {
  display: flex; gap: .6rem; align-items: flex-start;
  background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: .8rem;
}
.eq-requirement-card i { color: #b45309; font-size: 1.05rem; margin-top: .1rem; }
.eq-requirement-card strong { display: block; color: #0f172a; font-size: .84rem; }
.eq-requirement-card p { color: #78716c; font-size: .78rem; margin: .15rem 0 0; }
</style>
