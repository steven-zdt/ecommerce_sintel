<template>
  <div v-if="groups.length" class="eq-spec-groups">
    <div v-for="group in groups" :key="group.uuid" class="eq-spec-group">
      <button type="button" class="eq-spec-group-head" @click="toggle(group.uuid)">
        <h4>{{ group.name }}</h4>
        <i class="bi" :class="openGroups.has(group.uuid) ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
      </button>
      <div v-show="openGroups.has(group.uuid)" class="eq-spec-table">
        <div v-for="spec in group.specifications" :key="spec.uuid" class="eq-spec-row">
          <span>{{ spec.name }}</span>
          <strong>{{ spec.value }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  groups: { type: Array, default: () => [] },
});

const openGroups = ref(new Set());

function toggle(uuid) {
  const next = new Set(openGroups.value);
  if (next.has(uuid)) next.delete(uuid);
  else next.add(uuid);
  openGroups.value = next;
}

watch(
  () => props.groups,
  (groups) => {
    if (groups.length) openGroups.value = new Set([groups[0].uuid]);
  },
  { immediate: true },
);
</script>

<style scoped>
.eq-spec-groups { display: flex; flex-direction: column; gap: .75rem; }
.eq-spec-group {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
}
.eq-spec-group-head {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .6rem;
  padding: .8rem 1rem;
  border: 0;
  background: #f8fafc;
  cursor: pointer;
}
.eq-spec-group-head h4 {
  color: #0369a1; font-size: .8rem; font-weight: 850;
  text-transform: uppercase; letter-spacing: .06em; margin: 0;
}
.eq-spec-group-head i { color: #64748b; }
.eq-spec-table {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
}
.eq-spec-row {
  display: flex; justify-content: space-between; gap: .5rem;
  padding: .7rem .9rem; border-right: 1px solid #e2e8f0; border-top: 1px solid #e2e8f0;
  background: #fff;
}
.eq-spec-row span { color: #64748b; font-size: .8rem; }
.eq-spec-row strong { color: #0f172a; font-size: .82rem; text-align: right; }
@media (max-width: 575px) {
  .eq-spec-table { grid-template-columns: 1fr; }
}
</style>
