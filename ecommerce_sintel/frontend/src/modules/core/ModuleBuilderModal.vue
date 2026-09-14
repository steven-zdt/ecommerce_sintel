<template>
  <Teleport to="body">
  <div class="mb-overlay" @click.self="$emit('close')">
    <div class="mb-shell">

      <!-- HEADER -->
      <header class="mb-header">
        <div class="mb-header__info">
          <div class="mb-header__dot" :style="{ background: form.color_primary }"></div>
          <span class="mb-header__title">
            {{ props.module ? 'Editar sección' : 'Nueva sección' }}
            <span v-if="form.custom_label" class="mb-header__name">— {{ form.custom_label }}</span>
          </span>
        </div>
        <button class="mb-close" @click="$emit('close')"><i class="bi bi-x-lg"></i></button>
      </header>

      <!-- TABS -->
      <nav class="mb-tabs">
        <button
          v-for="t in TABS" :key="t.id"
          :class="['mb-tab', activeTab === t.id && 'mb-tab--active']"
          @click="activeTab = t.id"
        >
          <i :class="['bi', t.icon]"></i>
          <span>{{ t.label }}</span>
        </button>
      </nav>

      <!-- BODY -->
      <div class="mb-body">
        <div class="mb-form">

          <!-- Cada pestana es un hijo que muta el mismo objeto reactivo `form`.
               Se mantiene v-show (no v-if) para no re-montar los hijos al cambiar
               de pestana, igual que la version monolitica. -->
          <GeneralTab      v-show="activeTab === 'general'"      :form="form" :is-new="!props.module" />
          <PresentationTab v-show="activeTab === 'presentation'" :form="form" />
          <StyleTab        v-show="activeTab === 'style'"        :form="form" />
          <IconTab         v-show="activeTab === 'icon'"         :form="form" />
          <MediaTab        v-show="activeTab === 'media'"        :form="form" :image-state="imageState" />
          <LayoutTab       v-show="activeTab === 'layout'"       :form="form" />
          <AnimationTab    v-show="activeTab === 'animation'"    :form="form" />
          <ContentTab      v-show="activeTab === 'content'"      :form="form" />
          <ButtonsTab      v-show="activeTab === 'buttons'"      :form="form" />
          <BackgroundTab   v-show="activeTab === 'background'"   :form="form" />
          <ResponsiveTab   v-show="activeTab === 'responsive'"   :form="form" />
          <CarouselTab     v-show="activeTab === 'carousel'"     :form="form" />
          <MultimediaTab   v-show="activeTab === 'multimedia'"   :form="form" />

        </div><!-- /mb-form -->

        <!-- LIVE PREVIEW -->
        <aside class="mb-preview">
          <div class="mb-preview__header">
            <span>Vista previa</span>
            <div class="mb-preview__device-btns">
              <button v-for="d in ['desktop','tablet','mobile']" :key="d"
                :class="['mb-pvd-btn', previewDevice === d && 'active']"
                @click="previewDevice = d"
                :title="d">
                <i :class="pvDeviceIcon(d)"></i>
              </button>
            </div>
          </div>

          <div :class="['mb-preview__frame', `mb-preview__frame--${previewDevice}`]">
            <div class="mb-pv-section" :style="pvSectionStyle">
              <div v-if="form.bg_overlay" class="mb-pv-overlay" :style="{ opacity: form.bg_overlay_opacity / 100 }"></div>
              <div class="mb-pv-inner" :style="{ textAlign: form.text_align }">
                <div v-if="form.custom_icon" class="mb-pv-eyebrow" :style="{ color: form.color_primary }">
                  <i :class="['bi', form.custom_icon]"></i>
                </div>
                <div class="mb-pv-title" :style="{ color: form.color_text, fontSize: `${form.title_size * 0.5}rem`, fontWeight: form.font_weight }">
                  {{ form.custom_label || 'Título de la sección' }}
                </div>
                <div v-if="form.public_subtitle" class="mb-pv-subtitle" :style="{ color: form.color_text, fontSize: `${form.subtitle_size * 0.5}rem`, opacity: 0.7 }">
                  {{ form.public_subtitle }}
                </div>
                <div :class="['mb-pv-layout', `mb-pv-layout--${form.display_type}`]"
                  :style="{ '--pv-cols': pvCols, gap: `${form.gap * 0.5}rem` }">
                  <div v-for="n in pvItemCount" :key="n" class="mb-pv-item">
                    <div v-if="form.show_image" class="mb-pv-item__img"></div>
                    <div class="mb-pv-item__body">
                      <div v-if="form.show_icon" class="mb-pv-item__icon" :style="{ color: form.color_primary }">
                        <i :class="['bi', form.custom_icon || 'bi-star']"></i>
                      </div>
                      <div v-if="form.show_title" class="mb-pv-item__title" :style="{ background: form.color_text + '33' }"></div>
                      <div v-if="form.show_subtitle" class="mb-pv-item__sub" :style="{ background: form.color_text + '22' }"></div>
                      <div v-if="form.show_button" class="mb-pv-item__btn" :style="pvBtnStyle">
                        {{ form.btn_text || 'Ver más' }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <details class="mb-preview__json">
            <summary>JSON config</summary>
            <pre class="mb-preview__code">{{ JSON.stringify(configPayload, null, 2) }}</pre>
          </details>
        </aside>

      </div><!-- /mb-body -->

      <!-- FOOTER -->
      <footer class="mb-footer">
        <div v-if="error" class="mb-error">{{ error }}</div>
        <div class="mb-footer__actions">
          <button class="mb-btn" @click="$emit('close')">Cancelar</button>
          <button class="mb-btn mb-btn--primary" @click="save" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
            {{ props.module ? 'Guardar cambios' : 'Crear sección' }}
          </button>
        </div>
      </footer>

    </div>
  </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import { useLayoutEngine } from '@/composables/useLayoutEngine';

import GeneralTab      from './module-builder/GeneralTab.vue';
import PresentationTab from './module-builder/PresentationTab.vue';
import StyleTab        from './module-builder/StyleTab.vue';
import IconTab         from './module-builder/IconTab.vue';
import MediaTab        from './module-builder/MediaTab.vue';
import LayoutTab       from './module-builder/LayoutTab.vue';
import AnimationTab    from './module-builder/AnimationTab.vue';
import ContentTab      from './module-builder/ContentTab.vue';
import ButtonsTab      from './module-builder/ButtonsTab.vue';
import BackgroundTab   from './module-builder/BackgroundTab.vue';
import ResponsiveTab   from './module-builder/ResponsiveTab.vue';
import CarouselTab     from './module-builder/CarouselTab.vue';
import MultimediaTab   from './module-builder/MultimediaTab.vue';

const { resolveModuleBackgroundStyle } = useLayoutEngine();

const props = defineProps({
  module: { type: Object, default: null },
});
const emit = defineEmits(['close', 'saved']);

const store = useCoreAdminStore();
const toast = useToast();

// ── Tabs ──────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'general',      icon: 'bi-sliders',               label: 'General' },
  { id: 'presentation', icon: 'bi-layout-three-columns',   label: 'Presentación' },
  { id: 'style',        icon: 'bi-palette',               label: 'Estilo' },
  { id: 'icon',         icon: 'bi-star',                  label: 'Icono' },
  { id: 'media',        icon: 'bi-image',                 label: 'Imagen' },
  { id: 'layout',       icon: 'bi-grid-3x3',              label: 'Distribución' },
  { id: 'animation',    icon: 'bi-stars',                 label: 'Animaciones' },
  { id: 'content',      icon: 'bi-toggles',               label: 'Contenido' },
  { id: 'buttons',      icon: 'bi-cursor',                label: 'Botones' },
  { id: 'background',   icon: 'bi-paint-bucket',          label: 'Fondo' },
  { id: 'responsive',   icon: 'bi-tablet',                label: 'Responsive' },
  { id: 'carousel',     icon: 'bi-arrows-move',           label: 'Carrusel' },
  { id: 'multimedia',   icon: 'bi-film',                  label: 'Multimedia' },
];
const activeTab = ref('general');

// ── Form state ────────────────────────────────────────────────────────────────
const DEFAULT_FORM = () => ({
  module_key:           '',
  custom_label:         '',
  public_subtitle:      '',
  description:          '',
  is_visible:           true,
  display_order:        0,
  featured_items_limit: 8,
  display_type:         'grid',
  theme:                'light',
  color_primary:        '#2563eb',
  color_secondary:      '#7c3aed',
  color_text:           '#0f172a',
  color_bg:             '#ffffff',
  title_size:           2,
  subtitle_size:        1,
  font_weight:          '700',
  text_align:           'left',
  custom_icon:          'bi-grid',
  custom_url:           '/',
  columns:              3,
  columns_tablet:       2,
  columns_mobile:       1,
  padding:              'normal',
  gap:                  1,
  min_height:           '',
  max_width:            '',
  animation_type:       'fade',
  animation_duration:   500,
  animation_delay:      0,
  animation_repeat:     false,
  show_image:           true,
  show_icon:            true,
  show_title:           true,
  show_subtitle:        true,
  show_description:     true,
  show_price:           false,
  show_category:        false,
  show_button:          true,
  show_rating:          false,
  show_counter:         false,
  show_tags:            false,
  show_badge:           false,
  badge_text:           'Nuevo',
  badge_color:          '#f59e0b',
  stats:                [],
  btn_text:             'Ver más',
  btn_color:            '#2563eb',
  btn_icon:             'bi-arrow-right',
  btn_position:         'bottom',
  btn_style:            'filled',
  btn_target:           '_self',
  bg_type:              'color',
  bg_color:             '#ffffff',
  bg_gradient_from:     '#0f172a',
  bg_gradient_to:       '#1e3a8a',
  bg_pattern:           'dots',
  bg_overlay:           false,
  bg_overlay_opacity:   50,
  bg_filter:            'none',

  // ── Marketplace Showcase Fase 10 ──
  carousel: {
    items_desktop:   6,
    items_tablet:    3,
    items_mobile:    1.2,
    autoplay:        false,
    loop:            true,
    speed:           40,
    pause_on_hover:  true,
    pause_on_touch:  true,
    pause_on_focus:  true,
    show_arrows:     true,
    show_indicators: true,
  },
  media: {
    type:           'color',
    image:          '',
    video_url:      '',
    video_url_webm: '',
    poster:         '',
    blur:           0,
    glass:          false,
  },
  header: {
    title:      '',
    subtitle:   '',
    description: '',
    cta_text:   '',
    cta_url:    '',
    cta_target: '_self',
  },
  section_background: {
    type:           'none',
    image:          '',
    video_url:      '',
    video_url_webm: '',
    poster:         '',
    parallax:       false,
  },
});

const form = reactive(DEFAULT_FORM());

// ── Media ─────────────────────────────────────────────────────────────────────
// Estado de la subida de imagen de fondo. Vive en el shell porque save() lo
// necesita (multipart) y loadModule() lo repuebla; MediaTab.vue lo muta en sitio.
const imageState = reactive({
  file:     null,   // bgImgFile
  preview:  '',     // bgImgPreview
  remove:   false,  // removeImg
  dragging: false,  // imgDragging
});

// ── Preview ───────────────────────────────────────────────────────────────────
const previewDevice = ref('desktop');

// ── Error / saving ────────────────────────────────────────────────────────────
const saving = ref(false);
const error  = ref('');

// ── Populate from existing module ─────────────────────────────────────────────
function loadModule(mod) {
  const lc   = mod.layout_config  || {};
  const anim = lc.animation       || {};
  const show = lc.show            || {};
  const btn  = lc.button          || {};
  const bg   = lc.background      || {};
  const badge = lc.badge          || {};

  Object.assign(form, DEFAULT_FORM(), {
    module_key:           mod.module_key         || '',
    custom_label:         mod.custom_label        || '',
    public_subtitle:      lc.public_subtitle      || '',
    description:          lc.description          || '',
    is_visible:           mod.is_visible,
    display_order:        mod.display_order        || 0,
    featured_items_limit: mod.featured_items_limit || 8,
    display_type:         mod.display_type         || 'grid',
    theme:                lc.theme                || 'light',
    color_primary:        mod.custom_color        || '#2563eb',
    color_secondary:      lc.color_secondary      || '#7c3aed',
    color_text:           lc.color_text           || '#0f172a',
    color_bg:             lc.color_bg             || '#ffffff',
    title_size:           lc.title_size           || 2,
    subtitle_size:        lc.subtitle_size        || 1,
    font_weight:          lc.font_weight          || '700',
    text_align:           lc.text_align           || 'left',
    custom_icon:          mod.custom_icon         || 'bi-grid',
    custom_url:           mod.custom_url          || '/',
    columns:              lc.columns              || 3,
    columns_tablet:       lc.columns_tablet       || 2,
    columns_mobile:       lc.columns_mobile       || 1,
    padding:              lc.padding              || 'normal',
    gap:                  lc.gap                  || 1,
    min_height:           lc.min_height           || '',
    max_width:            lc.max_width            || '',
    animation_type:       anim.type               || 'fade',
    animation_duration:   anim.duration           || 500,
    animation_delay:      anim.delay              || 0,
    animation_repeat:     anim.repeat             || false,
    show_image:           show.image    !== false,
    show_icon:            show.icon     !== false,
    show_title:           show.title    !== false,
    show_subtitle:        show.subtitle !== false,
    show_description:     show.description !== false,
    show_price:           show.price    === true,
    show_category:        show.category === true,
    show_button:          show.button   !== false,
    show_rating:          show.rating   === true,
    show_counter:         show.counter  === true,
    show_tags:            show.tags     === true,
    show_badge:           show.badge    === true,
    badge_text:           badge.text    || 'Nuevo',
    badge_color:          badge.color   || '#f59e0b',
    stats:                Array.isArray(lc.stats) ? lc.stats.map(s => ({ value: s.value || '', label: s.label || '' })) : [],
    btn_text:             btn.text      || 'Ver más',
    btn_color:            btn.color     || '#2563eb',
    btn_icon:             btn.icon      || 'bi-arrow-right',
    btn_position:         btn.position  || 'bottom',
    btn_style:            btn.style     || 'filled',
    btn_target:           btn.target    || '_self',
    bg_type:              bg.type              || 'color',
    bg_color:             bg.color             || '#ffffff',
    bg_gradient_from:     bg.gradient_from     || '#0f172a',
    bg_gradient_to:       bg.gradient_to       || '#1e3a8a',
    bg_pattern:           bg.pattern           || 'dots',
    bg_overlay:           bg.overlay           || false,
    bg_overlay_opacity:   bg.overlay_opacity   || 50,
    bg_filter:            lc.bg_filter         || 'none',
    carousel:             lc.carousel ? {
      items_desktop:   lc.carousel.items_desktop ?? 6,
      items_tablet:    lc.carousel.items_tablet ?? 3,
      items_mobile:    lc.carousel.items_mobile ?? 1.2,
      autoplay:        lc.carousel.autoplay ?? false,
      loop:            lc.carousel.loop ?? true,
      speed:           lc.carousel.speed ?? 40,
      pause_on_hover:  lc.carousel.pause_on_hover !== false,
      pause_on_touch:  lc.carousel.pause_on_touch !== false,
      pause_on_focus:  lc.carousel.pause_on_focus !== false,
      show_arrows:     lc.carousel.show_arrows !== false,
      show_indicators: lc.carousel.show_indicators !== false,
    } : DEFAULT_FORM().carousel,
    media:                lc.media ? {
      type:           lc.media.type || 'color',
      image:          lc.media.image || '',
      video_url:      lc.media.video_url || '',
      video_url_webm: lc.media.video_url_webm || '',
      poster:         lc.media.poster || '',
      blur:           lc.media.blur || 0,
      glass:          lc.media.glass || false,
    } : DEFAULT_FORM().media,
    header:               lc.header ? {
      title:       lc.header.title || '',
      subtitle:    lc.header.subtitle || '',
      description: lc.header.description || '',
      cta_text:    lc.header.cta_text || '',
      cta_url:     lc.header.cta_url || '',
      cta_target:  lc.header.cta_target || '_self',
    } : DEFAULT_FORM().header,
    section_background:   lc.section_background ? {
      type:           lc.section_background.type || 'none',
      image:          lc.section_background.image || '',
      video_url:      lc.section_background.video_url || '',
      video_url_webm: lc.section_background.video_url_webm || '',
      poster:         lc.section_background.poster || '',
      parallax:       lc.section_background.parallax || false,
    } : DEFAULT_FORM().section_background,
  });

  imageState.preview = mod.background_image || '';
  imageState.remove  = false;
}

watch(() => props.module, (mod) => {
  activeTab.value = 'general';
  if (mod) loadModule(mod);
  else Object.assign(form, DEFAULT_FORM());
}, { immediate: true });

// ── Config payload ────────────────────────────────────────────────────────────
const configPayload = computed(() => ({
  public_subtitle: form.public_subtitle,
  description:     form.description,
  theme:           form.theme,
  color_secondary: form.color_secondary,
  color_text:      form.color_text,
  color_bg:        form.color_bg,
  title_size:      form.title_size,
  subtitle_size:   form.subtitle_size,
  font_weight:     form.font_weight,
  text_align:      form.text_align,
  columns:         form.columns,
  columns_tablet:  form.columns_tablet,
  columns_mobile:  form.columns_mobile,
  padding:         form.padding,
  gap:             form.gap,
  min_height:      form.min_height,
  max_width:       form.max_width,
  bg_filter:       form.bg_filter,
  animation: {
    type:     form.animation_type,
    duration: form.animation_duration,
    delay:    form.animation_delay,
    repeat:   form.animation_repeat,
  },
  show: {
    image: form.show_image, icon: form.show_icon, title: form.show_title,
    subtitle: form.show_subtitle, description: form.show_description,
    price: form.show_price, category: form.show_category, button: form.show_button,
    rating: form.show_rating, counter: form.show_counter, tags: form.show_tags,
    badge: form.show_badge,
  },
  badge: {
    text:  form.badge_text,
    color: form.badge_color,
  },
  stats: form.stats,
  button: {
    text: form.btn_text, color: form.btn_color, icon: form.btn_icon,
    position: form.btn_position, style: form.btn_style, target: form.btn_target,
  },
  background: {
    type:            form.bg_type,
    color:           form.bg_color,
    gradient_from:   form.bg_gradient_from,
    gradient_to:     form.bg_gradient_to,
    pattern:         form.bg_pattern,
    overlay:         form.bg_overlay,
    overlay_opacity: form.bg_overlay_opacity,
  },
  carousel:        form.carousel,
  media:           form.media,
  header:          form.header,
  section_background: form.section_background,
}));

// ── Preview computed ──────────────────────────────────────────────────────────
const pvSectionStyle = computed(() => {
  const bgStyle = resolveModuleBackgroundStyle({
    background: {
      type: form.bg_type, color: form.bg_color,
      gradient_from: form.bg_gradient_from, gradient_to: form.bg_gradient_to,
    },
  });
  return {
    background: bgStyle.background || '#f8fafc',
    backdropFilter: bgStyle.backdropFilter,
    padding: '0.75rem', borderRadius: '8px', position: 'relative', overflow: 'hidden', minHeight: '100px',
  };
});

const pvCols = computed(() => {
  if (previewDevice.value === 'mobile') return form.columns_mobile;
  if (previewDevice.value === 'tablet') return form.columns_tablet;
  return Math.min(form.columns, 4);
});

const pvItemCount = computed(() => Math.min(pvCols.value * 2, 6));

const pvBtnStyle = computed(() => {
  if (form.btn_style === 'outline') {
    return { border: `1px solid ${form.btn_color}`, color: form.btn_color, background: 'transparent', borderRadius: '3px', padding: '1px 6px', fontSize: '0.55rem', display: 'inline-block', marginTop: '3px' };
  }
  return { background: form.btn_color, color: '#fff', borderRadius: '3px', padding: '1px 6px', fontSize: '0.55rem', display: 'inline-block', marginTop: '3px' };
});

function pvDeviceIcon(d) {
  return d === 'desktop' ? 'bi bi-display' : d === 'tablet' ? 'bi bi-tablet' : 'bi bi-phone';
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function save() {
  if (!props.module && !form.module_key.trim()) {
    error.value = 'La clave interna es requerida.'; return;
  }
  if (!form.custom_label.trim()) {
    error.value = 'El nombre del módulo es requerido.'; return;
  }
  saving.value = true; error.value = '';

  const useMultipart = !!imageState.file || imageState.remove;
  let payload;

  if (useMultipart) {
    const fd = new FormData();
    fd.append('custom_label',         form.custom_label);
    fd.append('custom_icon',          form.custom_icon);
    fd.append('custom_url',           form.custom_url);
    fd.append('custom_color',         form.color_primary);
    fd.append('is_visible',           form.is_visible);
    fd.append('display_order',        form.display_order);
    fd.append('featured_items_limit', form.featured_items_limit);
    fd.append('display_type',         form.display_type);
    fd.append('layout_config',        JSON.stringify(configPayload.value));
    if (!props.module) fd.append('module_key', form.module_key);
    if (imageState.file) fd.append('background_image', imageState.file);
    if (imageState.remove) fd.append('remove_background_image', 'true');
    payload = fd;
  } else {
    payload = {
      custom_label:         form.custom_label,
      custom_icon:          form.custom_icon,
      custom_url:           form.custom_url,
      custom_color:         form.color_primary,
      is_visible:           form.is_visible,
      display_order:        form.display_order,
      featured_items_limit: form.featured_items_limit,
      display_type:         form.display_type,
      layout_config:        configPayload.value,
    };
    if (!props.module) payload.module_key = form.module_key;
  }

  const res = props.module
    ? await store.updateModule(props.module.uuid, payload)
    : await store.createModule(payload);

  if (res.ok) {
    toast.success(props.module ? 'Sección actualizada.' : 'Sección creada.');
    emit('saved', res.data);
  } else {
    const detail = res.error?.response?.data;
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Error al guardar.';
  }
  saving.value = false;
}
</script>

<style scoped>
/* ── Overlay & Shell ─────────────────────────────────────────────────────── */
.mb-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.6);
  backdrop-filter: blur(4px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mb-shell {
  width: 95vw;
  max-width: 1280px;
  height: 90vh;
  background: #ffffff;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 32px 80px rgba(0,0,0,.35);
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.mb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}
.mb-header__info { display: flex; align-items: center; gap: 0.6rem; }
.mb-header__dot  { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.mb-header__title { font-size: 0.9rem; font-weight: 600; color: #1e293b; }
.mb-header__name  { color: #64748b; font-weight: 400; }
.mb-close {
  background: none; border: none; padding: 0.35rem 0.5rem;
  border-radius: 6px; color: #64748b; cursor: pointer; font-size: 1rem;
  transition: background .15s, color .15s;
}
.mb-close:hover { background: #fee2e2; color: #dc2626; }

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.mb-tabs {
  display: flex;
  gap: 2px;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  overflow-x: auto;
  flex-shrink: 0;
  scrollbar-width: none;
}
.mb-tabs::-webkit-scrollbar { display: none; }
.mb-tab {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.38rem 0.75rem;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
  transition: background .15s, color .15s;
}
.mb-tab:hover  { background: #e2e8f0; color: #334155; }
.mb-tab--active { background: #eff6ff; color: #2563eb; font-weight: 600; }

/* ── Body ────────────────────────────────────────────────────────────────── */
.mb-body {
  display: grid;
  grid-template-columns: 1fr 300px;
  flex: 1;
  overflow: hidden;
}

/* ── Form area ───────────────────────────────────────────────────────────── */
.mb-form {
  overflow-y: auto;
  padding: 1.25rem;
  border-right: 1px solid #e2e8f0;
}

/* ── Preview panel ───────────────────────────────────────────────────────── */
.mb-preview {
  display: flex;
  flex-direction: column;
  background: #f1f5f9;
  overflow-y: auto;
}
.mb-preview__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.85rem;
  background: #e2e8f0;
  font-size: 0.75rem;
  font-weight: 600;
  color: #475569;
  flex-shrink: 0;
}
.mb-preview__device-btns { display: flex; gap: 4px; }
.mb-pvd-btn {
  padding: 0.2rem 0.4rem; border: 1px solid #cbd5e1; border-radius: 5px;
  background: none; cursor: pointer; color: #64748b; font-size: 0.75rem;
  transition: background .12s;
}
.mb-pvd-btn:hover  { background: #fff; }
.mb-pvd-btn.active { background: #fff; border-color: #2563eb; color: #2563eb; }

.mb-preview__frame {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}
.mb-preview__frame--desktop { align-items: flex-start; }
.mb-preview__frame--tablet  { max-width: 260px; margin: 0 auto; }
.mb-preview__frame--mobile  { max-width: 180px; margin: 0 auto; }

.mb-pv-section {
  width: 100%;
  min-height: 90px;
}
.mb-pv-overlay {
  position: absolute;
  inset: 0;
  background: #000;
  pointer-events: none;
}
.mb-pv-inner { position: relative; z-index: 1; }
.mb-pv-eyebrow { font-size: 0.7rem; margin-bottom: 0.3rem; }
.mb-pv-title   { font-size: 1rem; margin-bottom: 0.15rem; }
.mb-pv-subtitle { font-size: 0.65rem; margin-bottom: 0.4rem; }

.mb-pv-layout {
  display: grid;
  grid-template-columns: repeat(var(--pv-cols, 3), 1fr);
  gap: 0.4rem;
  margin-top: 0.5rem;
}
.mb-pv-layout--list,
.mb-pv-layout--timeline,
.mb-pv-layout--accordion { grid-template-columns: 1fr; }
.mb-pv-layout--carousel,
.mb-pv-layout--slider,
.mb-pv-layout--banner     { grid-template-columns: 1fr; }
.mb-pv-layout--split      { grid-template-columns: 1fr 1fr; }
.mb-pv-layout--minimal    { grid-template-columns: 1fr; }

.mb-pv-item {
  background: rgba(255,255,255,.15);
  border-radius: 5px;
  padding: 5px;
  min-height: 30px;
}
.mb-pv-item__img   { height: 28px; background: rgba(0,0,0,.12); border-radius: 3px; margin-bottom: 4px; }
.mb-pv-item__body  { display: flex; flex-direction: column; gap: 2px; }
.mb-pv-item__icon  { font-size: 0.7rem; }
.mb-pv-item__title { height: 6px; border-radius: 2px; }
.mb-pv-item__sub   { height: 4px; border-radius: 2px; width: 70%; }

.mb-preview__json {
  margin: 0;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}
.mb-preview__json summary {
  padding: 0.5rem 0.85rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  user-select: none;
}
.mb-preview__code {
  padding: 0.5rem 0.85rem;
  font-size: 0.62rem;
  color: #334155;
  margin: 0;
  max-height: 180px;
  overflow-y: auto;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.mb-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
  gap: 1rem;
}
.mb-footer__actions { display: flex; gap: 0.6rem; margin-left: auto; }
.mb-error   { font-size: 0.78rem; color: #dc2626; background: #fee2e2; padding: 0.35rem 0.75rem; border-radius: 6px; }
.mb-btn {
  padding: 0.45rem 1.1rem; border: 1px solid #d1d5db; border-radius: 7px;
  background: #fff; font-size: 0.82rem; font-weight: 500; color: #374151;
  cursor: pointer; transition: background .15s;
}
.mb-btn:hover         { background: #f1f5f9; }
.mb-btn--primary      { background: #2563eb; border-color: #2563eb; color: #fff; }
.mb-btn--primary:hover { background: #1d4ed8; }
.mb-btn--primary:disabled { opacity: .6; cursor: not-allowed; }
</style>
