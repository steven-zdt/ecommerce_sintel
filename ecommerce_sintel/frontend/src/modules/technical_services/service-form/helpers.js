/**
 * Helpers puros compartidos entre ServiceForm.vue (shell) y sus tabs.
 *
 * Solo vive aqui lo que necesita MAS DE UN archivo del formulario. Los
 * helpers de un solo tab (formatNum, formatDate) se quedan dentro de su
 * propio componente -- la regla es una sola copia de cada calculo.
 */

// Usado por VariantsTab (crear/editar/duplicar variante) y CostosTab
// (payload de cotizacion) -- ambos envian numeros "" -> null al backend.
export const cleanNum = (val) => {
  if (val === '' || val === null || val === undefined) return null;
  if (typeof val === 'number' && Number.isNaN(val)) return null;
  return val;
};
