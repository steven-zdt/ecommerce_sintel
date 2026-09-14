/**
 * Helpers puros compartidos entre VariantsTab.vue y CostosTab.vue (ambos
 * muestran precios/valores de reglas usando el mismo formato COP con
 * fallback "-" para null/vacio).
 */
import { formatCOP } from '@/utils/money';

export const formatNum = (val) => {
  if (val == null || val === '') return '—';
  return formatCOP(val);
};
