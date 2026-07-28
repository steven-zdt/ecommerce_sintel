// QuestionLabelResolver (H3, auditoria E2E 2026-07-23): unica fuente para
// convertir el valor "crudo" de una respuesta de QuoteQuestion en el texto
// que debe verse en pantalla -- usado por el resumen del cliente
// (QuoteSummaryStep.vue) y el visor del asesor (RequestViewer.vue), para
// que un SELECT/RADIO/MULTISELECT/CHECKBOX cuyo option.value difiera de su
// label (ej. tipo_de_inmueble: value='edificio', label='Edificio') se vea
// igual en ambos lugares sin duplicar la logica de resolucion.
//
// El equivalente para el PDF vive en pdf_service.py (_resolve_answer_display)
// -- no se puede compartir codigo JS/Python, pero sigue el mismo criterio.

// GPS: {lat,lng,accuracy} en exito, o el sentinela 'DENIED' si el navegador
// nego/no tiene el permiso (ver DynamicQuestionField.vue).
function formatRawValue(value) {
  if (Array.isArray(value)) return value.join(', ');
  if (value === 'DENIED') return 'No compartida (dirección manual)';
  if (value && typeof value === 'object' && 'lat' in value && 'lng' in value) {
    return `${value.lat.toFixed(5)}, ${value.lng.toFixed(5)}`;
  }
  return String(value);
}

function optionLabelFor(question, rawValue) {
  const option = (question?.options || []).find((o) => String(o.value) === String(rawValue));
  return option ? option.label : String(rawValue);
}

/**
 * Resuelve el valor de una respuesta al texto que debe mostrarse.
 * @param {*} value - valor crudo almacenado en answers[moduleUuid][key]
 * @param {object} [question] - la QuoteQuestion (con .options) para resolver
 *   SELECT/RADIO/MULTISELECT/CHECKBOX a su label. Si se omite (ej. valores
 *   derivados como labor_analysis, que no tienen una QuoteQuestion viva
 *   detras), se aplica solo el formateo generico de abajo.
 */
export function resolveQuestionLabel(value, question) {
  if (value === 'DENIED' || (value && typeof value === 'object' && 'lat' in value)) {
    return formatRawValue(value);
  }
  if (!question) return formatRawValue(value);
  if (Array.isArray(value)) return value.map((v) => optionLabelFor(question, v)).join(', ');
  return optionLabelFor(question, value);
}

// Alias retrocompatible -- codigo existente que solo necesita el formateo
// generico (sin resolver contra options) sigue funcionando igual.
export function formatQuoteAnswerValue(value) {
  return formatRawValue(value);
}
