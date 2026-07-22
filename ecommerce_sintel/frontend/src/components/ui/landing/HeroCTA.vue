<template>
  <div class="hcta-root">
    <component
      :is="primaryIsExternal ? 'a' : RouterLink"
      v-if="primaryLabel"
      :to="primaryIsExternal ? undefined : primaryUrl"
      :href="primaryIsExternal ? primaryUrl : undefined"
      class="hcta-btn hcta-primary"
    >
      {{ primaryLabel }}
      <svg class="hcta-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </component>

    <component
      :is="ghostIsExternal ? 'a' : RouterLink"
      v-if="ghostLabel"
      :to="ghostIsExternal ? undefined : ghostUrl"
      :href="ghostIsExternal ? ghostUrl : undefined"
      class="hcta-btn hcta-ghost"
    >
      {{ ghostLabel }}
    </component>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

const props = defineProps({
  primaryLabel: { type: String, default: '' },
  primaryUrl:   { type: String, default: '/' },
  ghostLabel:   { type: String, default: '' },
  ghostUrl:     { type: String, default: '/' },
});

const primaryIsExternal = computed(() => /^https?:\/\//.test(props.primaryUrl));
const ghostIsExternal   = computed(() => /^https?:\/\//.test(props.ghostUrl));
</script>

<style scoped>
.hcta-root {
  display: flex;
  gap: 0.85rem;
  flex-wrap: wrap;
  margin-top: 1.1rem;
}

.hcta-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: 9999px;
  padding: 0.72rem 1.75rem;
  text-decoration: none;
  transition: transform 0.28s cubic-bezier(0.16,1,0.3,1),
              box-shadow 0.28s ease,
              background 0.2s ease,
              opacity 0.2s ease;
  cursor: pointer;
  white-space: nowrap;
}

.hcta-primary {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #fff;
  box-shadow: 0 4px 20px rgba(37,99,235,.45), 0 1px 4px rgba(37,99,235,.3);
}
.hcta-primary:hover {
  color: #fff;
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 28px rgba(37,99,235,.55), 0 2px 8px rgba(37,99,235,.35);
}
.hcta-primary:active { transform: translateY(0) scale(.99); }

.hcta-arrow {
  flex-shrink: 0;
  transition: transform 0.22s ease;
}
.hcta-primary:hover .hcta-arrow { transform: translateX(3px); }

.hcta-ghost {
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.25);
  color: rgba(255,255,255,.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.hcta-ghost:hover {
  background: rgba(255,255,255,.2);
  color: #fff;
  border-color: rgba(255,255,255,.4);
  transform: translateY(-2px);
}

@media (max-width: 480px) {
  .hcta-root { flex-direction: column; }
  .hcta-btn  { justify-content: center; }
}
</style>
