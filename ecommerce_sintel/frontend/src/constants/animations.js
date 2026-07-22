// Tipos de animacion de scroll-reveal compartidos entre ModuleBuilderModal.vue
// (modulos) y HomeConfigView.vue (tarjetas) -- misma fuente de verdad, un solo
// lugar para agregar/quitar variantes.
export const ANIMATIONS = [
  { value: 'none',     icon: 'bi-slash-circle',    label: 'Ninguna' },
  { value: 'fade',     icon: 'bi-eye',             label: 'Fade' },
  { value: 'slide_up', icon: 'bi-arrow-up-circle', label: 'Slide Up' },
  { value: 'zoom',     icon: 'bi-zoom-in',         label: 'Zoom' },
  { value: 'flip',     icon: 'bi-arrow-repeat',    label: 'Flip' },
  { value: 'rotate',   icon: 'bi-arrow-clockwise', label: 'Rotate' },
  { value: 'parallax', icon: 'bi-layers',          label: 'Parallax' },
  { value: 'bounce',   icon: 'bi-activity',        label: 'Bounce' },
];
