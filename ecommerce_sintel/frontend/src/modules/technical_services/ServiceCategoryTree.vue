<template>
  <div class="category-tree-container">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border spinner-border-sm"></div>
    </div>
    <div v-else-if="!treeData.length" class="text-center py-5 text-muted">
      No hay categorías para mostrar.
    </div>
    <div v-else class="tree-root">
      <CategoryTreeNode v-for="element in treeData" :key="element.uuid" :element="element" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import CategoryTreeNode from './CategoryTreeNode.vue';

const props = defineProps({
  categories: {
    type: Array,
    required: true,
  },
  loading: Boolean,
});

const treeData = ref([]);

const buildTree = (items, parentId = null) => {
  return items
    .filter(item => item.parent === parentId)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    .map(item => ({
      ...item,
      children: buildTree(items, item.uuid),
    }));
};

watch(() => props.categories, (newCategories) => {
  treeData.value = buildTree(newCategories);
}, { immediate: true, deep: true });
</script>

<style scoped>
.ghost { opacity: 0.5; background: #c8e6c9; }
</style>