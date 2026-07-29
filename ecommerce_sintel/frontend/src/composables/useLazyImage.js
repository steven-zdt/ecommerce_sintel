/**
 * Composable para lazy loading de imágenes con IntersectionObserver.
 * Mejora performance: no carga imágenes fuera del viewport.
 */

import { ref, onMounted, onBeforeUnmount } from 'vue';

export function useLazyImage(imgRef, placeholder = null) {
  const src = ref(placeholder || null);
  const isLoaded = ref(false);
  let observer = null;

  onMounted(() => {
    if (!imgRef.value) return;

    const actualSrc = imgRef.value.dataset.src;
    if (!actualSrc) return;

    // Usar IntersectionObserver para lazy loading
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            src.value = actualSrc;
            isLoaded.value = true;
            observer?.unobserve(entry.target);
          }
        });
      },
      {
        rootMargin: '50px', // Cargar 50px antes de que sea visible
        threshold: 0,
      }
    );

    observer.observe(imgRef.value);
  });

  onBeforeUnmount(() => {
    if (observer && imgRef.value) {
      observer.unobserve(imgRef.value);
    }
  });

  return {
    src,
    isLoaded,
  };
}

/**
 * Hook para preload de imágenes críticas (hero image).
 * Las imágenes por encima del fold deben precargarse.
 */
export function usePreloadImage(imageUrl) {
  if (!imageUrl) return;

  if (typeof Image !== 'undefined') {
    const img = new Image();
    img.src = imageUrl;
  }
}

/**
 * Utilidad para generar srcset optimizado.
 * Retorna diferentes tamaños de imagen según el viewport.
 */
export function getSrcSet(baseUrl, sizes = [400, 800, 1200]) {
  if (!baseUrl) return '';
  return sizes
    .map((size) => {
      // Asumir que el backend soporta query param ?width=400
      return `${baseUrl}?width=${size} ${size}w`;
    })
    .join(', ');
}

/**
 * Utilidad para convertir URL de imagen a WebP si es soportado.
 */
export function getOptimizedImageUrl(imageUrl, format = 'webp') {
  if (!imageUrl) return '';

  const isSupported = {
    webp: () => {
      const canvas = document.createElement('canvas');
      canvas.width = 1;
      canvas.height = 1;
      return canvas.toDataURL('image/webp').indexOf('webp') === 5;
    },
  };

  if (format === 'webp' && isSupported.webp()) {
    // Reemplazar extensión o agregar query param
    const url = new URL(imageUrl, window.location.origin);
    url.searchParams.set('format', 'webp');
    return url.toString();
  }

  return imageUrl;
}
