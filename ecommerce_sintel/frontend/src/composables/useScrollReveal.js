import { ref, onMounted, onBeforeUnmount } from 'vue';

/**
 * Observa un elemento y expone `visible` cuando entra en el viewport.
 * Unico punto de IntersectionObserver reutilizado por landing/home components
 * (evita duplicar el mismo patron en cada componente).
 */
export function useScrollReveal({ threshold = 0.08, once = true } = {}) {
  const el = ref(null);
  const visible = ref(false);
  let observer = null;

  onMounted(() => {
    observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          visible.value = true;
          if (once) observer.disconnect();
        } else if (!once) {
          visible.value = false;
        }
      },
      { threshold }
    );
    if (el.value) observer.observe(el.value);
  });

  onBeforeUnmount(() => observer?.disconnect());

  return { el, visible };
}

const ANIMATION_CLASS = {
  none:     '',
  fade:     'sr-fade',
  slide_up: 'sr-slide-up',
  zoom:     'sr-zoom',
  flip:     'sr-flip',
  rotate:   'sr-rotate',
  parallax: 'sr-parallax',
  bounce:   'sr-bounce',
};

/** Resuelve la clase CSS de reveal para un tipo de animacion del layout_config. */
export function resolveRevealClass(type) {
  return ANIMATION_CLASS[type] ?? ANIMATION_CLASS.fade;
}
