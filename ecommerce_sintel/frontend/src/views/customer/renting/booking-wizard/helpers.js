/**
 * Helpers puros compartidos entre RentalBookingWizard.vue (shell) y sus 4 pasos.
 *
 * Solo viven aqui las funciones que necesitan MAS DE UN archivo del wizard.
 * Los helpers de un solo paso (money, fileSize, cleanPart) se quedan dentro de
 * su propio componente. La regla es tener UNA sola copia de cada calculo: el
 * riesgo real de esta descomposicion no es el tamano de los archivos, es que
 * dos copias de la misma logica derivada se separen con el tiempo.
 */

export const localISO = (date) => {
  const y = date.getFullYear(),
    m = String(date.getMonth() + 1).padStart(2, '0'),
    d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

export const dateAfter = (days) => {
  const value = new Date();
  value.setHours(12, 0, 0, 0);
  value.setDate(value.getDate() + days);
  return value;
};

export function earliestLabel(days) {
  return dateAfter(days).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
}

export const variantName = (v) =>
  v
    ? Object.values(v.attributes || {}).join(' · ') || 'Configuración estándar'
    : 'Configuración estándar';
