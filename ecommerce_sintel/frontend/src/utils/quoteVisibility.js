/**
 * Visibilidad condicional de preguntas de Quotes (Fase F,
 * PLAN_MAESTRO_QUOTES_UX.md). Funcion pura, compartida entre el wizard
 * publico (/cotizar) y la vista previa del admin (PreviewTemplate.vue) para
 * no duplicar la logica en 2 lugares -- ver DynamicQuestionField.vue, que ya
 * sigue este mismo criterio de componente compartido.
 *
 * Alcance deliberadamente acotado: solo decide mostrar/ocultar una
 * pregunta. Nunca calcula precio, mano de obra ni cantidades -- eso sigue
 * fuera de alcance por decision de negocio (ver "Fuera de alcance" en
 * ARQUITECTURA_COMPLETA_QUOTES.md).
 */

/**
 * @param {object} question - una entrada de module.questions (incluye
 *   is_visible, depends_on_question_key, depends_on_values)
 * @param {object} moduleAnswers - answers[moduleUuid], mapa key -> valor
 * @returns {boolean}
 */
export function isQuestionVisible(question, moduleAnswers) {
  if (!question.is_visible) return false;
  if (!question.depends_on_question_key) return true;

  const parentValue = moduleAnswers?.[question.depends_on_question_key];
  if (parentValue === undefined || parentValue === null || parentValue === '') return false;

  const triggerValues = question.depends_on_values || [];
  if (Array.isArray(parentValue)) {
    // MULTISELECT/CHECKBOX: visible si alguna respuesta coincide con algun valor disparador.
    return parentValue.some((v) => triggerValues.includes(String(v)));
  }
  return triggerValues.includes(String(parentValue));
}
