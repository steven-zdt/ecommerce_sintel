<template>
  <div :class="['fb-block', `fb-block--${block.layout_type}`]">
    <div v-if="block.layout_type !== 'text_centered'" class="fb-block__media">
      <img v-if="block.image" :src="block.image" :alt="block.image_alt || block.title" loading="lazy" class="fb-block__img">
      <div v-else class="fb-block__img-ph"></div>
      <div v-if="block.layout_type === 'full_image'" class="fb-block__media-overlay"></div>
    </div>

    <div class="fb-block__content">
      <span v-if="block.badge_text" class="fb-badge" :style="{ background: block.badge_color || '#f59e0b' }">
        {{ block.badge_text }}
      </span>

      <h3 v-if="block.title || block.title_highlighted" class="fb-block__title">
        {{ block.title }}
        <span v-if="block.title_highlighted" class="fb-block__title-highlight">{{ block.title_highlighted }}</span>
      </h3>

      <p v-if="block.description" class="fb-block__desc">{{ block.description }}</p>

      <ul v-if="benefits.length" class="fb-block__benefits">
        <li v-for="(b, i) in benefits" :key="i">
          <i v-if="b.icon" :class="['bi', b.icon]"></i>
          <span>{{ b.text }}</span>
        </li>
      </ul>

      <div v-if="stats.length" class="fb-block__stats">
        <div v-for="(s, i) in stats" :key="i" class="fb-block__stat">
          <strong>{{ s.value }}</strong>
          <span>{{ s.label }}</span>
        </div>
      </div>

      <div v-if="block.btn_primary_text || block.btn_secondary_text" class="fb-block__actions">
        <FeatureBannerButton
          v-if="block.btn_primary_text"
          :text="block.btn_primary_text" :icon="block.btn_primary_icon" :color="block.btn_primary_color"
          :btn-style="block.btn_primary_style" :url="block.btn_primary_url" :url-type="block.btn_primary_url_type"
          :target="block.btn_primary_target"
        />
        <FeatureBannerButton
          v-if="block.btn_secondary_text"
          :text="block.btn_secondary_text" :icon="block.btn_secondary_icon" :color="block.btn_secondary_color"
          :btn-style="block.btn_secondary_style" :url="block.btn_secondary_url" :url-type="block.btn_secondary_url_type"
          :target="block.btn_secondary_target"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * FeatureBannerBlock — un bloque (imagen + texto + botones) dentro de una
 * FeatureBannerRenderer.vue. `layout_type` controla orden/proporcion via CSS
 * (grid-template-columns + order), sin logica de render condicional extra --
 * mismo criterio ya usado en MarketplaceCard.vue (order:-1 para btn_position).
 */
import { computed } from 'vue';
import FeatureBannerButton from './FeatureBannerButton.vue';

const props = defineProps({
  block: { type: Object, required: true },
});

const benefits = computed(() => Array.isArray(props.block.benefits) ? props.block.benefits.filter(b => b.text) : []);
const stats = computed(() => Array.isArray(props.block.stats) ? props.block.stats.filter(s => s.value) : []);
</script>

<style scoped>
.fb-block {
  display: grid;
  gap: clamp(1.5rem, 4vw, 3rem);
  align-items: center;
  padding: clamp(1.5rem, 3vw, 2.5rem) 0;
}

/* ── Layouts: proporcion de columnas ─────────────────────────────────────── */
.fb-block--image_left,
.fb-block--image_right,
.fb-block--fifty_fifty { grid-template-columns: 1fr 1fr; }
.fb-block--sixty_forty { grid-template-columns: 3fr 2fr; }
.fb-block--forty_sixty { grid-template-columns: 2fr 3fr; }
.fb-block--text_centered { grid-template-columns: 1fr; text-align: center; max-width: 720px; margin: 0 auto; }
.fb-block--full_image { grid-template-columns: 1fr; position: relative; min-height: 360px; border-radius: 20px; overflow: hidden; }

/* image_right invierte el orden visual sin duplicar markup */
.fb-block--image_right .fb-block__media { order: 2; }
.fb-block--image_right .fb-block__content { order: 1; }

.fb-block__media { position: relative; border-radius: 18px; overflow: hidden; }
.fb-block--full_image .fb-block__media { position: absolute; inset: 0; border-radius: 0; }
.fb-block__img { width: 100%; height: 100%; min-height: 280px; object-fit: cover; display: block; }
.fb-block__img-ph { width: 100%; min-height: 280px; background: var(--fb-media-placeholder, #e2e8f0); border-radius: 18px; }
.fb-block__media-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,.15), rgba(0,0,0,.65));
}

.fb-block__content { position: relative; z-index: 1; }
.fb-block--full_image .fb-block__content { padding: clamp(2rem, 5vw, 3.5rem); color: #fff; }
.fb-block--text_centered .fb-block__benefits,
.fb-block--text_centered .fb-block__actions { justify-content: center; }
.fb-block--text_centered .fb-block__stats { justify-content: center; }

.fb-badge {
  display: inline-flex; align-items: center;
  font-size: .7rem; font-weight: 700; color: #fff;
  padding: .25rem .7rem; border-radius: 999px; margin-bottom: .75rem;
}

.fb-block__title { font-size: clamp(1.4rem, 3vw, 2.1rem); font-weight: 800; margin: 0 0 .75rem; line-height: 1.2; color: var(--fb-text, #0f172a); }
.fb-block__title-highlight { color: var(--fb-accent, #2563eb); }

.fb-block__desc { font-size: 1rem; line-height: 1.65; color: var(--fb-text-muted, #475569); margin: 0 0 1.25rem; }

.fb-block__benefits { list-style: none; padding: 0; margin: 0 0 1.25rem; display: flex; flex-direction: column; gap: .55rem; }
.fb-block__benefits li { display: flex; align-items: center; gap: .55rem; font-size: .92rem; color: var(--fb-text, #0f172a); }
.fb-block__benefits i { color: var(--fb-accent, #2563eb); font-size: 1.05rem; flex-shrink: 0; }

.fb-block__stats { display: flex; gap: 1.75rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.fb-block__stat { display: flex; flex-direction: column; }
.fb-block__stat strong { font-size: 1.5rem; font-weight: 800; color: var(--fb-accent, #2563eb); }
.fb-block__stat span { font-size: .78rem; color: var(--fb-text-muted, #64748b); }

.fb-block__actions { display: flex; gap: .75rem; flex-wrap: wrap; }

@media (max-width: 767px) {
  .fb-block--image_left,
  .fb-block--image_right,
  .fb-block--fifty_fifty,
  .fb-block--sixty_forty,
  .fb-block--forty_sixty {
    grid-template-columns: 1fr;
  }
  .fb-block--image_right .fb-block__media,
  .fb-block--image_right .fb-block__content { order: 0; }
}
</style>
