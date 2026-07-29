/**
 * Composable para mejoras de accesibilidad (WCAG 2.1 AA).
 * Proporciona utilidades para ARIA labels, keyboard navigation, etc.
 */

import { ref, computed } from 'vue';

/**
 * Hook para manejar navegación con teclado.
 * Soporta: Tab, Enter, Escape, Arrow keys.
 */
export function useKeyboardNavigation(options = {}) {
  const focusedIndex = ref(0);

  const handleKeyDown = (event, itemsLength) => {
    const { key } = event;
    const handlers = {
      ArrowDown: () => {
        focusedIndex.value = Math.min(focusedIndex.value + 1, itemsLength - 1);
        event.preventDefault();
      },
      ArrowUp: () => {
        focusedIndex.value = Math.max(focusedIndex.value - 1, 0);
        event.preventDefault();
      },
      Home: () => {
        focusedIndex.value = 0;
        event.preventDefault();
      },
      End: () => {
        focusedIndex.value = itemsLength - 1;
        event.preventDefault();
      },
      Escape: () => {
        focusedIndex.value = -1;
        options.onEscape?.();
        event.preventDefault();
      },
      Enter: () => {
        options.onSelect?.(focusedIndex.value);
        event.preventDefault();
      },
    };

    handlers[key]?.();
  };

  return {
    focusedIndex,
    handleKeyDown,
  };
}

/**
 * Genera ARIA labels para elementos complejos.
 */
export function getAriaLabel(config) {
  const parts = [];

  if (config.label) parts.push(config.label);
  if (config.value) parts.push(config.value);
  if (config.status) parts.push(`Estado: ${config.status}`);
  if (config.count) parts.push(`${config.count} elementos`);

  return parts.join(', ');
}

/**
 * Configuración de screen reader anunciable.
 */
export function getAriaLive(level = 'polite') {
  // 'polite' para cambios normales, 'assertive' para urgencia
  return {
    'aria-live': level,
    'aria-atomic': 'true',
  };
}

/**
 * Utilidad para describir rating con palabras.
 */
export function getRatingDescription(rating) {
  const descriptions = {
    5: 'Excelente, 5 estrellas',
    4: 'Muy bueno, 4 estrellas',
    3: 'Promedio, 3 estrellas',
    2: 'Por debajo del promedio, 2 estrellas',
    1: 'Pobre, 1 estrella',
  };
  return descriptions[Math.round(rating)] || 'Sin rating';
}

/**
 * Validar contraste de color (WCAG).
 * Retorna true si el contraste es suficiente (ratio >= 4.5:1).
 */
export function isColorContrastValid(color1, color2) {
  const getLuminance = (hex) => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = (rgb >> 16) & 0xff;
    const g = (rgb >> 8) & 0xff;
    const b = (rgb >> 0) & 0xff;

    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? luminance : luminance * 0.5;
  };

  const l1 = getLuminance(color1);
  const l2 = getLuminance(color2);
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);

  return ratio >= 4.5;
}

/**
 * Generar IDs únicos para aria-labelledby/aria-describedby.
 */
export function generateAriaId(prefix = 'aria') {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}
