// Extraccion del mensaje de error al enviar una cotizacion (DRF field errors
// -> primer mensaje util). Compartido entre useQuoteWizard.js y
// useCatalogQuoteWizard.js, que antes tenian este mismo bloque copiado
// (DUP-F7): ambos wizards divergen en el resto de su estado/logica lo
// suficiente como para no justificar un useWizardBase.js generico, pero
// este extracto puntual de manejo de errores si era una duplicacion real.
export function extractQuoteSubmitError(e, fallback = 'No pudimos enviar tu solicitud. Intenta de nuevo.') {
  const fieldErrors = e.response?.data;
  const firstFieldError = fieldErrors && typeof fieldErrors === 'object'
    ? Object.values(fieldErrors).flat()[0]
    : null;
  return fieldErrors?.detail || firstFieldError || fallback;
}
