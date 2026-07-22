<template>
  <nav v-if="totalPages > 1" aria-label="Paginacion" class="acc-pagination">
    <ul class="pagination pagination-sm mb-0">
      <li class="page-item" :class="{ disabled: page <= 1 }">
        <button class="page-link" :disabled="page <= 1" @click="$emit('update:page', page - 1)">
          <i class="bi bi-chevron-left"></i>
        </button>
      </li>
      <li class="page-item disabled d-flex align-items-center px-3">
        <span class="small text-muted">Pagina {{ page }} de {{ totalPages }}</span>
      </li>
      <li class="page-item" :class="{ disabled: page >= totalPages }">
        <button class="page-link" :disabled="page >= totalPages" @click="$emit('update:page', page + 1)">
          <i class="bi bi-chevron-right"></i>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
});
defineEmits(['update:page']);
</script>

<style scoped>
.acc-pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
