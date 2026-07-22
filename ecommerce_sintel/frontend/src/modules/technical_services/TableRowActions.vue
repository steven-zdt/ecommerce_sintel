<template>
  <div class="dropdown">
    <button
      class="btn btn-sm btn-light border"
      type="button"
      data-bs-toggle="dropdown"
      aria-expanded="false"
      @click.stop
    >
      <i class="bi bi-three-dots-vertical"></i>
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
      <li v-for="action in actions" :key="action.key">
        <button
          class="dropdown-item d-flex align-items-center gap-2"
          type="button"
          @click.stop="$emit(action.key, item)"
          :class="action.class"
        >
          <i :class="action.icon"></i>
          <span>{{ action.label }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  item: object;
  actions: {
    key: string;
    label: string;
    icon: string;
    class?: string;
  }[];
}>();

defineEmits<{ (e: string, item: object): void }>();
</script>