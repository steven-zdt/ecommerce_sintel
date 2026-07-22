<template>
  <div class="tree-node" :class="{ 'is-parent': isParent }">
    <div class="node-content" :class="{ 'is-ghost': element.is_active === false }">
      <i v-if="isParent" @click="isExpanded = !isExpanded" class="bi me-2 expand-icon" :class="isExpanded ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
      <i v-else class="bi me-2 expand-icon-placeholder"></i>
      
      <span class="node-label">{{ element.name }}</span>

      <span class="badge ms-auto me-2" :class="element.is_active ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
        {{ element.is_active ? 'Activa' : 'Inactiva' }}
      </span>
    </div>

    <div v-if="isParent && isExpanded" class="node-children">
      <CategoryTreeNode v-for="childElement in element.children" :key="childElement.uuid" :element="childElement" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  element: {
    type: Object,
    required: true,
  },
});

// Importar recursivamente el propio componente
const CategoryTreeNode = import.meta.env.PROD
  ? (await import('./CategoryTreeNode.vue')).default
  : (await import.meta.glob('./CategoryTreeNode.vue'))['./CategoryTreeNode.vue'];

const isExpanded = ref(true);

const isParent = computed(() => {
  return props.element.children && props.element.children.length > 0;
});
</script>

<style scoped>
.tree-node {
  position: relative;
}
.node-content {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  background-color: #fff;
  border: 1px solid #e2e8f0;
  margin-bottom: 4px;
}
.node-content.is-ghost {
  opacity: 0.5;
  background-color: #f8fafc;
}
.expand-icon {
  cursor: pointer;
}
.expand-icon-placeholder {
  width: 1em; /* Mismo ancho que el icono para alinear */
}
.node-children {
  padding-left: 28px;
  margin-top: 4px;
  position: relative;
}
.ghost {
  opacity: 0.5;
  background: #c8e6c9;
}
</style>