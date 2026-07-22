<template>
  <div class="acc-avatar-wrapper" :style="{ width: size + 'px', height: size + 'px' }" @click="$emit('click')">
    <img v-if="src" :src="src" alt="avatar" class="acc-avatar" />
    <div v-else class="acc-avatar acc-avatar--placeholder">
      <span v-if="initials">{{ initials }}</span>
      <i v-else class="bi bi-person-fill"></i>
    </div>
    <div v-if="editable" class="acc-avatar-edit-badge"><i class="bi bi-pencil-fill"></i></div>
  </div>
</template>

<script setup>
defineProps({
  src: { type: String, default: null },
  initials: { type: String, default: '' },
  size: { type: Number, default: 72 },
  editable: { type: Boolean, default: false },
});
defineEmits(['click']);
</script>

<script>
export default { name: 'CustomerAvatar' };
</script>

<style scoped>
.acc-avatar-wrapper {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}

.acc-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid var(--acc-border, #e5e7eb);
}

.acc-avatar--placeholder {
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-weight: 700;
  font-size: 1.4rem;
}

.acc-avatar-edit-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  background: var(--acc-accent, #2563eb);
  color: #fff;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  border: 2px solid #fff;
}
</style>
