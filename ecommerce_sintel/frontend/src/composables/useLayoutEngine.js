/**
 * Layout Engine — mapea configuracion de backend a nombres de componentes Vue.
 * No importa componentes directamente; retorna nombres para <component :is="">.
 */

export const BANNER_LAYOUTS = {
  image:    'HeroBanner',
  carousel: 'CarouselBanner',
  video:    'VideoBanner',
  split:    'SplitBanner',
  promo:    'PromoBanner',
};

export const MODULE_LAYOUTS = {
  grid:      'CardsGrid',
  slider:    'CardsSlider',
  carousel:  'CardsSlider',
  cards_h:   'CardsHorizontal',
  cards_v:   'CardsGrid',
  hero:      'CardsGrid',
  list:      'CardsHorizontal',
  highlight: 'CardsGrid',
};

export const CARD_VARIANTS = {
  vertical:   'CardVertical',
  horizontal: 'CardHorizontal',
  premium:    'CardPremium',
  compact:    'CardCompact',
  glass:      'CardGlass',
  dark:       'CardDark',
  gradient:   'CardGradient',
  image_bg:   'CardImageBg',
};

export const GROUP_LAYOUTS = {
  grid:      'CardsGrid',
  slider:    'CardsSlider',
  cards:     'CardsGrid',
  timeline:  'TimelineSection',
  tabs:      'TabsSection',
  accordion: 'AccordionSection',
  logos:     'LogoStrip',
  marquee:   'MarqueeStrip',
};

export const PADDING_MAP = {
  none:   '0',
  sm:     '2rem 0',
  normal: '4rem 0',
  lg:     '6rem 0',
  xl:     '8rem 0',
};

export function useLayoutEngine() {
  function resolveBannerLayout(banner) {
    if (banner.video) return 'VideoBanner';
    const type = banner.layout_type || 'image';
    return BANNER_LAYOUTS[type] || 'HeroBanner';
  }

  function resolveModuleLayout(module) {
    const type = module.display_type || 'grid';
    return MODULE_LAYOUTS[type] || 'CardsGrid';
  }

  function resolveCardVariant(card) {
    return CARD_VARIANTS[card.card_type || 'vertical'] || 'CardVertical';
  }

  function resolveGroupLayout(group) {
    return GROUP_LAYOUTS[group.layout_type || 'grid'] || 'CardsGrid';
  }

  function resolveGroupPadding(group) {
    return PADDING_MAP[group.padding || 'normal'] || '4rem 0';
  }

  function resolveColumns(group, fallback = 3) {
    return group.columns || fallback;
  }

  function buildSectionStyle(group) {
    const style = { padding: resolveGroupPadding(group) };
    if (group.bg_color) style.background = group.bg_color;
    if (group.bg_image) style.backgroundImage = `url(${group.bg_image})`;
    if (group.glass) {
      style.backdropFilter = 'blur(14px)';
      style.WebkitBackdropFilter = 'blur(14px)';
      if (!group.bg_color) style.background = 'rgba(255,255,255,.55)';
    }
    return style;
  }

  /**
   * Resuelve el estilo de fondo de un HomeModuleConfig.layout_config.background
   * (color/gradient/glass/pattern + overlay). Compartida entre la Vista Previa
   * del Constructor Visual (ModuleBuilderModal) y el render publico (ModuleCard)
   * para que nunca diverjan.
   */
  function resolveModuleBackgroundStyle(layoutConfig) {
    const bg = (layoutConfig && layoutConfig.background) || {};
    const style = {};
    if (bg.type === 'gradient') {
      style.background = `linear-gradient(135deg, ${bg.gradient_from || '#0f172a'}, ${bg.gradient_to || '#1e3a8a'})`;
    } else if (bg.type === 'glass') {
      style.background = bg.color || 'rgba(255,255,255,.12)';
      style.backdropFilter = 'blur(14px)';
      style.WebkitBackdropFilter = 'blur(14px)';
    } else if (bg.color) {
      style.background = bg.color;
    }
    return style;
  }

  function resolveModuleOverlayStyle(layoutConfig) {
    const bg = (layoutConfig && layoutConfig.background) || {};
    if (!bg.overlay) return null;
    const opacity = (bg.overlay_opacity ?? 50) / 100;
    return { background: `rgba(0,0,0,${opacity})` };
  }

  return {
    resolveBannerLayout,
    resolveModuleLayout,
    resolveCardVariant,
    resolveGroupLayout,
    resolveGroupPadding,
    resolveColumns,
    buildSectionStyle,
    resolveModuleBackgroundStyle,
    resolveModuleOverlayStyle,
  };
}
