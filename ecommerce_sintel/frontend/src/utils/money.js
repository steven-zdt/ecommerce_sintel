/**
 * Utilidad centralizada de formato de moneda (COP, es-CO).
 *
 * Reemplaza las ~120 instanciaciones inline de `Intl.NumberFormat('es-CO', ...)`
 * repartidas por el proyecto (auditoria 2026-07-23, AUDITORIA/13_AUDITORIA_FRONTEND_UI_2026-07-23.md).
 * Los formatters se crean una sola vez a nivel de modulo (no en cada render).
 */

const PLAIN_FORMATTER = new Intl.NumberFormat('es-CO');
const CURRENCY_FORMATTER = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
});

/**
 * Formatea un valor numerico como moneda colombiana.
 * `value` puede ser number, string numerico, null o undefined -- valores no
 * numericos caen a 0 (mismo comportamiento que `parseFloat(val) || 0`, el
 * patron mas comun encontrado en la auditoria).
 *
 * @param {number|string|null|undefined} value
 * @param {{ withSymbol?: boolean, decimals?: number }} [options]
 * @returns {string}
 */
export function formatCOP(value, { withSymbol = false, decimals } = {}) {
  const num = Number(value);
  const safeNum = Number.isFinite(num) ? num : 0;

  if (decimals !== undefined) {
    return new Intl.NumberFormat('es-CO', {
      style: withSymbol ? 'currency' : 'decimal',
      currency: withSymbol ? 'COP' : undefined,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(safeNum);
  }

  return withSymbol ? CURRENCY_FORMATTER.format(safeNum) : PLAIN_FORMATTER.format(safeNum);
}
