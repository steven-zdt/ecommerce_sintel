<template>
  <div :class="rootClass" :style="rootStyle" @click="navigate">

    <!-- ── IMAGE_BG variant ───────────────────────────────────────────────── -->
    <template v-if="card.card_type === 'image_bg'">
      <div class="ci-bg-img" :style="bgImgStyle"></div>
      <div class="ci-overlay"></div>
      <div class="ci-body ci-body--bg">
        <IconRenderer v-if="card.icon_class && !card.image" :icon="card.icon_class" extra-class="ci-icon ci-icon--light" />
        <div class="ci-title ci-title--light">{{ card.title }}</div>
        <div v-if="card.subtitle" class="ci-subtitle ci-subtitle--light">{{ card.subtitle }}</div>
      </div>
    </template>

    <!-- ── HORIZONTAL variant ─────────────────────────────────────────────── -->
    <template v-else-if="card.card_type === 'horizontal'">
      <div class="ci-h-media" :style="{ background: card.background_color }">
        <img v-if="card.image" :src="card.image" :alt="card.title" class="ci-h-media__img" loading="lazy">
        <IconRenderer v-else :icon="card.icon_class || 'bi-star'" extra-class="ci-icon--main" />
      </div>
      <div class="ci-body ci-body--h">
        <div class="ci-title">{{ card.title }}</div>
        <div v-if="card.subtitle" class="ci-subtitle">{{ card.subtitle }}</div>
        <div v-if="card.description" class="ci-desc">{{ card.description }}</div>
      </div>
    </template>

    <!-- ── COMPACT variant ────────────────────────────────────────────────── -->
    <template v-else-if="card.card_type === 'compact'">
      <div class="ci-compact-row">
        <div class="ci-compact-icon" :style="{ background: card.image ? 'transparent' : (card.background_color + '22'), color: card.background_color }">
          <img v-if="card.image" :src="card.image" :alt="card.title" class="ci-compact-img" loading="lazy">
          <IconRenderer v-else :icon="card.icon_class || 'bi-star'" />
        </div>
        <div>
          <div class="ci-title ci-title--sm">{{ card.title }}</div>
          <div v-if="card.subtitle" class="ci-subtitle ci-subtitle--xs">{{ card.subtitle }}</div>
        </div>
      </div>
    </template>

    <!-- ── GLASS variant ──────────────────────────────────────────────────── -->
    <template v-else-if="card.card_type === 'glass'">
      <div class="ci-glass-stripe" :style="{ background: card.background_color }"></div>
      <div v-if="card.image" class="ci-img-header">
        <img :src="card.image" :alt="card.title" class="ci-img-header__img" loading="lazy">
      </div>
      <IconRenderer v-else :icon="card.icon_class || 'bi-star'" extra-class="ci-icon--glass" :style="{ color: card.background_color }" />
      <div class="ci-title">{{ card.title }}</div>
      <div v-if="card.subtitle" class="ci-subtitle">{{ card.subtitle }}</div>
    </template>

    <!-- ── DARK variant ───────────────────────────────────────────────────── -->
    <template v-else-if="card.card_type === 'dark'">
      <div v-if="card.image" class="ci-img-header">
        <img :src="card.image" :alt="card.title" class="ci-img-header__img" loading="lazy">
      </div>
      <IconRenderer v-else :icon="card.icon_class || 'bi-star'" extra-class="ci-icon--dark" :style="{ color: card.background_color }" />
      <div class="ci-title ci-title--light">{{ card.title }}</div>
      <div v-if="card.subtitle" class="ci-subtitle ci-subtitle--muted">{{ card.subtitle }}</div>
    </template>

    <!-- ── GRADIENT variant ───────────────────────────────────────────────── -->
    <template v-else-if="card.card_type === 'gradient'">
      <div v-if="card.image" class="ci-img-header">
        <img :src="card.image" :alt="card.title" class="ci-img-header__img ci-img-header__img--overlay" loading="lazy">
      </div>
      <IconRenderer v-else :icon="card.icon_class || 'bi-star'" extra-class="ci-icon--grad" />
      <div class="ci-title ci-title--light">{{ card.title }}</div>
      <div v-if="card.subtitle" class="ci-subtitle ci-subtitle--light">{{ card.subtitle }}</div>
    </template>

    <!-- ── PREMIUM variant ────────────────────────────────────────────────── -->
    <template v-else-if="card.card_type === 'premium'">
      <div v-if="card.image" class="ci-img-header ci-img-header--premium">
        <img :src="card.image" :alt="card.title" class="ci-img-header__img" loading="lazy">
      </div>
      <div v-else class="ci-premium-top">
        <div class="ci-premium-dot" :style="{ background: card.background_color }"></div>
        <IconRenderer :icon="card.icon_class || 'bi-star'" extra-class="ci-icon--premium" :style="{ color: card.background_color }" />
      </div>
      <div class="ci-title ci-title--premium">{{ card.title }}</div>
      <div v-if="card.subtitle" class="ci-subtitle">{{ card.subtitle }}</div>
      <div v-if="card.description" class="ci-desc">{{ card.description }}</div>
      <div v-if="card.redirect_url" class="ci-link">Conoce mas <i class="bi bi-arrow-right"></i></div>
    </template>

    <!-- ── VERTICAL / default variant ────────────────────────────────────── -->
    <template v-else>
      <div v-if="card.image" class="ci-img-header">
        <img :src="card.image" :alt="card.title" class="ci-img-header__img" loading="lazy">
      </div>
      <div v-else class="ci-icon-circle" :style="{ background: card.background_color + '18' }">
        <IconRenderer :icon="card.icon_class || 'bi-star'" :style="{ color: card.background_color }" />
      </div>
      <div class="ci-title">{{ card.title }}</div>
      <div v-if="card.subtitle" class="ci-subtitle">{{ card.subtitle }}</div>
      <div v-if="card.description" class="ci-desc">{{ card.description }}</div>
    </template>

    <!-- Badge -->
    <span v-if="card.badge_text" class="ci-badge-featured">{{ card.badge_text }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { resolveRevealClass } from '@/composables/useScrollReveal';
import IconRenderer from '@/components/ui/IconRenderer.vue';

const props = defineProps({
  card:    { type: Object, required: true },
  visible: { type: Boolean, default: true },
});

const router = useRouter();

const rootClass = computed(() => {
  const t = props.card.card_type || 'vertical';
  return [
    'ci-root',
    `ci-root--${t}`,
    resolveRevealClass(props.card.animation),
    props.visible ? 'ci-root--visible' : '',
    props.card.is_featured ? 'ci-root--featured' : '',
    props.card.redirect_url ? 'ci-root--clickable' : '',
    props.card.image ? 'ci-root--has-image' : '',
  ];
});

const rootStyle = computed(() => {
  if (props.card.card_type === 'gradient') {
    return { background: `linear-gradient(135deg, ${props.card.background_color}, ${props.card.background_color}cc)` };
  }
  if (props.card.card_type === 'dark') {
    return { background: '#0f172a' };
  }
  return {};
});

const bgImgStyle = computed(() => {
  if (props.card.image) return { backgroundImage: `url(${props.card.image})` };
  return { background: props.card.background_color };
});

function navigate() {
  if (props.card.redirect_url) {
    if (props.card.redirect_url.startsWith('http')) {
      window.open(props.card.redirect_url, '_blank');
    } else {
      router.push(props.card.redirect_url);
    }
  }
}
</script>

<style scoped>
/* ── Base ──────────────────────────────────────────────────────────────────── */
.ci-root {
  position: relative;
  border-radius: 16px;
  padding: 1.5rem;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
  transition: transform 280ms cubic-bezier(.16,1,.3,1), box-shadow 280ms ease;
  overflow: hidden;
  opacity: 0;
  transform: translateY(20px);
}
.ci-root--visible {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 500ms ease, transform 500ms cubic-bezier(.16,1,.3,1);
}
.ci-root--clickable { cursor: pointer; }
.ci-root--clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 28px rgba(0,0,0,.1);
}
.ci-root--featured { border: 2px solid #2563eb; }

/* ── Variantes de reveal (card.animation) ────────────────────────────────────── */
.sr-zoom { transform: scale(0.88); }
.sr-zoom.ci-root--visible { transform: scale(1); }
.sr-flip { transform: rotateY(30deg); }
.sr-flip.ci-root--visible { transform: rotateY(0); }
.sr-rotate { transform: rotate(-5deg) translateY(20px); }
.sr-rotate.ci-root--visible { transform: rotate(0) translateY(0); }
.sr-parallax { transform: translateY(40px); }
.sr-parallax.ci-root--visible { transform: translateY(0); }
.sr-bounce.ci-root--visible { animation: ci-bounce 0.7s cubic-bezier(0.34,1.56,0.64,1); }
@keyframes ci-bounce {
  0%   { transform: translateY(20px); opacity: 0; }
  60%  { transform: translateY(-8px); opacity: 1; }
  100% { transform: translateY(0); }
}

/* Cuando tiene imagen: el padding-top se elimina (la imagen llega al borde) */
.ci-root--has-image:not(.ci-root--image_bg):not(.ci-root--horizontal):not(.ci-root--compact) {
  padding-top: 0;
}

/* ── Image header universal ───────────────────────────────────────────────── */
.ci-img-header {
  margin: 0 -1.5rem 1rem;
  overflow: hidden;
  border-radius: 16px 16px 0 0;
}
.ci-img-header--premium {
  margin: -1.5rem -1.5rem 1rem;
}
.ci-img-header__img {
  width: 100%;
  height: 160px;
  object-fit: cover;
  display: block;
  transition: transform 400ms ease;
}
.ci-root--clickable:hover .ci-img-header__img {
  transform: scale(1.04);
}
.ci-img-header__img--overlay {
  opacity: .85;
  mix-blend-mode: luminosity;
}

/* ── Vertical (default) ───────────────────────────────────────────────────── */
.ci-icon-circle {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: grid; place-items: center;
  font-size: 1.4rem;
  margin-bottom: 1rem;
}
.ci-title { font-weight: 700; font-size: .95rem; color: #0f172a; margin-bottom: .35rem; }
.ci-title--sm { font-size: .875rem; }
.ci-title--light { color: #fff; }
.ci-title--premium { font-size: 1rem; font-weight: 800; color: #0f172a; }
.ci-subtitle { font-size: .8rem; color: #64748b; }
.ci-subtitle--muted { color: #94a3b8; }
.ci-subtitle--light { color: rgba(255,255,255,.75); }
.ci-subtitle--xs { font-size: .75rem; }
.ci-desc { font-size: .8rem; color: #94a3b8; margin-top: .4rem; line-height: 1.5; }
.ci-link { font-size: .8rem; color: #2563eb; font-weight: 600; margin-top: auto; padding-top: .75rem; }

/* ── Horizontal ───────────────────────────────────────────────────────────── */
.ci-root--horizontal { display: flex; align-items: flex-start; gap: 1rem; padding: 1.25rem; }
.ci-h-media {
  width: 56px; height: 56px; flex-shrink: 0;
  border-radius: 12px; display: grid; place-items: center; overflow: hidden;
}
.ci-h-media__img { width: 100%; height: 100%; object-fit: cover; }
.ci-icon--main { font-size: 1.3rem; color: #fff; }
.ci-body--h { flex: 1; }

/* ── Glass ────────────────────────────────────────────────────────────────── */
.ci-root--glass {
  background: rgba(255,255,255,.72);
  backdrop-filter: blur(14px) saturate(180%);
  border: 1px solid rgba(255,255,255,.45);
}
.ci-glass-stripe {
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  border-radius: 16px 16px 0 0;
}
.ci-icon--glass { font-size: 2rem; margin-bottom: .75rem; display: block; }

/* ── Dark ─────────────────────────────────────────────────────────────────── */
.ci-root--dark { color: #e2e8f0; }
.ci-icon--dark { font-size: 2rem; display: block; margin-bottom: .75rem; }

/* ── Gradient ─────────────────────────────────────────────────────────────── */
.ci-root--gradient { color: #fff; }
.ci-icon--grad { font-size: 2rem; color: rgba(255,255,255,.85); display: block; margin-bottom: .75rem; }

/* ── Premium ──────────────────────────────────────────────────────────────── */
.ci-root--premium { display: flex; flex-direction: column; }
.ci-premium-top { display: flex; align-items: center; gap: .5rem; margin-bottom: .75rem; }
.ci-premium-dot { width: 8px; height: 8px; border-radius: 50%; }
.ci-icon--premium { font-size: 1.5rem; }

/* ── Compact ──────────────────────────────────────────────────────────────── */
.ci-root--compact { padding: .875rem; }
.ci-compact-row { display: flex; align-items: center; gap: .75rem; }
.ci-compact-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: grid; place-items: center; font-size: 1.1rem; flex-shrink: 0;
  overflow: hidden;
}
.ci-compact-img { width: 100%; height: 100%; object-fit: cover; border-radius: 10px; }

/* ── Image BG ─────────────────────────────────────────────────────────────── */
.ci-root--image_bg { padding: 0; min-height: 200px; display: flex; flex-direction: column; justify-content: flex-end; }
.ci-bg-img {
  position: absolute; inset: 0;
  background-size: cover; background-position: center;
  transition: transform 400ms ease;
}
.ci-root--clickable:hover .ci-bg-img { transform: scale(1.04); }
.ci-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,.65) 0%, transparent 60%); }
.ci-body--bg { position: relative; z-index: 1; padding: 1.25rem; }
.ci-icon--light { font-size: 1.6rem; color: rgba(255,255,255,.85); display: block; margin-bottom: .5rem; }

/* ── Badge ────────────────────────────────────────────────────────────────── */
.ci-badge-featured {
  position: absolute; top: .75rem; right: .75rem;
  background: #2563eb; color: #fff;
  font-size: .65rem; font-weight: 700; padding: .2rem .5rem;
  border-radius: 6px; text-transform: uppercase; letter-spacing: .05em;
}
</style>
