<template>
  <RouterLink v-if="urlType === 'INTERNA' && url" :to="url" class="fb-btn" :style="btnStyle" :class="styleClass">
    <i v-if="icon" :class="['bi', icon]"></i>
    {{ text }}
  </RouterLink>
  <a
    v-else-if="urlType === 'EXTERNA' && url"
    :href="url"
    :target="target || '_self'"
    :rel="target === '_blank' ? 'noopener noreferrer' : undefined"
    class="fb-btn" :style="btnStyle" :class="styleClass"
  >
    <i v-if="icon" :class="['bi', icon]"></i>
    {{ text }}
  </a>
  <a v-else-if="urlType === 'ANCHOR' && url" :href="url" class="fb-btn" :style="btnStyle" :class="styleClass" @click="scrollToAnchor">
    <i v-if="icon" :class="['bi', icon]"></i>
    {{ text }}
  </a>
  <span v-else class="fb-btn" :style="btnStyle" :class="styleClass">
    <i v-if="icon" :class="['bi', icon]"></i>
    {{ text }}
  </span>
</template>

<script setup>
/**
 * FeatureBannerButton — resuelve la URL por `url_type` EXPLICITO
 * (INTERNA/EXTERNA/ANCHOR, elegido por el admin), sin inferencia por regex
 * sobre el valor -- a diferencia del patron legado de MarketplaceCard.vue
 * (isExternal = /^https?:\/\//.test(url)). Ver HOME_MODULE_URLS.md.
 *
 * El caso ANCHOR (unico con logica real mas alla del <RouterLink>/<a>) delega
 * en el helper compartido resolveUrlNavigation() -- mismo que usa CardItem.vue
 * para el boton secundario de Card Group, evitando una tercera implementacion
 * de "scroll suave a #id".
 */
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { resolveUrlNavigation } from '@/utils/urlNavigation';

const props = defineProps({
  text: { type: String, default: '' },
  icon: { type: String, default: '' },
  color: { type: String, default: '#2563eb' },
  btnStyle: { type: String, default: 'filled' }, // filled/outline/ghost/minimal
  url: { type: String, default: '' },
  urlType: { type: String, default: 'INTERNA' },
  target: { type: String, default: '_self' },
});

const styleClass = computed(() => `fb-btn--${props.btnStyle}`);

const btnStyle = computed(() => {
  if (props.btnStyle === 'outline') return { color: props.color, borderColor: props.color };
  if (props.btnStyle === 'ghost' || props.btnStyle === 'minimal') return { color: props.color };
  return { background: props.color };
});

function scrollToAnchor(e) {
  e.preventDefault();
  resolveUrlNavigation(props.url, 'ANCHOR', null);
}
</script>

<style scoped>
.fb-btn {
  display: inline-flex; align-items: center; gap: .5rem;
  font-size: .88rem; font-weight: 700;
  padding: .65rem 1.4rem; border-radius: 999px;
  text-decoration: none; cursor: pointer;
  border: 1px solid transparent;
  transition: transform .18s ease, box-shadow .18s ease;
}
.fb-btn:hover { transform: translateY(-1px); }
.fb-btn--filled { color: #fff; }
.fb-btn--outline { background: transparent; border-color: currentColor; }
.fb-btn--ghost { background: transparent; }
.fb-btn--minimal { background: transparent; padding: 0; border-radius: 0; text-decoration: underline; }
</style>
